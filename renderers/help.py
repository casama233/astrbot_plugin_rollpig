from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

try:
    from ..help_system import HelpEntry, HelpSection
    from ..wiki_links import WIKI_HOME_URL
except ImportError:  # pragma: no cover - direct module loading compatibility
    from help_system import HelpEntry, HelpSection
    from wiki_links import WIKI_HOME_URL


CARD_WIDTH = 1040
OUTER_MARGIN = 28
COLUMN_GAP = 18
HEADER_HEIGHT = 176
FOOTER_HEIGHT = 96
SECTION_GAP = 18
SECTION_HEADER_HEIGHT = 54
ROW_GAP = 8
DETAIL_LINE_HEIGHT = 24
PNG_COMPRESS_LEVEL = 1


@dataclass(frozen=True)
class PreparedEntry:
    entry: HelpEntry
    detail_lines: tuple[str, ...]
    height: int


@dataclass(frozen=True)
class PreparedSection:
    section: HelpSection
    entries: tuple[PreparedEntry, ...]
    height: int


def _font_variant(font: ImageFont.ImageFont, size: int) -> ImageFont.ImageFont:
    variant = getattr(font, "font_variant", None)
    if callable(variant):
        try:
            return variant(size=size)
        except Exception:
            pass
    return font


def _text_width(text: str, font: ImageFont.ImageFont) -> int:
    try:
        bbox = font.getbbox(text)
        return max(0, int(bbox[2] - bbox[0]))
    except Exception:
        return max(0, int(getattr(font, "getlength", lambda value: len(value) * 10)(text)))


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> tuple[str, ...]:
    """Width-wrap CJK-friendly text with logarithmic prefix probes."""

    text = str(text or "").strip()
    if not text:
        return ("",)
    max_width = max(1, int(max_width))
    if _text_width(text, font) <= max_width:
        return (text,)

    lines: list[str] = []
    start = 0
    while start < len(text):
        remaining = text[start:]
        if _text_width(remaining, font) <= max_width:
            lines.append(remaining)
            break
        low, high = 1, len(remaining)
        best = 1
        while low <= high:
            mid = (low + high) // 2
            if _text_width(remaining[:mid], font) <= max_width:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        lines.append(remaining[:best])
        start += best
    return tuple(lines)


def prepare_help_sections(
    sections: tuple[HelpSection, ...],
    *,
    detail_font: ImageFont.ImageFont,
    column_width: int,
) -> tuple[PreparedSection, ...]:
    """Pre-compute wrapping and heights once before allocating the canvas."""

    detail_width = max(80, column_width - 44)
    prepared: list[PreparedSection] = []
    for section in sections:
        rows: list[PreparedEntry] = []
        for entry in section.entries:
            lines = _wrap_text(entry.detail, detail_font, detail_width)
            row_height = 34 + max(1, len(lines)) * DETAIL_LINE_HEIGHT + 14
            rows.append(PreparedEntry(entry, lines, row_height))
        content_height = sum(row.height for row in rows)
        if rows:
            content_height += ROW_GAP * (len(rows) - 1)
        prepared.append(
            PreparedSection(
                section=section,
                entries=tuple(rows),
                height=SECTION_HEADER_HEIGHT + content_height + 18,
            )
        )
    return tuple(prepared)


def help_card_height(prepared: tuple[PreparedSection, ...]) -> int:
    """Return the compact two-column card height for the visible sections."""

    height = HEADER_HEIGHT + 18
    for index in range(0, len(prepared), 2):
        pair = prepared[index : index + 2]
        height += max(section.height for section in pair) + SECTION_GAP
    return max(640, height + FOOTER_HEIGHT - SECTION_GAP)


def _draw_entry(
    draw: ImageDraw.ImageDraw,
    prepared: PreparedEntry,
    *,
    left: int,
    top: int,
    right: int,
    command_font: ImageFont.ImageFont,
    detail_font: ImageFont.ImageFont,
    palette: dict,
) -> None:
    entry = prepared.entry
    accent = palette["accent"]
    title = palette["title"]
    secondary = palette["secondary"]
    muted_surface = palette["surface_muted"]

    draw.rounded_rectangle(
        (left, top, right, top + prepared.height),
        18,
        fill=muted_surface,
    )
    bar_fill = accent if entry.kind != "status" else palette.get("muted", accent)
    draw.rounded_rectangle((left + 13, top + 13, left + 18, top + 42), 3, fill=bar_fill)
    draw.text(
        (left + 29, top + 11),
        entry.command,
        font=command_font,
        fill=title,
    )
    detail_y = top + 43
    for line in prepared.detail_lines:
        draw.text(
            (left + 29, detail_y),
            line,
            font=detail_font,
            fill=secondary,
        )
        detail_y += DETAIL_LINE_HEIGHT


def _draw_section(
    draw: ImageDraw.ImageDraw,
    prepared: PreparedSection,
    *,
    box: tuple[int, int, int, int],
    section_font: ImageFont.ImageFont,
    command_font: ImageFont.ImageFont,
    detail_font: ImageFont.ImageFont,
    palette: dict,
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, 24, fill=palette["surface"])
    draw.text(
        (left + 22, top + 16),
        prepared.section.title,
        font=section_font,
        fill=palette["accent"],
    )

    row_top = top + SECTION_HEADER_HEIGHT
    for index, row in enumerate(prepared.entries):
        _draw_entry(
            draw,
            row,
            left=left + 14,
            top=row_top,
            right=right - 14,
            command_font=command_font,
            detail_font=detail_font,
            palette=palette,
        )
        row_top += row.height
        if index != len(prepared.entries) - 1:
            row_top += ROW_GAP


def render_help_card(
    sections: tuple[HelpSection, ...],
    *,
    palette: dict,
    font_bold: ImageFont.ImageFont,
    font_traditional: ImageFont.ImageFont | None = None,
) -> Path:
    """Render a compact help image with complete Traditional Chinese coverage.

    Pillow does not provide browser-style font fallback for missing glyphs. The
    bundled display font is intentionally decorative and does not cover every
    Traditional Chinese code point used by the zh-TW help catalog, so prefer the
    plugin's full Traditional CJK face when it is available. ``font_bold`` stays
    as a compatibility fallback for older installations and direct renderer use.
    """

    text_font = font_traditional or font_bold
    title_font = _font_variant(text_font, 50)
    subtitle_font = _font_variant(text_font, 20)
    section_font = _font_variant(text_font, 25)
    command_font = _font_variant(text_font, 20)
    detail_font = _font_variant(text_font, 17)
    badge_font = _font_variant(text_font, 16)
    footer_font = _font_variant(text_font, 16)
    footer_url_font = _font_variant(text_font, 14)

    column_width = (CARD_WIDTH - OUTER_MARGIN * 2 - COLUMN_GAP) // 2
    prepared = prepare_help_sections(
        sections,
        detail_font=detail_font,
        column_width=column_width,
    )
    height = help_card_height(prepared)

    canvas = PILImage.new("RGB", (CARD_WIDTH, height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)

    header_bottom = HEADER_HEIGHT - 12
    draw.rounded_rectangle(
        (OUTER_MARGIN, 22, CARD_WIDTH - OUTER_MARGIN, header_bottom),
        28,
        fill=palette["surface"],
    )
    draw.text(
        (OUTER_MARGIN + 30, 43),
        "今日小豬 · 指令幫助",
        font=title_font,
        fill=palette["title"],
    )
    draw.text(
        (OUTER_MARGIN + 32, 108),
        "只顯示目前已啟用功能 · 繁體／簡體別名均可使用",
        font=subtitle_font,
        fill=palette["secondary"],
    )
    badge = "DYNAMIC HELP"
    badge_width = _text_width(badge, badge_font) + 34
    badge_left = CARD_WIDTH - OUTER_MARGIN - badge_width - 24
    draw.rounded_rectangle(
        (badge_left, 58, CARD_WIDTH - OUTER_MARGIN - 24, 94),
        18,
        fill=palette["surface_muted"],
    )
    draw.text(
        (badge_left + 17, 66),
        badge,
        font=badge_font,
        fill=palette["accent"],
    )

    y = HEADER_HEIGHT + 6
    for index in range(0, len(prepared), 2):
        pair = prepared[index : index + 2]
        row_height = max(section.height for section in pair)
        for offset, section in enumerate(pair):
            left = OUTER_MARGIN + offset * (column_width + COLUMN_GAP)
            right = left + column_width
            _draw_section(
                draw,
                section,
                box=(left, y, right, y + row_height),
                section_font=section_font,
                command_font=command_font,
                detail_font=detail_font,
                palette=palette,
            )
        y += row_height + SECTION_GAP

    footer = "完整玩法 · 管理 · 投稿 · 排障，請前往 今日小豬 Wiki"
    footer_width = _text_width(footer, footer_font)
    draw.text(
        ((CARD_WIDTH - footer_width) // 2, height - 68),
        footer,
        font=footer_font,
        fill=palette["accent"],
    )
    url_width = _text_width(WIKI_HOME_URL, footer_url_font)
    draw.text(
        ((CARD_WIDTH - url_width) // 2, height - 40),
        WIKI_HOME_URL,
        font=footer_url_font,
        fill=palette["muted"],
    )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    canvas.save(output, "PNG", compress_level=PNG_COMPRESS_LEVEL)
    return output
