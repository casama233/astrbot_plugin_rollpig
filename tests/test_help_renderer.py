from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFont

from help_system import (
    HelpEntry,
    HelpFeatureState,
    HelpSection,
    build_help_sections,
)
from renderers import help as help_renderer
from renderers.help import (
    CARD_WIDTH,
    help_card_height,
    prepare_help_sections,
    render_help_card,
)


PALETTE = {
    "canvas": (24, 24, 28),
    "surface": (38, 38, 44),
    "surface_muted": (50, 50, 58),
    "title": (245, 245, 248),
    "secondary": (190, 190, 198),
    "muted": (145, 145, 155),
    "accent": (240, 120, 150),
}


def _sections(count: int, detail: str = "Short detail") -> tuple[HelpSection, ...]:
    return (
        HelpSection(
            "Commands",
            tuple(HelpEntry(f"/command-{index}", detail) for index in range(count)),
        ),
    )


def test_help_height_is_row_driven_and_long_copy_cannot_bloat_card():
    font = ImageFont.load_default()
    column_width = 480
    short = prepare_help_sections(
        _sections(1), detail_font=font, column_width=column_width
    )
    long_copy = prepare_help_sections(
        _sections(1, "A very long detail that would previously wrap " * 20),
        detail_font=font,
        column_width=column_width,
    )
    many_rows = prepare_help_sections(
        _sections(8), detail_font=font, column_width=column_width
    )

    assert help_card_height(short) == help_card_height(long_copy)
    assert help_card_height(many_rows) > help_card_height(short)
    assert len(long_copy[0].entries[0].detail_lines) == 1


def test_full_feature_help_stays_short_enough_for_chat_image_delivery():
    font = ImageFont.load_default()
    column_width = (CARD_WIDTH - 26 * 2 - 16) // 2
    sections = build_help_sections(
        HelpFeatureState(
            at_view_pig=True,
            enable_new_pig_pity=True,
            enable_daily_duplicate_pity=True,
            enable_roast=True,
            enable_group_roast=True,
            enable_roast_reservation=True,
            enable_oven_refill=True,
            enable_group_eat=True,
            enable_roast_protection=True,
            enable_ai_roast_copy=True,
            enable_daily_report=True,
            daily_report_auto_send=False,
            daily_report_random_eat_enabled=True,
        )
    )
    prepared = prepare_help_sections(
        sections,
        detail_font=font,
        column_width=column_width,
    )

    assert help_card_height(prepared) <= 1180


def test_help_renderer_matches_precomputed_dynamic_size():
    font = ImageFont.load_default()
    sections = (
        HelpSection(
            "Core",
            (
                HelpEntry("/today", "Draw today's pig"),
                HelpEntry("/week", "Show a compact weekly summary"),
            ),
        ),
        HelpSection(
            "Group",
            (HelpEntry("/roast", "Roast one group member when enabled"),),
        ),
    )
    column_width = (CARD_WIDTH - 26 * 2 - 16) // 2
    expected_height = help_card_height(
        prepare_help_sections(sections, detail_font=font, column_width=column_width)
    )

    output = render_help_card(sections, palette=PALETTE, font_bold=font)
    try:
        with Image.open(output) as rendered:
            assert rendered.size == (CARD_WIDTH, expected_height)
            assert rendered.format == "PNG"
    finally:
        output.unlink(missing_ok=True)


def test_help_renderer_uses_standard_bold_font_for_every_text_role(monkeypatch):
    primary = object()
    traditional = object()
    selected = []
    drawable_font = ImageFont.load_default()

    def track_variant(font, size):
        selected.append((font, size))
        return drawable_font

    monkeypatch.setattr(help_renderer, "_font_variant", track_variant)
    sections = (
        HelpSection(
            "猪圈日报",
            (
                HelpEntry("/猪圈日报", "把今天谁最惨、谁最能烤贴上日报"),
                HelpEntry("/猪圈日报状态", "看看晚报醒没醒"),
                HelpEntry("/猪圈日报开启／关闭", "管理员管开关"),
            ),
        ),
    )

    output = render_help_card(
        sections,
        palette=PALETTE,
        font_bold=primary,
        font_traditional=traditional,
    )
    try:
        assert selected
        assert all(font is primary for font, _size in selected)
        assert {size for _font, size in selected} == {44, 21, 17, 15}
    finally:
        output.unlink(missing_ok=True)


def test_help_renderer_fixed_copy_is_simplified_chinese():
    source = Path(help_renderer.__file__).read_text(encoding="utf-8")
    assert "今日小猪 · 快速指令" in source
    assert "只列已启用功能 · 每条只说一件事 · 简繁别名都可用" in source
    assert "完整规则 · 管理 · 投稿 · 排障 → 今日小猪 Wiki（下方有链接）" in source
    assert "今日小豬 · 快速指令" not in source
