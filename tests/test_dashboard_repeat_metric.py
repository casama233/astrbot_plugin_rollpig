from pathlib import Path


def test_dashboard_trend_replaces_redundant_daily_draw_metric():
    entry = Path("pages/pig-manager/ex-integration.js").read_text(encoding="utf-8")
    source = Path("pages/pig-manager/dashboard-trend-integration.js").read_text(
        encoding="utf-8"
    )

    assert "import './dashboard-trend-integration.js';" in entry
    assert "repeats: Math.max(0, draws - unlocks)" in source
    assert "移动到折线可查看每日使用人数、重复抽中与新解锁" in source
    assert "近十四日使用人数、重复抽中与新解锁趋势" in source
    assert "14 日重复抽中" in source
    assert "label.textContent !== '重复抽中'" in source
    assert "bar.setAttribute('aria-label', `重复抽中 ${repeatCount} 次`)" in source


def test_repeat_metric_keeps_lifetime_draw_semantics_outside_trend_patch():
    source = Path("pages/pig-manager/dashboard-trend-integration.js").read_text(
        encoding="utf-8"
    )

    # The integration only post-processes the 14-day chart. It must not rewrite
    # overview metrics such as total_draws / the lifetime cumulative draw card.
    assert "total_draws" not in source
    assert "mDraws" not in source
    assert "cDraws" not in source
