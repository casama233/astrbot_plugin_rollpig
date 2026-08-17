from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Mapping

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

try:
    from ..animated_images import load_fitted_gif_frames
except ImportError:  # pragma: no cover - direct module loading compatibility
    from animated_images import load_fitted_gif_frames

from .common import draw_bold_text, get_text_size, wrap_text
from .pig_card import PigCardLayout


logger = logging.getLogger(__name__)


def _render_frame(
    avatar: PILImage.Image,
    *,
    pig_name: str,
    pig_desc: str,
    pig_analysis: str,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    font_regular: ImageFont.FreeTypeFont,
    layout: PigCardLayout,
) -> PILImage.Image:
    canvas_width = layout.canvas_width
    canvas_height = layout.canvas_height
    canvas = PILImage.new("RGB", (canvas_width, canvas_height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)

    avatar_w = avatar_h = layout.avatar_size
    name_font = font_bold
    name_w, name_h = get_text_size(pig_name, name_font)
    desc_font = font_regular.font_variant(size=layout.desc_font_size)
    desc_w, desc_h = get_text_size(pig_desc, desc_font)
    analysis_font = font_regular.font_variant(size=layout.analysis_font_size)
    line_height = int(layout.analysis_font_size * layout.analysis_line_height_factor)
    max_analysis_width = int(canvas_width * layout.analysis_width_ratio)
    analysis_lines = wrap_text(
        pig_analysis,
        analysis_font,
        max_analysis_width,
        max_lines=6,
    )
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
    canvas.paste(
        avatar,
        (avatar_x, avatar_y),
        mask=avatar if avatar.mode == "RGBA" else None,
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
    return canvas


def render_animated_pig_card(
    pig_data: Mapping[str, object],
    *,
    avatar_path: Path,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    font_regular: ImageFont.FreeTypeFont,
    layout: PigCardLayout | None = None,
) -> Path | None:
    """Render the complete pig card for every GIF frame and preserve timing."""
    layout = layout or PigCardLayout()
    try:
        animation = load_fitted_gif_frames(
            Path(avatar_path),
            (layout.avatar_size, layout.avatar_size),
        )
        pig_name = str(pig_data.get("name", "未知小猪") or "未知小猪")
        pig_desc = str(pig_data.get("description", "无描述") or "无描述")
        pig_analysis = str(pig_data.get("analysis", "无解析") or "无解析")
        palette_mode = getattr(
            getattr(PILImage, "Palette", PILImage),
            "ADAPTIVE",
            getattr(PILImage, "ADAPTIVE", 1),
        )
        cards = [
            _render_frame(
                avatar,
                pig_name=pig_name,
                pig_desc=pig_desc,
                pig_analysis=pig_analysis,
                palette=palette,
                font_bold=font_bold,
                font_regular=font_regular,
                layout=layout,
            ).convert("P", palette=palette_mode, colors=256)
            for avatar in animation.frames
        ]
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
            output_path = Path(tmp.name)
        cards[0].save(
            output_path,
            "GIF",
            save_all=True,
            append_images=cards[1:],
            duration=list(animation.durations),
            loop=animation.loop,
            disposal=2,
            optimize=True,
        )
        return output_path
    except Exception as exc:
        logger.warning("动画小猪卡渲染失败，将回退静态卡：%s", exc)
        return None
