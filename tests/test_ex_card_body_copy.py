from __future__ import annotations

import re

import pytest
from PIL import Image, ImageDraw, ImageFont

from display_copy import strip_ex_level_labels
from renderers import animated_pig_card, pig_card


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("EX1 的明日方猪刚从寻访袋里探头。", "明日方猪刚从寻访袋里探头。"),
        ("EX2 已经掌握标准答案。", "已经掌握标准答案。"),
        ("到了 EX5，你不再解释。", "到了这个阶段，你不再解释。"),
        ("只剩骨头。EX5 的升级内容很克制。", "只剩骨头。这个阶段的升级内容很克制。"),
        ("来到 EX5 后，设定已完整。", "来到这个阶段后，设定已完整。"),
        ("EX Lv.12 的熟客回来了。", "熟客回来了。"),
        ("普通故事和 EX 技能名称。", "普通故事和 EX 技能名称。"),
        ("INDEX1 和 EX1_extra 是标识。", "INDEX1 和 EX1_extra 是标识。"),
    ],
)
def test_card_copy_removes_level_labels_without_losing_the_story(raw, expected):
    assert strip_ex_level_labels(raw) == expected


@pytest.mark.parametrize("kind", ["static", "animated"])
@pytest.mark.parametrize("level", [None, 0, 1, 9])
def test_real_card_draws_level_only_in_footer(kind, level, tmp_path, monkeypatch):
    raw = {
        "id": "arknights-pig",
        "name": "明日方猪",
        "description": "寻访有光，但先别急着截图。",
        "analysis": "EX1 的明日方猪刚从寻访袋里探头。",
    }
    if level is not None:
        raw["_ex_level"] = level
    original = dict(raw)
    avatar = tmp_path / "avatar.gif"
    frames = [Image.new("RGB", (24, 24), color) for color in ("red", "blue")]
    frames[0].save(
        avatar, save_all=True, append_images=frames[1:], duration=[80, 140], loop=3
    )
    kwargs = {
        "palette": {
            "canvas": (29, 23, 30), "accent": (255, 120, 152),
            "title": (255, 223, 235), "body": (231, 203, 215),
            "secondary": (187, 152, 170),
        },
        "font_bold": ImageFont.truetype("DejaVuSans-Bold.ttf", 40),
        "font_regular": ImageFont.truetype("DejaVuSans.ttf", 24),
    }
    texts = []
    draw_text = ImageDraw.ImageDraw.text

    def tracked(draw, xy, text, *args, **options):
        texts.append(str(text))
        return draw_text(draw, xy, text, *args, **options)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", tracked)
    pig_card.clear_pig_card_cache()
    if kind == "static":
        output = pig_card.render_pig_card(
            raw, image_resolver=lambda _pig_id, _level: avatar, **kwargs
        )
    else:
        output = animated_pig_card.render_animated_pig_card(
            raw, avatar_path=avatar, **kwargs
        )
    try:
        assert output is not None
        frame_count = 1 if kind == "static" else 2
        if level is None:
            assert "EX1 的明日方猪刚从寻访袋里探头。" in "".join(texts)
            assert not any(text.startswith("EX Lv.") for text in texts)
        else:
            labels = [text for text in texts if re.search(r"EX\s*(?:Lv\.?)?\d", text)]
            assert labels == [f"EX Lv.{level}"] * frame_count
            assert "明日方猪刚从寻访袋里探头。" in "".join(texts)
        assert raw == original
        with Image.open(output) as result:
            assert result.n_frames == frame_count
            if kind == "animated":
                assert result.info["loop"] == 3
                durations = []
                for index in range(result.n_frames):
                    result.seek(index)
                    durations.append(result.info["duration"])
                assert durations == [80, 140]
    finally:
        if output is not None:
            output.unlink(missing_ok=True)
        pig_card.clear_pig_card_cache()
