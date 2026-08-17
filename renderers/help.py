from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

try:
    from ..help_system import HelpEntry, HelpSection
except ImportError:  # pragma: no cover - direct module loading compatibility
    from help_system import HelpEntry, HelpSection


CARD_WIDTH = 1040
OUTER_MARGIN = 26
COLUMN_GAP = 16
HEADER_HEIGHT = 138
FOOTER_HEIGHT = 62
SECTION_GAP = 12
SECTION_HEADER_HEIGHT = 38
ROW_GAP = 3
COMMAND_ROW_HEIGHT = 44
FEATURE_ROW_HEIGHT = 36
SECTION_BOTTOM_PADDING = 12
COMMAND_COLUMN_WIDTH = 190
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


@dataclass(frozen=True)
class PlacedSection:
    prepared: PreparedSection
    column: int
    top: int


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


def _ellipsize_text(text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    """Keep help summaries to one visual line without overflowing the card."""

    text = str(text or "").strip()
    if not text:
        return ""
    max_width = max(1, int(max_width))
    if _text_width(text, font) <= max_width:
        return text

    suffix = "…"
    low, high = 0, len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid].rstrip() + suffix
        if _text_width(candidate, font) <= max_width:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best or suffix


def prepare_help_sections(
    sections: tuple[HelpSection, ...],
    *,
    detail_font: ImageFont.ImageFont,
    column_width: int,
) -> tuple[PreparedSection, ...]:
    """Pre-compute one-line summaries and compact section heights."""

    detail_width = max(
        80,
        column_width - 28 - COMMAND_COLUMN_WIDTH - 28,
    )
    prepared: list[PreparedSection] = []
    for section in sections:
        rows: list[PreparedEntry] = []
        for entry in section.entries:
            detail = _ellipsize_text(entry.detail, detail_font, detail_width)
            row_height = (
                COMMAND_ROW_HEIGHT if entry.kind == "command" else FEATURE_ROW_HEIGHT
            )
            rows.append(PreparedEntry(entry, (detail,), row_height))
        content_height = sum(row.height for row in rows)
        if rows:
            content_height += ROW_GAP * (len(rows) - 1)
        prepared.append(
            PreparedSection(
                section=section,
                entries=tuple(rows),
                height=(
                    SECTION_HEADER_HEIGHT
                    + content_height
                    + SECTION_BOTTOM_PADDING
                ),
            )
        )
    return tuple(prepared)


def _place_sections(
    prepared: tuple[PreparedSection, ...],
) -> tuple[tuple[PlacedSection, ...], int]:
    """Balance independent-height sections across two columns.

    The old renderer forced each left/right pair to the taller height, producing
    large empty slabs whenever a short section was paired with a long one. A
    tiny masonry layout preserves reading order while removing that dead space.
    """

    column_tops = [HEADER_HEIGHT + 6, HEADER_HEIGHT + 6]
    placed: list[PlacedSection] = []
    for section in prepared:
        column = 0 if column_tops[0] <= column_tops[1] else 1
        top = column_tops[column]
        placed.append(PlacedSection(section, column, top))
        column_tops[column] += section.height + SECTION_GAP

    bottom = max(column_tops) - (SECTION_GAP if prepared else 0)
    return tuple(placed), bottom


def help_card_height(prepared: tuple[PreparedSection, ...]) -> int:
    """Return compact masonry card height for the visible sections."""

    _placed, bottom = _place_sections(prepared)
    return max(560, bottom + FOOTER_HEIGHT)


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

    center_y = top + prepared.height // 2
    bar_height = 20 if entry.kind == "command" else 16
    bar_fill = accent if entry.kind != "status" else palette.get("muted", accent)
    draw.rounded_rectangle(
        (left, center_y - bar_height // 2, left + 4, center_y + bar_height // 2),
        2,
        fill=bar_fill,
    )

    command_x = left + 14
    detail_x = command_x + COMMAND_COLUMN_WIDTH
    command_fill = title if entry.kind == "command" else accent
    draw.text(
        (command_x, top + (10 if entry.kind == "command" else 7)),
        entry.command,
        font=command_font,
        fill=command_fill,
    )
    draw.text(
        (detail_x, top + (11 if entry.kind == "command" else 8)),
        prepared.detail_lines[0],
        font=detail_font,
        fill=secondary,
    )

    draw.line(
        (left + 14, top + prepared.height - 1, right, top + prepared.height - 1),
        fill=palette["surface_muted"],
        width=1,
    )


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
    left, top, right, _bottom = box
    draw.rounded_rectangle(box, 22, fill=palette["surface"])
    draw.text(
        (left + 20, top + 9),
        prepared.section.title,
        font=section_font,
        fill=palette["accent"],
    )

    row_top = top + SECTION_HEADER_HEIGHT
    for index, row in enumerate(prepared.entries):
        _draw_entry(
            draw,
            row,
            left=left + 16,
            top=row_top,
            right=right - 16,
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
    """Render a short, scan-first help image for the currently enabled features."""

    # The generated quick-command card is intentionally Simplified Chinese.
    # Keep the compatibility parameter, but never switch to the Traditional-only fallback.
    text_font = font_bold
    title_font = _font_variant(text_font, 44)
    subtitle_font = _font_variant(text_font, 17)
    section_font = _font_variant(text_font, 21)
    command_font = _font_variant(text_font, 17)
    detail_font = _font_variant(text_font, 15)
    footer_font = _font_variant(text_font, 15)

    column_width = (CARD_WIDTH - OUTER_MARGIN * 2 - COLUMN_GAP) // 2
    prepared = prepare_help_sections(
        sections,
        detail_font=detail_font,
        column_width=column_width,
    )
    placed, _bottom = _place_sections(prepared)
    height = help_card_height(prepared)

    canvas = PILImage.new("RGB", (CARD_WIDTH, height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle(
        (OUTER_MARGIN, 20, CARD_WIDTH - OUTER_MARGIN, 124),
        26,
        fill=palette["surface"],
    )
    draw.text(
        (OUTER_MARGIN + 26, 34),
        "今日小猪 · 快速指令",
        font=title_font,
        fill=palette["title"],
    )
    draw.text(
        (OUTER_MARGIN + 28, 91),
        "⚠ 带 @ 的指令请手动输入后再点选群友 · 复制他人整条发送可能无效",
        font=subtitle_font,
        fill=palette["accent"],
    )

    for item in placed:
        left = OUTER_MARGIN + item.column * (column_width + COLUMN_GAP)
        right = left + column_width
        section = item.prepared
        _draw_section(
            draw,
            section,
            box=(left, item.top, right, item.top + section.height),
            section_font=section_font,
            command_font=command_font,
            detail_font=detail_font,
            palette=palette,
        )

    footer = "完整规则 · 管理 · 投稿 · 排障 → 今日小猪 Wiki（下方有链接）"
    footer_width = _text_width(footer, footer_font)
    draw.text(
        ((CARD_WIDTH - footer_width) // 2, height - 39),
        footer,
        font=footer_font,
        fill=palette["accent"],
    )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    canvas.save(output, "PNG", compress_level=PNG_COMPRESS_LEVEL)
    return output
