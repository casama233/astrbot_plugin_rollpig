from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE10_SENTINELS = {
    "buddha-pig": ("佛珠一转，全员佛猪", "一切随缘，佛猪成串"),
    "frozen-pig": ("物理冷静，冰块封装", "心如止水，止到结冰"),
    "invisible_pig": ("身体图层已设为透明", "透明度归零，围观不下线"),
    "lao_zhu_li": ("白胡子先把工龄报到", "老猪历，资历按年翻页"),
    "mc_porkchop": ("像素猪排已经烤熟", "生存背包里的压舱饭"),
    "pig_god": ("光环亮起，问题请排队", "智慧之神也不替你交卷"),
    "tank_pig": ("F 键已亮，驾驶位空着", "按 F 进入，前方请让猪"),
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


def test_phase10_shard_reaches_effective_bundled_loader_text_only():
    variants = _variants()

    for pig_id, (ex1, ex5) in PHASE10_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_phase10_visual_research_and_safety_boundaries_remain_explicit():
    variants = _variants()

    porkchop = _copy(variants, "mc_porkchop")
    assert all(token in porkchop for token in ("《我的世界》", "8 点", "四个鸡腿", "12.8", "64"))
    assert "恢复生命值" not in porkchop

    pig_god = _copy(variants, "pig_god")
    assert all(token in pig_god for token in ("白袍", "翅膀", "光环", "星星法杖"))
    assert all(token not in pig_god for token in ("祥云", "莲台", "宙斯", "雅典娜"))

    tank = _copy(variants, "tank_pig")
    assert all(token in tank for token in ("按 F 进入", "履带", "X", "炮塔"))
    assert all(token not in tank for token in ("肥婆", "胖女人", "坦克女", "母坦克"))

    veteran = _copy(variants, "lao_zhu_li")
    assert all(token in veteran for token in ("白胡子", "资历", "猪历", "版本史"))
    assert all(token not in veteran for token in ("题库", "刷题", "考试答案"))

    invisible = _copy(variants, "invisible_pig")
    assert all(token in invisible for token in ("透明通道", "耳朵", "眼睛", "鼻子", "碰撞"))
    assert "只剩一点若隐若现的猪鼻子" not in invisible

    buddha = _copy(variants, "buddha-pig")
    assert all(token in buddha for token in ("佛珠", "念珠", "施猪", "计数", "合十"))
    assert all(token not in buddha for token in ("迷信", "骗钱", "装神弄鬼"))

    frozen = _copy(variants, "frozen-pig")
    assert all(token in frozen for token in ("蓝色冰块", "雪花", "X", "低温"))
    assert "微波" not in frozen


def test_all_current_bundled_handwritten_copy_is_globally_unique_after_phase10():
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
