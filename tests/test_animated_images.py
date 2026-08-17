from __future__ import annotations

import io
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageFont

from animated_image_feature import AnimatedImageMixin
from animated_images import (
    image_extension_from_bytes,
    image_mime_type_from_bytes,
    is_animated_gif_bytes,
    normalize_image_bytes,
)
from renderers.animated_pig_card import render_animated_pig_card


def _animated_gif_bytes() -> bytes:
    frames = [
        PILImage.new("RGBA", (24, 16), (255, 0, 0, 255)),
        PILImage.new("RGBA", (24, 16), (0, 0, 255, 255)),
    ]
    output = io.BytesIO()
    frames[0].save(
        output,
        "GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[80, 140],
        loop=3,
        disposal=2,
    )
    return output.getvalue()


def test_normalize_preserves_animated_gif_frames_timing_and_loop():
    normalized = normalize_image_bytes(_animated_gif_bytes())

    assert is_animated_gif_bytes(normalized)
    assert image_extension_from_bytes(normalized) == "gif"
    assert image_mime_type_from_bytes(normalized) == "image/gif"
    with PILImage.open(io.BytesIO(normalized)) as result:
        assert result.size == (512, 512)
        assert result.n_frames == 2
        assert result.info.get("loop") == 3
        durations = []
        for index in range(result.n_frames):
            result.seek(index)
            durations.append(result.info.get("duration"))
        assert durations == [80, 140]


def test_normalize_still_image_remains_png():
    source = io.BytesIO()
    PILImage.new("RGB", (20, 30), (12, 34, 56)).save(source, "JPEG")
    normalized = normalize_image_bytes(source.getvalue())

    assert normalized.startswith(b"\x89PNG\r\n\x1a\n")
    assert image_extension_from_bytes(normalized) == "png"
    with PILImage.open(io.BytesIO(normalized)) as result:
        assert result.size == (512, 512)
        assert result.n_frames == 1


def test_custom_image_writer_uses_gif_extension_and_removes_old_png(tmp_path: Path):
    class Dummy(AnimatedImageMixin):
        IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "gif")

        def __init__(self):
            self.custom_image_dir = tmp_path

    old = tmp_path / "pig.png"
    old.write_bytes(b"old")
    dummy = Dummy()
    dummy._write_custom_image("pig", normalize_image_bytes(_animated_gif_bytes()))

    assert not old.exists()
    target = tmp_path / "pig.gif"
    assert target.exists()
    assert is_animated_gif_bytes(target.read_bytes())


def test_animated_card_keeps_multiple_frames(tmp_path: Path):
    avatar = tmp_path / "pig.gif"
    avatar.write_bytes(normalize_image_bytes(_animated_gif_bytes(), (64, 64)))
    font_regular = ImageFont.truetype("DejaVuSans.ttf", 36)
    font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 66)
    output = render_animated_pig_card(
        {
            "id": "pig",
            "name": "Pig",
            "description": "Animated",
            "analysis": "two frame regression",
        },
        avatar_path=avatar,
        palette={
            "canvas": (23, 19, 22),
            "accent": (255, 120, 152),
            "title": (255, 255, 255),
            "body": (240, 240, 240),
            "secondary": (190, 190, 190),
        },
        font_bold=font_bold,
        font_regular=font_regular,
    )
    try:
        assert output is not None
        assert output.suffix == ".gif"
        with PILImage.open(output) as result:
            assert result.size == (800, 800)
            assert result.n_frames == 2
            assert result.info.get("loop") == 3
    finally:
        if output is not None:
            output.unlink(missing_ok=True)
