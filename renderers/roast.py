from __future__ import annotations

import hashlib
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


RECIPES = (
    ("蜜汁脆皮", "外脆里嫩，甜度刚好，今日烦恼全部烤化。"),
    ("炭火蒜香", "火候拉满，蒜香扑鼻，猪圈厨神认证出品。"),
    ("椒盐黄金", "咸香酥脆，一口下去好运值直接加满。"),
    ("慢烤照烧", "低温慢烤锁住快乐，再刷上一层闪亮好运。"),
    ("香草熔岩", "表面平静，内心滚烫，是今天最有戏的小猪料理。"),
)


def render_roast_card(
    pig: Mapping[str, object],
    *,
    user_id: str,
    draw_date: str,
    ai_copy: str | None,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
    image_resolver: ImageResolver,
) -> Path:
    """Render the existing roast dish card from explicit view inputs only."""
    seed = f"{user_id}:{draw_date}:{pig.get('id')}"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    recipe, copy = RECIPES[digest[0] % len(RECIPES)]
    if ai_copy:
        recipe = "AI 私房"
        copy = ai_copy

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
    source = "AI 料理" if ai_copy else "本地料理"
    draw.text(
        (64, 58),
        f"今日烤猪 · {source}",
        font=title_font,
        fill=palette["roast_title"],
    )

    pig_id = str(pig.get("id") or "")
    path = image_resolver(pig_id, None)
    if path:
        thumb = fit_card_image(path, (430, 430))
        warm = PILImage.new("RGBA", thumb.size, (232, 91, 38, 45))
        thumb = PILImage.alpha_composite(thumb, warm)
        canvas.paste(thumb.convert("RGB"), (185, 150))

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
