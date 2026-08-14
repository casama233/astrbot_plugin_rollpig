from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, ImageOps


ImageResolver = Callable[[str, int | None], Path | None]


def get_text_size(
    text: str, font: ImageFont.FreeTypeFont
) -> tuple[int, int]:
    """Measure text compatibly across supported Pillow versions."""
    draw = ImageDraw.Draw(PILImage.new("RGB", (1, 1)))
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])
    except Exception:
        # Pillow kept textsize on older supported releases.
        return draw.textsize(text, font=font)


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


def fit_card_image(path: Path, size: tuple[int, int]) -> PILImage.Image:
    """Load one effective pig image and fit it into a renderer card slot."""
    with PILImage.open(path) as source:
        frame = ImageOps.exif_transpose(source).convert("RGBA")
        method = getattr(PILImage, "Resampling", PILImage).LANCZOS
        return ImageOps.fit(frame, size, method=method)
