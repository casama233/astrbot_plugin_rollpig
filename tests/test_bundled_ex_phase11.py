from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE11_SENTINELS = {
    "apple-of-eye-pig": ("两只手先把本猪捧稳", "明珠换猪，宠爱不减"),
    "char-siu": ("蜜汁刷满，叉烧上色", "黯然销魂，叉烧本人到场"),
    "chocolate-pig": ("朱古力换成猪古力", "入口即化，猪籍难保"),
    "jewelry-pig": ("珠宝改一字，猪宝登场", "移动珠宝柜，本猪本柜"),
    "juliet-pig": ("玫瑰叼好，罗密欧未读", "罗密欧上线，请别照原著"),
    "pearl-pig": ("贝壳开盖，珍猪到货", "真珠假猪？本猪保真"),
    "pork-floss": ("猪脸埋进肉丝窝", "生活揉碎，最后很下饭"),
    "suckling-pig": ("年纪轻轻，火候先成熟", "新人没过试用，先熟透了"),
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


def test_phase11_shard_reaches_effective_bundled_loader_text_only():
    variants = _variants()

    for pig_id, (ex1, ex5) in PHASE11_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_phase11_visual_wordplay_and_food_research_boundaries_remain_explicit():
    variants = _variants()

    pearl = _copy(variants, "pearl-pig")
    assert all(token in pearl for token in ("贝壳", "珠母质", "虹彩", "珍猪"))
    assert "你把一颗硕大的珍珠顶在身上" not in pearl

    cherished = _copy(variants, "apple-of-eye-pig")
    assert all(token in cherished for token in ("掌上明珠", "极受珍爱", "黄色双手", "四只蹄子"))

    chocolate = _copy(variants, "chocolate-pig")
    assert all(token in chocolate for token in ("粤语", "朱古力", "巧克力", "四条腿"))
    assert "喂猪吃巧克力" not in chocolate

    jewelry = _copy(variants, "jewelry-pig")
    assert all(token in jewelry for token in ("宝石棱面", "王冠", "珠链", "整体保价"))
    assert "从耳朵到尾巴挂满珠宝" not in jewelry

    juliet = _copy(variants, "juliet-pig")
    assert all(token in juliet for token in ("玫瑰", "罗密欧", "蒙太古", "凯普莱特", "名字改变"))
    assert "阳台" not in juliet

    char_siu = _copy(variants, "char-siu")
    assert all(token in char_siu for token in ("生块叉烧好过生你", "《食神》", "黯然销魂饭", "煎蛋", "焦边"))

    floss = _copy(variants, "pork-floss")
    assert all(token in floss for token in ("煮到纤维松散", "顺着纹理", "炒干", "搓松", "面包", "饭团"))

    suckling = _copy(variants, "suckling-pig")
    assert all(token in suckling for token in ("红苹果没有塞在嘴里", "猪背", "脆皮水", "风干", "绿叶"))
    assert "二至六个星期" not in suckling


def test_all_current_bundled_handwritten_copy_is_globally_unique_after_phase11():
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
