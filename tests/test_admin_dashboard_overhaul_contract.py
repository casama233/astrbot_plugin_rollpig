from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
ANALYTICS = (ROOT / "pages" / "pig-manager" / "ui-analytics.js").read_text(
    encoding="utf-8"
)
BOOTSTRAP = (ROOT / "pages" / "pig-manager" / "ui-bootstrap.js").read_text(
    encoding="utf-8"
)
OVERVIEW_CSS = (ROOT / "pages" / "pig-manager" / "ex-integration.css").read_text(
    encoding="utf-8"
)


def test_admin_asset_protocol_version_stays_compatible_with_inline_page_bootstrap():
    assert 'UI_ASSET_VERSION = "3.2.0"' in MAIN
    assert "const VERSION = '3.2.0';" in ANALYTICS
    assert "const VERSION = '3.2.0';" in BOOTSTRAP


def test_ai_copy_feature_state_is_exposed_to_dashboard():
    assert 'feature_flags["ai_roast_copy_enabled"] = enabled' in MAIN
    assert 'ai["enabled"] = enabled' in MAIN
    assert "data.feature_flags?.ai_roast_copy_enabled" in ANALYTICS


def test_ai_copy_dashboard_distinguishes_disabled_idle_running_and_samples():
    for token in (
        "kind: 'disabled'",
        "kind: 'idle'",
        "kind: 'running'",
        "kind: 'samples'",
        "目前未开启 AI 文案功能",
        "最近 7 日尚无完成样本",
        "任务正在生成",
        "AI 文案成功率 · 已完成样本",
    ):
        assert token in ANALYTICS
    assert "此区块不会显示 0% 成功率或 0 / 0 样本" in ANALYTICS


def test_overview_does_not_repeat_daily_draws_sparkline_as_a_second_trend():
    assert "#view-overview #vDraws svg{display:none!important}" in OVERVIEW_CSS
    assert "短期变化请看 14 日趋势" in OVERVIEW_CSS
    assert "近 14 日每日活跃" in OVERVIEW_CSS


def test_popularity_board_is_compact_card_style_leaderboard():
    for token in (
        "#view-overview #barChart{height:auto!important",
        "#view-overview #barChart .bar-row{",
        "border-radius:11px",
        "#view-overview #barChart .bar-row:nth-child(1)",
        "#view-overview #barChart .bar-value{",
    ):
        assert token in OVERVIEW_CSS
