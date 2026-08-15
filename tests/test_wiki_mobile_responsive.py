from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mobile_responsive_layer_loads_after_wiki_v3():
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    v3 = mkdocs.index("stylesheets/wiki-v3.css")
    responsive = mkdocs.index("stylesheets/wiki-responsive.css")
    assert responsive > v3


def test_mobile_hero_cannot_be_expanded_by_intrinsic_content():
    css = (ROOT / "docs/stylesheets/wiki-responsive.css").read_text(encoding="utf-8")

    assert ".pig-hero--v3 > *" in css
    assert "min-width: 0" in css
    assert "max-width: 100%" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css


def test_mobile_hero_text_and_actions_can_wrap():
    css = (ROOT / "docs/stylesheets/wiki-responsive.css").read_text(encoding="utf-8")

    assert ".pig-hero--v3 .pig-kicker" in css
    assert ".pig-hero--v3 .pig-button" in css
    assert ".pig-hero--v3 .pig-badge" in css
    assert "overflow-wrap: anywhere" in css
    assert "white-space: normal" in css


def test_narrow_mobile_console_collapses_to_one_column():
    css = (ROOT / "docs/stylesheets/wiki-responsive.css").read_text(encoding="utf-8")

    assert "@media (max-width: 430px)" in css
    assert ".pig-hero--v3 .pig-console__stats" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
