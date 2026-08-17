from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
SCHEMA = (ROOT / "_conf_schema.json").read_text(encoding="utf-8")


def test_review_routes_are_registered_only_with_maintainer_token():
    gate = LEGACY.index("        if self._public_source_review_routes_enabled:")
    resources = LEGACY.index('            f"/{self.PLUGIN_NAME}/resources/status"', gate)
    block = LEGACY[gate:resources]
    assert 'source/reviews"' in block
    assert 'source/reviews/image"' in block
    assert 'source/reviews/decision"' in block
    assert "self._public_source_review_routes_enabled = bool(" in LEGACY
    assert 'data["public_source_review_enabled"] = bool(' in LEGACY
    assert "and self._public_source_admin_token()" in LEGACY


def test_admin_token_is_not_a_public_plugin_config_field():
    assert "public_source_admin_token" not in SCHEMA
    assert "public_source_admin.token" in LEGACY


def test_review_panel_and_form_are_not_static_dom_for_normal_installs():
    static_markup = PAGE.split("const bridge=window.AstrBotPluginPage;", 1)[0]
    assert 'id="sourceReviewPanel"' not in static_markup
    assert 'id="reviewModal"' not in static_markup
    assert 'id="reviewNote"' not in static_markup
    assert 'id="reviewConfirm"' not in static_markup


def test_frontend_mounts_and_queries_reviews_only_after_capability():
    assert "publicSourceReviewEnabled=false" in PAGE
    assert "Boolean(d.public_source_review_enabled);syncReviewCapabilityUi()" in PAGE
    assert "function ensureReviewCapabilityUi(){if(!publicSourceReviewEnabled)return false;" in PAGE
    assert "async function loadSourceReviews(){if(!publicSourceReviewEnabled)" in PAGE
    assert "form.onsubmit=submitReviewDecision" in PAGE
    assert "$('reviewForm').onsubmit=" not in PAGE
