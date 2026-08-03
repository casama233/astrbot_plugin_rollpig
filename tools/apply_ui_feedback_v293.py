from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
page = ROOT / "pages/pig-manager/index.html"
metadata = ROOT / "metadata.yaml"
main = ROOT / "main.py"
updater = ROOT / "updater.py"
changelog = ROOT / "CHANGELOG.md"
feedback = ROOT / "pages/pig-manager/ui-feedback.js"

def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

# Load the resilience layer before the inline module captures the bridge methods.
replace_once(
    page,
    '<script src="/api/plugin/page/bridge-sdk.js"></script>\n<script type="module">',
    '<script src="/api/plugin/page/bridge-sdk.js"></script>\n<script src="./ui-feedback.js"></script>\n<script type="module">',
)

# Add explicit refresh-button feedback without coupling it to the inline module scope.
script = feedback.read_text(encoding="utf-8")
anchor = "\n  const toast = $('toast');\n"
if anchor not in script:
    raise SystemExit("ui-feedback.js: toast anchor not found")
refresh = r'''
  const refreshButton = $('refreshBtn');
  const loadingOverlay = $('loading');
  let refreshStartedAt = 0;
  let refreshResetTimer = null;
  function finishRefresh(message) {
    if (!refreshStartedAt || !refreshButton) return;
    const elapsed = ((Date.now() - refreshStartedAt) / 1000).toFixed(1);
    refreshStartedAt = 0;
    clearTimeout(refreshResetTimer);
    refreshButton.disabled = false;
    refreshButton.textContent = '↻';
    refreshButton.removeAttribute('aria-busy');
    refreshButton.title = `${message}（耗时 ${elapsed} 秒）`;
    const live = document.querySelector('.live');
    if (live) live.innerHTML = `<i class="live-dot"></i>${message} · ${elapsed}s`;
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || button.id !== 'refreshBtn' || state.restartRequired) return;
    refreshStartedAt = Date.now();
    button.disabled = true;
    button.textContent = '…';
    button.setAttribute('aria-busy', 'true');
    button.title = '正在刷新总览、图鉴、资源、版本与存储状态';
    const live = document.querySelector('.live');
    if (live) live.innerHTML = '<i class="live-dot"></i>正在刷新全部数据…';
    refreshResetTimer = setTimeout(() => finishRefresh('刷新超时，请查看各状态卡片'), 30000);
  }, true);
  if (loadingOverlay) {
    new MutationObserver(() => {
      if (refreshStartedAt && !loadingOverlay.classList.contains('show')) {
        setTimeout(() => finishRefresh('数据已刷新'), 50);
      }
    }).observe(loadingOverlay, {attributes: true, attributeFilter: ['class']});
  }
'''
feedback.write_text(script.replace(anchor, refresh + anchor, 1), encoding="utf-8")

replace_once(metadata, 'version: "2.9.2"', 'version: "2.9.3"')
replace_once(main, 'AstrBot-RollPig/2.9.2', 'AstrBot-RollPig/2.9.3')
replace_once(updater, 'AstrBot-RollPig-Safe-Updater/2.9.2', 'AstrBot-RollPig-Safe-Updater/2.9.3')

text = changelog.read_text(encoding="utf-8")
entry = """# 更新\n## v2.9.3 (2026-08-04)\n### 管理面板操作反馈与待重启保护\n- 修复安全更新后页面文件已替换、但 AstrBot 尚未重启时，新页面请求旧后端路由并只显示“未找到该路由”的问题；现在会明确提示页面／运行时版本不一致并要求重启。\n- 新增醒目的“等待重启”横幅；待重启期间禁用迁移、验证、导出、回滚、同步与更新按钮，防止重复触发不存在或尚未载入的接口。\n- 迁移、验证、导出、回滚、同步、检查更新与安全更新均显示独立按钮状态、执行阶段、已等待时间、耗时及持久成功／失败反馈。\n- 全量刷新按钮现在显示刷新中状态与耗时；存储状态路由缺失时不再使整个管理页初始化失败。\n\n"""
if not text.startswith("# 更新\n"):
    raise SystemExit("CHANGELOG header mismatch")
changelog.write_text(entry + text[len("# 更新\n"):], encoding="utf-8")

(ROOT / "tests/test_dashboard_feedback.py").write_text(
    '''from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nPAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")\nFEEDBACK = (ROOT / "pages/pig-manager/ui-feedback.js").read_text(encoding="utf-8")\nMAIN = (ROOT / "main.py").read_text(encoding="utf-8")\n\n\ndef test_feedback_layer_loads_before_inline_module():\n    external = '<script src="./ui-feedback.js"></script>'\n    assert external in PAGE\n    assert PAGE.index(external) < PAGE.index('<script type="module">')\n\n\ndef test_feedback_layer_explains_stale_runtime_routes():\n    assert "页面与运行中的插件后端版本不一致" in FEEDBACK\n    assert "请先重启 AstrBot" in FEEDBACK\n    assert "storage/status" in FEEDBACK\n    assert "restart_required" in FEEDBACK\n    assert "等待重启" in FEEDBACK\n\n\ndef test_feedback_layer_tracks_each_long_operation_and_refresh():\n    for route in (\n        "resources/sync", "storage/migrate", "storage/verify",\n        "storage/export", "storage/rollback", "updates/check", "updates/apply",\n    ):\n        assert route in FEEDBACK\n    assert "已等待 ${seconds} 秒" in FEEDBACK\n    assert "耗时 ${elapsed} 秒" in FEEDBACK\n    assert "refreshBtn" in FEEDBACK\n    assert "正在刷新全部数据" in FEEDBACK\n\n\ndef test_dashboard_routes_are_registered_server_side():\n    for route in (\n        "/storage/status", "/storage/migrate", "/storage/verify",\n        "/storage/export", "/storage/rollback", "/updates/status",\n        "/updates/check", "/updates/apply",\n    ):\n        assert route in MAIN\n''',
    encoding="utf-8",
)
