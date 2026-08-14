from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, ImageOps


ImageResolver = Callable[[str, int | None], Path | None]
PNG_COMPRESS_LEVEL = 1


def get_text_size(
    text: str, font: ImageFont.FreeTypeFont
) -> tuple[int, int]:
    """Measure text without allocating a scratch image on modern Pillow."""
    try:
        bbox = font.getbbox(text)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    except Exception:
        draw = ImageDraw.Draw(PILImage.new("RGB", (1, 1)))
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])
        except Exception:
            return draw.textsize(text, font=font)


def wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    *,
    max_lines: int | None = None,
    ellipsis: str = "…",
) -> list[str]:
    """Wrap text with logarithmic width probes instead of repeated prefix scans."""
    text = str(text or "")
    if not text:
        return []
    max_width = max(1, int(max_width))
    lines: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        if max_lines is not None and len(lines) >= max_lines:
            break
        remaining = text[start:]
        if get_text_size(remaining, font)[0] <= max_width:
            lines.append(remaining)
            break

        low, high = 1, len(remaining)
        best = 1
        while low <= high:
            mid = (low + high) // 2
            if get_text_size(remaining[:mid], font)[0] <= max_width:
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        segment = remaining[:best]
        has_more = start + best < text_len
        is_last_slot = max_lines is not None and len(lines) == max_lines - 1
        if is_last_slot and has_more:
            segment = segment.rstrip(ellipsis)
            while segment and get_text_size(segment + ellipsis, font)[0] > max_width:
                segment = segment[:-1]
            lines.append((segment or remaining[:1]) + ellipsis)
            break

        lines.append(segment)
        start += best
    return lines


def draw_bold_text(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    """Preserve the legacy synthetic-bold fallback."""
    x, y = pos
    for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        draw.text((x + ox, y + oy), text, fill=fill, font=font)
    draw.text((x, y), text, fill=fill, font=font)


@lru_cache(maxsize=192)
def _fit_card_image_cached(
    path_value: str,
    mtime_ns: int,
    file_size: int,
    width: int,
    height: int,
) -> PILImage.Image:
    del mtime_ns, file_size  # cache-key only
    path = Path(path_value)
    with PILImage.open(path) as source:
        frame = ImageOps.exif_transpose(source).convert("RGBA")
        method = getattr(PILImage, "Resampling", PILImage).LANCZOS
        return ImageOps.fit(frame, (width, height), method=method)


def clear_fit_card_image_cache() -> None:
    """Clear renderer thumbnails after an explicit resource reload."""
    _fit_card_image_cached.cache_clear()


def fit_card_image(path: Path, size: tuple[int, int]) -> PILImage.Image:
    """Load and fit one image, reusing bounded decoded thumbnails when unchanged."""
    path = Path(path)
    width, height = (max(1, int(size[0])), max(1, int(size[1])))
    stat = path.stat()
    cached = _fit_card_image_cached(
        str(path.resolve()),
        int(stat.st_mtime_ns),
        int(stat.st_size),
        width,
        height,
    )
    return cached.copy()


def save_png(image: PILImage.Image, path: Path) -> None:
    """Favor low CPU latency for transient chat images over maximum compression."""
    image.save(path, "PNG", compress_level=PNG_COMPRESS_LEVEL)
