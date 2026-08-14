from pathlib import Path


def test_public_source_submit_is_sandbox_safe_and_requires_explicit_second_click():
    page = (Path(__file__).resolve().parents[1] / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    start = page.index("async function submitPublicSource")
    end = page.index("async function paintReviewCanvas", start)
    submit_code = page[start:end]

    assert "window.confirm" not in submit_code
    assert "dataset.submitConfirm" in submit_code
    assert "再次点击确认" in submit_code
    assert "pigs/submit-public-source" in submit_code
    assert "confirm:true" in submit_code
    assert "submitPublicSource(localOverrides[Number(b.dataset.submit)],b)" in page
    assert "type=\"button\" data-submit" in page
