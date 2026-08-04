from __future__ import annotations

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
entry = f'''## v{VERSION} (2026-08-04)
### Analytics 初始化时序修复
- 修复 AstrBot 管理桥接尚未就绪时，深度 Analytics 过早标记为已初始化并永久退出的问题。
- Analytics 现在会以 100ms 间隔、最多 8 秒等待桥接；桥接就绪后才设置完成标记并读取聚合数据。
- 重复注入保持幂等；桥接长期不可用时显示局部错误与“重新连接”，普通总览、图鉴和管理操作不受影响。
- 所有管理页资源缓存键同步提升至 v{VERSION}，不修改 SQLite 单一权威、API 契约或业务流程。

'''
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
    write(path, read(path).replace("3.0.1", VERSION))

old_contract = ROOT / "tests/test_v301_release_contract.py"
new_contract = ROOT / "tests/test_v302_release_contract.py"
if old_contract.exists() and not new_contract.exists():
    old_contract.rename(new_contract)
contract = new_contract.read_text(encoding="utf-8")
contract = contract.replace("3.0.1", VERSION).replace("v301", "v302")
new_contract.write_text(contract, encoding="utf-8")

write(
    "tests/analytics_bridge_harness.cjs",
    r"""const fs = require('fs');
const vm = require('vm');
const path = require('path');
const source = fs.readFileSync(
  path.join(__dirname, '..', 'pages', 'pig-manager', 'ui-analytics.js'),
  'utf8'
);

function context() {
  let now = 0;
  const timers = [];
  const listeners = {};
  const elements = new Map();
  const anchor = {insertAdjacentElement(_where, node) { elements.set(node.id, node); }};
  const document = {
    readyState: 'loading',
    querySelector(selector) { return selector === '#view-overview .metrics' ? anchor : null; },
    getElementById(id) { return elements.get(id) || null; },
    createElement() { return {id: '', className: '', innerHTML: '', addEventListener() {}}; },
    addEventListener(name, fn) { listeners[name] = fn; }
  };
  const window = {
    setTimeout(fn) { timers.push(fn); return timers.length; },
    addEventListener() {}
  };
  const sandbox = {
    window,
    document,
    performance: {now: () => now},
    console,
    Intl,
    Promise,
    Array,
    Number,
    String,
    Math,
    Object,
    Error
  };
  vm.createContext(sandbox);
  return {
    sandbox,
    window,
    timers,
    listeners,
    advance(ms) {
      now += ms;
      const fn = timers.shift();
      if (fn) fn();
    }
  };
}

const delayed = context();
vm.runInContext(source, delayed.sandbox);
if (delayed.window.__rollpigAnalyticsUiReady) throw new Error('ready set before bridge');
if (delayed.timers.length !== 1) throw new Error('expected one wait timer');
vm.runInContext(source, delayed.sandbox);
if (delayed.timers.length !== 1) throw new Error('duplicate injection scheduled another timer');
delayed.window.AstrBotPluginPage = {apiGet: async () => ({data: {}})};
delayed.advance(100);
if (!delayed.window.__rollpigAnalyticsUiReady) throw new Error('bridge arrival did not initialize');

const missing = context();
vm.runInContext(source, missing.sandbox);
for (let i = 0; i < 80; i += 1) missing.advance(100);
if (missing.window.__rollpigAnalyticsUiReady) throw new Error('timeout marked analytics ready');
if (!missing.window.__rollpigAnalyticsUiState.timedOut) throw new Error('timeout state not recorded');
if (missing.timers.length !== 0) throw new Error('polling continued after timeout');
""",
)

write(
    "tests/test_analytics_bridge_bootstrap.py",
    r"""from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pages" / "pig-manager" / "ui-analytics.js"
HARNESS = ROOT / "tests" / "analytics_bridge_harness.cjs"


def test_bridge_ready_flag_is_set_only_inside_initialize():
    source = SCRIPT.read_text(encoding="utf-8")
    initialize = source.index("const initialize = bridge =>")
    ready_assignment = source.index("window[READY_KEY] = true")
    bridge_lookup = source.index("const bridge = window.AstrBotPluginPage")
    assert initialize < ready_assignment < bridge_lookup
    assert "window[STATE_KEY]?.starting" in source
    assert "MAX_WAIT_MS = 8000" in source
    assert "window.setTimeout(waitForBridge, POLL_MS)" in source
    assert "analyticsBridgeRetry" in source


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_bridge_bootstrap_delay_duplicate_and_timeout():
    result = subprocess.run(
        ["node", str(HARNESS)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
""",
)

for temporary in (
    ROOT / "scripts/apply_analytics_bridge_fix_v302.py",
    ROOT / ".github/workflows/apply-analytics-bridge-fix-v302.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.0.2 analytics bridge fix applied")
