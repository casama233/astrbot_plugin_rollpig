#!/usr/bin/env python3
"""Historical RollPig catalog merge helper retained for provenance auditing.

The pre-v3.4 external Felis compatibility snapshot is no longer a publishable
source.  Production/public publishing must use independently verified provenance
instead.  This module keeps the generic merge machinery for local fixtures and
forensic comparison, while failing closed for the historical external snapshot
unless a caller explicitly opts into audit-only processing in code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


@dataclass(frozen=True)
class CompatibilitySpec:
    repository: str
    commit: str
    resource_version: str
    pig_json_sha256: str
    sentinel_ids: tuple[str, ...] = ()


LEGACY_COMPATIBILITY = CompatibilitySpec(
    repository="Felis2026/rollpig-resources",
    commit="17ac1586a91c33995883803a55e2f755047f6e1f",
    resource_version="2026-08-10.1",
    pig_json_sha256="687a491e541869cf1ef4f495e9189cf358a0d68655d1f780395a482113bc8be8",
    sentinel_ids=("miku-pig", "wechat-pig", "duke-pig"),
)

COMPATIBILITY_FLOOR_FILENAME = "compatibility_floor.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_records(root: Path) -> list[dict]:
    path = root / "pig.json"
    try:
        records = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取 {path}: {exc}") from exc
    if not isinstance(records, list) or not records:
        raise ValueError(f"{path} 必須是非空陣列")
    seen: set[str] = set()
    normalized: list[dict] = []
    for raw in records:
        if not isinstance(raw, dict):
            raise ValueError(f"{path} 含非物件記錄")
        item = dict(raw)
        pig_id = str(item.get("id") or "").strip()
        if not pig_id:
            raise ValueError(f"{path} 含空白小豬 ID")
        if pig_id in seen:
            raise ValueError(f"{path} 小豬 ID 重複：{pig_id}")
        seen.add(pig_id)
        item["id"] = pig_id
        normalized.append(item)
    return normalized


def _image_root(root: Path) -> Path:
    for name in ("image", "images"):
        candidate = root / name
        if candidate.is_dir():
            return candidate
    raise ValueError(f"{root} 缺少 image/ 或 images/ 目錄")


def _image_map(root: Path) -> dict[str, Path]:
    images: dict[str, Path] = {}
    for path in sorted(_image_root(root).iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        pig_id = path.stem
        if pig_id in images:
            raise ValueError(f"{root} 同一 ID 存在多張圖片：{pig_id}")
        images[pig_id] = path
    return images


def _verify_snapshot(
    root: Path,
    spec: CompatibilitySpec,
) -> tuple[list[dict], dict[str, Path]]:
    manifest_path = root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取固定兼容 manifest：{exc}") from exc
    if str(manifest.get("resource_version") or "") != spec.resource_version:
        raise ValueError(
            "兼容快照 resource_version 不符："
            f"預期 {spec.resource_version}，實際 {manifest.get('resource_version')}"
        )
    pig_json = root / "pig.json"
    digest = _sha256(pig_json)
    if digest != spec.pig_json_sha256:
        raise ValueError(
            "兼容快照 pig.json 指紋不符；拒絕用可變或錯誤來源建立官方豬源"
        )
    records = _load_records(root)
    images = _image_map(root)
    ids = {str(item["id"]) for item in records}
    missing_images = ids.difference(images)
    if missing_images:
        raise ValueError(
            "固定兼容快照缺圖：" + ", ".join(sorted(missing_images)[:10])
        )
    missing_sentinels = set(spec.sentinel_ids).difference(ids)
    if missing_sentinels:
        raise ValueError(
            "固定兼容快照缺少哨兵 ID：" + ", ".join(sorted(missing_sentinels))
        )
    return records, images


def _copy_primary_extras(primary_root: Path, output: Path) -> None:
    variants = primary_root / "pig_ex_variants.json"
    if variants.is_file():
        shutil.copyfile(variants, output / variants.name)
    variant_images = primary_root / "ex_variants"
    if variant_images.is_dir():
        shutil.copytree(variant_images, output / "ex_variants")
    curated_packs = primary_root / "ex_curated"
    if curated_packs.is_dir():
        shutil.copytree(curated_packs, output / "ex_curated")


def merge_catalog(
    primary_root: Path,
    compatibility_root: Path,
    output: Path,
    *,
    spec: CompatibilitySpec | None = LEGACY_COMPATIBILITY,
    allow_unverified_external_compat: bool = False,
) -> dict:
    """Create a merged catalog for fixtures/audit without mutating inputs.

    The historical Felis snapshot is explicitly blocked by default because its
    redistribution rights are not established for current publishing.  The
    opt-in exists only so maintainers can reproduce historical restored-ID sets
    in an isolated audit environment; callers must not publish that output.
    """
    if spec == LEGACY_COMPATIBILITY and not allow_unverified_external_compat:
        raise PermissionError(
            "historical Felis compatibility floor is quarantined; "
            "publishing/automatic redistribution is disabled"
        )

    primary_root = primary_root.resolve()
    compatibility_root = compatibility_root.resolve()
    output = output.resolve()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"輸出目錄已存在：{output}")

    primary_records = _load_records(primary_root)
    primary_images = _image_map(primary_root)
    primary_ids = {str(item["id"]) for item in primary_records}
    missing_primary_images = primary_ids.difference(primary_images)
    if missing_primary_images:
        raise ValueError(
            "目前 AstrBot catalog 缺圖："
            + ", ".join(sorted(missing_primary_images)[:10])
        )

    if spec is None:
        compatibility_records = _load_records(compatibility_root)
        compatibility_images = _image_map(compatibility_root)
    else:
        compatibility_records, compatibility_images = _verify_snapshot(
            compatibility_root, spec
        )
    compatibility_ids = {str(item["id"]) for item in compatibility_records}
    missing_compat_images = compatibility_ids.difference(compatibility_images)
    if missing_compat_images:
        raise ValueError(
            "兼容 catalog 缺圖：" + ", ".join(sorted(missing_compat_images)[:10])
        )

    primary_by_id = {str(item["id"]): item for item in primary_records}
    merged_records: list[dict] = []
    for item in compatibility_records:
        pig_id = str(item["id"])
        merged_records.append(dict(primary_by_id.get(pig_id, item)))
    for item in primary_records:
        if str(item["id"]) not in compatibility_ids:
            merged_records.append(dict(item))

    output.mkdir(parents=True)
    output_images = output / "image"
    output_images.mkdir()
    for item in merged_records:
        pig_id = str(item["id"])
        source = primary_images.get(pig_id) or compatibility_images.get(pig_id)
        if source is None:
            raise ValueError(f"合併後缺少圖片：{pig_id}")
        target = output_images / f"{pig_id}{source.suffix.lower()}"
        shutil.copyfile(source, target)

    (output / "pig.json").write_text(
        json.dumps(merged_records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _copy_primary_extras(primary_root, output)

    floor = {
        "schema_version": 1,
        "policy": "audit-only-compatibility-floor",
        "source_repository": spec.repository if spec else "test-fixture",
        "source_commit": spec.commit if spec else "",
        "source_resource_version": spec.resource_version if spec else "",
        "source_pig_json_sha256": spec.pig_json_sha256 if spec else "",
        "ids": sorted(compatibility_ids),
    }
    (output / COMPATIBILITY_FLOOR_FILENAME).write_text(
        json.dumps(floor, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    merged_ids = {str(item["id"]) for item in merged_records}
    restored_ids = sorted(compatibility_ids.difference(primary_ids))
    return {
        "primary_count": len(primary_ids),
        "compatibility_count": len(compatibility_ids),
        "merged_count": len(merged_ids),
        "restored_count": len(restored_ids),
        "restored_ids": restored_ids,
        "audit_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--compat", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.parse_args()
    raise PermissionError(
        "legacy compatibility-floor publishing is disabled; "
        "use the provenance audit workflow instead"
    )


if __name__ == "__main__":
    raise SystemExit(main())
