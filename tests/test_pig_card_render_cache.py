from __future__ import annotations

from PIL import Image, ImageFont

from renderers import pig_card


def _palette():
    return {
        "canvas": (250, 245, 247),
        "accent": (180, 70, 90),
        "title": (60, 50, 55),
        "body": (80, 70, 75),
        "secondary": (110, 95, 100),
    }


def test_completed_pig_card_cache_skips_second_render(tmp_path, monkeypatch):
    source = tmp_path / "cached-pig.png"
    Image.new("RGBA", (64, 64), (240, 120, 150, 255)).save(source)
    pig_card.clear_pig_card_cache()

    fit_calls = 0
    save_calls = 0
    original_fit = pig_card.fit_card_image
    original_save = pig_card.save_png

    def tracked_fit(*args, **kwargs):
        nonlocal fit_calls
        fit_calls += 1
        return original_fit(*args, **kwargs)

    def tracked_save(*args, **kwargs):
        nonlocal save_calls
        save_calls += 1
        return original_save(*args, **kwargs)

    monkeypatch.setattr(pig_card, "fit_card_image", tracked_fit)
    monkeypatch.setattr(pig_card, "save_png", tracked_save)

    data = {
        "id": "cached-pig",
        "name": "Cache Pig",
        "description": "fast path",
        "analysis": "render once and reuse the completed png",
    }
    layout = pig_card.PigCardLayout(
        canvas_width=360,
        canvas_height=360,
        avatar_size=96,
        desc_font_size=14,
        analysis_font_size=12,
        spacing_avatar_name=10,
        spacing_name_desc=10,
        spacing_desc_analysis=12,
    )
    bold = ImageFont.load_default(size=20)
    regular = ImageFont.load_default(size=14)
    resolver = lambda _pig_id, _ex_level: source

    first = pig_card.render_pig_card(
        data,
        palette=_palette(),
        font_bold=bold,
        font_regular=regular,
        image_resolver=resolver,
        layout=layout,
    )
    second = pig_card.render_pig_card(
        data,
        palette=_palette(),
        font_bold=bold,
        font_regular=regular,
        image_resolver=resolver,
        layout=layout,
    )

    assert first is not None and second is not None
    assert first != second
    assert first.read_bytes() == second.read_bytes()
    assert fit_calls == 1
    assert save_calls == 1

    first.unlink(missing_ok=True)
    second.unlink(missing_ok=True)


def test_completed_card_cache_invalidates_when_source_image_changes(
    tmp_path, monkeypatch
):
    source = tmp_path / "changing-pig.png"
    Image.new("RGBA", (48, 48), (255, 100, 120, 255)).save(source)
    pig_card.clear_pig_card_cache()

    save_calls = 0
    original_save = pig_card.save_png

    def tracked_save(*args, **kwargs):
        nonlocal save_calls
        save_calls += 1
        return original_save(*args, **kwargs)

    monkeypatch.setattr(pig_card, "save_png", tracked_save)
    data = {
        "id": "changing-pig",
        "name": "Changing Pig",
        "description": "source aware",
        "analysis": "image identity belongs in the completed card cache key",
    }
    layout = pig_card.PigCardLayout(
        canvas_width=340,
        canvas_height=340,
        avatar_size=90,
        desc_font_size=14,
        analysis_font_size=12,
    )
    bold = ImageFont.load_default(size=20)
    regular = ImageFont.load_default(size=14)
    resolver = lambda _pig_id, _ex_level: source

    first = pig_card.render_pig_card(
        data,
        palette=_palette(),
        font_bold=bold,
        font_regular=regular,
        image_resolver=resolver,
        layout=layout,
    )
    assert first is not None

    # Change both dimensions and encoded payload size so invalidation does not
    # depend on filesystem timestamp granularity.
    Image.new("RGBA", (61, 61), (80, 140, 240, 255)).save(source)
    second = pig_card.render_pig_card(
        data,
        palette=_palette(),
        font_bold=bold,
        font_regular=regular,
        image_resolver=resolver,
        layout=layout,
    )
    assert second is not None
    assert save_calls == 2

    first.unlink(missing_ok=True)
    second.unlink(missing_ok=True)
