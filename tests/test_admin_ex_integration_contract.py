from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "pig-manager" / "index.html"
EX_JS = ROOT / "pages" / "pig-manager" / "ex-integration.js"
EX_CSS = ROOT / "pages" / "pig-manager" / "ex-integration.css"


def page_text() -> str:
    return PAGE.read_text(encoding="utf-8")


def integration_text() -> str:
    return EX_JS.read_text(encoding="utf-8")


def test_main_manager_ex_entrypoints_are_visible():
    page = page_text()
    script = integration_text()
    assert "EX 1–5" in page
    assert "data-ex-manager" in page
    assert "openExManager" in script
    assert "ex/variants" in script


def test_main_manager_ex_editor_supports_level_write_reset_and_image_preview():
    text = integration_text()
    assert "ex/variants/save" in text
    assert "ex/variants/delete" in text
    assert "ex/variants/image" in text
    assert "EX Lv.${state.level}" in text
    assert "留空＝繼承" in text


def test_public_source_preview_has_actions_instead_of_close_only():
    page = page_text()
    script = integration_text()
    assert "publicSourceExSummary" in page
    assert "publicSourceManageEx" in page
    assert "publicSourceLocateLocal" in page
    assert "管理本地 EX" in page
    assert "在本地图鉴定位" in page
    assert "renderPublicSourceSummary" in script


def test_ex_manager_assets_are_loaded_and_responsive():
    page = page_text()
    css = EX_CSS.read_text(encoding="utf-8")
    assert './ex-integration.css' in page
    assert './ex-integration.js' in page
    assert ".ex-manager-modal" in css
    assert ".ex-level-tabs" in css
    assert "@media(max-width:760px)" in css


def test_main_manager_ex_modal_has_stage2_effective_preview_parity():
    script = integration_text()
    css = EX_CSS.read_text(encoding="utf-8")
    for marker in (
        "data-compare-toggle",
        "data-effective-image",
        "data-base-card",
        "data-effective-zoom",
        "data-base-zoom",
        "Base ↔ EX",
        "function openPreviewLightbox",
        "function loadEffectiveImage",
        "function loadBaseImage",
    ):
        assert marker in script
    assert "effective: true" in script
    assert "base: true" in script
    assert "remove_image: removeImage" in script
    assert "source: 'pending'" in script
    assert "exPreviewImage" not in script
    assert "exLocalImage" not in script
    assert ".ex-preview-stage.comparing" in css
    assert ".ex-preview-lightbox" in css


def test_main_and_standalone_ex_preview_entrypoints_cannot_drift_again():
    main_modal = integration_text()
    standalone = (ROOT / "pages" / "pig-manager-ex" / "index.html").read_text(encoding="utf-8")
    for marker in (
        "Base ↔ EX",
        "data-compare-toggle",
        "data-effective-image",
        "data-base-card",
        "data-effective-zoom",
        "data-base-zoom",
    ):
        assert marker in main_modal
        assert marker in standalone
    assert "effective: true" in main_modal
    assert "effective:true" in standalone
    assert "base: true" in main_modal
    assert "base:true" in standalone
