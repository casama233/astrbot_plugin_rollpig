from __future__ import annotations

import pytest

from ex_variants import resolve_ex_variant, serialize_ex_variants, validate_ex_variants


def _payload():
    return {
        "schema_version": 1,
        "pigs": {
            "sleep-pig": {
                "2": {
                    "image": "sleep-pig-ex2.png",
                    "description": "睡得更香",
                },
                "4": {"analysis": "EX4 才出现的新旁白。"},
                "5": {"image": "sleep-pig-ex5.gif"},
            }
        },
    }


def test_sparse_variants_inherit_each_field_independently():
    variants = validate_ex_variants(
        _payload(), {"sleep-pig"}, image_extensions={"png", "gif"}
    )
    base = {
        "id": "sleep-pig",
        "name": "睡觉猪",
        "description": "基础描述",
        "analysis": "基础旁白",
    }

    ex1 = resolve_ex_variant(base, variants, 1)
    assert ex1["description"] == "基础描述"
    assert "_ex_image" not in ex1

    ex3 = resolve_ex_variant(base, variants, 3)
    assert ex3["description"] == "睡得更香"
    assert ex3["analysis"] == "基础旁白"
    assert ex3["_ex_image"] == "sleep-pig-ex2.png"
    assert ex3["_ex_variant_level"] == 2

    ex5 = resolve_ex_variant(base, variants, 5)
    assert ex5["description"] == "睡得更香"
    assert ex5["analysis"] == "EX4 才出现的新旁白。"
    assert ex5["_ex_image"] == "sleep-pig-ex5.gif"
    assert ex5["_ex_level"] == 5

    ex9 = resolve_ex_variant(base, variants, 9)
    assert ex9["_ex_image"] == "sleep-pig-ex5.gif"
    assert ex9["analysis"] == "EX4 才出现的新旁白。"


def test_variant_cannot_change_identity_or_name():
    payload = {"pigs": {"sleep-pig": {"1": {"name": "另一个名字"}}}}
    with pytest.raises(ValueError, match="不允许字段"):
        validate_ex_variants(payload, {"sleep-pig"})


def test_variant_rejects_unknown_pig_and_unsafe_image_name():
    with pytest.raises(ValueError, match="不存在的小猪"):
        validate_ex_variants(_payload(), {"other-pig"}, image_extensions={"png", "gif"})
    payload = {"pigs": {"sleep-pig": {"1": {"image": "../escape.png"}}}}
    with pytest.raises(ValueError, match="图片文件名无效"):
        validate_ex_variants(payload, {"sleep-pig"})


def test_variant_levels_are_limited_to_one_through_five():
    payload = {"pigs": {"sleep-pig": {"6": {"description": "too high"}}}}
    with pytest.raises(ValueError, match="必须在 1-5"):
        validate_ex_variants(payload, {"sleep-pig"})


def test_serialization_is_canonical_and_round_trips():
    variants = validate_ex_variants(
        _payload(), {"sleep-pig"}, image_extensions={"png", "gif"}
    )
    serialized = serialize_ex_variants(variants)
    assert serialized["schema_version"] == 1
    assert list(serialized["pigs"]["sleep-pig"]) == ["2", "4", "5"]
    assert validate_ex_variants(
        serialized, {"sleep-pig"}, image_extensions={"png", "gif"}
    ) == variants
