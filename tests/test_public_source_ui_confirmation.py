from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "pig-manager" / "index.html"


def test_public_source_submit_is_sandbox_safe_and_requires_explicit_second_click():
    page = PAGE.read_text(encoding="utf-8")
    start = page.index("async function submitPublicSource")
    end = page.index("async function paintReviewCanvas", start)
    submit_code = page[start:end]

    assert "window.confirm" not in submit_code
    assert "dataset.submitConfirm" in submit_code
    assert "再次点击确认" in submit_code
    assert "pigs/submit-public-source" in submit_code
    assert "confirm:true" in submit_code
    assert "submitPublicSource(localOverrides[Number(b.dataset.submit)],b)" in page
    assert 'type="button" data-submit' in page


def test_public_source_review_decision_uses_capability_gated_in_page_modal():
    page = PAGE.read_text(encoding="utf-8")
    static_markup = page.split("const bridge=window.AstrBotPluginPage;", 1)[0]
    start = page.index("function ensureReviewCapabilityUi")
    end = page.index("function updateFlow", start)
    review_code = page[start:end]

    assert "window.confirm" not in review_code
    assert "window.prompt" not in review_code
    assert 'id="reviewModal"' not in static_markup
    assert 'id="reviewForm"' not in static_markup
    assert 'id="reviewNote"' not in static_markup
    assert "if(!publicSourceReviewEnabled)return false" in review_code
    assert "modal.id='reviewModal'" in review_code
    assert 'id="reviewForm"' in review_code
    assert 'id="reviewNote" maxlength="300"' in review_code
    assert "form.onsubmit=submitReviewDecision" in review_code
    assert "source/reviews/decision" in review_code
    assert "confirm:true" in review_code
    assert "批准并立即发布" in review_code
    assert "确认拒绝" in review_code
