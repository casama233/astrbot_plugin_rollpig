from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, ImageOps

from .common import ImageResolver, draw_bold_text, get_text_size

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PigCardLayout:
    canvas_width: int = 800
    canvas_height: int = 800
    avatar_size: int = 280
    spacing_avatar_name: int = 20
    spacing_name_desc: int = 25
    spacing_desc_analysis: int = 30
    desc_font_size: int = 32
    analysis_font_size: int = 28
    analysis_line_height_factor: float = 1.6
    analysis_width_ratio: float = 0.85


def render_pig_card(
    pig_data: Mapping[str, object],
    *,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    font_regular: ImageFont.FreeTypeFont,
    image_resolver: ImageResolver,
    layout: PigCardLayout | None = None,
) -> Path | None:
    """Render one pig card without knowing storage, AstrBot events or sync state."""
    layout = layout or PigCardLayout()
    pig_id = str(pig_data.get("id", "") or "")
    pig_name = str(pig_data.get("name", "未知小猪") or "未知小猪")
    pig_desc = str(pig_data.get("description", "无描述") or "无描述")
    pig_analysis = str(pig_data.get("analysis", "无解析") or "无解析")

    canvas_width = layout.canvas_width
    canvas_height = layout.canvas_height
    canvas = PILImage.new("RGB", (canvas_width, canvas_height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)

    avatar_w = avatar_h = layout.avatar_size
    avatar = None
    avatar_path = image_resolver(
        pig_id, int(pig_data.get("_ex_level", 0) or 0)
    )
    if avatar_path:
        try:
            with PILImage.open(avatar_path) as source:
                method = getattr(PILImage, "Resampling", PILImage).LANCZOS
                avatar = ImageOps.fit(
                    ImageOps.exif_transpose(source).convert("RGBA"),
                    (avatar_w, avatar_h),
                    method,
                )
        except Exception as exc:
            logger.error("加载小猪图片失败：%s", exc)
            avatar = None

    name_font = font_bold
    name_w, name_h = get_text_size(pig_name, name_font)

    desc_font = font_regular.font_variant(size=layout.desc_font_size)
    desc_w, desc_h = get_text_size(pig_desc, desc_font)

    analysis_font = font_regular.font_variant(size=layout.analysis_font_size)
    line_height = int(
        layout.analysis_font_size * layout.analysis_line_height_factor
    )
    max_analysis_width = int(canvas_width * layout.analysis_width_ratio)
    analysis_lines: list[str] = []
    current_line = ""
    for char in pig_analysis:
        current_line += char
        line_w, _ = get_text_size(current_line, analysis_font)
        if line_w > max_analysis_width:
            analysis_lines.append(current_line[:-1])
            current_line = char
    if current_line:
        analysis_lines.append(current_line)
    max_analysis_lines = 6
    if len(analysis_lines) > max_analysis_lines:
        analysis_lines = analysis_lines[:max_analysis_lines]
        analysis_lines[-1] = analysis_lines[-1].rstrip("…") + "…"
    analysis_total_h = len(analysis_lines) * line_height

    total_content_h = (
        avatar_h
        + layout.spacing_avatar_name
        + name_h
        + layout.spacing_name_desc
        + desc_h
        + layout.spacing_desc_analysis
        + analysis_total_h
    )
    start_y = (canvas_height - total_content_h) // 2

    avatar_x = (canvas_width - avatar_w) // 2
    avatar_y = start_y
    if avatar:
        canvas.paste(
            avatar,
            (avatar_x, avatar_y),
            mask=avatar if avatar.mode == "RGBA" else None,
        )
    else:
        error_font = font_regular.font_variant(size=24)
        error_text = "图片加载失败"
        error_w, _ = get_text_size(error_text, error_font)
        error_x = (canvas_width - error_w) // 2
        draw.text(
            (error_x, avatar_y + 120),
            error_text,
            fill=palette["accent"],
            font=error_font,
        )

    name_y = avatar_y + avatar_h + layout.spacing_avatar_name
    name_x = (canvas_width - name_w) // 2
    draw_bold_text(
        draw,
        (name_x, name_y),
        pig_name,
        name_font,
        palette["title"],
    )

    desc_y = name_y + name_h + layout.spacing_name_desc
    desc_x = (canvas_width - desc_w) // 2
    draw.text(
        (desc_x, desc_y),
        pig_desc,
        fill=palette["body"],
        font=desc_font,
    )

    analysis_y = desc_y + desc_h + layout.spacing_desc_analysis
    for line in analysis_lines:
        line_w, _ = get_text_size(line, analysis_font)
        line_x = (canvas_width - line_w) // 2
        draw.text(
            (line_x, analysis_y),
            line,
            fill=palette["secondary"],
            font=analysis_font,
        )
        analysis_y += line_height

    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            canvas.save(tmp_path, format="PNG", quality=95)
        logger.debug("合成图片成功，临时文件路径：%s", tmp_path.absolute())
        if not tmp_path.exists():
            logger.error("临时文件创建失败：%s", tmp_path)
            return None
        return tmp_path
    except Exception as exc:
        logger.error("合成图片失败：%s", exc)
        return None
