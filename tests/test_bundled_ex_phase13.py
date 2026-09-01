from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
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


def _catalog() -> list[dict]:
    return json.loads((RESOURCE_DIR / "pig.json").read_text(encoding="utf-8-sig"))


def _catalog_by_id() -> dict[str, dict]:
    return {
        str(item.get("id") or ""): item
        for item in _catalog()
        if isinstance(item, dict) and str(item.get("id") or "")
    }


def _variants() -> dict[str, dict[int, dict[str, str]]]:
    pig_ids = set(_catalog_by_id())
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


def test_phase13_shard_reaches_effective_bundled_loader_text_only():
    variants = _variants()

    for pig_id, (ex1, ex5) in PHASE13_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_phase13_visual_wordplay_research_and_safety_boundaries_remain_explicit():
    variants = _variants()

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


def test_all_99_bundled_pigs_now_have_globally_unique_handwritten_copy():
    variants = _variants()
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
