from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "pages/pig-manager/ui-feedback.js").read_text(encoding="utf-8")
FEEDBACK = (ROOT / "pages/pig-manager/ui-feedback-core.js").read_text(encoding="utf-8")
ENTERPRISE = (ROOT / "pages/pig-manager/ui-enterprise.js").read_text(encoding="utf-8")
THEME = (ROOT / "pages/pig-manager/enterprise-theme.css").read_text(encoding="utf-8")
ANALYTICS = (ROOT / "pages/pig-manager/ui-analytics.js").read_text(encoding="utf-8")
ANALYTICS_THEME = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


def test_feedback_layer_loads_before_inline_module():
    external = '<script src="./ui-feedback.js?v=3.0.5"></script>'
    assert external in PAGE
    assert PAGE.index(external) < PAGE.index('<script type="module">')
    assert "./ui-feedback-core.js" in LOADER
    assert "./ui-enterprise.js" in LOADER
    assert "./ui-analytics.js" in LOADER
    assert "rollpig-inline-assets:start" not in PAGE


def test_feedback_layer_explains_stale_runtime_routes():
    assert "页面与运行中的插件后端版本不一致" in FEEDBACK
    assert "请先重启 AstrBot" in FEEDBACK
    assert "storage/status" in FEEDBACK
    assert "restart_required" in FEEDBACK
    assert "等待重启" in FEEDBACK


def test_feedback_layer_tracks_each_long_operation_and_refresh():
    for route in (
        "resources/sync",
        "storage/migrate",
        "storage/verify",
        "storage/rebuild",
        "storage/export",
        "storage/rollback",
        "updates/check",
        "updates/apply",
    ):
        assert route in FEEDBACK
    assert "已等待 ${seconds} 秒" in FEEDBACK
    assert "耗时 ${elapsed} 秒" in FEEDBACK
    assert "refreshBtn" in FEEDBACK
    assert "正在刷新全部数据" in FEEDBACK


def test_dashboard_routes_are_registered_server_side():
    for route in (
        "/storage/status",
        "/storage/migrate",
        "/storage/verify",
        "/storage/rebuild",
        "/storage/export",
        "/storage/rollback",
        "/updates/status",
        "/updates/check",
        "/updates/apply",
    ):
        assert route in MAIN


def test_feedback_layer_uses_in_page_confirmation_for_sandboxed_plugin_pages():
    assert "function showPageConfirm" in FEEDBACK
    assert "pageConfirmDialog" in FEEDBACK
    for button_id in (
        "storageMigrateBtn",
        "storageRebuildBtn",
        "storageRollbackBtn",
        "updateApplyBtn",
        "aiDraftBtn",
    ):
        assert button_id in FEEDBACK
    assert "invokeLegacyConfirmedHandler" in FEEDBACK
    assert "window.confirm = () =>" in FEEDBACK


def test_enterprise_theme_keeps_ui_compact_consistent_and_responsive():
    for token in (
        "--radius-sm",
        "--focus-ring",
        ".operation-card",
        ".update-actions",
        ".pig-grid",
        ".dialog",
        ".btn[aria-busy=\"true\"]",
        "@media (max-width: 680px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert token in THEME
    assert ".ambient,\n.noise" in THEME
    assert "backdrop-filter: none" in THEME


def test_enterprise_enhancement_adds_accessibility_without_api_changes():
    for marker in (
        "root.dataset.uiVersion",
        "skip-link",
        "aria-live",
        "aria-modal",
        "MutationObserver",
        "has-busy-operation",
        "operation-card--storage",
        "operation-card--update",
    ):
        assert marker in ENTERPRISE
    assert "apiGet" not in ENTERPRISE
    assert "apiPost" not in ENTERPRISE


def test_sqlite_migration_is_logged_before_work_and_on_safe_failure():
    assert "开始 SQLite 存储迁移" in MAIN
    assert "SQLite 存储迁移未切换后端" in MAIN


def test_commercial_analytics_layer_is_read_only_responsive_and_resilient():
    for marker in (
        "analytics/insights",
        "analyticsSuite",
        "activity-heatmap",
        "retention-ring",
        "rising-table",
        "renderError",
        "analyticsRetry",
    ):
        assert marker in ANALYTICS
    assert "apiPost" not in ANALYTICS
    assert "@media (max-width: 620px)" in ANALYTICS_THEME
    assert "@media (prefers-reduced-motion: reduce)" in ANALYTICS_THEME
    assert ".analytics-kpis" in ANALYTICS_THEME
    assert ".analytics-grid" in ANALYTICS_THEME


def test_read_only_analytics_route_is_registered():
    assert "/analytics/insights" in MAIN
    assert "page_analytics_insights" in MAIN
    assert "不返回用户、群组或聊天原始标识" in MAIN
