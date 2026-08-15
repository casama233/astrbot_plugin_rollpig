from __future__ import annotations

import json
from pathlib import Path

from ex_variants import (
    build_effective_ex_variants,
    resolve_ex_variant,
    validate_ex_variants,
)


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_and_effective_variants():
    pigs = _load_json(RESOURCE_DIR / "pig.json")
    pig_by_id = {
        str(item.get("id") or ""): item
        for item in pigs
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    explicit = validate_ex_variants(
        _load_json(RESOURCE_DIR / "pig_ex_variants.json"),
        set(pig_by_id),
        image_extensions={"png", "jpg", "jpeg", "gif", "webp"},
    )
    effective = build_effective_ex_variants(pigs, explicit)
    return pigs, pig_by_id, explicit, effective


def test_bundled_ex_pack_is_curated_complete_and_visible():
    _, pig_by_id, explicit, effective = _catalog_and_effective_variants()

    # The hand-written starter pack remains a curated layer, now with complete
    # Lv1-Lv5 copy rather than the earlier sparse product proof-of-concept.
    assert len(explicit) >= 10
    for pig_id, levels in explicit.items():
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(levels[level].get("description") for level in range(1, 6))
        assert all(levels[level].get("analysis") for level in range(1, 6))
        assert len({levels[level]["description"] for level in range(1, 6)}) == 5
        assert len({levels[level]["analysis"] for level in range(1, 6)}) == 5

        base = pig_by_id[pig_id]
        resolved = resolve_ex_variant(base, effective, 5)
        assert resolved["_ex_level"] == 5
        assert resolved["_ex_variant_level"] == 5
        assert (
            resolved.get("description") != base.get("description")
            or resolved.get("analysis") != base.get("analysis")
            or resolved.get("_ex_image")
        ), pig_id


def test_every_bundled_catalog_pig_has_five_distinct_effective_copy_levels():
    _, pig_by_id, _, effective = _catalog_and_effective_variants()

    # This is the product gate: adding a bundled pig without effective EX copy
    # must fail CI. The same generator is applied at runtime to cloud/compat pigs.
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


def test_generated_baseline_covers_cloud_or_compat_pigs_not_in_curated_pack():
    pig = {
        "id": "compat-only-pig",
        "name": "兼容旧猪",
        "description": "从旧公共源回来的熟面孔",
        "analysis": "这只猪只存在于兼容恢复后的活动目录，用来证明完整 EX 文案不依赖 bundled 手写名单。",
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
            1: {"description": "手写 EX1"},
            3: {"analysis": "手写 EX3 分析"},
            5: {"description": "手写 EX5"},
        }
    }
    effective = build_effective_ex_variants([pig], overrides)

    assert effective["test-pig"][1]["description"] == "手写 EX1"
    assert effective["test-pig"][2]["description"] == "手写 EX1"
    assert effective["test-pig"][3]["analysis"] == "手写 EX3 分析"
    assert effective["test-pig"][4]["analysis"] == "手写 EX3 分析"
    assert effective["test-pig"][5]["description"] == "手写 EX5"
    # Fields not explicitly overridden still come from the per-level baseline.
    assert effective["test-pig"][1]["analysis"] != effective["test-pig"][2]["analysis"]


def test_curated_pig_keeps_expected_signature_copy_and_lv5_plus_fallback():
    _, pig_by_id, _, effective = _catalog_and_effective_variants()
    base = pig_by_id["pig"]

    ex3 = resolve_ex_variant(base, effective, 3)
    assert ex3["description"] == "默认款进入资深区，猪圈流程已背熟"
    assert "老员工的从容" in ex3["analysis"]

    ex9 = resolve_ex_variant(base, effective, 9)
    assert ex9["_ex_level"] == 9
    assert ex9["_ex_variant_level"] == 5
    assert ex9["description"] == "默认款？现在是资深标准猪"
    assert "拿你当参照物" in ex9["analysis"]
