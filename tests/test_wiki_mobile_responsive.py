from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESPONSIVE = ROOT / "docs" / "stylesheets" / "wiki-responsive.css"
BRAND_ICONS = ROOT / "docs" / "stylesheets" / "brand-icons.css"


def _responsive_css() -> str:
    return RESPONSIVE.read_text(encoding="utf-8")


def test_responsive_layer_loads_after_wiki_v3():
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    v3 = mkdocs.index("stylesheets/wiki-v3.css")
    responsive = mkdocs.index("stylesheets/wiki-responsive.css")
    assert responsive > v3


def test_home_keeps_mobile_navigation_but_drops_desktop_document_sidebars():
    home = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    front_matter = home.split("---", 2)[1]
    css = _responsive_css()

    # Do not use Material's `hide: navigation`: that also removes the mobile
    # drawer, while the tab bar itself disappears on narrow viewports.
    assert "hide:" not in front_matter
    assert "@media screen and (min-width: 76.25em)" in css
    assert ".md-main__inner.md-grid:has(.pig-hero--v3) > .md-sidebar" in css
    assert "display: none" in css


def test_wide_desktop_expansion_is_scoped_to_the_landing_page():
    css = _responsive_css()

    assert "--pig-home-max-width: 1480px" in css
    assert "@media screen and (min-width: 76.25em)" in css
    assert ".md-main__inner.md-grid:has(.pig-hero--v3)" in css
    assert "max-width: var(--pig-home-max-width)" in css
    assert "--pig-doc-max-width" not in css


def test_rendered_markdown_paragraph_wrappers_keep_their_layout_roles():
    css = _responsive_css()

    for selector in (
        ".pig-actions > p",
        ".pig-badges > p",
        ".pig-live-strip__track > p",
        ".pig-console__top > p",
        ".pig-console-stat > p",
        ".pig-mascot > p",
        ".pig-evolution-flow > p",
        ".pig-charge-row > p",
        ".pig-layer > p",
        ".pig-checklist > p",
        ".pig-pity-gauge > p",
    ):
        assert selector in css

    assert ".pig-console-stat > p > em" in css
    assert "grid-template-columns: minmax(0, 1fr) auto" in css


def test_branded_mascot_supports_mkdocs_paragraph_wrapper():
    css = BRAND_ICONS.read_text(encoding="utf-8")

    assert ".pig-mascot > p > .pig-brand-icon" in css
    assert ".pig-mascot:hover > p > .pig-brand-icon" in css


def test_custom_components_follow_content_width_not_only_viewport_width():
    css = _responsive_css()

    assert "container: pig-content / inline-size" in css
    assert "@container pig-content (max-width: 64rem)" in css
    assert "@container pig-content (max-width: 52rem)" in css
    assert "@container pig-content (max-width: 40rem)" in css

    for component in (
        ".pig-versus",
        ".pig-outcome-grid",
        ".pig-creator-pipeline",
        ".pig-triage",
        ".pig-roast-demo",
        ".pig-card-grid",
    ):
        assert component in css


def test_hero_reserves_desktop_hud_space_and_stacks_when_content_is_narrow():
    css = _responsive_css()

    assert "minmax(20rem, .92fr)" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
    assert "container: pig-hero / inline-size" in css
    assert "@container pig-hero (max-width: 42rem)" in css
    assert "@container pig-hero (max-width: 29rem)" in css


def test_hero_hud_text_cannot_force_or_clip_the_stats_grid():
    css = _responsive_css()

    assert ".pig-console-stat > p" in css
    assert "grid-template-columns: minmax(0, 1fr) auto" in css
    assert ".pig-console-stat strong" in css
    assert "overflow-wrap: anywhere" in css


def test_hero_headline_keeps_a_safe_desktop_measure_without_aggressive_breaks():
    css = _responsive_css()
    wrapping_block = css.split(".pig-hero--v3 h1,", 1)[1].split("}", 1)[0]
    size_block = css.split(".pig-hero--v3 h1 {", 1)[1].split("}", 1)[0]

    assert "overflow-wrap: normal" in wrapping_block
    assert "word-break: normal" in wrapping_block
    assert "max-width: 100%" in size_block
    assert "font-size: clamp(48px, 5cqw, 72px)" in size_block
    assert "max-width: 12ch" not in css


def test_intermediate_width_tab_bar_scrolls_instead_of_squeezing_labels():
    css = _responsive_css()

    assert ".md-tabs__inner" in css
    assert "overflow-x: auto" in css
    assert ".md-tabs__list" in css
    assert "width: max-content" in css
    assert ".md-tabs__item" in css
    assert "flex: 0 0 auto" in css


def test_mobile_fallbacks_remain_available_without_container_queries():
    css = _responsive_css()

    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 600px)" in css
    assert "@media (max-width: 430px)" in css
    assert ".pig-hero--v3 .pig-console__stats" in css
