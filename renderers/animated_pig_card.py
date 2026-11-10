from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Mapping

from PIL import Image as PILImage
from PIL import ImageFont

try:
    from ..animated_images import load_fitted_gif_frames
except ImportError:  # pragma: no cover - direct module loading compatibility
    from animated_images import load_fitted_gif_frames

from .pig_card import (
    PigCardLayout,
    render_pig_card_frame,
)


logger = logging.getLogger(__name__)


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
        ex_level = (
            max(0, int(pig_data.get("_ex_level", 0) or 0))
            if "_ex_level" in pig_data
            else None
        )
        palette_mode = getattr(
            getattr(PILImage, "Palette", PILImage),
            "ADAPTIVE",
            getattr(PILImage, "ADAPTIVE", 1),
        )
        cards = [
            render_pig_card_frame(
                avatar,
                pig_name=pig_name,
                pig_desc=pig_desc,
                pig_analysis=pig_analysis,
                ex_level=ex_level,
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
