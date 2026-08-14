from __future__ import annotations

from PIL import Image, ImageFont

from renderers import common


def test_get_text_size_avoids_scratch_image_on_modern_pillow(monkeypatch):
    font = ImageFont.load_default()

    def fail_new(*_args, **_kwargs):
        raise AssertionError("scratch image allocation should not be needed")

    monkeypatch.setattr(common.PILImage, "new", fail_new)
    width, height = common.get_text_size("renderer", font)
    assert width > 0
    assert height >= 0


def test_fit_card_image_reuses_cached_decode_and_returns_copies(tmp_path, monkeypatch):
    path = tmp_path / "pig.png"
    Image.new("RGBA", (48, 48), (255, 100, 120, 255)).save(path)
    common.clear_fit_card_image_cache()

    original_open = common.PILImage.open
    open_calls = 0

    def tracked_open(*args, **kwargs):
        nonlocal open_calls
        open_calls += 1
        return original_open(*args, **kwargs)

    monkeypatch.setattr(common.PILImage, "open", tracked_open)
    first = common.fit_card_image(path, (24, 24))
    second = common.fit_card_image(path, (24, 24))

    assert open_calls == 1
    assert first.size == (24, 24)
    assert second.size == (24, 24)
    assert first is not second

    first.putpixel((0, 0), (0, 0, 0, 0))
    assert second.getpixel((0, 0)) != (0, 0, 0, 0)


def test_wrap_text_respects_width_and_line_limit():
    font = ImageFont.load_default()
    max_width = common.get_text_size("abc", font)[0]
    lines = common.wrap_text(
        "abcdefghij",
        font,
        max_width,
        max_lines=2,
        ellipsis=".",
    )

    assert len(lines) == 2
    assert lines[-1].endswith(".")
    assert all(common.get_text_size(line, font)[0] <= max_width for line in lines)
