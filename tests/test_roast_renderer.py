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


def test_roast_renderer_smoke_and_dimensions():
    bold = ImageFont.truetype("DejaVuSans.ttf", 66)
    body = ImageFont.truetype("DejaVuSans.ttf", 26)
    output = render_roast_card(
        {"id": "demo", "name": "Demo Pig"},
        user_id="u1",
        draw_date="2026-08-14",
        ai_copy=None,
        palette=PALETTE,
        font_bold=bold,
        body_font=body,
        image_resolver=_no_image,
    )
    try:
        assert output.exists()
        with PILImage.open(output) as image:
            assert image.format == "PNG"
            assert image.size == (800, 870)
    finally:
        output.unlink(missing_ok=True)
