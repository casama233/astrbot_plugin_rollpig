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


def test_admin_trend_panel_stretches_without_fixed_dashboard_height():
    page = _page()
    assert ".trend-panel{align-self:stretch" in page
    assert ".trend-panel>.chart{flex:1 1 300px;min-height:300px;height:auto}" in page
    dashboard_rule = page.split(".dashboard-grid{", 1)[1].split("}", 1)[0]
    assert "height:" not in dashboard_rule
    assert "min-height:" not in dashboard_rule
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in page
    assert "@media(max-width:760px){.trend-summary" in page


def test_retention_ring_label_stays_inside_responsive_donut():
    css = (PAGE.parent / "analytics-theme.css").read_text(encoding="utf-8")
    assert ".retention-ring div {" in css
    assert "max-width: calc(100% - 26px);" in css
    assert ".retention-ring span {" in css
    assert "white-space: normal;" in css
    assert "overflow-wrap: anywhere;" in css


def test_metric_sparklines_use_monotone_curves_and_honest_visual_range():
    page = _page()
    assert "function metricSparkRange" in page
    assert "function monotoneSparkPath" in page
    assert "Math.hypot(a,b)" in page
    assert "norm>3" in page
    assert "minSpan=" in page
    assert "const w=240,h=48,padX=5,padY=7" in page
    assert 'vector-effect="non-scaling-stroke"' in page
    assert 'class="spark-endpoint"' in page
    assert "line=pts.map((p,i)=>`${i?'L':'M'}" not in page


def test_metric_cards_keep_five_requested_kpis_with_real_context():
    page = _page()
    for label in ("总使用人数", "累计抽取", "今日活跃", "人均解锁", "平均收藏率"):
        assert f'<span class="label">{label}</span>' in page
    assert '<span class="label">小猪总数</span>' not in page
    assert page.count('<article class="metric') == 5
    for metric_id in ("cUsers", "cDraws", "cToday", "cAverage", "cRate"):
        assert f'id="{metric_id}"' in page
    assert "当前快照 · 无历史序列" not in page
    assert "metric-snapshot-viz" not in page
    assert "metric-scope" not in page
    for viz_id in ("vUsers", "vDraws", "vToday", "vAverage", "vRate"):
        assert f'id="{viz_id}"' in page
    assert "renderMetricMeter('vUsers',today,totalUsers" in page
    assert "renderSpark('vDraws',cumulativeDraws,2,'近 14 日累计抽取轨迹')" in page
    assert "renderSpark('vToday',users,3,'近 14 日每日活跃人数')" in page
    assert "renderMetricRuler('vAverage',averageUnlocked,catalog" in page
    assert "renderMetricRate('vRate',rate" in page
    assert "totalDraws-totalDraws14" in page
    for useful_copy in ("今日活跃", "占累计", "近 14 日", "较昨日", "人均尚未探索", "按当前图鉴计算"):
        assert useful_copy in page
