from __future__ import annotations

import json
from pathlib import Path

import pytest

from felis_direct_feature import FELIS_DIRECT_IDS
from felis_ex_copy import (
    FELIS_DIRECT_EX_COPY_FILENAME,
    FELIS_DIRECT_EX_COPY_SCOPE,
    load_felis_direct_ex_copy,
)


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"

PHASE_ONE_HANDWRITTEN_IDS = {
    "coding-pig",
    "emoji-king-pig",
    "niuma-pig",
    "noob-pig",
    "party-pig",
    "screenshot-pig",
    "shopping-pig",
    "tv-pig",
}


def _payload() -> dict:
    return json.loads(
        (RESOURCE_DIR / FELIS_DIRECT_EX_COPY_FILENAME).read_text(encoding="utf-8-sig")
    )


def test_felis_original_ex_specs_are_complete_and_provenance_scoped():
    payload = _payload()
    provenance = payload["provenance"]
    assert provenance["scope"] == FELIS_DIRECT_EX_COPY_SCOPE
    assert provenance["upstream_ex_used"] is False
    assert set(payload["pigs"]) == set(FELIS_DIRECT_IDS)
    assert len(payload["pigs"]) == 34

    for pig_id, spec in payload["pigs"].items():
        assert isinstance(spec, dict), pig_id
        assert "image" not in spec
        if pig_id in PHASE_ONE_HANDWRITTEN_IDS:
            assert set(spec) == {"levels"}, pig_id
            assert set(spec["levels"]) == {"1", "2", "3", "4", "5"}, pig_id
            for item in spec["levels"].values():
                assert set(item) == {"description", "analysis"}, pig_id
                assert all(str(value).strip() for value in item.values()), pig_id
        else:
            assert set(spec) == {"name", "theme", "progress", "lesson"}, pig_id
            assert all(str(value).strip() for value in spec.values()), pig_id


def test_phase_one_handwritten_copy_is_not_generic_growth_template():
    payload = _payload()
    forbidden_fragments = (
        "开始形成自己的节奏",
        "进入稳定期",
        "成长收在一句话里",
    )
    for pig_id in PHASE_ONE_HANDWRITTEN_IDS:
        levels = payload["pigs"][pig_id]["levels"]
        combined = "\n".join(
            item[field]
            for item in levels.values()
            for field in ("description", "analysis")
        )
        assert not any(fragment in combined for fragment in forbidden_fragments), pig_id


def test_felis_original_ex_expands_to_five_text_only_levels_per_id():
    variants = load_felis_direct_ex_copy(
        RESOURCE_DIR,
        FELIS_DIRECT_IDS,
        FELIS_DIRECT_IDS,
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )
    assert set(variants) == set(FELIS_DIRECT_IDS)

    for pig_id, levels in variants.items():
        assert set(levels) == {1, 2, 3, 4, 5}, pig_id
        descriptions = []
        analyses = []
        for item in levels.values():
            assert set(item) == {"description", "analysis"}, pig_id
            descriptions.append(item["description"])
            analyses.append(item["analysis"])
            assert len(item["description"]) <= 120
            assert len(item["analysis"]) <= 800
        assert len(set(descriptions)) == 5, pig_id
        assert len(set(analyses)) == 5, pig_id


def test_felis_original_ex_is_filtered_to_runtime_catalog_without_weakening_pack_validation():
    active = {"awakened-pig", "coding-pig"}
    variants = load_felis_direct_ex_copy(
        RESOURCE_DIR,
        active,
        FELIS_DIRECT_IDS,
        image_extensions={"png"},
    )
    assert set(variants) == active


def test_felis_original_ex_rejects_any_image_or_extra_authoring_field(tmp_path: Path):
    payload = _payload()
    payload["pigs"]["awakened-pig"]["image"] = "awakened-pig-ex1.png"
    (tmp_path / FELIS_DIRECT_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="规格字段不完整"):
        load_felis_direct_ex_copy(
            tmp_path,
            FELIS_DIRECT_IDS,
            FELIS_DIRECT_IDS,
            image_extensions={"png"},
        )


def test_felis_original_ex_rejects_incomplete_handwritten_levels(tmp_path: Path):
    payload = _payload()
    del payload["pigs"]["coding-pig"]["levels"]["5"]
    (tmp_path / FELIS_DIRECT_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="完整提供 EX1-EX5"):
        load_felis_direct_ex_copy(
            tmp_path,
            FELIS_DIRECT_IDS,
            FELIS_DIRECT_IDS,
            image_extensions={"png"},
        )


def test_felis_original_ex_rejects_provenance_that_claims_upstream_ex_use(tmp_path: Path):
    payload = _payload()
    payload["provenance"]["upstream_ex_used"] = True
    (tmp_path / FELIS_DIRECT_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="upstream_ex_used=false"):
        load_felis_direct_ex_copy(
            tmp_path,
            FELIS_DIRECT_IDS,
            FELIS_DIRECT_IDS,
            image_extensions={"png"},
        )
