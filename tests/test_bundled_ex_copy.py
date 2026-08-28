from __future__ import annotations

import json
from pathlib import Path

import pytest

from bundled_ex_copy import (
    BUNDLED_EX_COPY_FILENAME,
    BUNDLED_EX_COPY_SCOPE,
    load_bundled_ex_copy,
)


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE1_IDS = {
    "explosive-pig",
    "human",
    "magic-pig",
    "mechanical-pig",
    "pig",
    "skeleton-pig",
    "zhuge-liang",
    "zombie-pig",
}


def _payload() -> dict:
    return json.loads(
        (RESOURCE_DIR / BUNDLED_EX_COPY_FILENAME).read_text(encoding="utf-8-sig")
    )


def _bundled_ids() -> set[str]:
    raw = json.loads((RESOURCE_DIR / "pig.json").read_text(encoding="utf-8-sig"))
    return {
        str(item.get("id") or "")
        for item in raw
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def test_phase1_pack_is_text_only_and_provenance_scoped():
    payload = _payload()
    provenance = payload["provenance"]
    assert provenance["scope"] == BUNDLED_EX_COPY_SCOPE
    assert provenance["quarantined_ex_used"] is False
    assert set(payload["pigs"]) == PHASE1_IDS
    assert PHASE1_IDS <= _bundled_ids()

    for pig_id, spec in payload["pigs"].items():
        assert set(spec) == {"levels"}, pig_id
        assert set(spec["levels"]) == {"1", "2", "3", "4", "5"}, pig_id
        descriptions = []
        analyses = []
        for item in spec["levels"].values():
            assert set(item) == {"description", "analysis"}, pig_id
            assert all(str(value).strip() for value in item.values()), pig_id
            descriptions.append(item["description"])
            analyses.append(item["analysis"])
        assert len(set(descriptions)) == 5, pig_id
        assert len(set(analyses)) == 5, pig_id


def test_phase1_loader_returns_only_active_bundled_ids():
    active = {"human", "pig", "cloud-only-pig"}
    variants = load_bundled_ex_copy(
        RESOURCE_DIR,
        active,
        _bundled_ids(),
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )

    assert set(variants) == {"human", "pig"}
    for levels in variants.values():
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_phase1_loader_rejects_unknown_non_lineage_id(tmp_path: Path):
    payload = _payload()
    payload["pigs"]["cloud-only-pig"] = payload["pigs"]["pig"]
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="只能引用 resource/pig.json"):
        load_bundled_ex_copy(
            tmp_path,
            {"pig", "cloud-only-pig"},
            _bundled_ids(),
            image_extensions={"png"},
        )


def test_phase1_loader_rejects_image_field(tmp_path: Path):
    payload = _payload()
    payload["pigs"]["pig"]["levels"]["1"]["image"] = "pig-ex1.png"
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="字段不完整"):
        load_bundled_ex_copy(
            tmp_path,
            {"pig"},
            _bundled_ids(),
            image_extensions={"png"},
        )


def test_phase1_loader_rejects_incomplete_levels(tmp_path: Path):
    payload = _payload()
    del payload["pigs"]["human"]["levels"]["5"]
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="完整提供 EX1-EX5"):
        load_bundled_ex_copy(
            tmp_path,
            {"human"},
            _bundled_ids(),
            image_extensions={"png"},
        )


def test_phase1_loader_rejects_quarantined_ex_claim(tmp_path: Path):
    payload = _payload()
    payload["provenance"]["quarantined_ex_used"] = True
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="quarantined_ex_used=false"):
        load_bundled_ex_copy(
            tmp_path,
            PHASE1_IDS,
            _bundled_ids(),
            image_extensions={"png"},
        )
