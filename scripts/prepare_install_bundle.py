#!/usr/bin/env python3
"""Prune a staged RollPig install tree to the offline bootstrap resource set.

The repository keeps the complete authoring resources for source builds and
content regression tests. Marketplace/GitHub release archives are staged copies
and intentionally carry only a small, internally consistent offline catalog;
the normal cloud-resource sync expands that catalog after installation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

# Keep the original ten handcrafted bundled EX pigs plus every pig that current
# runtime/tests treat as a stable special/signature fixture. This is deliberately
# explicit: adding a new source pig must not silently grow marketplace archives.
BOOTSTRAP_PIG_IDS = (
    "human",
    "pig",
    "black-pig",
    "wild-boar",
    "zhuge-liang",
    "zombie-pig",
    "explosive-pig",
    "magic-pig",
    "mechanical-pig",
    "pig-ball",
    "big-lazy-pig",
    "apple-pig",
    "burger-pig",
    "juliet-pig",
    "lard-pig",
    "mc_porkchop",
    "pig-turtle",
    "piggy-bank",
    "rainbow-pig",
    "repeater-pig",
    "salmon-sushi-pig",
    "streamer-pig",
)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload, *, indent: int) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent) + "\n",
        encoding="utf-8",
    )


def prepare_install_bundle(
    root: Path,
    *,
    bootstrap_ids: Iterable[str] = BOOTSTRAP_PIG_IDS,
) -> dict[str, int]:
    root = Path(root)
    resource = root / "resource"
    pig_path = resource / "pig.json"
    variants_path = resource / "pig_ex_variants.json"
    image_dir = resource / "image"

    if not pig_path.is_file() or not image_dir.is_dir():
        raise ValueError(f"not a RollPig staged install tree: {root}")

    selected_order = tuple(dict.fromkeys(str(value).strip() for value in bootstrap_ids))
    if not selected_order or any(not value for value in selected_order):
        raise ValueError("bootstrap pig IDs must be non-empty")
    selected = set(selected_order)

    pigs = _load_json(pig_path)
    if not isinstance(pigs, list):
        raise ValueError("resource/pig.json must be a JSON array")
    source_by_id = {
        str(item.get("id") or "").strip(): item
        for item in pigs
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    missing_records = selected.difference(source_by_id)
    if missing_records:
        raise ValueError(
            "bootstrap pigs missing from source catalog: "
            + ", ".join(sorted(missing_records))
        )

    filtered_pigs = []
    for item in pigs:
        if not isinstance(item, dict):
            continue
        normalized_id = str(item.get("id") or "").strip()
        if normalized_id not in selected:
            continue
        normalized_item = dict(item)
        normalized_item["id"] = normalized_id
        filtered_pigs.append(normalized_item)

    filtered_ids = {str(item["id"]).strip() for item in filtered_pigs}
    if filtered_ids != selected or len(filtered_pigs) != len(selected):
        raise ValueError("bootstrap catalog filtering produced an inconsistent ID set")
    _write_json(pig_path, filtered_pigs, indent=4)

    if variants_path.is_file():
        variants = _load_json(variants_path)
        if not isinstance(variants, dict) or not isinstance(variants.get("pigs"), dict):
            raise ValueError("resource/pig_ex_variants.json has an invalid schema")
        variants = dict(variants)
        variants["pigs"] = {
            pig_id: value
            for pig_id, value in variants["pigs"].items()
            if str(pig_id) in selected
        }
        _write_json(variants_path, variants, indent=2)

    before_files = [
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    ]
    before_bytes = sum(path.stat().st_size for path in before_files)
    for path in before_files:
        if path.stem not in selected:
            path.unlink()

    remaining = [
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    ]
    remaining_by_stem: dict[str, list[Path]] = {}
    for path in remaining:
        remaining_by_stem.setdefault(path.stem, []).append(path)

    missing_images = selected.difference(remaining_by_stem)
    duplicate_images = {
        pig_id: paths
        for pig_id, paths in remaining_by_stem.items()
        if pig_id in selected and len(paths) != 1
    }
    extra_images = set(remaining_by_stem).difference(selected)
    if missing_images or duplicate_images or extra_images:
        raise ValueError(
            "bootstrap image set is inconsistent: "
            f"missing={sorted(missing_images)}, "
            f"duplicates={sorted(duplicate_images)}, extra={sorted(extra_images)}"
        )

    after_bytes = sum(path.stat().st_size for path in remaining)
    return {
        "pig_count": len(filtered_pigs),
        "image_count": len(remaining),
        "image_bytes_before": before_bytes,
        "image_bytes_after": after_bytes,
        "image_bytes_removed": before_bytes - after_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="staged plugin root to prune in-place")
    args = parser.parse_args()
    stats = prepare_install_bundle(args.root)
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
