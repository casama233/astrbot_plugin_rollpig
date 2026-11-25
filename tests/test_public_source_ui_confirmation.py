import json
import re
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
    assert "再点一次确认" in submit_code
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
    encoded_form = re.search(r'modal\.innerHTML=("(?:[^"\\]|\\.)*")', review_code)
    assert encoded_form is not None
    form = json.loads(encoded_form[1])
    assert 'id="reviewForm"' in form
    assert 'id="reviewNote" maxlength="300"' in form
    assert "form.onsubmit=submitReviewDecision" in review_code
    assert "source/reviews/decision" in review_code
    assert "confirm:true" in review_code
    assert "const approving=decision==='approve'" in review_code
    assert "pendingReviewDecision={pig:p,decision}" in review_code
    assert "确认驳回" in review_code
