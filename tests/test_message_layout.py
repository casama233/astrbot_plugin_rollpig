from pathlib import Path

from message_layout import mention_body_on_new_line


ROOT = Path(__file__).resolve().parents[1]


def test_mention_body_moves_copy_to_exactly_one_fresh_line():
    assert mention_body_on_new_line(" 🔥 刚抽完猪") == "\n🔥 刚抽完猪"
    assert mention_body_on_new_line("\n\n🪵 又有人添柴") == "\n🪵 又有人添柴"


def test_mention_body_preserves_internal_paragraph_breaks():
    assert (
        mention_body_on_new_line("  第一行\n第二行\n\n第三段")
        == "\n第一行\n第二行\n\n第三段"
    )
    assert mention_body_on_new_line("") == ""
    assert mention_body_on_new_line(None) == ""


def test_main_applies_layout_only_for_group_mentions():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "from .message_layout import mention_body_on_new_line" in source
    assert "from message_layout import mention_body_on_new_line" in source
    assert "async def _send_with_mention(" in source
    assert "if self._event_group_id(event)" in source
    assert "mention_body_on_new_line(text)" in source
    assert "super()._send_with_mention(event, user_id, body)" in source
