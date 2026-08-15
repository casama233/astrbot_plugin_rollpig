from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable, Mapping

from PIL import Image as PILImage
from PIL import ImageDraw, ImageEnhance, ImageFont, ImageOps


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


@lru_cache(maxsize=192)
def _contain_card_image_cached(
    path_value: str,
    mtime_ns: int,
    file_size: int,
    width: int,
    height: int,
) -> PILImage.Image:
    """Decode one asset for thumbnail use without cropping transparent artwork."""
    del mtime_ns, file_size  # cache-key only
    path = Path(path_value)
    with PILImage.open(path) as source:
        frame = ImageOps.exif_transpose(source).convert("RGBA")
        method = getattr(PILImage, "Resampling", PILImage).LANCZOS
        return ImageOps.contain(frame, (width, height), method=method)


def clear_fit_card_image_cache() -> None:
    """Clear renderer image caches after an explicit resource reload."""
    _fit_card_image_cached.cache_clear()
    _contain_card_image_cached.cache_clear()


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


def contain_card_image(path: Path, size: tuple[int, int]) -> PILImage.Image:
    """Load one image inside ``size`` while preserving its complete aspect ratio."""
    path = Path(path)
    width, height = (max(1, int(size[0])), max(1, int(size[1])))
    stat = path.stat()
    cached = _contain_card_image_cached(
        str(path.resolve()),
        int(stat.st_mtime_ns),
        int(stat.st_size),
        width,
        height,
    )
    return cached.copy()


def _palette_rgb(
    palette: Mapping[str, object],
    key: str,
    fallback: tuple[int, int, int],
) -> tuple[int, int, int]:
    raw = palette.get(key, fallback)
    if isinstance(raw, (tuple, list)) and len(raw) >= 3:
        try:
            return tuple(max(0, min(255, int(value))) for value in raw[:3])  # type: ignore[return-value]
        except (TypeError, ValueError):
            pass
    return fallback


def _blend_rgb(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, float(amount)))
    return tuple(
        round(a + (b - a) * amount) for a, b in zip(left, right)
    )


def render_catalog_thumbnail(
    path: Path,
    size: tuple[int, int],
    *,
    palette: Mapping[str, object],
    locked: bool = False,
    radius: int = 20,
    padding: int = 9,
) -> PILImage.Image:
    """Render a Pigsty/catalog thumbnail with the management-panel visual model.

    The management page keeps transparent pig artwork on a pink-tinted surface.
    Chat-image catalog renderers previously converted RGBA assets to RGB before
    compositing, which turned transparent pixels black. This helper preserves
    alpha, supplies the same style of themed surface, and contains (rather than
    crops) unusual pig silhouettes such as hats, tails and long hair.
    """
    width, height = (max(1, int(size[0])), max(1, int(size[1])))
    radius = max(0, min(int(radius), min(width, height) // 2))
    padding = max(0, min(int(padding), max(0, min(width, height) // 2 - 1)))

    surface_rgb = _palette_rgb(palette, "surface", (43, 33, 38))
    accent_rgb = _palette_rgb(palette, "accent", (255, 120, 152))
    canvas_rgb = _palette_rgb(palette, "canvas", (23, 19, 22))
    # Mirror the panel's pink-soft -> strong-surface feeling without coupling the
    # Pillow renderer to CSS literals. The current image theme drives both ends.
    start_rgb = _blend_rgb(surface_rgb, accent_rgb, 0.16)
    end_rgb = _blend_rgb(surface_rgb, canvas_rgb, 0.10)

    gradient = PILImage.new("RGBA", (width, height))
    pixels: list[tuple[int, int, int, int]] = []
    denominator = max(1, width + height - 2)
    for y in range(height):
        for x in range(width):
            factor = (x + y) / denominator
            color = _blend_rgb(start_rgb, end_rgb, factor)
            pixels.append((*color, 255))
    gradient.putdata(pixels)

    rounded_mask = PILImage.new("L", (width, height), 0)
    ImageDraw.Draw(rounded_mask).rounded_rectangle(
        (0, 0, width - 1, height - 1), radius=radius, fill=255
    )
    surface = PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
    surface.paste(gradient, (0, 0), rounded_mask)

    inner_width = max(1, width - padding * 2)
    inner_height = max(1, height - padding * 2)
    artwork = contain_card_image(path, (inner_width, inner_height))
    if locked:
        alpha = artwork.getchannel("A")
        artwork = ImageOps.grayscale(artwork).convert("RGBA")
        artwork = ImageEnhance.Brightness(artwork).enhance(0.62)
        artwork.putalpha(alpha)

    offset = ((width - artwork.width) // 2, (height - artwork.height) // 2)
    surface.alpha_composite(artwork, dest=offset)
    return surface


def save_png(image: PILImage.Image, path: Path) -> None:
    """Favor low CPU latency for transient chat images over maximum compression."""
    image.save(path, "PNG", compress_level=PNG_COMPRESS_LEVEL)
