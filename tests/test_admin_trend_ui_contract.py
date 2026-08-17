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

def test_metric_sparklines_use_local_data_range_and_stable_svg_geometry():
    page = _page()
    assert "function metricSparkRange" in page
    assert "Math.min(0,...values)" not in page
    assert "range=metricSparkRange(nums)" in page
    assert "root.classList.remove('metric-snapshot-viz')" in page
    assert "const w=180,h=38,pad=3" in page
    assert "baseline=h-pad" in page
    assert 'vector-effect="non-scaling-stroke"' in page



def test_metric_cards_use_real_daily_series_and_do_not_fabricate_history():
    page = _page()
    assert "const cumulative=" not in page
    assert "renderSpark('vDraws',draws,2,'近 14 日每日抽取')" in page
    assert "renderSpark('vToday',users,3,'近 14 日每日活跃')" in page
    assert "function renderMetricSnapshot" in page
    assert "function renderMetricSignal" not in page
    for metric_id in ("vUsers", "vPigs", "vAverage", "vRate"):
        assert f"renderMetricSnapshot('{metric_id}'" in page
    assert "当前快照 · 无历史序列" in page
