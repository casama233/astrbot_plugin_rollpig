from __future__ import annotations

from PIL import Image, ImageFont

from help_system import HelpEntry, HelpSection
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


def test_help_height_is_content_driven_not_fixed():
    font = ImageFont.load_default()
    column_width = 480
    short = prepare_help_sections(
        _sections(1), detail_font=font, column_width=column_width
    )
    long = prepare_help_sections(
        _sections(8, "A much longer detail that should wrap over multiple lines " * 3),
        detail_font=font,
        column_width=column_width,
    )

    assert help_card_height(short) >= 640
    assert help_card_height(long) > help_card_height(short)
    assert help_card_height(short) != 1700


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
    column_width = (CARD_WIDTH - 28 * 2 - 18) // 2
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


def test_help_renderer_prefers_traditional_font_for_every_text_role(monkeypatch):
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
            "豬圈日報",
            (
                HelpEntry("/豬圈日報", "把今天誰最慘、誰最能烤貼上日報"),
                HelpEntry("/豬圈日報狀態", "看看晚報醒沒醒"),
                HelpEntry("/豬圈日報開啟／關閉", "管理員管開關"),
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
        assert all(font is traditional for font, _size in selected)
        assert {size for _font, size in selected} == {50, 20, 25, 17, 16, 14}
    finally:
        output.unlink(missing_ok=True)
