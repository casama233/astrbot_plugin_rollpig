from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from bundled_ex_copy import load_bundled_ex_copy

ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"


@pytest.fixture(scope="module")
def variants():
    pig_ids = set(_catalog_by_id())
    return load_bundled_ex_copy(
        RESOURCE_DIR, pig_ids, pig_ids,
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )


def _catalog() -> list[dict]:
    return json.loads((RESOURCE_DIR / "pig.json").read_text(encoding="utf-8-sig"))

def _catalog_by_id() -> dict[str, dict]:
    return {
        str(item.get("id") or ""): item
        for item in _catalog()
        if isinstance(item, dict) and str(item.get("id") or "")
    }

def _copy(variants, pig_id: str) -> str:
    return "".join(
        variants[pig_id][level]["description"] + variants[pig_id][level]["analysis"]
        for level in range(1, 6)
    )

def test_phase10_visual_research_and_safety_boundaries_remain_explicit(variants):

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

def test_phase11_visual_wordplay_and_food_research_boundaries_remain_explicit(variants):

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

def test_phase12_visual_wordplay_food_and_brand_boundaries_remain_explicit(variants):

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

def test_phase13_visual_wordplay_research_and_safety_boundaries_remain_explicit(variants):

    bamboo = _copy(variants, "bamboo-pig")
    assert all(
        token in bamboo
        for token in ("笋壳", "嫩绿笋尖", "夺笋啊", "多损啊", "山上的笋都被你夺完了", "光环")
    )

    curator = _copy(variants, "curator-pig")
    assert all(
        token in curator
        for token in ("白衬衫", "细领结", "棕色围裙", "主理人", "主打不理人")
    )

    upper = _copy(variants, "upper-class-pig")
    assert all(
        token in upper
        for token in ("黑色礼服", "白衬衫", "红领结", "资产来源暂不核验", "卷尾")
    )
    assert all(token not in upper for token in ("刀叉", "燕尾服"))

    alien = _copy(variants, "alien-pig")
    assert all(
        token in alien
        for token in ("高饱和黄绿色", "蓝色猪鼻", "黑眼", "没有飞碟，也没有天线", "待核")
    )
    assert all(token not in alien for token in ("外星人IP", "某作品角色", "飞碟驾驶员"))

    tiramisu = _copy(variants, "tiramisu-pig")
    assert all(
        token in tiramisu
        for token in ("手指饼", "马斯卡彭", "咖啡", "可可", "tirami su", "把我拉起来")
    )
    assert "水果是这张图的摆盘，不必冒充经典配方" in tiramisu

    antibacterial = _copy(variants, "antibacterial-pig")
    assert all(
        token in antibacterial
        for token in ("盾牌", "99.9%", "检测报告未到", "不开心不是菌", "真正的测试条件")
    )
    assert all(
        token not in antibacterial
        for token in ("已证实杀菌率", "真实杀菌率99.9%", "可预防疾病", "医疗功效")
    )

    pigskin = _copy(variants, "pigskin-pig")
    assert all(token in pigskin for token in ("卷尾", "勿扰灯", "不等于结束", "休眠一晚"))
    assert all(token not in pigskin for token in ("自杀", "尸体", "死亡", "上吊"))

    muscle = _copy(variants, "muscle-pig")
    assert all(
        token in muscle
        for token in ("二头肌", "胸肌", "腹部", "大腿", "卷尾", "不是训练处方")
    )

    elephant = _copy(variants, "elephant-pig")
    assert "猪鼻子插大葱——装象（装相）" in elephant
    assert "没有象皮、象耳或真正长鼻" in elephant
    assert all(token not in elephant for token in ("披上灰色象皮", "扇动大耳朵", "真正象鼻"))

    hanging = _copy(variants, "hanging-pig")
    assert all(
        token in hanging
        for token in (
            "绕在小猪躯干前段",
            "并没有套住颈部",
            "载荷平衡",
            "下方不该站人",
            "不骑、不荡、不突然加速",
            "安全落地",
            "不是自伤场景",
        )
    )
    assert "不是习惯悬空，是安全完成一次吊运" in hanging
    assert all(
        token not in hanging
        for token in ("吊着吊着就习惯了", "上吊练习", "悬空很舒服", "继续晃两下")
    )

def test_phase13_repairs_materially_inaccurate_elephant_and_hanging_base_copy():
    catalog = _catalog_by_id()

    elephant = catalog["elephant-pig"]
    assert elephant["name"] == "装象猪"
    assert elephant["description"] == "猪鼻插葱，装相"
    assert "猪鼻子插大葱——装象（装相）" in elephant["analysis"]
    assert "没有披象皮，也没有长出真正象鼻" in elephant["analysis"]
    assert all(
        token not in elephant["analysis"]
        for token in ("披上灰色象皮", "扇动大耳朵", "长出大耳朵")
    )

    hanging = catalog["hanging-pig"]
    assert hanging["name"] == "吊运猪"
    assert hanging["description"] == "吊带绕身，安全落地"
    assert all(
        token in hanging["analysis"]
        for token in ("躯干前段", "并不在颈部", "清空载荷下方", "禁止骑乘与摇晃", "不是自伤场景")
    )
    assert all(token not in hanging["analysis"] for token in ("再晃两下", "上吊猪"))

def test_all_bundled_authored_copy_is_globally_unique(variants):
    catalog_ids = set(_catalog_by_id())
    assert set(variants) == catalog_ids
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

def test_phase8_research_boundaries_remain_visible_in_copy(variants):

    assert "猪突猛进" in variants["wild-boar"][3]["description"]
    assert "不顾四周" in variants["wild-boar"][3]["analysis"]
    assert "反串" in variants["pork-skewer"][3]["description"]
    assert "挑起争执" in variants["pork-skewer"][3]["analysis"]
    assert "带节奏" in variants["pork-skewer"][5]["description"]
    assert "fufu" in variants["doll-pig"][1]["analysis"]
    assert "初音" not in "".join(
        item["analysis"] for item in variants["doll-pig"].values()
    )
    assert "硬度" in variants["crystal-pig"][3]["analysis"]
    assert "韧性" in variants["crystal-pig"][3]["analysis"]
    assert "不是没上色" in variants["snow-pig"][1]["analysis"]
    assert "熊猫" in variants["black-white-pig"][3]["analysis"]
    assert "奶牛" in variants["black-white-pig"][3]["analysis"]
    combined_black_white = "".join(
        item["description"] + item["analysis"]
        for item in variants["black-white-pig"].values()
    )
    assert "Monokuro" not in combined_black_white
    assert "San-X" not in combined_black_white

def test_phase9_visual_and_reference_boundaries_remain_explicit(variants):

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
