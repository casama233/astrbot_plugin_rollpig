from pathlib import Path


INTEGRATION = Path("pages/pig-manager/dashboard-trend-integration.js")
BROWSER_REGRESSION = Path("tests/browser/dashboard-repeat-metric.test.mjs")


def test_dashboard_trend_uses_semantic_metric_identity_and_error_handling():
    entry = Path("pages/pig-manager/ex-integration.js").read_text(encoding="utf-8")
    source = INTEGRATION.read_text(encoding="utf-8")

    assert "import './dashboard-trend-integration.js';" in entry
    assert "repeats: Math.max(0, draws - unlocks)" in source
    assert "first?.status === 'error'" in source
    assert "payload?.status === 'error'" in source
    assert 'data-rollpig-metric' in source
    assert "REPEAT_METRIC_ID = 'repeat-draws'" in source
    assert "legend[1]" not in source
    assert "items[2]" not in source
    assert "tooltipRows[1]" not in source
    assert "移动到折线可查看每日使用人数、重复抽中与新解锁" in source
    assert "近十四日使用人数、重复抽中与新解锁趋势" in source
    assert "14 日重复抽中" in source
    assert "bar.setAttribute('aria-label', `重复抽中 ${repeatCount} 次`)" in source


def test_repeat_metric_has_executable_browser_regression():
    assert BROWSER_REGRESSION.is_file()
    source = BROWSER_REGRESSION.read_text(encoding="utf-8")

    assert "patches reordered metric DOM by identity" in source
    assert "['30.000', '0.000', '0.000']" in source
    assert "overview unavailable" in source
    assert "data-rollpig-metric=\"repeat-draws\"" in source


def test_repeat_metric_browser_regression_is_ci_gated():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "npm ci --ignore-scripts --no-audit --no-fund" in workflow
    assert "tests/browser/dashboard-repeat-metric.test.mjs" in workflow


def test_repeat_metric_keeps_lifetime_draw_semantics_outside_trend_patch():
    source = INTEGRATION.read_text(encoding="utf-8")

    # The integration only post-processes the 14-day chart. It must not rewrite
    # overview metrics such as total_draws / the lifetime cumulative draw card.
    assert "total_draws" not in source
    assert "mDraws" not in source
    assert "cDraws" not in source
