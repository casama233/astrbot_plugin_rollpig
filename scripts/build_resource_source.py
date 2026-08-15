#!/usr/bin/env python3
"""Build a validated, immutable RollPig resource-source release directory."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ex_variants import (
    build_effective_ex_variants,
    serialize_ex_variants,
    validate_ex_variants,
)


CLIENT_ID = "astrbot_plugin_rollpig_plus"
PROTOCOL_VERSION = 1
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGES = 500
MAX_VARIANT_IMAGES = 1000
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
VERSION_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_catalog(source_root: Path) -> list[dict]:
    catalog_path = source_root / "pig.json"
    try:
        records = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取 pig.json：{exc}") from exc
    if not isinstance(records, list) or not records:
        raise ValueError("pig.json 必須是非空陣列")
    if len(records) > MAX_IMAGES:
        raise ValueError(f"小豬數量超過 {MAX_IMAGES}")
    seen: set[str] = set()
    normalized: list[dict] = []
    for raw in records:
        if not isinstance(raw, dict):
            raise ValueError("pig.json 含非物件記錄")
        item = dict(raw)
        pig_id = str(item.get("id") or "").strip()
        if not ID_PATTERN.fullmatch(pig_id):
            raise ValueError(f"小豬 ID 無效：{pig_id}")
        if pig_id in seen:
            raise ValueError(f"小豬 ID 重複：{pig_id}")
        for key in ("name", "description", "analysis"):
            if not str(item.get(key) or "").strip():
                raise ValueError(f"{pig_id} 缺少 {key}")
        item["id"] = pig_id
        seen.add(pig_id)
        normalized.append(item)
    return normalized


def _validate_image(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"資源圖片不能是符號連結：{label}")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError(f"圖片超過 10 MiB：{label}")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except Exception as exc:
        raise ValueError(f"圖片無法解碼：{label}") from exc
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise ValueError(f"圖片像素超過安全上限：{label}")


def _load_images(source_root: Path, pig_ids: set[str]) -> dict[str, Path]:
    image_root = source_root / "image"
    if not image_root.is_dir():
        raise ValueError("缺少 resource/image 目錄")
    images: dict[str, Path] = {}
    for path in sorted(image_root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        pig_id = path.stem
        if pig_id in images:
            raise ValueError(f"同一 ID 存在多張圖片：{pig_id}")
        _validate_image(path, path.name)
        images[pig_id] = path
    missing = pig_ids.difference(images)
    extras = set(images).difference(pig_ids)
    if missing:
        raise ValueError(f"缺少圖片：{', '.join(sorted(missing)[:10])}")
    if extras:
        raise ValueError(f"存在無對應資料的圖片：{', '.join(sorted(extras)[:10])}")
    return images


def _read_variant_document(
    path: Path,
    pig_ids: set[str],
    *,
    allow_foreign_ids: bool = False,
) -> dict[str, dict[int, dict[str, str]]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取 {path.name}：{exc}") from exc
    if allow_foreign_ids:
        if not isinstance(raw, dict):
            raise ValueError(f"{path.name} 必須是 JSON 物件")
        raw_pigs = raw.get("pigs", {})
        if not isinstance(raw_pigs, dict):
            raise ValueError(f"{path.name} pigs 必須是物件")
        raw = {
            "schema_version": raw.get("schema_version", 1),
            "pigs": {
                str(pig_id): levels
                for pig_id, levels in raw_pigs.items()
                if str(pig_id) in pig_ids
            },
        }
        if not raw["pigs"]:
            return {}
    return validate_ex_variants(
        raw,
        pig_ids,
        image_extensions={item.lstrip(".") for item in IMAGE_EXTENSIONS},
    )


def _load_explicit_ex_authoring(
    source_root: Path,
    pig_ids: set[str],
) -> dict[str, dict[int, dict[str, str]]]:
    """Merge the base EX document and optional curated authoring packs."""
    explicit: dict[str, dict[int, dict[str, str]]] = {}
    variants_path = source_root / "pig_ex_variants.json"
    if variants_path.exists():
        explicit.update(_read_variant_document(variants_path, pig_ids))

    curated_root = source_root / "ex_curated"
    if curated_root.is_dir():
        for pack in sorted(curated_root.glob("*.json")):
            variants = _read_variant_document(
                pack,
                pig_ids,
                allow_foreign_ids=True,
            )
            duplicates = set(explicit).intersection(variants)
            if duplicates:
                raise ValueError(
                    f"EX authoring 重复小猪（{pack.name}）："
                    + ", ".join(sorted(duplicates))
                )
            explicit.update(variants)
    return explicit


def _load_ex_variants(
    source_root: Path, records: list[dict]
) -> tuple[dict, dict[str, Path]]:
    pig_ids = {str(item["id"]) for item in records}
    explicit = _load_explicit_ex_authoring(source_root, pig_ids)

    # Materialize one canonical Resource Protocol document. Official releases
    # are gated separately to require explicit curated EX1-EX5 copy for every
    # official ID; the deterministic baseline remains only a safety fallback for
    # generic fixtures, local content and future non-official catalogs.
    effective = build_effective_ex_variants(records, explicit)
    canonical = serialize_ex_variants(effective)
    declared = {
        str(item.get("image") or "")
        for levels in effective.values()
        for item in levels.values()
        if str(item.get("image") or "")
    }
    if len(declared) > MAX_VARIANT_IMAGES:
        raise ValueError(f"EX 差分圖片數量超過 {MAX_VARIANT_IMAGES}")
    image_root = source_root / "ex_variants"
    if declared and not image_root.is_dir():
        raise ValueError("EX 差分宣告了圖片，但缺少 resource/ex_variants 目錄")
    found: dict[str, Path] = {}
    if image_root.is_dir():
        for path in sorted(image_root.iterdir()):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if path.name in found:
                raise ValueError(f"EX 差分圖片重複：{path.name}")
            _validate_image(path, f"ex_variants/{path.name}")
            found[path.name] = path
    missing = declared.difference(found)
    extras = set(found).difference(declared)
    if missing:
        raise ValueError(f"缺少 EX 差分圖片：{', '.join(sorted(missing)[:10])}")
    if extras:
        raise ValueError(f"存在未被引用的 EX 差分圖片：{', '.join(sorted(extras)[:10])}")
    return canonical, found


def _file_entry(path: Path, relative: str, *, filename: str | None = None) -> dict:
    return {
        **({"filename": filename} if filename is not None else {}),
        "path": relative,
        "size": path.stat().st_size,
        "sha256": _sha256(path),
    }


def build_source(
    source_root: Path,
    output: Path,
    resource_version: str,
    generated_at: str | None = None,
) -> dict:
    """Validate source assets and atomically create one publishable directory."""
    source_root = source_root.resolve()
    output = output.resolve()
    if not VERSION_PATTERN.fullmatch(resource_version):
        raise ValueError("resource version 只允許英數、點、底線與連字號")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"輸出目錄已存在：{output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    records = _load_catalog(source_root)
    pig_ids = {item["id"] for item in records}
    images = _load_images(source_root, pig_ids)
    ex_bundle = _load_ex_variants(source_root, records)
    stamp = (
        generated_at
        or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    )
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent))
    )
    try:
        image_output = staging / "images"
        image_output.mkdir()
        pig_path = staging / "pig.json"
        pig_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        image_entries: list[dict] = []
        total_bytes = pig_path.stat().st_size
        for pig_id in sorted(images):
            source = images[pig_id]
            target = image_output / f"{pig_id}{source.suffix.lower()}"
            shutil.copyfile(source, target)
            total_bytes += target.stat().st_size
            image_entries.append(
                _file_entry(target, f"images/{target.name}", filename=target.name)
            )

        manifest = {
            "schema_version": PROTOCOL_VERSION,
            "client": CLIENT_ID,
            "resource_version": resource_version,
            "generated_at": stamp,
            "pig_count": len(records),
            "package_size": 0,
            "pig_json": _file_entry(pig_path, "pig.json"),
            "images": image_entries,
        }

        canonical, variant_images = ex_bundle
        variant_pig_count = len(canonical.get("pigs", {}))
        if variant_pig_count != len(records):
            raise AssertionError("EX 五級文案未覆蓋完整 catalog")
        variant_output = staging / "ex_variants"
        variant_output.mkdir()
        ex_path = staging / "pig_ex_variants.json"
        ex_path.write_text(
            json.dumps(canonical, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        total_bytes += ex_path.stat().st_size
        variant_entries: list[dict] = []
        for filename in sorted(variant_images):
            source = variant_images[filename]
            target = variant_output / filename
            shutil.copyfile(source, target)
            total_bytes += target.stat().st_size
            variant_entries.append(
                _file_entry(
                    target,
                    f"ex_variants/{filename}",
                    filename=filename,
                )
            )
        variant_image_count = len(variant_entries)
        manifest["ex_variants"] = _file_entry(ex_path, "pig_ex_variants.json")
        manifest["variant_images"] = variant_entries
        manifest["ex_variant_pig_count"] = variant_pig_count

        manifest["package_size"] = total_bytes
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        health = {
            "status": "ok",
            "client": CLIENT_ID,
            "protocol_version": PROTOCOL_VERSION,
            "resource_version": resource_version,
            "generated_at": stamp,
            "pig_count": len(records),
            "package_size": total_bytes,
            "ex_variant_pig_count": variant_pig_count,
            "ex_variant_image_count": variant_image_count,
        }
        (staging / "health.json").write_text(
            json.dumps(health, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        staging.rename(output)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("resource"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--generated-at")
    args = parser.parse_args()
    manifest = build_source(
        args.source,
        args.output,
        args.version,
        generated_at=args.generated_at,
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "resource_version": manifest["resource_version"],
                "pig_count": manifest["pig_count"],
                "package_size": manifest["package_size"],
                "ex_variant_pig_count": manifest["ex_variant_pig_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
