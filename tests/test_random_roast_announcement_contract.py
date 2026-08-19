from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEATURE = (ROOT / "random_roast_feature.py").read_text(encoding="utf-8")


def test_random_roast_announcement_places_target_mention_inside_sentence():
    assert 'prefix = "🎲 随机转盘停在了 "' in FEATURE
    assert 'suffix = " 头上。后厨说：就你了。"' in FEATURE
    assert "Comp.Plain(prefix)" in FEATURE
    assert "Comp.At(qq=mention_id, name=telegram_name)" in FEATURE
    assert "Comp.Plain(suffix)" in FEATURE
    assert "await event.send(self._random_roast_target_announcement(event, target_id))" in FEATURE
    assert "随机转盘停在你头上" not in FEATURE


def test_random_roast_announcement_keeps_cross_platform_mention_fallbacks():
    assert 'platform_type in {"slack", "qq_official"}' in FEATURE
    assert 'f"{prefix}<@{mention_id}>{suffix}"' in FEATURE
    assert 'platform_type == "telegram"' in FEATURE
    assert 'f"{prefix}@{telegram_name}{suffix}"' in FEATURE
    assert "tg://user?id={mention_id}" in FEATURE
