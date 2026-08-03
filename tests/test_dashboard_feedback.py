from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
FEEDBACK = (ROOT / "pages/pig-manager/ui-feedback.js").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


def test_feedback_layer_loads_before_inline_module():
    external = '<script src="./ui-feedback.js"></script>'
    assert external in PAGE
    assert PAGE.index(external) < PAGE.index('<script type="module">')


def test_feedback_layer_explains_stale_runtime_routes():
    assert "页面与运行中的插件后端版本不一致" in FEEDBACK
    assert "请先重启 AstrBot" in FEEDBACK
    assert "storage/status" in FEEDBACK
    assert "restart_required" in FEEDBACK
    assert "等待重启" in FEEDBACK


def test_feedback_layer_tracks_each_long_operation_and_refresh():
    for route in (
        "resources/sync", "storage/migrate", "storage/verify",
        "storage/export", "storage/rollback", "updates/check", "updates/apply",
    ):
        assert route in FEEDBACK
    assert "已等待 ${seconds} 秒" in FEEDBACK
    assert "耗时 ${elapsed} 秒" in FEEDBACK
    assert "refreshBtn" in FEEDBACK
    assert "正在刷新全部数据" in FEEDBACK


def test_dashboard_routes_are_registered_server_side():
    for route in (
        "/storage/status", "/storage/migrate", "/storage/verify",
        "/storage/export", "/storage/rollback", "/updates/status",
        "/updates/check", "/updates/apply",
    ):
        assert route in MAIN
