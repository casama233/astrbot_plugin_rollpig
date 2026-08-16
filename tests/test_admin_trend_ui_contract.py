from pathlib import Path


PAGE = Path(__file__).resolve().parents[1] / "pages" / "pig-manager" / "index.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_admin_trend_uses_curves_without_smoothing_away_daily_points():
    page = _page()
    assert "function smoothLinePath" in page
    assert "curve=.42" in page
    assert " C ${" in page
    assert "userLine=smoothLinePath" in page
    assert "unlockLine=smoothLinePath" in page


def test_admin_trend_has_compact_four_metric_summary_strip():
    page = _page()
    assert "trendSummary" in page
    assert "trend-summary" in page
    for label in ("活跃峰值", "日均活跃", "14 日抽取", "14 日新解锁"):
        assert label in page


def test_admin_trend_panel_does_not_stretch_into_dead_space():
    page = _page()
    assert ".trend-panel{align-self:start" in page
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in page
    assert "@media(max-width:760px){.trend-summary" in page
