import datetime
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageFont

from renderers import (
    WeeklyEntry,
    render_catalog_grid,
    render_pig_card,
    render_pigsty,
    render_weekly_summary,
)


PALETTE = {
    "canvas": (255, 247, 244),
    "surface": (255, 255, 255),
    "surface_muted": (239, 232, 233),
    "title": (72, 44, 51),
    "body": (82, 55, 63),
    "secondary": (145, 99, 110),
    "muted": (155, 109, 119),
    "accent": (223, 91, 116),
    "locked": (232, 226, 227),
    "locked_text": (130, 120, 123),
}


def _fonts():
    return (
        ImageFont.truetype("DejaVuSans.ttf", 66),
        ImageFont.truetype("DejaVuSans.ttf", 32),
    )


def _no_image(_pig_id: str, _ex_level: int | None = None) -> Path | None:
    return None


def _assert_png(path: Path, size: tuple[int, int]):
    try:
        assert path.exists()
        with PILImage.open(path) as image:
            assert image.format == "PNG"
            assert image.size == size
    finally:
        path.unlink(missing_ok=True)


def test_pig_card_renderer_smoke():
    bold, regular = _fonts()
    output = render_pig_card(
        {
            "id": "demo",
            "name": "Demo Pig",
            "description": "Friendly pig",
            "analysis": "A deterministic renderer smoke test.",
        },
        palette=PALETTE,
        font_bold=bold,
        font_regular=regular,
        image_resolver=_no_image,
    )
    assert output is not None
    _assert_png(output, (800, 800))


def test_catalog_grid_renderer_smoke():
    bold, regular = _fonts()
    output = render_catalog_grid(
        [
            {"id": "a", "name": "Alpha", "description": "First"},
            {"id": "b", "name": "Beta", "description": "Second"},
        ],
        "Random pigs",
        "Does not alter collection",
        palette=PALETTE,
        font_bold=bold,
        font_regular=regular,
        image_resolver=_no_image,
    )
    _assert_png(output, (900, 430))


def test_pigsty_renderer_smoke():
    bold, regular = _fonts()
    catalog = [
        {"id": "a", "name": "Alpha", "description": "First"},
        {"id": "b", "name": "Beta", "description": "Second"},
    ]
    user = {
        "pigs": {"a": {"count": 2}},
        "total_draws": 3,
    }
    output, page = render_pigsty(
        catalog=catalog,
        user=user,
        ordered_pigs=catalog,
        favorite_name="Alpha",
        page=1,
        total_pages=1,
        page_size=12,
        palette=PALETTE,
        font_bold=bold,
        font_regular=regular,
        image_resolver=_no_image,
    )
    assert page == 1
    _assert_png(output, (900, 1260))


def test_weekly_renderer_smoke():
    bold, regular = _fonts()
    monday = datetime.date(2026, 8, 10)
    entries = [
        WeeklyEntry(
            day=monday + datetime.timedelta(days=index),
            pig=(
                {"id": f"p{index}", "name": f"Pig {index}", "description": "ok"}
                if index < 3
                else None
            ),
            was_eaten=index == 1,
        )
        for index in range(7)
    ]
    output = render_weekly_summary(
        entries,
        today=monday + datetime.timedelta(days=4),
        monday=monday,
        palette=PALETTE,
        font_bold=bold,
        font_regular=regular,
        image_resolver=_no_image,
    )
    _assert_png(output, (900, 1080))
