from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage

from renderers.common import render_catalog_thumbnail


PALETTE = {
    "canvas": (23, 19, 22),
    "surface": (43, 33, 38),
    "accent": (255, 120, 152),
}


def _write_rgba(path: Path, size: tuple[int, int], color=(255, 40, 60, 255)) -> None:
    image = PILImage.new("RGBA", size, (0, 0, 0, 0))
    left = max(1, size[0] // 10)
    top = max(1, size[1] // 10)
    right = max(left + 1, size[0] - left)
    bottom = max(top + 1, size[1] - top)
    for y in range(top, bottom):
        for x in range(left, right):
            image.putpixel((x, y), color)
    image.save(path)


def test_catalog_thumbnail_keeps_transparency_off_black_background(tmp_path: Path):
    source = tmp_path / "transparent-pig.png"
    _write_rgba(source, (80, 80))

    thumb = render_catalog_thumbnail(
        source,
        (120, 120),
        palette=PALETTE,
        radius=20,
        padding=10,
    )

    # Rounded outer corners remain transparent so the parent card can show
    # through, while transparent pixels inside the artwork receive the themed
    # pink/surface background instead of RGB conversion black.
    assert thumb.mode == "RGBA"
    assert thumb.getpixel((0, 0))[3] == 0
    inner = thumb.getpixel((20, 20))
    assert inner[3] == 255
    assert inner[:3] != (0, 0, 0)
    assert inner[0] > inner[1]


def test_catalog_thumbnail_contains_wide_art_without_square_crop(tmp_path: Path):
    source = tmp_path / "wide-pig.png"
    PILImage.new("RGBA", (200, 50), (250, 10, 20, 255)).save(source)

    thumb = render_catalog_thumbnail(
        source,
        (120, 120),
        palette=PALETTE,
        radius=20,
        padding=10,
    )

    subject_pixels = [
        (x, y)
        for y in range(120)
        for x in range(120)
        if (lambda px: px[0] > 220 and px[1] < 40 and px[2] < 50)(
            thumb.getpixel((x, y))
        )
    ]
    xs = [point[0] for point in subject_pixels]
    ys = [point[1] for point in subject_pixels]
    assert max(xs) - min(xs) >= 95
    assert max(ys) - min(ys) <= 30


def test_locked_catalog_thumbnail_grays_and_darkens_only_artwork(tmp_path: Path):
    source = tmp_path / "locked-pig.png"
    PILImage.new("RGBA", (60, 60), (240, 30, 50, 255)).save(source)

    unlocked = render_catalog_thumbnail(
        source,
        (100, 100),
        palette=PALETTE,
        padding=12,
    )
    locked = render_catalog_thumbnail(
        source,
        (100, 100),
        palette=PALETTE,
        locked=True,
        padding=12,
    )

    unlocked_subject = unlocked.getpixel((50, 50))
    locked_subject = locked.getpixel((50, 50))
    assert max(locked_subject[:3]) - min(locked_subject[:3]) <= 1
    assert sum(locked_subject[:3]) < sum(unlocked_subject[:3])
    # x=8 is outside the contained artwork (which starts at x=12) but remains
    # safely inside the rounded surface at the vertical center.
    assert locked.getpixel((8, 50)) == unlocked.getpixel((8, 50))


def test_catalog_renderers_share_the_alpha_safe_thumbnail_helper():
    source = Path("renderers/catalog.py").read_text(encoding="utf-8")
    assert source.count("render_catalog_thumbnail(") == 2
    assert 'thumb.convert("RGB")' not in source
