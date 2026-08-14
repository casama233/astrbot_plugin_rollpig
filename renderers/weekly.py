from __future__ import annotations

import datetime
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from .common import ImageResolver, fit_card_image, get_text_size


@dataclass(frozen=True)
class WeeklyEntry:
    day: datetime.date
    pig: Mapping[str, object] | None
    was_eaten: bool = False


def render_weekly_summary(
    entries: Sequence[WeeklyEntry],
    *,
    today: datetime.date,
    monday: datetime.date,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    font_regular: ImageFont.FreeTypeFont,
    image_resolver: ImageResolver,
) -> Path:
    """Render a seven-day summary from storage-independent weekly entries."""
    canvas = PILImage.new("RGB", (900, 1080), palette["canvas"])
    draw = ImageDraw.Draw(canvas)
    title_font = font_bold.font_variant(size=50)
    body_font = font_bold.font_variant(size=27)
    small_font = font_regular.font_variant(size=20)
    draw.rounded_rectangle((28, 22, 872, 135), 28, fill=palette["surface"])
    draw.text(
        (56, 40),
        "本周小猪周报",
        font=title_font,
        fill=palette["title"],
    )
    draw.text(
        (58, 101),
        f"{monday.isoformat()} — {(monday + datetime.timedelta(days=6)).isoformat()}",
        font=small_font,
        fill=palette["secondary"],
    )
    weekday_names = [
        "星期一",
        "星期二",
        "星期三",
        "星期四",
        "星期五",
        "星期六",
        "星期日",
    ]
    collected = 0
    normalized = list(entries[:7])
    for index in range(7):
        day = monday + datetime.timedelta(days=index)
        entry = normalized[index] if index < len(normalized) else WeeklyEntry(day, None)
        pig = entry.pig
        was_eaten = bool(entry.was_eaten)
        y = 155 + index * 125
        active = day <= today
        fill = palette["surface"] if pig else palette["surface_muted"]
        draw.rounded_rectangle((34, y, 866, y + 104), 22, fill=fill)
        draw.text(
            (58, y + 19),
            weekday_names[index],
            font=body_font,
            fill=palette["body"],
        )
        draw.text(
            (58, y + 62),
            f"{day.month}/{day.day}",
            font=small_font,
            fill=palette["muted"],
        )
        if pig:
            collected += 1
            path = image_resolver(
                str(pig.get("id") or ""),
                int(pig.get("_ex_level", 0) or 0),
            )
            if path:
                try:
                    thumb = fit_card_image(path, (82, 82))
                    canvas.paste(thumb.convert("RGB"), (270, y + 11))
                except Exception:
                    pass
            pig_name = str(pig.get("name") or "未知小猪")
            pig_desc = str(pig.get("description") or "")
            pig_name = pig_name if len(pig_name) <= 14 else pig_name[:13] + "…"
            pig_desc = pig_desc if len(pig_desc) <= 28 else pig_desc[:27] + "…"
            draw.text(
                (378, y + 18),
                pig_name,
                font=body_font,
                fill=palette["title"],
            )
            draw.text(
                (378, y + 62),
                pig_desc,
                font=small_font,
                fill=palette["secondary"],
            )
            if was_eaten:
                badge = "被吃掉了"
                badge_w, _ = get_text_size(badge, small_font)
                badge_x = 842 - badge_w - 22
                draw.rounded_rectangle(
                    (badge_x - 12, y + 16, 846, y + 49),
                    14,
                    fill=(181, 71, 95),
                )
                draw.text(
                    (badge_x, y + 21),
                    badge,
                    font=small_font,
                    fill=(255, 244, 247),
                )
        else:
            status = "等待未来" if not active else "本日未抽取"
            draw.text(
                (300, y + 37),
                status,
                font=body_font,
                fill=palette["muted"],
            )
    summary = f"本周已签到 {collected}/7 天"
    summary_w, _ = get_text_size(summary, body_font)
    draw.text(
        ((900 - summary_w) // 2, 1040),
        summary,
        font=body_font,
        fill=palette["accent"],
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    canvas.save(output, "PNG", optimize=True)
    return output
