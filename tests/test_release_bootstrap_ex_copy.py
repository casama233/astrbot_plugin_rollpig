from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from bundled_ex_copy import load_bundled_ex_copy
from scripts.prepare_install_bundle import BOOTSTRAP_PIG_IDS, prepare_install_bundle

ROOT = Path(__file__).resolve().parents[1]


def _staged_source(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
    source = ROOT / "resource"
    stage = tmp_path / "plugin"
    resource = stage / "resource"
    images = resource / "image"
    images.mkdir(parents=True)
    paths = [source / "pig.json", *sorted(source.glob("bundled_ex_copy*.json"))]
    assert len(paths) > 1
    original = {str(path): path.read_bytes() for path in paths}
    for path in paths:
        shutil.copyfile(path, resource / path.name)
    # The pruning contract only needs an ID-to-image file mapping.
    for item in json.loads((resource / "pig.json").read_text(encoding="utf-8-sig")):
        Image.new("RGB", (2, 2)).save(images / f"{item['id']}.png")
    return stage, original


def _packaged_copy(stage: Path):
    resource = stage / "resource"
    pigs = json.loads((resource / "pig.json").read_text(encoding="utf-8-sig"))
    ids = {item["id"] for item in pigs}
    return load_bundled_ex_copy(resource, ids, ids, image_extensions={"png"})


def test_staged_bootstrap_retains_all_five_explicit_ex_levels(tmp_path: Path):
    stage, original = _staged_source(tmp_path)
    full_ids = {
        item["id"]
        for item in json.loads((ROOT / "resource" / "pig.json").read_text(encoding="utf-8-sig"))
    }
    expected = load_bundled_ex_copy(
        ROOT / "resource", set(BOOTSTRAP_PIG_IDS), full_ids, image_extensions={"png"}
    )
    result = prepare_install_bundle(stage)
    actual = _packaged_copy(stage)

    assert result["pig_count"] == result["image_count"] == 22
    assert set(actual) == set(BOOTSTRAP_PIG_IDS)
    assert actual == expected
    assert sum(len(levels) for levels in actual.values()) == 110
    for pack in (stage / "resource").glob("bundled_ex_copy*.json"):
        payload = json.loads(pack.read_text(encoding="utf-8"))
        assert payload["pigs"]  # Runtime rejects empty authoring shards.
        assert set(payload["pigs"]).issubset(BOOTSTRAP_PIG_IDS)
    for name, content in original.items():
        assert Path(name).read_bytes() == content  # Never prune canonical source.


def test_bootstrap_ex_pruning_is_repeatable_and_keeps_felis_source(tmp_path: Path):
    stage, _ = _staged_source(tmp_path)
    felis = stage / "resource" / "felis_direct_ex_copy.json"
    felis.write_text('{"independent_direct_source": true}\n', encoding="utf-8")
    prepare_install_bundle(stage)
    first = _packaged_copy(stage)
    pack_bytes = {
        path.name: path.read_bytes()
        for path in (stage / "resource").glob("bundled_ex_copy*.json")
    }
    prepare_install_bundle(stage)
    assert _packaged_copy(stage) == first
    assert {
        path.name: path.read_bytes()
        for path in (stage / "resource").glob("bundled_ex_copy*.json")
    } == pack_bytes
    assert felis.read_text(encoding="utf-8") == '{"independent_direct_source": true}\n'


@pytest.mark.parametrize("invalid", ["unknown", "duplicate", "symlink"])
def test_invalid_authoring_is_rejected_before_catalog_is_pruned(tmp_path: Path, invalid: str):
    stage, _ = _staged_source(tmp_path)
    resource = stage / "resource"
    source = next(resource.glob("bundled_ex_copy*.json"))
    extra = resource / "bundled_ex_copy_invalid.json"
    if invalid == "symlink":
        extra.symlink_to(source.name)
    else:
        payload = json.loads(source.read_text(encoding="utf-8"))
        pig_id = next(iter(payload["pigs"]))
        payload["pigs"] = {
            ("not-a-catalog-pig" if invalid == "unknown" else pig_id): payload["pigs"][pig_id]
        }
        extra.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    original_catalog = (resource / "pig.json").read_bytes()
    with pytest.raises(ValueError):
        prepare_install_bundle(stage)
    assert (resource / "pig.json").read_bytes() == original_catalog
