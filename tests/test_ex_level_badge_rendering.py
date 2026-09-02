from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from renderers import animated_pig_card, pig_card


PALETTE = {
    "canvas": (255, 247, 244),
    "accent": (223, 91, 116),
    "title": (72, 44, 51),
    "body": (82, 55, 63),
    "secondary": (145, 99, 110),
}


def _fonts():
    return (
        ImageFont.truetype("DejaVuSans-Bold.ttf", 40),
        ImageFont.truetype("DejaVuSans.ttf", 24),
    )


def _pig(ex_level: int | None = None) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "badge-pig",
        "name": "Badge Pig",
        "description": "Visible growth",
        "analysis": "The card must make collection growth explicit.",
    }
    if ex_level is not None:
        data["_ex_level"] = ex_level
    return data


def test_badge_label_uses_actual_level_above_content_cap():
    _bold, regular = _fonts()
    label, _font, width, height = pig_card.ex_level_badge_metrics(
        9,
        regular,
        pig_card.PigCardLayout(),
    )

    assert label == "EX Lv.9"
    assert width > 0
    assert height > 0


def test_badge_pill_paints_the_accent_surface():
    _bold, regular = _fonts()
    layout = pig_card.PigCardLayout()
    canvas = PILImage.new("RGB", (240, 90), PALETTE["canvas"])
    draw = ImageDraw.Draw(canvas)

    pig_card.draw_ex_level_badge(
        draw,
        center_x=120,
        top=12,
        ex_level=5,
        palette=PALETTE,
        font_regular=regular,
        layout=layout,
    )

    colors = {
        color: count
        for count, color in (
            canvas.getcolors(maxcolors=canvas.width * canvas.height) or []
        )
    }
    accent_pixels = colors.get(PALETTE["accent"], 0)
    assert accent_pixels > 100


def test_static_card_draws_ex_zero_but_omits_badge_without_metadata(
    monkeypatch,
):
    bold, regular = _fonts()
    pig_card.clear_pig_card_cache()
    layout = pig_card.PigCardLayout(
        canvas_width=480,
        canvas_height=480,
        avatar_size=140,
        desc_font_size=20,
        analysis_font_size=18,
        ex_badge_font_size=18,
    )
    calls: list[int] = []
    original = pig_card.draw_ex_level_badge

    def tracked(*args, **kwargs):
        calls.append(int(kwargs["ex_level"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(pig_card, "draw_ex_level_badge", tracked)
    with_badge = pig_card.render_pig_card(
        _pig(0),
        palette=PALETTE,
        font_bold=bold,
        font_regular=regular,
        image_resolver=lambda _pig_id, _ex_level: None,
        layout=layout,
    )
    without_badge = pig_card.render_pig_card(
        _pig(),
        palette=PALETTE,
        font_bold=bold,
        font_regular=regular,
        image_resolver=lambda _pig_id, _ex_level: None,
        layout=layout,
    )

    try:
        assert with_badge is not None
        assert without_badge is not None
        assert calls == [0]
        assert with_badge.read_bytes() != without_badge.read_bytes()
    finally:
        if with_badge is not None:
            with_badge.unlink(missing_ok=True)
        if without_badge is not None:
            without_badge.unlink(missing_ok=True)
        pig_card.clear_pig_card_cache()


def test_animated_card_draws_uncapped_level_on_every_frame(tmp_path, monkeypatch):
    bold, regular = _fonts()

    @dataclass(frozen=True)
    class Animation:
        frames: tuple[PILImage.Image, ...]
        durations: tuple[int, ...]
        loop: int

    animation = Animation(
        frames=(
            PILImage.new("RGBA", (96, 96), (255, 0, 0, 255)),
            PILImage.new("RGBA", (96, 96), (0, 0, 255, 255)),
        ),
        durations=(80, 140),
        loop=3,
    )
    monkeypatch.setattr(
        animated_pig_card,
        "load_fitted_gif_frames",
        lambda _path, _size: animation,
    )
    calls: list[int] = []
    original = animated_pig_card.draw_ex_level_badge

    def tracked(*args, **kwargs):
        calls.append(int(kwargs["ex_level"]))
        return original(*args, **kwargs)

    monkeypatch.setattr(animated_pig_card, "draw_ex_level_badge", tracked)
    avatar_path = tmp_path / "placeholder.gif"
    output = animated_pig_card.render_animated_pig_card(
        _pig(9),
        avatar_path=avatar_path,
        palette=PALETTE,
        font_bold=bold,
        font_regular=regular,
        layout=pig_card.PigCardLayout(
            canvas_width=480,
            canvas_height=480,
            avatar_size=140,
            desc_font_size=20,
            analysis_font_size=18,
            ex_badge_font_size=18,
        ),
    )

    try:
        assert output is not None
        assert calls == [9, 9]
        with PILImage.open(output) as result:
            assert result.n_frames == 2
            assert result.info.get("loop") == 3
    finally:
        if output is not None:
            output.unlink(missing_ok=True)
