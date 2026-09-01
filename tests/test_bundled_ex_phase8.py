from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
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


def _variants() -> dict[str, dict[int, dict[str, str]]]:
    pigs = json.loads((RESOURCE_DIR / "pig.json").read_text(encoding="utf-8-sig"))
    pig_ids = {
        str(item.get("id") or "")
        for item in pigs
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    return load_bundled_ex_copy(
        RESOURCE_DIR,
        pig_ids,
        pig_ids,
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )


def test_phase8_shard_reaches_effective_bundled_loader_text_only():
    variants = _variants()

    for pig_id, (ex1, ex5) in PHASE8_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())


def test_phase8_research_boundaries_remain_visible_in_copy():
    variants = _variants()

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


def test_display_copy_guard_scans_every_bundled_authoring_shard():
    source = (ROOT / "scripts/check_display_copy.py").read_text(encoding="utf-8")

    assert 'glob("bundled_ex_copy*.json")' in source
