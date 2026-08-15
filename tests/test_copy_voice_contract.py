from __future__ import annotations

import json
from pathlib import Path

from player_copy import PLAYER_COPY, copy_placeholders


ROOT = Path(__file__).resolve().parents[1]


def test_help_locales_keep_the_same_keys_and_placeholders():
    traditional = PLAYER_COPY["zh-TW"]
    simplified = PLAYER_COPY["zh-CN"]
    assert set(traditional) == set(simplified)
    for key in traditional:
        assert copy_placeholders(traditional[key]) == copy_placeholders(simplified[key]), key


def test_help_copy_is_short_scan_first_and_still_rollpig():
    traditional = PLAYER_COPY["zh-TW"]
    simplified = PLAYER_COPY["zh-CN"]

    assert traditional["help.admin.panel_title"] == "管理面板"
    assert simplified["help.admin.panel_title"] == "管理面板"
    assert "新豬機率會提高" in traditional["help.mechanic.new_pig_pity"]
    assert "新猪概率会提高" in simplified["help.mechanic.new_pig_pity"]
    assert "全群添柴" in traditional["help.group.oven_refill"]
    assert "全群添柴" in simplified["help.group.oven_refill"]
    assert "補貨就添柴" in traditional["help.group.firewood_router"]
    assert "补货就添柴" in simplified["help.group.firewood_router"]
    assert "EX Lv.1–5" in traditional["help.mechanic.ex_growth"]
    assert "EX Lv.1–5" in simplified["help.mechanic.ex_growth"]

    # Quick-help copy must stay short enough to scan inside a chat image.
    for locale, catalog in PLAYER_COPY.items():
        for key, value in catalog.items():
            if key.startswith("help.") and ".section." not in key:
                assert len(value) <= 34, (locale, key, value)


def test_signature_gameplay_copy_keeps_the_rollpig_voice():
    oven = (ROOT / "oven_refill_feature.py").read_text(encoding="utf-8")
    firewood = (ROOT / "reservation_firewood_feature.py").read_text(encoding="utf-8")
    roast_policy = (ROOT / "services" / "roast_service.py").read_text(encoding="utf-8")
    legacy = (ROOT / "legacy_main.py").read_text(encoding="utf-8")

    assert "一个人搬柴不叫补货，叫加班" in oven
    assert "左手当主厨、右手再冒充群友" in firewood
    assert "猪身安全险" in roast_policy
    assert "后厨还没穷到要做闭环供应链" in legacy


def test_remastered_pigs_do_not_fall_back_to_personality_quiz_copy():
    pigs = json.loads((ROOT / "resource" / "pig.json").read_text(encoding="utf-8"))
    by_id = {
        str(item.get("id") or ""): str(item.get("analysis") or "")
        for item in pigs
        if isinstance(item, dict)
    }

    selected = {
        "rainbow-pig",
        "big-lazy-pig",
        "pig-turtle",
        "apple-pig",
        "piggy-bank",
        "juliet-pig",
        "streamer-pig",
        "repeater-pig",
        "burger-pig",
    }
    assert selected.issubset(by_id)

    stale_phrases = (
        "性格随和",
        "真诚又有魅力",
        "被动退让",
        "高贵的灵魂",
        "爱情理想主义者",
        "值得被别人捧在手心",
        "坚持不懈地努力",
        "象征着幸运和成功",
        "独特的个人魅力",
        "值得信赖的可靠前辈",
    )
    selected_copy = "\n".join(by_id[pig_id] for pig_id in sorted(selected))
    for phrase in stale_phrases:
        assert phrase not in selected_copy, phrase

    assert "上进心也想躺会儿" in by_id["big-lazy-pig"]
    assert "生态" in by_id["apple-pig"]
    assert "闭环" not in by_id["piggy-bank"]
    assert "原创内容几乎查无此猪" in by_id["repeater-pig"]
    assert "问题没解决，但热量上来了" in by_id["burger-pig"]


def test_copy_style_document_keeps_accuracy_before_the_joke():
    style = (ROOT / "docs" / "COPY-STYLE.md").read_text(encoding="utf-8")
    assert "先講結果／規則" in style
    assert "技術錯誤" in style
    assert "真實原因永遠優先於笑點" in style
    assert "禁止人格測評模板" in style
    assert "搬柴" in style
    assert "添煤" not in style
