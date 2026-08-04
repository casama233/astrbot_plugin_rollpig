from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.2"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text and old not in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old!r}")
    write(path, text.replace(old, new, 1))


analytics_path = "pages/pig-manager/ui-analytics.js"
analytics = read(analytics_path)
old_top = """(() => {\n  if (window.__rollpigAnalyticsUiReady) return;\n  window.__rollpigAnalyticsUiReady = true;\n\n  const bridge = window.AstrBotPluginPage;\n  if (!bridge) return;\n"""
new_top = """(() => {\n  const STATE_KEY = '__rollpigAnalyticsUiState';\n  const READY_KEY = '__rollpigAnalyticsUiReady';\n  const MAX_WAIT_MS = 8000;\n  const POLL_MS = 100;\n\n  if (window[READY_KEY] || window[STATE_KEY]?.starting) return;\n\n  const state = window[STATE_KEY] || {\n    starting: false,\n    attempts: 0,\n    startedAt: 0,\n    timedOut: false,\n    timer: null\n  };\n  window[STATE_KEY] = state;\n\n  const initialize = bridge => {\n    if (window[READY_KEY]) return;\n    window[READY_KEY] = true;\n    state.starting = false;\n    state.timedOut = false;\n    state.timer = null;\n"""
if new_top not in analytics:
    if analytics.count(old_top) != 1:
        raise SystemExit("ui-analytics.js: bootstrap top anchor not found")
    analytics = analytics.replace(old_top, new_top, 1)

old_bottom = """  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});\n  else start();\n})();\n"""
new_bottom = """  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});\n  else start();\n  };\n\n  const renderBridgeError = () => {\n    if (window[READY_KEY]) return;\n    const anchor = document.querySelector('#view-overview .metrics');\n    if (!anchor) {\n      if (document.readyState === 'loading') {\n        document.addEventListener('DOMContentLoaded', renderBridgeError, {once: true});\n      }\n      return;\n    }\n    let suite = document.getElementById('analyticsSuite');\n    if (!suite) {\n      suite = document.createElement('section');\n      suite.id = 'analyticsSuite';\n      suite.className = 'analytics-suite';\n      anchor.insertAdjacentElement('afterend', suite);\n    }\n    suite.innerHTML = '<div class="analytics-error"><strong>深度分析尚未连接管理桥接</strong><span>AstrBot 管理桥接在 8 秒内没有就绪。普通总览与管理功能不受影响，可点击重试。</span><button type="button" class="btn ghost" id="analyticsBridgeRetry">重新连接</button></div>';\n    document.getElementById('analyticsBridgeRetry')?.addEventListener('click', () => {\n      state.starting = true;\n      state.timedOut = false;\n      state.attempts = 0;\n      state.startedAt = performance.now();\n      suite.innerHTML = '<div class="analytics-skeleton analytics-skeleton--chart"></div>';\n      waitForBridge();\n    }, {once: true});\n  };\n\n  const waitForBridge = () => {\n    if (window[READY_KEY]) return;\n    const bridge = window.AstrBotPluginPage;\n    if (bridge) {\n      initialize(bridge);\n      return;\n    }\n    if (performance.now() - state.startedAt >= MAX_WAIT_MS) {\n      state.starting = false;\n      state.timedOut = true;\n      state.timer = null;\n      console.error('[rollpig] Analytics bootstrap timed out waiting for AstrBotPluginPage');\n      renderBridgeError();\n      return;\n    }\n    state.attempts += 1;\n    state.timer = window.setTimeout(waitForBridge, POLL_MS);\n  };\n\n  state.starting = true;\n  state.startedAt = performance.now();\n  waitForBridge();\n})();\n"""
if new_bottom not in analytics:
    if analytics.count(old_bottom) != 1:
        raise SystemExit("ui-analytics.js: bootstrap bottom anchor not found")
    analytics = analytics.replace(old_bottom, new_bottom, 1)
write(analytics_path, analytics)

replace_once("metadata.yaml", 'version: "3.0.1"', f'version: "{VERSION}"')
replace_once("main.py", "AstrBot-RollPig/3.0.1", f"AstrBot-RollPig/{VERSION}")
replace_once(
    "updater.py",
    "AstrBot-RollPig-Safe-Updater/3.0.1",
    f"AstrBot-RollPig-Safe-Updater/{VERSION}",
)

index = read("pages/pig-manager/index.html")
index = index.replace("ui-feedback.js?v=3.0.1", f"ui-feedback.js?v={VERSION}")
index = index.replace("v3.0.1", f"v{VERSION}")
write("pages/pig-manager/index.html", index)

loader = read("pages/pig-manager/ui-feedback.js")
loader = loader.replace("const ASSET_VERSION = '3.0.1'", f"const ASSET_VERSION = '{VERSION}'")
loader = loader.replace("?v=3.0.1", f"?v={VERSION}")
write("pages/pig-manager/ui-feedback.js", loader)

changelog = read("CHANGELOG.md")
entry = f'''## v{VERSION} (2026-08-04)\n### Analytics 初始化时序修复\n- 修复 AstrBot 管理桥接尚未就绪时，深度 Analytics 过早标记为已初始化并永久退出的问题。\n- Analytics 现在会以 100ms 间隔、最多 8 秒等待桥接；桥接就绪后才设置完成标记并读取聚合数据。\n- 重复注入保持幂等；桥接长期不可用时显示局部错误与“重新连接”，普通总览、图鉴和管理操作不受影响。\n- 所有管理页资源缓存键同步提升至 v{VERSION}，不修改 SQLite 单一权威、API 契约或业务流程。\n\n'''
if entry not in changelog:
    if not changelog.startswith("# 更新\n"):
        raise SystemExit("CHANGELOG.md: missing heading")
    changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
write("CHANGELOG.md", changelog)

for path in (
    "tests/test_dashboard_feedback.py",
    "tests/test_source_regressions.py",
    "tests/test_ui_cache_busting.py",
):
    text = read(path).replace("3.0.1", VERSION)
    write(path, text)

old_contract = ROOT / "tests/test_v301_release_contract.py"
new_contract = ROOT / "tests/test_v302_release_contract.py"
if old_contract.exists() and not new_contract.exists():
    old_contract.rename(new_contract)
contract = new_contract.read_text(encoding="utf-8").replace("3.0.1", VERSION).replace("v301", "v302")
new_contract.write_text(contract, encoding="utf-8")

write(
    "tests/test_analytics_bridge_bootstrap.py",
    '''from __future__ import annotations\n\nimport json\nimport shutil\nimport subprocess\nfrom pathlib import Path\n\nimport pytest\n\nROOT = Path(__file__).resolve().parents[1]\nSCRIPT = ROOT / "pages" / "pig-manager" / "ui-analytics.js"\n\n\ndef test_bridge_ready_flag_is_set_only_inside_initialize():\n    source = SCRIPT.read_text(encoding="utf-8")\n    bridge_lookup = source.index("const bridge = window.AstrBotPluginPage")\n    initialize = source.index("const initialize = bridge =>")\n    ready_assignment = source.index("window[READY_KEY] = true")\n    assert initialize < ready_assignment < bridge_lookup\n    assert "window[STATE_KEY]?.starting" in source\n    assert "MAX_WAIT_MS = 8000" in source\n    assert "window.setTimeout(waitForBridge, POLL_MS)" in source\n    assert "analyticsBridgeRetry" in source\n\n\n@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")\ndef test_bridge_bootstrap_delay_duplicate_and_timeout(tmp_path):\n    harness = tmp_path / "analytics-bootstrap-test.cjs"\n    harness.write_text(\n        f'''const fs = require('fs');\nconst vm = require('vm');\nconst source = fs.readFileSync({json.dumps(str(SCRIPT))}, 'utf8');\n\nfunction context() {{\n  let now = 0;\n  const timers = [];\n  const listeners = {{}};\n  const anchor = {{insertAdjacentElement() {{}}}};\n  const elements = new Map();\n  const document = {{\n    readyState: 'loading',\n    querySelector(selector) {{ return selector === '#view-overview .metrics' ? anchor : null; }},\n    getElementById(id) {{ return elements.get(id) || null; }},\n    createElement() {{\n      const node = {{id: '', className: '', innerHTML: '', addEventListener() {{}}}};\n      return node;\n    }},\n    addEventListener(name, fn) {{ listeners[name] = fn; }}\n  }};\n  anchor.insertAdjacentElement = (_where, node) => elements.set(node.id, node);\n  const window = {{\n    setTimeout(fn) {{ timers.push(fn); return timers.length; }},\n    addEventListener() {{}}\n  }};\n  const sandbox = {{window, document, performance: {{now: () => now}}, console, Intl, Promise, Array, Number, String, Math, Object, Error}};\n  vm.createContext(sandbox);\n  return {{sandbox, window, timers, listeners, advance(ms) {{ now += ms; const fn = timers.shift(); if (fn) fn(); }}};\n}}\n\nconst delayed = context();\nvm.runInContext(source, delayed.sandbox);\nif (delayed.window.__rollpigAnalyticsUiReady) throw new Error('ready set before bridge');\nif (delayed.timers.length !== 1) throw new Error('expected one wait timer');\nvm.runInContext(source, delayed.sandbox);\nif (delayed.timers.length !== 1) throw new Error('duplicate injection scheduled another timer');\ndelayed.window.AstrBotPluginPage = {{apiGet: async () => ({{data: {{}}}})}};\ndelayed.advance(100);\nif (!delayed.window.__rollpigAnalyticsUiReady) throw new Error('bridge arrival did not initialize');\n\nconst missing = context();\nvm.runInContext(source, missing.sandbox);\nfor (let i = 0; i < 80; i += 1) missing.advance(100);\nif (missing.window.__rollpigAnalyticsUiReady) throw new Error('timeout marked analytics ready');\nif (!missing.window.__rollpigAnalyticsUiState.timedOut) throw new Error('timeout state not recorded');\nif (missing.timers.length !== 0) throw new Error('polling continued after timeout');\n''',\n        encoding="utf-8",\n    )\n    result = subprocess.run(\n        ["node", str(harness)], capture_output=True, text=True, check=False\n    )\n    assert result.returncode == 0, result.stdout + result.stderr\n''',
)

for temporary in (
    ROOT / "scripts/apply_analytics_bridge_fix_v302.py",
    ROOT / ".github/workflows/apply-analytics-bridge-fix-v302.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.0.2 analytics bridge fix applied")
