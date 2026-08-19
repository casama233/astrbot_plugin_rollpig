from __future__ import annotations

import json
from pathlib import Path

from ex_variants import build_effective_ex_variants
from scripts.prepare_install_bundle import BOOTSTRAP_PIG_IDS, prepare_install_bundle


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "resource"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_bootstrap_ids_exist_with_one_bundled_image_each():
    pigs = _load(RESOURCE / "pig.json")
    source_ids = {str(item["id"]) for item in pigs}
    selected = set(BOOTSTRAP_PIG_IDS)
    assert 16 <= len(selected) <= 24
    assert len(selected) == len(BOOTSTRAP_PIG_IDS)
    assert selected <= source_ids

    images = [path for path in (RESOURCE / "image").iterdir() if path.is_file()]
    image_stems = [path.stem for path in images]
    for pig_id in selected:
        assert image_stems.count(pig_id) == 1, pig_id


def test_bootstrap_pigs_keep_complete_ex_baseline_without_authored_bundle():
    pigs = _load(RESOURCE / "pig.json")
    selected = set(BOOTSTRAP_PIG_IDS)
    bootstrap_records = [item for item in pigs if str(item.get("id") or "") in selected]
    effective = build_effective_ex_variants(bootstrap_records, {})

    assert not (RESOURCE / "pig_ex_variants.json").exists()
    assert set(effective) == selected
    for pig_id, levels in effective.items():
        assert set(levels) == {1, 2, 3, 4, 5}, pig_id


def test_prepare_install_bundle_filters_catalog_variants_and_images(tmp_path: Path):
    root = tmp_path / "plugin"
    resource = root / "resource"
    image_dir = resource / "image"
    image_dir.mkdir(parents=True)

    pigs = [
        {"id": " keep-a ", "name": "A", "description": "A", "analysis": "A"},
        {"id": "drop", "name": "D", "description": "D", "analysis": "D"},
        {"id": "keep-b", "name": "B", "description": "B", "analysis": "B"},
    ]
    (resource / "pig.json").write_text(
        json.dumps(pigs, ensure_ascii=False), encoding="utf-8"
    )
    (resource / "pig_ex_variants.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pigs": {
                    "keep-a": {"1": {"description": "A1"}},
                    "drop": {"1": {"description": "D1"}},
                },
            }
        ),
        encoding="utf-8",
    )
    (image_dir / "keep-a.png").write_bytes(b"a")
    (image_dir / "drop.png").write_bytes(b"drop")
    (image_dir / "keep-b.webp").write_bytes(b"bb")

    stats = prepare_install_bundle(root, bootstrap_ids=(" keep-a ", "keep-b"))

    assert stats["pig_count"] == 2
    assert stats["image_count"] == 2
    assert stats["image_bytes_removed"] == 4
    assert [item["id"] for item in _load(resource / "pig.json")] == [
        "keep-a",
        "keep-b",
    ]
    assert set(_load(resource / "pig_ex_variants.json")["pigs"]) == {"keep-a"}
    assert {path.name for path in image_dir.iterdir()} == {"keep-a.png", "keep-b.webp"}
