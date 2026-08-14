from __future__ import annotations

from PIL import Image, ImageFont

from help_system import HelpEntry, HelpSection
from renderers.help import CARD_WIDTH, help_card_height, prepare_help_sections, render_help_card


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
    short = prepare_help_sections(_sections(1), detail_font=font, column_width=column_width)
    long = prepare_help_sections(
        _sections(8, "A much longer detail that should wrap over multiple lines " * 3),
        detail_font=font,
        column_width=column_width,
    )

    assert help_card_height(short) >= 640
    assert help_card_height(long) > help_card_height(short)
    assert help_card_height(short) != 1700


def test_help_renderer_matches_precomputed_dynamic_size(tmp_path):
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
