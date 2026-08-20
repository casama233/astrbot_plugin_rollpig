from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageFont

from renderers import render_roast_card


PALETTE = {
    "roast_canvas": (44, 35, 34),
    "roast_surface": (61, 47, 45),
    "roast_outline": (134, 84, 66),
    "roast_title": (245, 218, 195),
    "roast_body": (231, 204, 184),
}


def _no_image(_pig_id: str, _ex_level: int | None = None) -> Path | None:
    return None


def _render_with_resolver(image_resolver) -> Path:
    bold = ImageFont.truetype("DejaVuSans.ttf", 66)
    body = ImageFont.truetype("DejaVuSans.ttf", 26)
    return render_roast_card(
        {"id": "demo", "name": "Demo Pig"},
        user_id="u1",
        draw_date="2026-08-14",
        ai_copy=None,
        palette=PALETTE,
        font_bold=bold,
        body_font=body,
        image_resolver=image_resolver,
    )


def _assert_placeholder_is_visible(image: PILImage.Image) -> None:
    image_area = image.crop((185, 150, 615, 580))
    colors = set(image_area.getdata())
    assert PALETTE["roast_outline"] in colors
    assert PALETTE["roast_surface"] in colors
    assert len(colors) > 3


def test_roast_renderer_missing_image_draws_placeholder():
    output = _render_with_resolver(_no_image)
    try:
        assert output.exists()
        with PILImage.open(output) as image:
            assert image.format == "PNG"
            assert image.size == (800, 870)
            _assert_placeholder_is_visible(image)
    finally:
        output.unlink(missing_ok=True)


def test_roast_renderer_broken_image_draws_placeholder(tmp_path: Path):
    broken = tmp_path / "demo.png"
    broken.write_bytes(b"not-a-real-image")

    def broken_image(_pig_id: str, _ex_level: int | None = None) -> Path:
        return broken

    output = _render_with_resolver(broken_image)
    try:
        with PILImage.open(output) as image:
            _assert_placeholder_is_visible(image)
    finally:
        output.unlink(missing_ok=True)
