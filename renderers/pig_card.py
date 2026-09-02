from __future__ import annotations

import logging
import tempfile
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from .common import (
    ImageResolver,
    draw_bold_text,
    fit_card_image,
    get_text_size,
    save_png,
    wrap_text,
)

logger = logging.getLogger(__name__)

PIG_CARD_CACHE_MAX_ITEMS = 32
PIG_CARD_CACHE_MAX_BYTES = 16 * 1024 * 1024
_PIG_CARD_CACHE_VERSION = 2
_pig_card_cache: OrderedDict[tuple[object, ...], bytes] = OrderedDict()
_pig_card_cache_bytes = 0
_pig_card_cache_lock = threading.RLock()


@dataclass(frozen=True)
class PigCardLayout:
    canvas_width: int = 800
    canvas_height: int = 800
    avatar_size: int = 280
    spacing_avatar_name: int = 20
    spacing_avatar_badge: int = 12
    spacing_badge_name: int = 14
    spacing_name_desc: int = 25
    spacing_desc_analysis: int = 30
    desc_font_size: int = 32
    analysis_font_size: int = 28
    analysis_line_height_factor: float = 1.6
    analysis_width_ratio: float = 0.85
    ex_badge_font_size: int = 24
    ex_badge_padding_x: int = 16
    ex_badge_padding_y: int = 7


def ex_level_badge_metrics(
    ex_level: int,
    font_regular: ImageFont.FreeTypeFont,
    layout: PigCardLayout,
) -> tuple[str, ImageFont.FreeTypeFont, int, int]:
    """Return the uncapped EX label and its compact pill geometry."""
    level = max(0, int(ex_level or 0))
    label = f"EX Lv.{level}"
    badge_font = font_regular.font_variant(size=max(1, layout.ex_badge_font_size))
    text_w, text_h = get_text_size(label, badge_font)
    width = text_w + max(0, layout.ex_badge_padding_x) * 2
    height = text_h + max(0, layout.ex_badge_padding_y) * 2
    return label, badge_font, width, height


def draw_ex_level_badge(
    draw: ImageDraw.ImageDraw,
    *,
    center_x: int,
    top: int,
    ex_level: int,
    palette: Mapping[str, object],
    font_regular: ImageFont.FreeTypeFont,
    layout: PigCardLayout,
) -> None:
    """Draw an explicit EX level pill without capping levels above EX5."""
    label, badge_font, width, height = ex_level_badge_metrics(
        ex_level,
        font_regular,
        layout,
    )
    left = int(center_x - width / 2)
    right = left + width
    bottom = top + height
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=max(1, height // 2),
        fill=palette["accent"],
    )
    try:
        bbox = draw.textbbox((0, 0), label, font=badge_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = left + (width - text_w) // 2 - bbox[0]
        text_y = top + (height - text_h) // 2 - bbox[1]
    except Exception:
        text_w, text_h = get_text_size(label, badge_font)
        text_x = left + (width - text_w) // 2
        text_y = top + (height - text_h) // 2
    draw.text(
        (text_x, text_y),
        label,
        fill=palette["canvas"],
        font=badge_font,
    )


def _font_identity(font: ImageFont.FreeTypeFont) -> tuple[object, ...]:
    try:
        name = tuple(font.getname())
    except Exception:
        name = (font.__class__.__name__,)
    return (
        str(getattr(font, "path", "") or ""),
        name,
        int(getattr(font, "size", 0) or 0),
        int(getattr(font, "index", 0) or 0),
    )


def _avatar_identity(path: Path | None) -> tuple[tuple[object, ...], bool]:
    if path is None:
        return ("", 0, 0), True
    path = Path(path)
    try:
        stat = path.stat()
        return (
            str(path.resolve()),
            int(stat.st_mtime_ns),
            int(stat.st_size),
        ), True
    except OSError:
        return (str(path), -1, -1), False


def _palette_identity(palette: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    keys = ("canvas", "accent", "title", "body", "secondary")
    return tuple((key, repr(palette.get(key))) for key in keys)


def _get_cached_pig_card(key: tuple[object, ...]) -> bytes | None:
    with _pig_card_cache_lock:
        payload = _pig_card_cache.get(key)
        if payload is None:
            return None
        _pig_card_cache.move_to_end(key)
        return payload


def _remember_pig_card(key: tuple[object, ...], payload: bytes) -> None:
    global _pig_card_cache_bytes
    if not payload or len(payload) > PIG_CARD_CACHE_MAX_BYTES:
        return
    with _pig_card_cache_lock:
        previous = _pig_card_cache.pop(key, None)
        if previous is not None:
            _pig_card_cache_bytes -= len(previous)
        _pig_card_cache[key] = payload
        _pig_card_cache_bytes += len(payload)
        while (
            len(_pig_card_cache) > PIG_CARD_CACHE_MAX_ITEMS
            or _pig_card_cache_bytes > PIG_CARD_CACHE_MAX_BYTES
        ):
            _old_key, old_payload = _pig_card_cache.popitem(last=False)
            _pig_card_cache_bytes -= len(old_payload)


def clear_pig_card_cache() -> None:
    """Drop completed-card bytes, primarily for tests and explicit maintenance."""
    global _pig_card_cache_bytes
    with _pig_card_cache_lock:
        _pig_card_cache.clear()
        _pig_card_cache_bytes = 0


def _write_temp_png(payload: bytes) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(payload)
        return Path(tmp.name)


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
    ex_level = max(0, int(pig_data.get("_ex_level", 0) or 0))
    show_ex_badge = "_ex_level" in pig_data

    avatar_path = image_resolver(pig_id, ex_level)
    avatar_key, cacheable = _avatar_identity(avatar_path)
    cache_key: tuple[object, ...] = (
        _PIG_CARD_CACHE_VERSION,
        pig_id,
        pig_name,
        pig_desc,
        pig_analysis,
        ex_level,
        show_ex_badge,
        layout,
        _palette_identity(palette),
        _font_identity(font_bold),
        _font_identity(font_regular),
        avatar_key,
    )
    cached = _get_cached_pig_card(cache_key) if cacheable else None
    if cached is not None:
        try:
            output = _write_temp_png(cached)
            logger.debug("复用已合成的小猪卡缓存：%s", output.absolute())
            return output
        except OSError as exc:
            logger.warning("写入小猪卡缓存临时文件失败，将重新渲染：%s", exc)

    canvas_width = layout.canvas_width
    canvas_height = layout.canvas_height
    canvas = PILImage.new("RGB", (canvas_width, canvas_height), palette["canvas"])
    draw = ImageDraw.Draw(canvas)

    avatar_w = avatar_h = layout.avatar_size
    avatar = None
    if avatar_path:
        try:
            avatar = fit_card_image(avatar_path, (avatar_w, avatar_h))
        except Exception as exc:
            logger.error("加载小猪图片失败：%s", exc)
            avatar = None
            cacheable = False

    name_font = font_bold
    name_w, name_h = get_text_size(pig_name, name_font)

    badge_h = 0
    if show_ex_badge:
        _label, _badge_font, _badge_w, badge_h = ex_level_badge_metrics(
            ex_level,
            font_regular,
            layout,
        )

    desc_font = font_regular.font_variant(size=layout.desc_font_size)
    desc_w, desc_h = get_text_size(pig_desc, desc_font)

    analysis_font = font_regular.font_variant(size=layout.analysis_font_size)
    line_height = int(
        layout.analysis_font_size * layout.analysis_line_height_factor
    )
    max_analysis_width = int(canvas_width * layout.analysis_width_ratio)
    analysis_lines = wrap_text(
        pig_analysis,
        analysis_font,
        max_analysis_width,
        max_lines=6,
    )
    analysis_total_h = len(analysis_lines) * line_height

    avatar_name_spacing = layout.spacing_avatar_name
    if show_ex_badge:
        avatar_name_spacing = (
            layout.spacing_avatar_badge + badge_h + layout.spacing_badge_name
        )
    total_content_h = (
        avatar_h
        + avatar_name_spacing
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

    if show_ex_badge:
        badge_y = avatar_y + avatar_h + layout.spacing_avatar_badge
        draw_ex_level_badge(
            draw,
            center_x=canvas_width // 2,
            top=badge_y,
            ex_level=ex_level,
            palette=palette,
            font_regular=font_regular,
            layout=layout,
        )
        name_y = badge_y + badge_h + layout.spacing_badge_name
    else:
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
        save_png(canvas, tmp_path)
        logger.debug("合成图片成功，临时文件路径：%s", tmp_path.absolute())
        if not tmp_path.exists():
            logger.error("临时文件创建失败：%s", tmp_path)
            return None
        if cacheable:
            try:
                _remember_pig_card(cache_key, tmp_path.read_bytes())
            except OSError as exc:
                logger.debug("读取小猪卡缓存内容失败：%s", exc)
        return tmp_path
    except Exception as exc:
        logger.error("合成图片失败：%s", exc)
        return None
