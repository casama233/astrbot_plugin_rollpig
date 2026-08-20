from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Mapping

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from .common import (
    ImageResolver,
    fit_card_image,
    get_text_size,
    save_png,
    wrap_text,
)


logger = logging.getLogger(__name__)

_EMERGENCY_LOCAL_COPY = {
    "dish": "猪圈炭火特餐",
    "copy": "猪鼻一拱上烤架，今天不是翻身，是后厨很专业地帮你翻面。",
}
_ROAST_IMAGE_BOX = (185, 150, 615, 580)


def _draw_missing_pig_placeholder(
    draw: ImageDraw.ImageDraw,
    *,
    pig_id: str,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
) -> None:
    """Keep roast cards readable when the resolved pig image cannot be rendered."""
    left, top, right, bottom = _ROAST_IMAGE_BOX
    center_x = (left + right) // 2

    draw.rounded_rectangle(
        _ROAST_IMAGE_BOX,
        34,
        fill=palette["roast_canvas"],
        outline=palette["roast_outline"],
        width=4,
    )

    # A small vector pig face keeps the card visually intentional without
    # depending on another image asset that could be missing for the same reason.
    face_y = top + 145
    draw.ellipse(
        (center_x - 72, face_y - 72, center_x + 72, face_y + 72),
        fill=palette["roast_surface"],
        outline=palette["roast_outline"],
        width=4,
    )
    draw.polygon(
        (
            (center_x - 58, face_y - 48),
            (center_x - 94, face_y - 92),
            (center_x - 88, face_y - 24),
        ),
        fill=palette["roast_surface"],
        outline=palette["roast_outline"],
    )
    draw.polygon(
        (
            (center_x + 58, face_y - 48),
            (center_x + 94, face_y - 92),
            (center_x + 88, face_y - 24),
        ),
        fill=palette["roast_surface"],
        outline=palette["roast_outline"],
    )
    draw.ellipse(
        (center_x - 54, face_y - 8, center_x + 54, face_y + 55),
        fill=palette["roast_outline"],
    )
    draw.ellipse(
        (center_x - 32, face_y + 12, center_x - 14, face_y + 35),
        fill=palette["roast_canvas"],
    )
    draw.ellipse(
        (center_x + 14, face_y + 12, center_x + 32, face_y + 35),
        fill=palette["roast_canvas"],
    )

    label_font = font_bold.font_variant(size=28)
    detail_font = body_font.font_variant(size=19)
    label = "小猪图片暂不可用"
    label_w, _ = get_text_size(label, label_font)
    draw.text(
        (center_x - label_w // 2, top + 265),
        label,
        font=label_font,
        fill=palette["roast_title"],
    )
    detail = f"资源 ID：{pig_id or 'unknown'}"
    detail_w, _ = get_text_size(detail, detail_font)
    draw.text(
        (center_x - detail_w // 2, top + 318),
        detail,
        font=detail_font,
        fill=palette["roast_body"],
    )


def render_roast_card(
    pig: Mapping[str, object],
    *,
    user_id: str,
    draw_date: str,
    ai_copy: str | None,
    local_copy: Mapping[str, object] | None = None,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
    image_resolver: ImageResolver,
) -> Path:
    """Render one roast card from an already-selected AI or local copy."""
    del user_id, draw_date  # selection/repeat policy belongs to the caller.
    selected = local_copy if isinstance(local_copy, Mapping) else _EMERGENCY_LOCAL_COPY
    recipe = str(selected.get("dish") or _EMERGENCY_LOCAL_COPY["dish"])
    copy = str(selected.get("copy") or _EMERGENCY_LOCAL_COPY["copy"])
    if ai_copy:
        recipe = "AI 猪圈私房"
        copy = str(ai_copy)

    canvas = PILImage.new("RGB", (800, 870), palette["roast_canvas"])
    draw = ImageDraw.Draw(canvas)
    title_font = font_bold.font_variant(size=52)
    name_font = font_bold.font_variant(size=38)
    draw.rounded_rectangle(
        (34, 28, 766, 830),
        38,
        fill=palette["roast_surface"],
        outline=palette["roast_outline"],
        width=5,
    )
    source = "AI 猪话" if ai_copy else "猪圈本地话"
    draw.text(
        (64, 58),
        f"今日烤猪 · {source}",
        font=title_font,
        fill=palette["roast_title"],
    )

    pig_id = str(pig.get("id") or "")
    path = image_resolver(pig_id, None)
    image_drawn = False
    if path:
        try:
            thumb = fit_card_image(path, (430, 430))
            warm = PILImage.new("RGBA", thumb.size, (232, 91, 38, 45))
            thumb = PILImage.alpha_composite(thumb, warm)
            canvas.paste(thumb.convert("RGB"), (185, 150))
            image_drawn = True
        except Exception as exc:
            logger.warning(
                "烤猪卡小猪图片加载失败：pig_id=%s path=%s (%s)",
                pig_id or "<empty>",
                path,
                exc,
            )
    else:
        logger.warning("烤猪卡未解析到小猪图片：pig_id=%s", pig_id or "<empty>")

    if not image_drawn:
        _draw_missing_pig_placeholder(
            draw,
            pig_id=pig_id,
            palette=palette,
            font_bold=font_bold,
            body_font=body_font,
        )

    dish_name = f"{recipe}{pig.get('name', '小猪')}"
    dish_name = dish_name if len(dish_name) <= 16 else dish_name[:15] + "…"
    dish_w, _ = get_text_size(dish_name, name_font)
    draw.text(
        ((800 - dish_w) // 2, 625),
        dish_name,
        font=name_font,
        fill=palette["roast_title"],
    )

    lines = wrap_text(copy, body_font, 640, max_lines=3)
    for index, line in enumerate(lines):
        line_w, _ = get_text_size(line, body_font)
        draw.text(
            ((800 - line_w) // 2, 705 + index * 42),
            line,
            font=body_font,
            fill=palette["roast_body"],
        )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    save_png(canvas, output)
    return output
