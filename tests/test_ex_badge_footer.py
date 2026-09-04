from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFont

from renderers import animated_pig_card, pig_card


PALETTES = (
    {
        "canvas": (255, 247, 244),
        "accent": (223, 91, 116),
        "title": (72, 44, 51),
        "body": (82, 55, 63),
        "secondary": (145, 99, 110),
    },
    {
        "canvas": (29, 23, 30),
        "accent": (255, 120, 152),
        "title": (255, 223, 235),
        "body": (231, 203, 215),
        "secondary": (187, 152, 170),
    },
)


@pytest.fixture(autouse=True)
def clear_cache():
    pig_card.clear_pig_card_cache()
    yield
    pig_card.clear_pig_card_cache()


def _fonts():
    return (
        ImageFont.truetype("DejaVuSans-Bold.ttf", 40),
        ImageFont.truetype("DejaVuSans.ttf", 24),
    )


def _layout():
    return pig_card.PigCardLayout(
        canvas_width=480,
        canvas_height=480,
        avatar_size=140,
        desc_font_size=20,
        analysis_font_size=18,
        ex_badge_font_size=18,
    )


def _pig(level=9, *, long=False):
    data = {
        "id": "footer-pig",
        "name": "Footer Pig",
        "description": "Visible growth",
        "analysis": (
            "Long explanation must never collide with the EX footer. " * 30
            if long else "The pig keeps its details together."
        ),
    }
    if level is not None:
        data["_ex_level"] = level
    return data


def _render(kind, data, tmp_path, layout, palette=PALETTES[0]):
    bold, regular = _fonts()
    avatar = Image.new("RGBA", (layout.avatar_size, layout.avatar_size), (60, 110, 140, 255))
    if kind == "animated":
        return animated_pig_card._render_frame(
            avatar,
            pig_name=data["name"],
            pig_desc=data["description"],
            pig_analysis=data["analysis"],
            ex_level=data.get("_ex_level"),
            palette=palette,
            font_bold=bold,
            font_regular=regular,
            layout=layout,
        )
    avatar_path = tmp_path / "avatar.png"
    avatar.save(avatar_path)
    output = pig_card.render_pig_card(
        data,
        palette=palette,
        font_bold=bold,
        font_regular=regular,
        image_resolver=lambda _id, _level: avatar_path,
        layout=layout,
    )
    assert output is not None
    try:
        with Image.open(output) as image:
            return image.copy()
    finally:
        output.unlink(missing_ok=True)


def _track_badges(monkeypatch, kind):
    module = pig_card if kind == "static" else animated_pig_card
    original = module.draw_ex_level_badge
    calls = []

    def tracked(*args, **kwargs):
        calls.append(dict(kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "draw_ex_level_badge", tracked)
    return calls


@pytest.mark.parametrize("kind", ["static", "animated"])
@pytest.mark.parametrize("level", [0, 1, 9])
@pytest.mark.parametrize("palette", PALETTES, ids=["light", "dark"])
def test_ex_badge_is_centered_at_bottom_after_all_copy(
    kind, level, palette, tmp_path, monkeypatch,
):
    layout = _layout()
    calls = _track_badges(monkeypatch, kind)
    text_boxes = []
    original_text = ImageDraw.ImageDraw.text

    def tracked_text(draw, xy, text, *args, **kwargs):
        if not str(text).startswith("EX Lv."):
            text_boxes.append(draw.textbbox(xy, text, font=kwargs.get("font")))
        return original_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", tracked_text)
    result = _render(kind, _pig(level), tmp_path, layout, palette)
    assert len(calls) == 1
    call = calls[0]
    label, _, width, height = pig_card.ex_level_badge_metrics(level, _fonts()[1], layout)
    assert label == f"EX Lv.{level}"
    assert call["center_x"] == result.width // 2
    assert call["top"] == result.height - layout.ex_badge_bottom_margin - height
    assert min(box[1] for box in text_boxes) >= 0
    assert max(box[3] for box in text_boxes) <= call["top"] - layout.spacing_analysis_badge
    left = int(call["center_x"] - width / 2)
    assert result.getpixel((left + 4, call["top"] + height // 2)) == palette["accent"]


@pytest.mark.parametrize("kind", ["static", "animated"])
def test_missing_collection_metadata_has_no_footer(kind, tmp_path, monkeypatch):
    calls = _track_badges(monkeypatch, kind)
    layout = _layout()
    result = _render(kind, _pig(None), tmp_path, layout)
    assert calls == []
    assert result.size == (layout.canvas_width, layout.canvas_height)


@pytest.mark.parametrize("kind", ["static", "animated"])
def test_short_cards_do_not_split_avatar_from_name_or_move_body(
    kind, tmp_path, monkeypatch,
):
    layout = pig_card.PigCardLayout()
    calls = _track_badges(monkeypatch, kind)
    before = _render(kind, _pig(None), tmp_path, layout)
    after = _render(kind, _pig(1), tmp_path, layout)
    assert before.size == after.size == (800, 800)
    body_box = (0, 0, after.width, calls[0]["top"])
    assert ImageChops.difference(before.crop(body_box), after.crop(body_box)).getbbox() is None


@pytest.mark.parametrize("kind", ["static", "animated"])
def test_six_line_analysis_keeps_top_and_footer_clear(kind, tmp_path, monkeypatch):
    layout = _layout()
    calls = _track_badges(monkeypatch, kind)
    boxes = []
    original_text = ImageDraw.ImageDraw.text

    def tracked_text(draw, xy, text, *args, **kwargs):
        if not str(text).startswith("EX Lv."):
            boxes.append(draw.textbbox(xy, text, font=kwargs.get("font")))
        return original_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", tracked_text)
    result = _render(kind, _pig(9, long=True), tmp_path, layout)
    assert result.height > layout.canvas_height
    assert min(box[1] for box in boxes) >= layout.content_top_margin
    assert max(box[3] for box in boxes) <= calls[0]["top"] - layout.spacing_analysis_badge
    badge_h = pig_card.ex_level_badge_metrics(9, _fonts()[1], layout)[3]
    assert result.height - calls[0]["top"] - badge_h == layout.ex_badge_bottom_margin


@pytest.mark.parametrize("level", [0, 9])
@pytest.mark.parametrize("long", [False, True])
def test_static_and_animated_cards_share_the_same_pixel_layout(level, long, tmp_path):
    data = _pig(level, long=long)
    static = _render("static", data, tmp_path, _layout())
    animated = _render("animated", data, tmp_path, _layout())
    assert static.size == animated.size
    assert ImageChops.difference(static, animated).getbbox() is None


def test_gif_footer_position_and_animation_timing_are_stable(tmp_path, monkeypatch):
    @dataclass(frozen=True)
    class Animation:
        frames: tuple[Image.Image, ...]
        durations: tuple[int, ...]
        loop: int

    layout = _layout()
    size = (layout.avatar_size, layout.avatar_size)
    animation = Animation(
        (Image.new("RGBA", size, (255, 0, 0, 255)), Image.new("RGBA", size, (0, 0, 255, 255))),
        (80, 140),
        3,
    )
    monkeypatch.setattr(animated_pig_card, "load_fitted_gif_frames", lambda _path, _size: animation)
    calls = _track_badges(monkeypatch, "animated")
    bold, regular = _fonts()
    output = animated_pig_card.render_animated_pig_card(
        _pig(9, long=True),
        avatar_path=tmp_path / "animation.gif",
        palette=PALETTES[1],
        font_bold=bold,
        font_regular=regular,
        layout=layout,
    )
    assert output is not None
    try:
        assert len(calls) == 2
        assert calls[0]["top"] == calls[1]["top"]
        assert calls[0]["center_x"] == calls[1]["center_x"]
        with Image.open(output) as result:
            assert result.n_frames == 2
            assert result.info["loop"] == animation.loop
            durations = []
            for index in range(result.n_frames):
                result.seek(index)
                durations.append(result.info["duration"])
            assert tuple(durations) == animation.durations
    finally:
        output.unlink(missing_ok=True)
