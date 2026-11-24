from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from PIL import ImageChops, ImageDraw

from .common import wrap_text


REPORT_WIDTH = 1200
REPORT_HEIGHT = 1280
REPORT_HEIGHT_WITH_SACRIFICE = 1390
REPORT_MAX_HEIGHT = 1400
PNG_COMPRESS_LEVEL = 1

_RECEIPT_LABEL = "猪圈日报 · 今日小票"
_LEDGER_TITLE = "今日记录明细"
_LEDGER_ROWS = (
    ("draws", "抽猪人数（人）"),
    ("pig_variety", "抽中猪种（种）"),
    ("roasts", "成功上桌（次）"),
    ("eats", "被吃人数（人）"),
    ("escapes", "逃脱次数（次）"),
    ("backlashes", "反噬次数（次）"),
    ("oven_refills", "实际补货（次）"),
    ("oven_refill_supports", "添柴人次（人次）"),
)

_HEADLINES = (
    (
        "backlashes",
        "炉膛反吞火把",
        "今天炉火反噬了 {backlashes} 次，铁钳把柄都烤出了焦油味。",
    ),
    (
        "escapes",
        "后栅栏又松了",
        "今天成功逃脱了 {escapes} 次，门闩被拱弯得连铁丝都缠不住。",
    ),
    (
        "eats",
        "食槽底被舔亮",
        "今天一共有 {eats} 人被吃，连刷槽的猪鬃扫把都啃秃了。",
    ),
    (
        "roasts",
        "热盘上桌",
        "烤架今天稳稳送出 {roasts} 次好货，铁托盘刚滑出炉口，出餐铃自己先响了两声。",
    ),
    (
        "oven_refills",
        "后厨推来新木箱",
        "炉膛里刚添进新货，今天累计 {oven_refills} 次实际补货，木箱盖子正搭在旁边。",
    ),
    (
        "oven_refill_supports",
        "炉膛添柴",
        "今天有 {oven_refill_supports} 人次往柴堆抱了木头，签收单在炉边夹得哗哗响，烤箱还在等着下一趟补货。",
    ),
    (
        "popular_peak",
        "签筒卡死同款",
        "同款猪最高被抽中 {popular_peak} 次，竹签上的漆全蹭在了同一面。",
    ),
    (
        "draws",
        "猪圈门口排长队",
        "今天共 {draws} 人进圈抽猪，木门槛被鞋底磨出一道凹槽。",
    ),
)

_EMPTY_HEADLINE = (
    "今天还没开张",
    "猪圈里暂时没动静，干草垛上的露水都没被拱散。",
)

_AWARD_META = (
    ("roast_maniac", "烧烤狂人", '今天没人折腾烤箱，主厨到点准时下班。'),
    ("miserable_ingredient", "最惨食材", '今天没人包场烤架，食材区难得风平浪静。'),
    ("escape_master", "逃脱大师", '今天没人成功越狱，大伙都乖乖排好队了。'),
    ("backlash_king", "反噬之王", '今天灶台没炸，反噬之王带薪休假一天。'),
)


def _fit_text(draw: ImageDraw.ImageDraw, text: object, font, max_width: int) -> str:
    value = str(text or "")
    if draw.textlength(value, font=font) <= max_width:
        return value
    suffix = "…"
    while value and draw.textlength(value + suffix, font=font) > max_width:
        value = value[:-1]
    return value + suffix if value else suffix


def _activity_story(report: dict[str, Any]) -> tuple[str, str]:
    for field, title, template in _HEADLINES:
        count = int(report.get(field, 0) or 0)
        if count > (1 if field == "popular_peak" else 0):
            return title, template.format(**{field: count})
    return _EMPTY_HEADLINE


def _draw_receipt(plugin, canvas, draw, report, palette) -> None:
    draw.rounded_rectangle((36, 30, 1164, 786), 30, fill=palette["surface"])
    for x in range(66, 1134, 24):
        draw.polygon(((x, 787), (x + 6, 778), (x + 12, 787)), fill=palette["canvas"])

    masthead_font = plugin.font_bold.font_variant(size=30)
    date_font = plugin.font_regular.font_variant(size=25)
    headline_font = plugin.font_bold.font_variant(size=54)
    story_font = plugin.font_regular.font_variant(size=32)
    draw.text((72, 60), _RECEIPT_LABEL, font=masthead_font, fill=palette["secondary"])
    draw.text(
        (1126, 67),
        str(report.get("date") or ""),
        font=date_font,
        fill=palette["secondary"],
        anchor="ra",
    )
    for x in range(72, 1124, 28):
        draw.line((x, 119, x + 15, 119), fill=palette["line"], width=2)
    title, story = _activity_story(report)
    draw.text((72, 150), title, font=headline_font, fill=palette["title"])
    for row, line in enumerate(wrap_text(story, story_font, 1056, max_lines=2)):
        draw.text((72, 234 + row * 43), line, font=story_font, fill=palette["body"])
    draw.line((72, 330, 1126, 330), fill=palette["line"], width=2)

    draw.text((72, 353), _LEDGER_TITLE, font=masthead_font, fill=palette["title"])
    label_font = plugin.font_regular.font_variant(size=25)
    value_font = plugin.font_bold.font_variant(size=28)
    for index, (field, label) in enumerate(_LEDGER_ROWS):
        y = 409 + index * 43
        value = str(int(report.get(field, 0) or 0))
        draw.text((72, y), label, font=label_font, fill=palette["body"])
        draw.text((632, y), value, font=value_font, fill=palette["title"], anchor="ra")
        draw.line((72, y + 34, 632, y + 34), fill=palette["line"])

    _draw_popular(plugin, canvas, draw, report, palette, (672, 352, 1128, 748))


def _draw_popular(plugin, canvas, draw, report, palette, box) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, 28, fill=palette["surface_alt"])
    title_font = plugin.font_bold.font_variant(size=29)
    name_font = plugin.font_bold.font_variant(size=27)
    body_font = plugin.font_regular.font_variant(size=20)
    accent_font = plugin.font_bold.font_variant(size=23)
    max_width = right - left - 56
    center = (left + right) // 2
    draw.text((left + 28, top + 22), "今日热猪榜", font=title_font, fill=palette["title"])
    popular = list(report.get("popular_pigs", []) or [])
    if not popular:
        variety = int(report.get("pig_variety", 0) or 0)
        peak = int(report.get("popular_peak", 0) or 0)
        if variety > 1 and peak == 1:
            headline = f"{variety} 种小猪各来一次"
            copy = "今天没有撞衫王，猪圈审美难得百花齐放。"
        else:
            headline = "暂时没有热门款"
            copy = "大家还没把同一只猪抽到能成立粉丝后援会。"
        headline_y = top + max(96, (bottom - top) // 2 - 28)
        draw.text((left + 28, headline_y), headline, font=name_font, fill=palette["muted"])
        for row, line in enumerate(wrap_text(copy, body_font, max_width, max_lines=2)):
            draw.text(
                (left + 28, headline_y + 45 + row * 30),
                line,
                font=body_font,
                fill=palette["body"],
            )
        return

    pig = popular[0]
    pig_id = str(pig.get("id") or "")
    path = plugin.find_image_file(pig_id)
    name_y = top + 128
    if path:
        try:
            thumb = plugin._fit_card_image(path, (152, 152)).convert("RGBA")
            mask = PILImage.new("L", thumb.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, 151, 151), 24, fill=255)
            canvas.paste(
                thumb, (center - 76, top + 82), ImageChops.multiply(thumb.getchannel("A"), mask)
            )
            name_y = top + 249
        except Exception:
            pass
    name = str(pig.get("name") or pig_id or "未知小猪")
    count = int(pig.get("count", 0) or 0)
    draw.text(
        (center, name_y),
        _fit_text(draw, name, name_font, max_width),
        font=name_font,
        fill=palette["title"],
        anchor="ma",
    )
    draw.text(
        (center, name_y + 46),
        f"今天出现 {count} 次",
        font=accent_font,
        fill=palette["title"],
        anchor="ma",
    )
    copy = (
        "撞衫属于集体行为。"
        if len(popular) <= 1
        else f"另有 {len(popular) - 1} 种并列，今天撞衫是团建。"
    )
    draw.text(
        (center, name_y + 86),
        _fit_text(draw, copy, body_font, max_width),
        font=body_font,
        fill=palette["body"],
        anchor="ma",
    )


def _draw_award(plugin, canvas, draw, report, palette, box, key, title, empty_copy) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, 24, fill=palette["surface"])
    title_font = plugin.font_bold.font_variant(size=22)
    name_font = plugin.font_bold.font_variant(size=24)
    small_font = plugin.font_regular.font_variant(size=16)
    draw.text((left + 22, top + 18), title, font=title_font, fill=palette["accent"])
    award = (report.get("awards", {}) or {}).get(key, {}) or {}
    winners = [str(value) for value in award.get("winners", []) if str(value)]
    value = int(award.get("value", 0) or 0)
    if not winners:
        draw.text(
            (left + 22, top + 60),
            "今天没人领走这个称号",
            font=name_font,
            fill=palette["muted"],
        )
        draw.text(
            (left + 22, top + 99),
            _fit_text(draw, empty_copy, small_font, right - left - 44),
            font=small_font,
            fill=palette["secondary"],
        )
        return
    winner = winners[0]
    plugin._paste_report_avatar(
        canvas,
        draw,
        report,
        winner,
        (right - 86, top + 18, right - 28, top + 76),
        palette,
    )
    draw.text(
        (left + 22, top + 58),
        _fit_text(
            draw,
            plugin._report_display_name(report, winner),
            name_font,
            right - left - 132,
        ),
        font=name_font,
        fill=palette["title"],
    )
    suffix = f"{value} 次" + (f" · 并列 {len(winners)} 人" if len(winners) > 1 else "")
    draw.text((left + 22, top + 94), suffix, font=small_font, fill=palette["accent"])
    quip = str(getattr(plugin, "_REPORT_QUIPS", {}).get(key, ""))
    draw.text(
        (left + 22, top + 122),
        _fit_text(draw, quip, small_font, right - left - 44),
        font=small_font,
        fill=palette["secondary"],
    )


def _draw_sacrifice(plugin, canvas, draw, report, palette, box) -> None:
    sacrifice_id = str(report.get("sacrifice_id") or "")
    if not sacrifice_id:
        return
    left, top, right, bottom = box
    draw.rounded_rectangle(
        box,
        26,
        fill=palette["surface"],
        outline=palette["danger"],
        width=2,
    )
    title_font = plugin.font_bold.font_variant(size=22)
    name_font = plugin.font_bold.font_variant(size=26)
    small_font = plugin.font_regular.font_variant(size=16)
    draw.text((left + 22, top + 16), "今日祭品", font=title_font, fill=palette["danger"])
    plugin._paste_report_avatar(
        canvas,
        draw,
        report,
        sacrifice_id,
        (left + 22, top + 53, left + 84, top + 115),
        palette,
    )
    draw.text(
        (left + 102, top + 58),
        plugin._report_display_name(report, sacrifice_id, 20),
        font=name_font,
        fill=palette["title"],
    )
    draw.text(
        (left + 102, top + 96),
        "晚报发出前还很完整，现在已经正式进入菜单。",
        font=small_font,
        fill=palette["secondary"],
    )


def render_daily_report_dashboard(plugin, report: dict[str, Any]) -> Path:
    """Render the group's daily activity and awards as a receipt."""
    palette = plugin._report_palette()
    sacrifice_id = str(report.get("sacrifice_id") or "")
    height = REPORT_HEIGHT_WITH_SACRIFICE if sacrifice_id else REPORT_HEIGHT
    if height > REPORT_MAX_HEIGHT:
        raise ValueError("daily report canvas exceeds chat-safe height")

    canvas = PILImage.new("RGB", (REPORT_WIDTH, height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)
    hero_font = plugin.font_bold.font_variant(size=28)
    small_font = plugin.font_regular.font_variant(size=15)

    _draw_receipt(plugin, canvas, draw, report, palette)
    draw.text((54, 818), "今日猪圈名人堂", font=hero_font, fill=palette["title"])
    for index, (key, title, empty_copy) in enumerate(_AWARD_META):
        row, col = divmod(index, 2)
        x = 44 + col * 566
        y = 850 + row * 170
        _draw_award(
            plugin,
            canvas,
            draw,
            report,
            palette,
            (x, y, x + 546, y + 150),
            key,
            title,
            empty_copy,
        )

    footer_y = 1204
    if sacrifice_id:
        _draw_sacrifice(
            plugin,
            canvas,
            draw,
            report,
            palette,
            (44, 1182, 1156, 1310),
        )
        footer_y = 1332
    draw.line((58, footer_y, 1142, footer_y), fill=palette["line"], width=2)
    detail_missing = int(report.get("roast_detail_missing", 0) or 0)
    footer = (
        f"另有 {detail_missing} 笔历史烤猪只有总量；称号只按可追溯事件统计。"
        if detail_missing > 0
        else "统计只记 RollPig 玩法事件 · 并列称号照实保留 · 明天继续看谁倒霉。"
    )
    draw.text((62, footer_y + 18), footer, font=small_font, fill=palette["muted"])

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    canvas.save(output, "PNG", compress_level=PNG_COMPRESS_LEVEL)
    return output
