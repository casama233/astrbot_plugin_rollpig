from __future__ import annotations

import json
from pathlib import Path

import pytest

from bundled_ex_copy import (
    BUNDLED_EX_COPY_FILENAME,
    BUNDLED_EX_COPY_GLOB,
    BUNDLED_EX_COPY_SCOPE,
    load_bundled_ex_copy,
)


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
HANDWRITTEN_IDS = {
    "abstract-pig",
    "alien-pig",
    "android-pig",
    "antibacterial-pig",
    "apple-of-eye-pig",
    "apple-pig",
    "bacon",
    "bamboo-pig",
    "bandage-pig",
    "big-lazy-pig",
    "black-pig",
    "black-white-pig",
    "buddha-pig",
    "burger-pig",
    "chained_crown_pig",
    "char-siu",
    "chef-pig",
    "chocolate-pig",
    "clean-pig",
    "coder-pig",
    "computer-pig",
    "crystal-pig",
    "curator-pig",
    "cyberpunk-pig",
    "delivery-pig",
    "demon-pig",
    "dirty-pig",
    "doll-pig",
    "early-class-pig",
    "elephant-pig",
    "error-404-pig",
    "everest-pig",
    "explosive-pig",
    "fishing-pig",
    "frozen-pig",
    "goblin-pig",
    "hanging-pig",
    "heaven-pig",
    "homebody-pig",
    "human",
    "invisible_pig",
    "jewelry-pig",
    "juliet-pig",
    "landmine-pig",
    "lao_zhu_li",
    "lard-pig",
    "leek-pig",
    "lemon-pig",
    "little-red-pig",
    "magic-pig",
    "mc_porkchop",
    "mechanical-pig",
    "mini-pig",
    "muscle-pig",
    "oreo-pig",
    "pearl-pig",
    "pig",
    "pig-ball",
    "pig-bun",
    "pig-cat",
    "pig-die",
    "pig-human",
    "pig-skin-milk",
    "pig-souffle",
    "pig-stamp",
    "pig-turtle",
    "pig_god",
    "piggy-bank",
    "pigskin-pig",
    "pigsleep",
    "pork-floss",
    "pork-skewer",
    "prison-break-pig",
    "protagonist-pig",
    "rainbow-pig",
    "repeater-pig",
    "roasted-pig",
    "salmon-sushi-pig",
    "skeleton-pig",
    "snow-pig",
    "soul-pig",
    "spider-pig",
    "streamer-pig",
    "stuck-pig",
    "study-pig",
    "suckling-pig",
    "taffy-pig",
    "tangyuan_pig",
    "tank_pig",
    "taxi-pig",
    "teammate-pig",
    "tiramisu-pig",
    "upper-class-pig",
    "vangogh_pig",
    "watermelon-pig",
    "wild-boar",
    "world-ruler-pig",
    "zhuge-liang",
    "zombie-pig",
}
def _base_payload() -> dict:
    return json.loads(
        (RESOURCE_DIR / BUNDLED_EX_COPY_FILENAME).read_text(encoding="utf-8-sig")
    )


def _payloads() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8-sig"))
        for path in sorted(RESOURCE_DIR.glob(BUNDLED_EX_COPY_GLOB))
    ]


def _authored_specs() -> dict:
    specs = {}
    for payload in _payloads():
        overlap = set(specs).intersection(payload["pigs"])
        assert not overlap
        specs.update(payload["pigs"])
    return specs


def _bundled_ids() -> set[str]:
    raw = json.loads((RESOURCE_DIR / "pig.json").read_text(encoding="utf-8-sig"))
    return {
        str(item.get("id") or "")
        for item in raw
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def test_handwritten_pack_is_text_only_and_provenance_scoped():
    payloads = _payloads()
    assert payloads
    for payload in payloads:
        provenance = payload["provenance"]
        assert provenance["scope"] == BUNDLED_EX_COPY_SCOPE
        assert provenance["quarantined_ex_used"] is False

    specs = _authored_specs()
    assert set(specs) == HANDWRITTEN_IDS
    assert len(HANDWRITTEN_IDS) == 99
    assert HANDWRITTEN_IDS == _bundled_ids()

    for pig_id, spec in specs.items():
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


def test_canonical_copy_records_gemini_authorship_for_all_owned_pigs():
    from felis_direct_feature import FELIS_DIRECT_IDS

    ledger = json.loads((RESOURCE_DIR / "COPY-AUTHORING.json").read_text())
    assert ledger["authoring_method"] == "gemini-generated-explicit-copy"
    assert ledger["editorial_rewrites_by_codex"] is False
    assert set(ledger["pigs"]) == _bundled_ids() | set(FELIS_DIRECT_IDS)
    for pig_id, author in ledger["pigs"].items():
        assert author["model"] in {"gemini-4-argon", "gemini-4-hydrogen"}, pig_id
        assert author["strict_model"] is True, pig_id
        assert author["request_id"], pig_id
        assert author["levels"] == list(map(str, range(6))), pig_id


def test_loader_returns_only_active_bundled_ids():
    active = {
        "human",
        "pig",
        "leek-pig",
        "study-pig",
        "coder-pig",
        "pig-stamp",
        "taffy-pig",
        "black-pig",
        "cloud-only-pig",
    }
    variants = load_bundled_ex_copy(
        RESOURCE_DIR,
        active,
        _bundled_ids(),
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )

    assert set(variants) == {
        "human",
        "pig",
        "leek-pig",
        "study-pig",
        "coder-pig",
        "pig-stamp",
        "taffy-pig",
        "black-pig",
    }
    for levels in variants.values():
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_loader_rejects_duplicate_ids_across_shards(tmp_path: Path):
    payload = _base_payload()
    duplicate = {
        "schema_version": 1,
        "provenance": payload["provenance"],
        "pigs": {"pig": payload["pigs"]["pig"]},
    }
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "bundled_ex_copy_phase99.json").write_text(
        json.dumps(duplicate, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"重复定义.*pig"):
        load_bundled_ex_copy(
            tmp_path,
            _bundled_ids(),
            _bundled_ids(),
            image_extensions={"png"},
        )


def test_loader_rejects_unknown_non_lineage_id(tmp_path: Path):
    payload = _base_payload()
    payload["pigs"]["cloud-only-pig"] = payload["pigs"]["pig"]
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"resource/pig\.json.*cloud-only-pig"):
        load_bundled_ex_copy(
            tmp_path,
            {"pig", "cloud-only-pig"},
            _bundled_ids(),
            image_extensions={"png"},
        )


def test_loader_rejects_image_field(tmp_path: Path):
    payload = _base_payload()
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


def test_loader_rejects_incomplete_levels(tmp_path: Path):
    payload = _base_payload()
    del payload["pigs"]["human"]["levels"]["5"]
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"EX1.*EX5"):
        load_bundled_ex_copy(
            tmp_path,
            {"human"},
            _bundled_ids(),
            image_extensions={"png"},
        )


def test_loader_rejects_quarantined_ex_claim(tmp_path: Path):
    payload = _base_payload()
    payload["provenance"]["quarantined_ex_used"] = True
    (tmp_path / BUNDLED_EX_COPY_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="quarantined_ex_used=false"):
        load_bundled_ex_copy(
            tmp_path,
            HANDWRITTEN_IDS,
            _bundled_ids(),
            image_extensions={"png"},
        )
