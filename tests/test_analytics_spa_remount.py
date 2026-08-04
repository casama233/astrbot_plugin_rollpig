from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pages" / "pig-manager" / "ui-analytics.js"


def test_analytics_is_root_bound_and_has_no_bridge_polling():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "const VERSION = '3.1.1'" in source
    assert "previous.root === pageRoot" in source
    assert "previous?.abortController?.abort()" in source
    assert "state.refresh = loadInsights" in source
    assert "MAX_WAIT_MS" not in source
    assert "POLL_MS" not in source
    assert "waitForBridge" not in source
    assert "setInterval" not in source
    assert "MutationObserver" not in source
    assert "__rollpigAnalyticsHashHandler" not in source
