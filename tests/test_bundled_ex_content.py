from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy
from ex_variants import build_effective_ex_variants, resolve_ex_variant


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


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_and_effective_variants():
    pigs = _load_json(RESOURCE_DIR / "pig.json")
    pig_by_id = {
        str(item.get("id") or ""): item
        for item in pigs
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    explicit = load_bundled_ex_copy(
        RESOURCE_DIR,
        pig_by_id,
        pig_by_id,
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )
    effective = build_effective_ex_variants(pigs, explicit)
    return pigs, pig_by_id, explicit, effective


def test_bundled_release_keeps_quarantined_authored_packs_absent():
    _, pig_by_id, explicit, effective = _catalog_and_effective_variants()

    assert not (RESOURCE_DIR / "pig_ex_variants.json").exists()
    assert not (RESOURCE_DIR / "ex_curated").exists()
    assert set(explicit) == PHASE1_IDS
    assert PHASE1_IDS < set(pig_by_id)
    assert effective


def test_every_bundled_catalog_pig_still_has_five_distinct_effective_copy_levels():
    _, pig_by_id, _, effective = _catalog_and_effective_variants()

    assert set(effective) == set(pig_by_id)
    for pig_id, base in pig_by_id.items():
        levels = effective[pig_id]
        assert set(levels) == {1, 2, 3, 4, 5}, pig_id
        descriptions = [levels[level].get("description", "") for level in range(1, 6)]
        analyses = [levels[level].get("analysis", "") for level in range(1, 6)]
        assert all(descriptions), pig_id
        assert all(analyses), pig_id
        assert len(set(descriptions)) == 5, pig_id
        assert len(set(analyses)) == 5, pig_id
        assert all(len(value) <= 120 for value in descriptions), pig_id
        assert all(len(value) <= 800 for value in analyses), pig_id

        for level in range(1, 6):
            resolved = resolve_ex_variant(base, effective, level)
            assert resolved["_ex_variant_level"] == level
            assert resolved["description"] == descriptions[level - 1]
            assert resolved["analysis"] == analyses[level - 1]


def test_phase1_pigs_use_handwritten_copy_instead_of_generic_phase_suffixes():
    _, _, explicit, effective = _catalog_and_effective_variants()
    generic_fragments = {
        "开始养熟",
        "熟客上线",
        "资深返场",
        "招牌常驻",
        "完全体",
        "熟悉度 +1",
        "默契升温",
        "老熟人模式",
        "猪圈常驻",
        "终极熟客",
    }

    for pig_id in PHASE1_IDS:
        assert effective[pig_id] == explicit[pig_id]
        descriptions = {item["description"] for item in effective[pig_id].values()}
        assert not any(
            fragment in description
            for fragment in generic_fragments
            for description in descriptions
        ), pig_id


def test_unwritten_bundled_pigs_keep_deterministic_baseline_safety_net():
    _, pig_by_id, explicit, effective = _catalog_and_effective_variants()
    unwritten = set(pig_by_id).difference(explicit)
    assert unwritten

    pig_id = sorted(unwritten)[0]
    levels = effective[pig_id]
    assert set(levels) == {1, 2, 3, 4, 5}
    assert all(levels[level]["description"] for level in levels)
    assert all(levels[level]["analysis"] for level in levels)


def test_generated_baseline_covers_cloud_or_compat_pigs_without_authored_copy():
    pig = {
        "id": "compat-only-pig",
        "name": "兼容旧猪",
        "description": "从旧公共源回来的熟面孔",
        "analysis": "这只猪只存在于活动目录，用来证明完整 EX 文案不依赖 bundled 手写名单。",
    }
    effective = build_effective_ex_variants([pig], {})

    assert set(effective) == {"compat-only-pig"}
    assert set(effective["compat-only-pig"]) == {1, 2, 3, 4, 5}
    assert len(
        {effective["compat-only-pig"][level]["description"] for level in range(1, 6)}
    ) == 5
    assert len(
        {effective["compat-only-pig"][level]["analysis"] for level in range(1, 6)}
    ) == 5


def test_sparse_override_layer_keeps_per_field_inheritance_over_baseline():
    pig = {
        "id": "test-pig",
        "name": "测试猪",
        "description": "基础短句",
        "analysis": "基础长文案",
    }
    overrides = {
        "test-pig": {
            1: {"description": "本地 EX1"},
            3: {"analysis": "本地 EX3 分析"},
            5: {"description": "本地 EX5"},
        }
    }
    effective = build_effective_ex_variants([pig], overrides)

    assert effective["test-pig"][1]["description"] == "本地 EX1"
    assert effective["test-pig"][2]["description"] == "本地 EX1"
    assert effective["test-pig"][3]["analysis"] == "本地 EX3 分析"
    assert effective["test-pig"][4]["analysis"] == "本地 EX3 分析"
    assert effective["test-pig"][5]["description"] == "本地 EX5"
    assert effective["test-pig"][1]["analysis"] != effective["test-pig"][2]["analysis"]


def test_generated_baseline_lv5_is_used_for_higher_collection_levels():
    _, pig_by_id, _, effective = _catalog_and_effective_variants()
    base = pig_by_id["pig"]

    ex5 = resolve_ex_variant(base, effective, 5)
    ex9 = resolve_ex_variant(base, effective, 9)
    assert ex5["_ex_variant_level"] == 5
    assert ex9["_ex_level"] == 9
    assert ex9["_ex_variant_level"] == 5
    assert ex9["description"] == ex5["description"]
    assert ex9["analysis"] == ex5["analysis"]
