from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE12_SENTINELS = {
    "burger-pig": ("上下面包先把本猪夹稳", "生活夹我，我夹成整套套餐"),
    "chef-pig": ("厨师帽先把猪厨坐实", "本猪掌勺，本猪不入菜单"),
    "everest-pig": ("雪峰长出一只猪鼻", "世界之巅改挂猪鼻坐标"),
    "lard-pig": ("脂肪下锅，猪魂出碗", "肉身成油，光环完成归档"),
    "mini-pig": ("三十六乘三十二像素报到", "今日小猪，小到成为彩蛋"),
    "oreo-pig": ("两片黑饼夹出一只猪", "猪利猪出品，经典猪味"),
    "pig-skin-milk": ("双皮奶换字，猪皮奶上桌", "两层奶皮，零片真实猪皮"),
    "prison-break-pig": ("房门一开，本猪先退租", "出猪屋完成，泥坑是新址"),
    "salmon-sushi-pig": ("醋饭托底，三文猪上席", "三文鱼改一字，整猪成一贯"),
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


def test_phase12_shard_reaches_effective_bundled_loader_text_only():
    variants = _variants()

    for pig_id, (ex1, ex5) in PHASE12_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_phase12_visual_wordplay_food_and_brand_boundaries_remain_explicit():
    variants = _variants()

    everest = _copy(variants, "everest-pig")
    assert all(token in everest for token in ("8848.86", "雪面高程", "小方格围巾", "猪鼻"))
    assert all(token not in everest for token in ("登顶尸体", "遇难者", "插旗"))

    burger = _copy(variants, "burger-pig")
    assert all(token in burger for token in ("生活给我施压", "面包", "生菜", "芝士", "粉色夹层"))
    assert all(token not in burger for token in ("牛肉饼", "鸡肉饼"))

    chef = _copy(variants, "chef-pig")
    assert all(token in chef for token in ("厨师帽", "花边碗", "餐具", "镜子", "不入菜单"))
    assert "刀工精湛" not in chef

    house = _copy(variants, "prison-break-pig")
    assert all(token in house for token in ("出租屋", "出猪屋", "不住了", "不猪了", "红屋顶", "蓝窗户"))
    assert "身后没有铁栏，也没有追兵" in house
    assert all(token not in house for token in ("越狱成功", "牢房", "狱警"))

    milk = _copy(variants, "pig-skin-milk")
    assert all(
        token in milk
        for token in ("双皮奶", "第一层奶皮", "蛋清", "第二层奶皮", "零片真实猪皮")
    )
    assert "不是真的往甜品里放猪皮" in milk
    assert all(token not in milk for token in ("加入真实猪皮", "配料含猪皮", "用猪皮制作"))

    lard = _copy(variants, "lard-pig")
    assert all(
        token in lard
        for token in ("搪瓷碗", "小火慢炼", "油渣", "滤网", "淡黄色", "乳白色", "光环")
    )
    assert all(token not in lard for token in ("更健康", "营养价值", "减肥"))

    mini = _copy(variants, "mini-pig")
    assert all(token in mini for token in ("240×240", "36×32", "2%", "浏览器缩放", "冠名权"))

    oreo = _copy(variants, "oreo-pig")
    assert all(
        token in oreo
        for token in ("两片黑色巧克力饼干", "扭开", "奶油", "牛奶", "猪利猪", "经典猪味")
    )
    assert "不是官方联名" in oreo

    sushi = _copy(variants, "salmon-sushi-pig")
    assert all(
        token in sushi
        for token in ("醋饭", "握寿司", "橙色身体", "奶白条纹", "上层配料", "酱油", "孜然")
    )
    assert "这不是新鲜现切的一片鱼" in sushi
    assert all(token not in sushi for token in ("可以直接生食", "保证生食安全", "现切鱼片上桌"))


def test_mini_pig_copy_matches_current_transparent_asset_geometry():
    with Image.open(RESOURCE_DIR / "image" / "mini-pig.png") as image:
        rgba = image.convert("RGBA")
        assert rgba.size == (240, 240)
        assert rgba.getchannel("A").getbbox() == (102, 112, 138, 144)


def test_all_current_bundled_handwritten_copy_is_globally_unique_after_phase12():
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
