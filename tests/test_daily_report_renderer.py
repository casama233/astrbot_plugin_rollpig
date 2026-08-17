from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from renderers.daily_report import (
    REPORT_HEIGHT,
    REPORT_HEIGHT_WITH_SACRIFICE,
    REPORT_MAX_HEIGHT,
    REPORT_WIDTH,
    _EVENT_META,
    _EVENT_ROW_STEP,
    _EVENT_ROW_TOP_OFFSET,
    _METRIC_CARD_HEIGHT,
    _METRIC_HINT_TOP_OFFSET,
    _METRIC_ROW_STEP,
    _METRIC_TRACK_BOTTOM_PADDING,
    _SUMMARY_PANEL_BOTTOM,
    _SUMMARY_PANEL_TOP,
    _activity_story,
    render_daily_report_dashboard,
)


ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "resource" / "font" / "荆南麦圆体.otf"


class _FakeReportPlugin:
    _REPORT_QUIPS = {
        "roast_maniac": "后厨正在考虑给他发长期工牌。",
        "miserable_ingredient": "今天基本没怎么离开过烤架。",
        "escape_master": "烤架至今没想明白他是怎么跑掉的。",
        "backlash_king": "你以为你在烤他，其实他在等你上桌。",
    }

    def __init__(self):
        self.font_regular = ImageFont.truetype(str(FONT), 24)
        self.font_bold = ImageFont.truetype(str(FONT), 28)

    def _report_palette(self):
        return {
            "canvas": (24, 19, 25),
            "surface": (48, 39, 49),
            "surface_alt": (62, 51, 62),
            "title": (246, 226, 232),
            "body": (235, 216, 222),
            "secondary": (199, 169, 180),
            "muted": (159, 128, 139),
            "accent": (255, 116, 157),
            "accent_soft": (92, 49, 68),
            "good": (119, 207, 169),
            "warn": (244, 181, 93),
            "danger": (238, 115, 131),
            "line": (85, 64, 78),
        }

    def _report_display_name(self, report, user_id, limit=16):
        name = str(report.get("profiles", {}).get(str(user_id), {}).get("display_name") or user_id)
        return name if len(name) <= limit else name[: max(1, limit - 1)] + "…"

    def _paste_report_avatar(self, canvas, draw, report, user_id, box, palette):
        draw.ellipse(box, fill=palette["accent_soft"], outline=palette["accent"], width=2)

    def find_image_file(self, pig_id):
        return None


def _report(*, sacrifice=False):
    report = {
        "date": "2026-08-16",
        "active_users": 16,
        "draws": 16,
        "roasts": 5,
        "eats": 2,
        "escapes": 3,
        "backlashes": 2,
        "oven_refill_supports": 6,
        "oven_refills": 1,
        "popular_pigs": [
            {"id": "salmon-sushi-pig", "name": "猪寿司拼盘", "count": 3},
            {"id": "black-pig", "name": "小黑猪", "count": 3},
        ],
        "pig_variety": 12,
        "popular_peak": 3,
        "awards": {
            "roast_maniac": {"value": 3, "winners": ["u1"]},
            "miserable_ingredient": {"value": 2, "winners": ["u2"]},
            "escape_master": {"value": 2, "winners": ["u3"]},
            "backlash_king": {"value": 2, "winners": ["u4", "u5"]},
        },
        "profiles": {
            "u1": {"display_name": "主厨一号"},
            "u2": {"display_name": "今日食材"},
            "u3": {"display_name": "跑路冠军"},
            "u4": {"display_name": "反噬一号"},
            "u5": {"display_name": "反噬二号"},
            "u6": {"display_name": "日报祭品"},
        },
        "avatars": {},
        "roast_detail_missing": 0,
    }
    if sacrifice:
        report["sacrifice_id"] = "u6"
    return report


def test_visual_daily_report_has_chat_safe_fixed_dimensions():
    plugin = _FakeReportPlugin()
    output = render_daily_report_dashboard(plugin, _report())
    try:
        with Image.open(output) as image:
            assert image.size == (REPORT_WIDTH, REPORT_HEIGHT)
            assert image.height <= REPORT_MAX_HEIGHT
    finally:
        output.unlink(missing_ok=True)


def test_sacrifice_report_still_stays_below_hard_height_cap():
    plugin = _FakeReportPlugin()
    output = render_daily_report_dashboard(plugin, _report(sacrifice=True))
    try:
        with Image.open(output) as image:
            assert image.size == (REPORT_WIDTH, REPORT_HEIGHT_WITH_SACRIFICE)
            assert image.height <= REPORT_MAX_HEIGHT
    finally:
        output.unlink(missing_ok=True)


def test_empty_daily_report_renders_without_inventing_activity():
    plugin = _FakeReportPlugin()
    empty = {
        "date": "2026-08-16",
        "awards": {},
        "profiles": {},
        "avatars": {},
    }
    mood, story = _activity_story(empty)
    assert mood == "猪圈休市"
    assert "还没什么动静" in story

    output = render_daily_report_dashboard(plugin, empty)
    try:
        with Image.open(output) as image:
            assert image.size == (REPORT_WIDTH, REPORT_HEIGHT)
    finally:
        output.unlink(missing_ok=True)


def test_main_keeps_daily_report_under_shared_render_backpressure():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "from .renderers.daily_report import render_daily_report_dashboard" in source
    assert "self._run_with_render_slot(render_daily_report_dashboard, self, report)" in source

def test_compact_layout_keeps_text_and_fifth_event_row_inside_their_cards():
    assert _METRIC_CARD_HEIGHT == 124
    assert _METRIC_ROW_STEP > _METRIC_CARD_HEIGHT
    track_y = _METRIC_CARD_HEIGHT - _METRIC_TRACK_BOTTOM_PADDING
    assert track_y - _METRIC_HINT_TOP_OFFSET >= 24

    panel_height = _SUMMARY_PANEL_BOTTOM - _SUMMARY_PANEL_TOP
    last_row_bar_bottom = (
        _EVENT_ROW_TOP_OFFSET
        + (len(_EVENT_META) - 1) * _EVENT_ROW_STEP
        + 20
    )
    # Reserve enough room after the fifth row for the in-panel refill summary.
    assert last_row_bar_bottom <= panel_height - 38
