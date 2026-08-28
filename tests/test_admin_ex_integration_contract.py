from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "pig-manager" / "index.html"
EX_JS = ROOT / "pages" / "pig-manager" / "ex-integration.js"
EX_CORE_JS = ROOT / "pages" / "pig-manager" / "ex-integration-core.js"
EX_CSS = ROOT / "pages" / "pig-manager" / "ex-integration.css"


def page_text() -> str:
    return PAGE.read_text(encoding="utf-8")


def integration_text() -> str:
    """Return the EX implementation source, not the thin module loader."""
    return EX_CORE_JS.read_text(encoding="utf-8")


def integration_wrapper_text() -> str:
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
    assert "ex/variants/card" in text
    assert "EX Lv.${state.level}" in text
    assert "留空＝继承" in text


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
    wrapper = integration_wrapper_text()
    css = EX_CSS.read_text(encoding="utf-8")
    assert './ex-integration.css' in page
    assert './ex-integration.js' in page
    assert "import './ex-integration-core.js'" in wrapper
    assert "import './rights-integration.js'" in wrapper
    assert ".ex-manager-modal" in css
    assert ".ex-level-tabs" in css
    assert "@media(max-width:760px)" in css


def test_main_manager_ex_modal_has_stage2_effective_preview_parity():
    script = integration_text()
    css = EX_CSS.read_text(encoding="utf-8")
    for marker in (
        "data-compare-toggle",
        "data-effective-card-image",
        "data-base-card-image",
        "data-base-card",
        "data-effective-zoom",
        "data-base-zoom",
        "Base ↔ EX",
        "真实发送 renderer",
        "function openPreviewLightbox",
        "function loadEffectiveCard",
        "function loadBaseCard",
    ):
        assert marker in script
    assert "effective: true" in script
    assert "base: true" in script
    assert "ex/variants/card" in script
    assert "markPreviewPending" in script
    assert "exPreviewImage" not in script
    assert "exLocalImage" not in script
    assert ".ex-preview-stage.comparing" in css
    assert ".ex-preview-lightbox" in css


def test_ex_preview_has_one_canonical_management_surface():
    main_modal = integration_text()
    for marker in (
        "Base ↔ EX",
        "data-compare-toggle",
        "data-effective-card-image",
        "data-base-card-image",
        "data-base-card",
        "data-effective-zoom",
        "data-base-zoom",
        "真实发送 renderer",
    ):
        assert marker in main_modal
    assert "effective: true" in main_modal
    assert "base: true" in main_modal
    assert not (ROOT / "pages" / "pig-manager-ex" / "index.html").exists()
    assert not (
        ROOT / "pages" / "pig-manager-ex-public-source" / "index.html"
    ).exists()


def test_main_preview_no_longer_rebuilds_card_copy_in_browser():
    script = integration_text()
    assert "ex/variants/card" in script
    assert "ex-preview-body" not in script
    assert "data-effective-image" not in script
    assert "source: 'pending'" not in script


def test_main_ex_modal_does_not_inject_dynamic_data_with_innerhtml():
    script = integration_text()
    render_modal = script.split("function renderModal() {", 1)[1].split(
        "async function fileData(input)", 1
    )[0]
    assert "body.innerHTML" not in render_modal
    assert "body.replaceChildren" in render_modal
    assert ".textContent = text" in render_modal
    assert "description.value = local.description" in render_modal
    assert "analysis.value = local.analysis" in render_modal
