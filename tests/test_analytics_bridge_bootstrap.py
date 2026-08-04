from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pages" / "pig-manager" / "ui-analytics.js"
BOOTSTRAP = ROOT / "pages" / "pig-manager" / "ui-bootstrap.js"


def test_analytics_requires_an_explicit_bootstrap_click_and_no_bridge_polling():
    analytics = SCRIPT.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    assert "const bridge = window.AstrBotPluginPage" in analytics
    assert "button.addEventListener('click', load" in bootstrap
    assert "bridge.apiGet('ui/assets'" in bootstrap
    assert "waitForBridge" not in analytics
    assert "MAX_WAIT_MS" not in analytics
    assert "POLL_MS" not in analytics
    assert "setInterval" not in analytics
    assert "window.setTimeout(waitForBridge" not in analytics


def test_missing_bridge_is_reported_only_after_the_user_clicks():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    lookup = bootstrap.index("const bridge = window.AstrBotPluginPage")
    click_binding = bootstrap.index("button.addEventListener('click', load")
    load_function = bootstrap.index("const load = async () =>")
    assert load_function < lookup < click_binding
    assert "AstrBot Plugin Page Bridge 不存在" in bootstrap
    assert "数据总览、猪猪图鉴和管理操作不受影响" in bootstrap
