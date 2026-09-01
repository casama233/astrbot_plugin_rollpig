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
PHASE2_SENTINELS = {
    "android-pig": ("开发者选项已解锁", "冰箱也想刷系统"),
    "apple-pig": ("基础款，不基础价", "猪 Pro Max"),
    "early-class-pig": ("7:59 极限入教室", "早八人自动驾驶"),
    "error-404-pig": ("404 猪 Not Found", "错误页面成了主页"),
    "little-red-pig": ("拍完再吃", "全猪圈种成草原"),
    "pigsleep": ("服务器繁忙，请稍后撸", "AGI 未到，猪先睡了"),
    "repeater-pig": ("+1", "全群只剩回声"),
    "streamer-pig": ("家人们晚上好", "下播先把白菜吃了"),
}
PHASE3_SENTINELS = {
    "goblin-pig": ("外卖放门口，谢谢", "文明社会已退出"),
    "leek-pig": ("刚割完，又冒头了", "韭菜永动机"),
    "lemon-pig": ("我没酸，柠檬自己酸", "全群 pH 值下降"),
    "pig-die": ("今天听骰子的", "不满意就再 Roll"),
    "protagonist-pig": ("镜头呢？我到了", "全世界都是我的番外"),
    "spider-pig": ("我不是猪，我是 Bug", "Issue 区生态保护"),
    "teammate-pig": ("看我操作", "猪队友终身成就"),
    "watermelon-pig": ("前排吃瓜", "瓜吃群众"),
}
PHASE4_SENTINELS = {
    "abstract-pig": ("面数不足，猪味够", "再减就是猪方块"),
    "big-lazy-pig": ("先躺五分钟", "猪生已永久横屏"),
    "computer-pig": ("开机请等半小时", "答案出了：明天再看"),
    "fishing-pig": ("今天真摸到鱼了", "带薪摸鱼，功德圆满"),
    "landmine-pig": ("没事，先开一罐", "天亮了，箱也空了"),
    "pig-turtle": ("有事先缩一下", "问题还在，猪没了"),
    "stuck-pig": ("门：禁止本猪通过", "门框先辞职了"),
    "study-pig": ("书名有点针对猪", "知识改变命运：先跑路"),
}
PHASE5_SENTINELS = {
    "bacon": ("猪已切换条状", "煎熬到最后成早餐"),
    "bandage-pig": ("绷不住了（物理）", "木乃猪热修版"),
    "clean-pig": ("泥坑已被拉黑", "洗到猪圈开始反光"),
    "coder-pig": ("本地明明是好的", "服务崩了，我也崩了"),
    "delivery-pig": ("此面朝上，猪也朝上", "拆箱发现是活猪"),
    "dirty-pig": ("这是泥膜，不是脏", "泥坑原厂漆"),
    "homebody-pig": ("今天也不出门", "世界很大，Wi-Fi 满格"),
    "roasted-pig": ("火有点大", "生活下手，直接出餐"),
}
PHASE6_SENTINELS = {
    "cyberpunk-pig": ("义体开机，猪仍是猪", "未来到了，电量 1%"),
    "demon-pig": ("坏点子加载中", "全猪圈坏主意供应商"),
    "heaven-pig": ("盒饭领完，翅膀到账", "飞升成功，俗务照抢"),
    "pig-ball": ("请勿踢，本猪会滚", "滚了，真的滚了"),
    "pig-human": ("人模猪样", "物种字段填写失败"),
    "pig-stamp": ("此猪已盖章", "猪圈认证中心本猪"),
    "piggy-bank": ("投币后会哼", "钱存满了，出口没做"),
    "world-ruler-pig": ("地球是我的坐垫", "统治世界，午睡优先"),
}
PHASE7_SENTINELS = {
    "taffy-pig": ("关注塔菲谢谢喵", "永远喜欢塔菲喵"),
}
PHASE8_SENTINELS = {
    "black-pig": ("卤色已经挂满全身", "暗黑模式由我维护"),
    "black-white-pig": ("黑猪白猪合并安装", "黑白配色，本猪独占"),
    "crystal-pig": ("棱面先把彩虹拆开", "全猪圈最贵的易碎品"),
    "doll-pig": ("软乎乎已缝制上线", "Hand Made 猪圈孤品"),
    "pork-skewer": ("货真价实被串了", "只带孜然，不带节奏"),
    "snow-pig": ("白到轮廓要靠描边", "冬季保护色永久生效"),
    "soul-pig": ("灵魂先从猪身下班", "肉身离线，猪魂常驻"),
    "wild-boar": ("獠牙先替本猪发言", "野外版本没有刹车键"),
}
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
PHASE10_SENTINELS = {
    "buddha-pig": ("佛珠一转，全员佛猪", "一切随缘，佛猪成串"),
    "frozen-pig": ("物理冷静，冰块封装", "心如止水，止到结冰"),
    "invisible_pig": ("身体图层已设为透明", "透明度归零，围观不下线"),
    "lao_zhu_li": ("白胡子先把工龄报到", "老猪历，资历按年翻页"),
    "mc_porkchop": ("像素猪排已经烤熟", "生存背包里的压舱饭"),
    "pig_god": ("光环亮起，问题请排队", "智慧之神也不替你交卷"),
    "tank_pig": ("F 键已亮，驾驶位空着", "按 F 进入，前方请让猪"),
}
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
PHASE13_SENTINELS = {
    "alien-pig": ("荧光绿先突破地球色卡", "外星身份待验，配色已经登陆"),
    "antibacterial-pig": ("泡沫装箱，99.9%先印上", "剩下0.1%，确认就是本猪"),
    "bamboo-pig": ("猪笋破土，光环先到", "夺笋到封神，光环已到账"),
    "curator-pig": ("围裙系好，猪理人上岗", "主理一切，暂时不理人"),
    "elephant-pig": ("猪鼻插葱，先装半只象", "大象没装成，歇后语装完整"),
    "hanging-pig": ("吊带绕身，旧名字先撤回", "吊运结束，四蹄安全落地"),
    "muscle-pig": ("问就是练的，滤镜没这预算", "肌肉震场，猪鼻验明正身"),
    "pigskin-pig": ("电量耗尽，猪皮切到待机", "耗尽不等于结束，先充一晚"),
    "tiramisu-pig": ("提拉米苏换尾，提拉米猪", "请把我提起来，别切成块"),
    "upper-class-pig": ("红领结先替先生报到", "上流到最后，卷尾仍很诚实"),
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


def test_phase2_to_phase13_sentinel_copy_remains_handwritten():
    specs = _authored_specs()
    sentinels = {
        **PHASE2_SENTINELS,
        **PHASE3_SENTINELS,
        **PHASE4_SENTINELS,
        **PHASE5_SENTINELS,
        **PHASE6_SENTINELS,
        **PHASE7_SENTINELS,
        **PHASE8_SENTINELS,
        **PHASE9_SENTINELS,
        **PHASE10_SENTINELS,
        **PHASE11_SENTINELS,
        **PHASE12_SENTINELS,
        **PHASE13_SENTINELS,
    }
    for pig_id, (ex1, ex5) in sentinels.items():
        levels = specs[pig_id]["levels"]
        assert levels["1"]["description"] == ex1
        assert levels["5"]["description"] == ex5


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

    with pytest.raises(ValueError, match="分片重复定义小猪"):
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

    with pytest.raises(ValueError, match="只能引用 resource/pig.json"):
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

    with pytest.raises(ValueError, match="完整提供 EX1-EX5"):
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
