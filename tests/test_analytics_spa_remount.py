from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pages" / "pig-manager" / "ui-analytics.js"


def test_spa_remount_contract_is_versioned_and_dom_aware():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "const BOOTSTRAP_VERSION = '3.0.5'" in source
    assert "const mounted = () => Boolean(document.getElementById('analyticsSuite'))" in source
    assert "previousState?.version === BOOTSTRAP_VERSION" in source
    assert "window[READY_KEY] = false" in source
    assert "refreshBtn.dataset.rollpigAnalyticsBound" in source
    assert "window.__rollpigAnalyticsHashHandler" in source
