#!/usr/bin/env python3
"""Validate and publish machine-readable provenance for bundled image replacements."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_image(source_root: Path, pig_id: str) -> Path:
    found = [
        path
        for path in (source_root / "image").glob(f"{pig_id}.*")
        if path.is_file()
        and path.stem == pig_id
        and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if len(found) != 1:
        raise ValueError(
            f"{pig_id} 必須恰好對應一張 bundled image；實際找到 {len(found)} 張"
        )
    return found[0]


def _load_catalog_ids(source_root: Path) -> set[str]:
    path = source_root / "pig.json"
    try:
        records = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取 pig.json：{exc}") from exc
    if not isinstance(records, list) or not records:
        raise ValueError("pig.json 必須是非空陣列")
    ids: set[str] = set()
    for raw in records:
        pig_id = str(raw.get("id") or "").strip() if isinstance(raw, dict) else ""
        if not ID_PATTERN.fullmatch(pig_id):
            raise ValueError(f"pig.json 小豬 ID 無效：{pig_id}")
        if pig_id in ids:
            raise ValueError(f"pig.json 小豬 ID 重複：{pig_id}")
        ids.add(pig_id)
    return ids


def _load_artifact_image_ids(manifest_path: Path) -> set[str]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取生成 artifact manifest：{exc}") from exc
    images = manifest.get("images") if isinstance(manifest, dict) else None
    if not isinstance(images, list):
        raise ValueError("生成 artifact manifest images 必須是陣列")
    ids: set[str] = set()
    for raw in images:
        filename = str(raw.get("filename") or "") if isinstance(raw, dict) else ""
        path = Path(filename)
        if (
            not filename
            or path.name != filename
            or path.stem in ids
            or path.suffix.lower() not in IMAGE_EXTENSIONS
        ):
            raise ValueError(f"生成 artifact manifest 圖片記錄無效：{filename}")
        ids.add(path.stem)
    return ids


def load_and_validate(
    source_root: Path,
    artifact_manifest: Path | None = None,
) -> dict:
    source_root = source_root.resolve()
    path = source_root / "asset_provenance.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"無法讀取 asset_provenance.json：{exc}") from exc

    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("asset_provenance.json schema_version 必須為 1")
    assets = payload.get("assets")
    withheld = payload.get("withheld", {})
    if not isinstance(assets, dict) or not assets:
        raise ValueError("asset_provenance.json assets 必須是非空物件")
    if not isinstance(withheld, dict):
        raise ValueError("asset_provenance.json withheld 必須是物件")
    overlap = set(assets).intersection(withheld)
    if overlap:
        raise ValueError(
            "同一 ID 不能同時 approved 與 withheld：" + ", ".join(sorted(overlap))
        )
    catalog_ids = _load_catalog_ids(source_root)

    for pig_id, raw in assets.items():
        if not ID_PATTERN.fullmatch(str(pig_id)) or not isinstance(raw, dict):
            raise ValueError(f"asset provenance 記錄無效：{pig_id}")
        if pig_id not in catalog_ids:
            raise ValueError(f"{pig_id} approved provenance ID 不在 pig.json")
        if raw.get("redistribution_allowed") is not True:
            raise ValueError(
                f"{pig_id} approved asset 必須 redistribution_allowed=true"
            )
        if raw.get("binary_committed") is not True:
            raise ValueError(f"{pig_id} replacement binary 尚未標記為 committed")
        for field in (
            "asset_role",
            "rights_basis",
            "source_repo",
            "source_path",
            "license",
            "source_sha256",
            "replacement_sha256",
        ):
            if not str(raw.get(field) or "").strip():
                raise ValueError(f"{pig_id} 缺少 provenance 欄位：{field}")
        source_sha = str(raw["source_sha256"])
        replacement_sha = str(raw["replacement_sha256"])
        if not SHA256_PATTERN.fullmatch(source_sha):
            raise ValueError(f"{pig_id} source_sha256 格式無效")
        if not SHA256_PATTERN.fullmatch(replacement_sha):
            raise ValueError(f"{pig_id} replacement_sha256 格式無效")
        attribution = raw.get("attribution")
        if not isinstance(attribution, list) or not all(
            isinstance(item, str) and item.strip() for item in attribution
        ):
            raise ValueError(f"{pig_id} attribution 必須是非空字串陣列")
        image = _find_image(source_root, str(pig_id))
        actual = _sha256(image)
        if actual != replacement_sha:
            raise ValueError(
                f"{pig_id} bundled image SHA-256 不符：expected={replacement_sha} actual={actual}"
            )

    for pig_id, raw in withheld.items():
        if not ID_PATTERN.fullmatch(str(pig_id)) or not isinstance(raw, dict):
            raise ValueError(f"withheld provenance 記錄無效：{pig_id}")
        if raw.get("redistribution_allowed") is not False:
            raise ValueError(
                f"{pig_id} withheld asset 必須 redistribution_allowed=false"
            )
        if not str(raw.get("reason") or "").strip():
            raise ValueError(f"{pig_id} withheld asset 缺少 reason")

    if artifact_manifest is not None:
        artifact_ids = _load_artifact_image_ids(artifact_manifest.resolve())
        missing = set(assets).difference(artifact_ids)
        if missing:
            raise ValueError(
                "approved provenance 圖片未出現在生成 artifact："
                + ", ".join(sorted(missing))
            )

    return payload


def publish(payload: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("resource"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact-manifest", type=Path)
    args = parser.parse_args()
    payload = load_and_validate(args.source, args.artifact_manifest)
    if args.output is not None:
        publish(payload, args.output)
    print(
        json.dumps(
            {
                "approved_asset_count": len(payload["assets"]),
                "withheld_asset_count": len(payload.get("withheld", {})),
                "output": str(args.output.resolve()) if args.output else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
