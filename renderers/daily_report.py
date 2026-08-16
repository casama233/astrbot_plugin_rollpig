from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from PIL import ImageDraw


REPORT_WIDTH = 1200
REPORT_HEIGHT = 1280
REPORT_HEIGHT_WITH_SACRIFICE = 1390
REPORT_MAX_HEIGHT = 1400
PNG_COMPRESS_LEVEL = 1


_METRIC_META = (
    ("active_users", "活跃猪友", "今天在猪圈露过脸"),
    ("draws", "今日抽猪", "今天真正开过奖"),
    ("roasts", "成功上架", "后厨今天端走的猪"),
    ("eats", "今日被吃", "真的从名单里少掉了"),
    ("escapes", "成功逃脱", "从烤架边上跑掉"),
    ("backlashes", "触发反噬", "烤人不成反上桌"),
)

_EVENT_META = (
    ("draws", "抽猪"),
    ("roasts", "上烤架"),
    ("eats", "被吃"),
    ("escapes", "逃脱"),
    ("backlashes", "反噬"),
)

_AWARD_META = (
    ("roast_maniac", "烧烤狂人", "今天没人把烤箱玩疯，主厨准点下班。"),
    ("miserable_ingredient", "最惨食材", "今天没人长期躺烤架，食材区难得和平。"),
    ("escape_master", "逃脱大师", "今天没人成功跑路，大家都挺认命。"),
    ("backlash_king", "反噬之王", "后厨今天没炸，反噬之王请假一天。"),
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
    draws = int(report.get("draws", 0) or 0)
    roasts = int(report.get("roasts", 0) or 0)
    eats = int(report.get("eats", 0) or 0)
    escapes = int(report.get("escapes", 0) or 0)
    backlashes = int(report.get("backlashes", 0) or 0)
    refill = int(report.get("oven_refills", 0) or 0)
    supports = int(report.get("oven_refill_supports", 0) or 0)

    chaos = roasts + eats + escapes + backlashes
    if backlashes >= 2:
        return "翻车现场", f"今天反噬 {backlashes} 次，后厨锅盖已经开始申请工伤。"
    if roasts + eats >= max(3, draws // 3):
        return "后厨高温", f"今天上架 {roasts}、被吃 {eats}；大家显然不只来抽猪。"
    if escapes >= 2:
        return "集体跑路", f"今天有 {escapes} 次成功逃脱，烤架的尊严掉了一地。"
    if refill or supports:
        return "后厨补能", f"今天补货 {refill} 次、添柴 {supports} 人次，火还没打算下班。"
    if chaos == 0 and draws:
        return "纯抽猪局", f"{draws} 位群友安静抽猪，后厨今天罕见地没开火。"
    if draws:
        return "小火慢炖", f"{draws} 次抽猪，{chaos} 次搞事；今天总体还算克制。"
    return "猪圈休市", "今天还没什么动静，小猪们正在认真地假装营业。"


def _metric_color(palette: dict[str, tuple[int, int, int]], key: str):
    if key in {"roasts", "eats"}:
        return palette["danger"]
    if key == "escapes":
        return palette["good"]
    if key == "backlashes":
        return palette["warn"]
    return palette["accent"]


def _draw_metric(plugin, draw, palette, box, key, label, hint, value, scale) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, 24, fill=palette["surface"])
    value_font = plugin.font_bold.font_variant(size=38)
    label_font = plugin.font_bold.font_variant(size=20)
    hint_font = plugin.font_regular.font_variant(size=16)
    draw.text((left + 22, top + 15), str(value), font=value_font, fill=palette["title"])
    draw.text((left + 22, top + 61), label, font=label_font, fill=palette["secondary"])
    draw.text(
        (left + 22, top + 91),
        _fit_text(draw, hint, hint_font, right - left - 44),
        font=hint_font,
        fill=palette["muted"],
    )
    track_left, track_right = left + 22, right - 22
    track_y = bottom - 17
    draw.rounded_rectangle(
        (track_left, track_y, track_right, track_y + 7),
        4,
        fill=palette["surface_alt"],
    )
    if value > 0:
        ratio = min(1.0, value / max(1, scale))
        fill_right = max(
            track_left + 10,
            int(track_left + (track_right - track_left) * ratio),
        )
        draw.rounded_rectangle(
            (track_left, track_y, fill_right, track_y + 7),
            4,
            fill=_metric_color(palette, key),
        )


def _draw_event_chart(plugin, draw, report, palette, box) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, 28, fill=palette["surface"])
    title_font = plugin.font_bold.font_variant(size=29)
    label_font = plugin.font_bold.font_variant(size=19)
    value_font = plugin.font_bold.font_variant(size=18)
    small_font = plugin.font_regular.font_variant(size=16)
    draw.text((left + 28, top + 22), "今日搞事分布", font=title_font, fill=palette["title"])
    draw.text(
        (left + 28, top + 61),
        "条越长，今天越像是谁的主场。",
        font=small_font,
        fill=palette["muted"],
    )
    values = [int(report.get(key, 0) or 0) for key, _ in _EVENT_META]
    maximum = max(1, max(values, default=0))
    bar_left = left + 132
    bar_right = right - 60
    y = top + 99
    for (key, label), value in zip(_EVENT_META, values):
        dot = _metric_color(palette, key)
        draw.ellipse((left + 28, y + 4, left + 40, y + 16), fill=dot)
        draw.text((left + 50, y - 2), label, font=label_font, fill=palette["secondary"])
        draw.rounded_rectangle(
            (bar_left, y + 4, bar_right, y + 20),
            8,
            fill=palette["surface_alt"],
        )
        if value > 0:
            end = max(
                bar_left + 16,
                int(bar_left + (bar_right - bar_left) * value / maximum),
            )
            draw.rounded_rectangle(
                (bar_left, y + 4, end, y + 20),
                8,
                fill=dot,
            )
        value_text = str(value)
        text_w = draw.textlength(value_text, font=value_font)
        draw.text(
            (right - 26 - text_w, y - 2),
            value_text,
            font=value_font,
            fill=palette["title"],
        )
        y += 39


def _draw_popular(plugin, canvas, draw, report, palette, box) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, 28, fill=palette["surface"])
    title_font = plugin.font_bold.font_variant(size=29)
    name_font = plugin.font_bold.font_variant(size=27)
    body_font = plugin.font_regular.font_variant(size=17)
    accent_font = plugin.font_bold.font_variant(size=18)
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
        draw.text((left + 28, top + 86), headline, font=name_font, fill=palette["muted"])
        draw.text((left + 28, top + 127), copy, font=body_font, fill=palette["secondary"])
        return

    pig = popular[0]
    pig_id = str(pig.get("id") or "")
    path = plugin.find_image_file(pig_id)
    if path:
        try:
            thumb = plugin._fit_card_image(path, (116, 116))
            mask = PILImage.new("L", (116, 116), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, 115, 115), 24, fill=255)
            canvas.paste(thumb.convert("RGB"), (left + 28, top + 78), mask)
        except Exception:
            pass
    name = str(pig.get("name") or pig_id or "未知小猪")
    count = int(pig.get("count", 0) or 0)
    draw.text(
        (left + 166, top + 84),
        _fit_text(draw, name, name_font, right - left - 194),
        font=name_font,
        fill=palette["title"],
    )
    draw.text(
        (left + 168, top + 126),
        f"今天出现 {count} 次",
        font=accent_font,
        fill=palette["accent"],
    )
    copy = (
        "撞衫属于集体行为。"
        if len(popular) <= 1
        else f"另有 {len(popular) - 1} 种并列，今天撞衫是团建。"
    )
    draw.text((left + 168, top + 158), copy, font=body_font, fill=palette["secondary"])


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
    """Render a compact, chart-forward report using only existing truthful fields."""
    palette = plugin._report_palette()
    sacrifice_id = str(report.get("sacrifice_id") or "")
    height = REPORT_HEIGHT_WITH_SACRIFICE if sacrifice_id else REPORT_HEIGHT
    if height > REPORT_MAX_HEIGHT:
        raise ValueError("daily report canvas exceeds chat-safe height")

    canvas = PILImage.new("RGB", (REPORT_WIDTH, height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)
    title_font = plugin.font_bold.font_variant(size=54)
    date_font = plugin.font_bold.font_variant(size=22)
    hero_font = plugin.font_bold.font_variant(size=28)
    body_font = plugin.font_regular.font_variant(size=18)
    small_font = plugin.font_regular.font_variant(size=15)

    mood, story = _activity_story(report)
    draw.rounded_rectangle((36, 30, 1164, 190), 34, fill=palette["surface"])
    draw.text((70, 53), "猪圈日报", font=title_font, fill=palette["title"])
    draw.text((72, 123), str(report.get("date") or ""), font=date_font, fill=palette["accent"])
    draw.text(
        (270, 127),
        _fit_text(draw, story, body_font, 610),
        font=body_font,
        fill=palette["secondary"],
    )
    draw.rounded_rectangle((920, 58, 1128, 158), 24, fill=palette["accent_soft"])
    draw.text((946, 76), "今日主旋律", font=small_font, fill=palette["secondary"])
    draw.text((946, 105), mood, font=hero_font, fill=palette["accent"])

    metric_values = [int(report.get(key, 0) or 0) for key, _, _ in _METRIC_META]
    metric_scale = max(1, max(metric_values, default=0))
    for index, ((key, label, hint), value) in enumerate(zip(_METRIC_META, metric_values)):
        row, col = divmod(index, 3)
        x = 44 + col * 378
        y = 214 + row * 132
        _draw_metric(
            plugin,
            draw,
            palette,
            (x, y, x + 350, y + 116),
            key,
            label,
            hint,
            value,
            metric_scale,
        )

    _draw_event_chart(plugin, draw, report, palette, (44, 486, 674, 744))
    _draw_popular(plugin, canvas, draw, report, palette, (696, 486, 1156, 744))
    draw.text(
        (54, 765),
        f"今日补货 {int(report.get('oven_refills', 0) or 0)} 次 · 添柴 {int(report.get('oven_refill_supports', 0) or 0)} 人次",
        font=body_font,
        fill=palette["secondary"],
    )
    draw.text((54, 806), "今日猪圈名人堂", font=hero_font, fill=palette["title"])
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
