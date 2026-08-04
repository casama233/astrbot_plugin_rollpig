from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "pages" / "pig-manager"


def test_optional_enhancement_sources_have_no_continuous_watchers_or_intervals():
    for filename in ("ui-enterprise.js", "ui-feedback-core.js", "ui-analytics.js"):
        source = (UI / filename).read_text(encoding="utf-8")
        assert "MutationObserver" not in source
        assert "setInterval" not in source


def test_default_bootstrap_does_not_load_legacy_enhancement_modules():
    source = (UI / "ui-bootstrap.js").read_text(encoding="utf-8")
    assert "ui-enterprise" not in source
    assert "ui-feedback-core" not in source
    assert "analyticsLoadBtn" in source
