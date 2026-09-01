from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE9_SENTINELS = {
    "chained_crown_pig": ("王冠刚戴，锁链已签收", "猪王坐稳，活动半径两米"),
    "pig-bun": ("蒸笼掀盖先对上猪眼", "猪包出笼，概不试吃"),
    "pig-cat": ("猫纹猪鼻同时在线", "物种栏正式填写猪咪"),
    "pig-souffle": ("蛋白霜把本猪托起来", "趁热端走，迟到就扁"),
    "rainbow-pig": ("不是好色，是色很多", "斯图亚特·彩虹猪，全彩"),
    "tangyuan_pig": ("芝麻请假，黑猪麻代班", "黑猪麻出锅，团圆超载"),
    "taxi-pig": ("师傅，出猪车走不走", "生活所迫，猪程必达"),
    "vangogh_pig": ("金猪误入《星月夜》", "这幅名叫《星月猪》"),
}


def _catalog_ids() -> set[str]:
    pigs = json.loads((RESOURCE_DIR / "pig.json").read_text(encoding="utf-8-sig"))
    return {
        str(item.get("id") or "")
        for item in pigs
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def _variants() -> dict[str, dict[int, dict[str, str]]]:
    pig_ids = _catalog_ids()
    return load_bundled_ex_copy(
        RESOURCE_DIR,
        pig_ids,
        pig_ids,
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )


def _copy(variants, pig_id: str) -> str:
    return "".join(
        variants[pig_id][level]["description"] + variants[pig_id][level]["analysis"]
        for level in range(1, 6)
    )


def test_phase9_shard_reaches_effective_bundled_loader_text_only():
    variants = _variants()

    for pig_id, (ex1, ex5) in PHASE9_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_phase9_visual_and_reference_boundaries_remain_explicit():
    variants = _variants()

    pig_cat = _copy(variants, "pig-cat")
    assert all(token in pig_cat for token in ("橘猫", "胡须", "猪鼻", "猪尾", "猪咪"))

    rainbow = _copy(variants, "rainbow-pig")
    assert "斯图亚特·彩虹猪" in rainbow
    assert all(token not in rainbow for token in ("Stuart Little", "LGBT", "骄傲月", "检索不到"))

    pig_bun = _copy(variants, "pig-bun")
    assert all(token in pig_bun for token in ("蒸笼", "收口褶", "内馅"))
    assert "猪肉馅" not in pig_bun

    taxi = _copy(variants, "taxi-pig")
    assert all(token in taxi for token in ("出猪车", "起步价", "计价器", "打表"))

    souffle = _copy(variants, "pig-souffle")
    assert all(token in souffle for token in ("蛋白网络", "气泡", "回落", "蓝莓"))

    crown = _copy(variants, "chained_crown_pig")
    assert "欲戴王冠，必承其重" in crown
    assert "莎士比亚" not in crown

    vangogh = _copy(variants, "vangogh_pig")
    assert all(token in vangogh for token in ("《星月夜》", "旋涡", "左右耳", "笔触"))
    assert all(token not in vangogh for token in ("精神病", "疯子", "发疯"))

    tangyuan = _copy(variants, "tangyuan_pig")
    assert all(token in tangyuan for token in ("黑猪麻", "黑芝麻", "团圆"))


def test_all_current_bundled_handwritten_copy_is_globally_unique():
    variants = _variants()
    assert len(variants) == 99

    descriptions = [
        levels[level]["description"]
        for levels in variants.values()
        for level in range(1, 6)
    ]
    analyses = [
        levels[level]["analysis"]
        for levels in variants.values()
        for level in range(1, 6)
    ]
    assert len(descriptions) == len(set(descriptions)) == 495
    assert len(analyses) == len(set(analyses)) == 495
