#!/usr/bin/env python3
"""Build a validated, immutable RollPig resource-source release directory."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from PIL import Image


CLIENT_ID = "astrbot_plugin_rollpig_plus"
PROTOCOL_VERSION = 1
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGES = 500
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


def _load_images(source_root: Path, pig_ids: set[str]) -> dict[str, Path]:
    image_root = source_root / "image"
    if not image_root.is_dir():
        raise ValueError("缺少 resource/image 目錄")
    images: dict[str, Path] = {}
    for path in sorted(image_root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if path.is_symlink():
            raise ValueError(f"資源圖片不能是符號連結：{path.name}")
        pig_id = path.stem
        if pig_id in images:
            raise ValueError(f"同一 ID 存在多張圖片：{pig_id}")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError(f"圖片超過 10 MiB：{path.name}")
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
        except Exception as exc:
            raise ValueError(f"圖片無法解碼：{path.name}") from exc
        if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
            raise ValueError(f"圖片像素超過安全上限：{path.name}")
        images[pig_id] = path
    missing = pig_ids.difference(images)
    extras = set(images).difference(pig_ids)
    if missing:
        raise ValueError(f"缺少圖片：{', '.join(sorted(missing)[:10])}")
    if extras:
        raise ValueError(f"存在無對應資料的圖片：{', '.join(sorted(extras)[:10])}")
    return images


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
    images = _load_images(source_root, {item["id"] for item in records})
    stamp = generated_at or dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
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
            size = target.stat().st_size
            total_bytes += size
            image_entries.append(
                {
                    "filename": target.name,
                    "path": f"images/{target.name}",
                    "size": size,
                    "sha256": _sha256(target),
                }
            )
        manifest = {
            "schema_version": PROTOCOL_VERSION,
            "client": CLIENT_ID,
            "resource_version": resource_version,
            "generated_at": stamp,
            "pig_count": len(records),
            "package_size": total_bytes,
            "pig_json": {
                "path": "pig.json",
                "size": pig_path.stat().st_size,
                "sha256": _sha256(pig_path),
            },
            "images": image_entries,
        }
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
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
