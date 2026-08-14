from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, ImageOps

from .common import ImageResolver, fit_card_image, get_text_size

logger = logging.getLogger(__name__)


def render_pigsty(
    *,
    catalog: Sequence[Mapping[str, object]],
    user: Mapping[str, object],
    ordered_pigs: Sequence[Mapping[str, object]],
    favorite_name: str,
    page: int,
    total_pages: int,
    page_size: int,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    font_regular: ImageFont.FreeTypeFont,
    image_resolver: ImageResolver,
) -> tuple[Path, int]:
    """Render the permanent collection from an already prepared read model."""
    total = len(catalog)
    total_pages = max(1, int(total_pages))
    page = min(max(1, int(page)), total_pages)
    raw_unlocked = user.get("pigs", {}) if isinstance(user, Mapping) else {}
    unlocked = raw_unlocked if isinstance(raw_unlocked, Mapping) else {}
    catalog_ids = {str(pig.get("id") or "") for pig in catalog}
    unlocked_count = len(set(unlocked).intersection(catalog_ids))
    page_size = max(1, int(page_size))
    start = (page - 1) * page_size
    pigs = list(ordered_pigs[start : start + page_size])

    width, height = 900, 1260
    canvas = PILImage.new("RGB", (width, height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)
    title_font = font_bold.font_variant(size=52)
    stat_font = font_regular.font_variant(size=26)
    name_font = font_bold.font_variant(size=25)
    small_font = font_regular.font_variant(size=20)

    draw.rounded_rectangle((28, 24, 872, 195), 30, fill=palette["surface"])
    draw.text(
        (58, 45),
        "我的猪圈 · 永久图鉴",
        font=title_font,
        fill=palette["title"],
    )
    rate = (unlocked_count / total * 100) if total else 0
    stat = f"已解锁 {unlocked_count}/{total}  ·  收藏率 {rate:.1f}%"
    draw.text((60, 122), stat, font=stat_font, fill=palette["secondary"])

    favorite_name = str(favorite_name or "暂无")
    favorite_name = (
        favorite_name if len(favorite_name) <= 10 else favorite_name[:9] + "…"
    )
    highest_ex = max(
        (
            max(0, int(record.get("count", 0)) - 1)
            for record in unlocked.values()
            if isinstance(record, Mapping)
        ),
        default=0,
    )
    growth = (
        f"本命 {favorite_name}  ·  最高 EX Lv.{highest_ex}  ·  "
        f"累计 {int(user.get('total_draws', 0) or 0)} 次"
    )
    draw.text((60, 158), growth, font=small_font, fill=palette["muted"])

    card_w, card_h = 260, 218
    gap_x, gap_y = 30, 28
    origin_x, origin_y = 30, 220
    for index, pig in enumerate(pigs):
        row, col = divmod(index, 3)
        x = origin_x + col * (card_w + gap_x)
        y = origin_y + row * (card_h + gap_y)
        pig_id = str(pig.get("id") or "")
        is_unlocked = pig_id in unlocked
        bg = palette["surface"] if is_unlocked else palette["locked"]
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), 24, fill=bg)

        count = 0
        if is_unlocked:
            record = unlocked.get(pig_id, {})
            if isinstance(record, Mapping):
                count = int(record.get("count", 1) or 1)
            else:
                count = 1
        image_path = image_resolver(
            pig_id,
            max(0, count - 1) if is_unlocked else 0,
        )
        if image_path:
            try:
                thumb = fit_card_image(image_path, (130, 130))
                if not is_unlocked:
                    thumb = ImageOps.grayscale(thumb).convert("RGBA")
                    shade = PILImage.new("RGBA", thumb.size, (20, 16, 23, 120))
                    thumb = PILImage.alpha_composite(thumb, shade)
                mask = PILImage.new("L", thumb.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, 129, 129), 22, fill=255
                )
                canvas.paste(thumb.convert("RGB"), (x + 65, y + 16), mask)
            except Exception as exc:
                logger.warning("渲染图鉴小猪 %s 失败：%s", pig_id, exc)

        name = str(pig.get("name") or "未知小猪")
        if len(name) > 9:
            name = name[:8] + "…"
        name_w, _ = get_text_size(name, name_font)
        draw.text(
            (x + (card_w - name_w) // 2, y + 155),
            name,
            font=name_font,
            fill=palette["title"] if is_unlocked else palette["locked_text"],
        )
        label = (
            f"EX Lv.{max(0, count - 1)} · ×{count}"
            if is_unlocked
            else "尚未解锁"
        )
        label_w, _ = get_text_size(label, small_font)
        draw.text(
            (x + (card_w - label_w) // 2, y + 190),
            label,
            font=small_font,
            fill=palette["accent"] if is_unlocked else palette["muted"],
        )

    footer = (
        f"已解锁优先  ·  第 {page}/{total_pages} 页  ·  使用 /我的猪圈 页码 翻页"
    )
    footer_w, _ = get_text_size(footer, stat_font)
    draw.text(
        ((width - footer_w) // 2, 1210),
        footer,
        font=stat_font,
        fill=palette["secondary"],
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    canvas.save(output, "PNG", optimize=True)
    return output, page


def render_catalog_grid(
    pigs: Sequence[Mapping[str, object]],
    title: str,
    subtitle: str,
    *,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    font_regular: ImageFont.FreeTypeFont,
    image_resolver: ImageResolver,
) -> Path:
    """Render the random/search nine-grid from already selected pigs."""
    pigs = list(pigs[:9])
    rows = max(1, math.ceil(len(pigs) / 3))
    width, height = 900, 155 + rows * 245 + 30
    canvas = PILImage.new("RGB", (width, height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)
    title_font = font_bold.font_variant(size=48)
    subtitle_font = font_bold.font_variant(size=21)
    name_font = font_bold.font_variant(size=25)
    desc_font = font_regular.font_variant(size=18)
    draw.rounded_rectangle((28, 22, 872, 132), 28, fill=palette["surface"])
    safe_title = title if len(title) <= 18 else title[:17] + "…"
    safe_subtitle = subtitle if len(subtitle) <= 36 else subtitle[:35] + "…"
    draw.text((56, 40), safe_title, font=title_font, fill=palette["title"])
    draw.text(
        (58, 98),
        safe_subtitle,
        font=subtitle_font,
        fill=palette["secondary"],
    )
    for index, pig in enumerate(pigs):
        row, col = divmod(index, 3)
        x, y = 30 + col * 290, 155 + row * 245
        draw.rounded_rectangle(
            (x, y, x + 260, y + 218), 22, fill=palette["surface"]
        )
        path = image_resolver(
            str(pig.get("id") or ""),
            int(pig.get("_ex_level", 0) or 0),
        )
        if path:
            try:
                thumb = fit_card_image(path, (140, 140))
                mask = PILImage.new("L", thumb.size, 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    (0, 0, 139, 139), 20, fill=255
                )
                canvas.paste(thumb.convert("RGB"), (x + 60, y + 12), mask)
            except Exception as exc:
                logger.warning("渲染小猪列表图片失败：%s", exc)
        name = str(pig.get("name") or "未知小猪")
        name = name if len(name) <= 9 else name[:8] + "…"
        name_w, _ = get_text_size(name, name_font)
        draw.text(
            (x + (260 - name_w) // 2, y + 158),
            name,
            font=name_font,
            fill=palette["title"],
        )
        desc = str(pig.get("description") or "")
        desc = desc if len(desc) <= 14 else desc[:13] + "…"
        desc_w, _ = get_text_size(desc, desc_font)
        draw.text(
            (x + (260 - desc_w) // 2, y + 193),
            desc,
            font=desc_font,
            fill=palette["muted"],
        )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    canvas.save(output, "PNG", optimize=True)
    return output
