from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .common import PNG_COMPRESS_LEVEL, wrap_text


WEEKLY_WIDTH = 900
_MARGIN = 52
_PAPER = (247, 235, 216)
_INK = (41, 28, 24)
_RUBY = (135, 40, 58)
_RULE = (204, 170, 147)
_POLL_PAPER = (237, 215, 196)


def _text_lines(text: str, font, width: int) -> list[str]:
    return [
        line
        for paragraph in text.splitlines()
        for line in wrap_text(paragraph, font, width)
    ]


def _draw_pig_stamp(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((707, 42, 842, 177), outline=_RUBY, width=3)
    draw.ellipse((714, 49, 835, 170), outline=_RUBY, width=2)
    draw.polygon(((742, 86), (744, 68), (761, 82)), fill=_RUBY)
    draw.polygon(((788, 82), (805, 68), (807, 86)), fill=_RUBY)
    draw.ellipse((735, 80, 814, 143), fill=_RUBY)
    draw.ellipse((750, 96, 758, 104), fill=_PAPER)
    draw.ellipse((790, 96, 798, 104), fill=_PAPER)
    draw.rounded_rectangle((754, 111, 796, 132), radius=11, fill=_PAPER)
    draw.ellipse((762, 117, 769, 125), fill=_RUBY)
    draw.ellipse((780, 117, 787, 125), fill=_RUBY)


def render_weekly_tabloid(plugin, article: dict) -> Path:
    """Lay out a newspaper-style weekly edition with a readable voting stub."""
    regular = plugin.font_regular.font_variant
    bold = plugin.font_bold.font_variant
    title_font = bold(size=53)
    heading_font = bold(size=32)
    story_font = regular(size=32)
    label_font = regular(size=26)
    value_font = bold(size=36)

    title = wrap_text(article["title"], title_font, 610, max_lines=2)
    story = _text_lines(article["story"], story_font, WEEKLY_WIDTH - 2 * _MARGIN)
    poll_heading, *poll_lines = article["poll"]
    poll_width = WEEKLY_WIDTH - 2 * _MARGIN - 56
    poll_head = _text_lines(poll_heading, heading_font, poll_width)
    poll_body = [line for item in poll_lines for line in _text_lines(item, label_font, poll_width)]
    award_lines = [
        (
            f"{label} · {count}",
            wrap_text(players, label_font, 315, max_lines=2),
        )
        for label, players, count in article["awards"]
    ]

    masthead_bottom = max(170, 50 + len(title) * 62 + 45)
    story_bottom = masthead_bottom + 68 + 46 * len(story)
    stats_bottom = story_bottom + 208
    awards_height = 68 + 108 * ((len(award_lines) + 1) // 2) if award_lines else 0
    poll_top = stats_bottom + awards_height + 24
    poll_height = 64 + 42 * len(poll_head) + 40 * len(poll_body)
    height = poll_top + poll_height + 38

    canvas = Image.new("RGB", (WEEKLY_WIDTH, height), _PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, WEEKLY_WIDTH, 10), fill=_RUBY)
    _draw_pig_stamp(draw)
    for index, line in enumerate(title):
        draw.text((_MARGIN, 45 + index * 62), line, font=title_font, fill=_RUBY)
    draw.text((_MARGIN + 4, masthead_bottom - 40), article["period"], font=label_font, fill=_INK)
    draw.line((_MARGIN, masthead_bottom + 16, WEEKLY_WIDTH - _MARGIN, masthead_bottom + 16), fill=_RUBY, width=3)
    for index, line in enumerate(story):
        draw.text((_MARGIN, masthead_bottom + 43 + 46 * index), line, font=story_font, fill=_INK)
    draw.line((_MARGIN, story_bottom, WEEKLY_WIDTH - _MARGIN, story_bottom), fill=_RULE, width=2)

    column_width = (WEEKLY_WIDTH - 2 * _MARGIN) // 3
    for index, (label, total) in enumerate(article["stats"]):
        row, column = divmod(index, 3)
        x = _MARGIN + column * column_width
        y = story_bottom + 16 + row * 96
        draw.text((x, y), total, font=value_font, fill=_RUBY)
        for line_index, line in enumerate(wrap_text(label, label_font, column_width - 20, max_lines=2)):
            draw.text((x, y + 42 + line_index * 25), line, font=label_font, fill=_INK)
    draw.line((_MARGIN, stats_bottom, WEEKLY_WIDTH - _MARGIN, stats_bottom), fill=_RULE, width=2)

    if award_lines:
        draw.text((_MARGIN, stats_bottom + 16), article["awards_title"], font=heading_font, fill=_RUBY)
        for index, (label, players) in enumerate(award_lines):
            row, column = divmod(index, 2)
            x = _MARGIN + column * 400
            y = stats_bottom + 68 + row * 108
            draw.text((x, y), label, font=label_font, fill=_RUBY)
            for line_index, line in enumerate(players):
                draw.text((x, y + 35 + line_index * 29), line, font=label_font, fill=_INK)

    draw.rounded_rectangle(
        (_MARGIN, poll_top, WEEKLY_WIDTH - _MARGIN, poll_top + poll_height),
        radius=14, fill=_POLL_PAPER, outline=_RULE, width=2,
    )
    y = poll_top + 25
    for line in poll_head:
        draw.text((_MARGIN + 28, y), line, font=heading_font, fill=_RUBY)
        y += 42
    for line in poll_body:
        draw.text((_MARGIN + 28, y), line, font=label_font, fill=_INK)
        y += 40

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    try:
        canvas.save(output, "PNG", compress_level=PNG_COMPRESS_LEVEL)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return output
