from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.3"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


analytics_path = "pages/pig-manager/ui-analytics.js"
analytics = read(analytics_path)

old_bootstrap = """  const STATE_KEY = '__rollpigAnalyticsUiState';
  const READY_KEY = '__rollpigAnalyticsUiReady';
  const MAX_WAIT_MS = 8000;
  const POLL_MS = 100;

  if (window[READY_KEY] || window[STATE_KEY]?.starting) return;

  const state = window[STATE_KEY] || {
    starting: false,
    attempts: 0,
    startedAt: 0,
    timedOut: false,
    timer: null
  };
  window[STATE_KEY] = state;

  const initialize = bridge => {
    if (window[READY_KEY]) return;
    window[READY_KEY] = true;
    state.starting = false;
    state.timedOut = false;
    state.timer = null;
"""

new_bootstrap = """  const STATE_KEY = '__rollpigAnalyticsUiState';
  const READY_KEY = '__rollpigAnalyticsUiReady';
  const BOOTSTRAP_VERSION = '3.0.3';
  const MAX_WAIT_MS = 8000;
  const POLL_MS = 100;

  const mounted = () => Boolean(document.getElementById('analyticsSuite'));
  const previousState = window[STATE_KEY];

  if (
    previousState?.version === BOOTSTRAP_VERSION &&
    previousState.starting
  ) return;

  if (
    previousState?.version === BOOTSTRAP_VERSION &&
    window[READY_KEY] &&
    mounted()
  ) {
    previousState.refresh?.();
    return;
  }

  if (previousState?.timer && window.clearTimeout) {
    window.clearTimeout(previousState.timer);
  }

  window[READY_KEY] = false;
  const state = {
    version: BOOTSTRAP_VERSION,
    starting: false,
    initialized: false,
    attempts: 0,
    startedAt: 0,
    timedOut: false,
    timer: null,
    refresh: null
  };
  window[STATE_KEY] = state;

  const initialize = bridge => {
    if (state.initialized && mounted()) {
      state.refresh?.();
      return;
    }
    window[READY_KEY] = true;
    state.initialized = true;
    state.timedOut = false;
    state.timer = null;
"""

if new_bootstrap not in analytics:
    if analytics.count(old_bootstrap) != 1:
        raise SystemExit("ui-analytics.js: bootstrap anchor not found")
    analytics = analytics.replace(old_bootstrap, new_bootstrap, 1)

old_start = """  const start = () => {
    ensureSuite();
    loadInsights();
    document.getElementById('refreshBtn')?.addEventListener('click', () => {
      window.setTimeout(loadInsights, 180);
    });
    window.addEventListener('hashchange', () => {
      if (location.hash.replace(/^#\\/?/, '') !== 'catalog') loadInsights();
    });
  };
"""

new_start = """  const start = () => {
    const suite = ensureSuite();
    if (!suite) {
      state.starting = false;
      return;
    }

    window[READY_KEY] = true;
    state.initialized = true;
    state.starting = false;
    state.refresh = loadInsights;
    loadInsights();

    const refreshBtn = document.getElementById('refreshBtn');
    if (
      refreshBtn &&
      refreshBtn.dataset.rollpigAnalyticsBound !== BOOTSTRAP_VERSION
    ) {
      refreshBtn.dataset.rollpigAnalyticsBound = BOOTSTRAP_VERSION;
      refreshBtn.addEventListener('click', () => {
        window.setTimeout(loadInsights, 180);
      });
    }

    if (!window.__rollpigAnalyticsHashHandler) {
      window.__rollpigAnalyticsHashHandler = () => {
        if (location.hash.replace(/^#\\/?/, '') !== 'catalog') {
          window[STATE_KEY]?.refresh?.();
        }
      };
      window.addEventListener(
        'hashchange',
        window.__rollpigAnalyticsHashHandler
      );
    }
  };
"""

if new_start not in analytics:
    if analytics.count(old_start) != 1:
        raise SystemExit("ui-analytics.js: start anchor not found")
    analytics = analytics.replace(old_start, new_start, 1)

write(analytics_path, analytics)

for path in (
    "metadata.yaml",
    "main.py",
    "updater.py",
    "pages/pig-manager/index.html",
    "pages/pig-manager/ui-feedback.js",
    "tests/test_dashboard_feedback.py",
    "tests/test_source_regressions.py",
    "tests/test_ui_cache_busting.py",
    "tests/test_analytics_bridge_bootstrap.py",
):
    text = read(path).replace("3.0.2", VERSION)
    if path == "tests/test_analytics_bridge_bootstrap.py":
        text = text.replace(
            'assert "window[STATE_KEY]?.starting" in source',
            'assert "previousState?.version === BOOTSTRAP_VERSION" in source',
        )
    write(path, text)

old_contract = ROOT / "tests/test_v302_release_contract.py"
new_contract = ROOT / "tests/test_v303_release_contract.py"
if old_contract.exists() and not new_contract.exists():
    old_contract.rename(new_contract)
if new_contract.exists():
    contract = new_contract.read_text(encoding="utf-8")
    contract = contract.replace("3.0.2", VERSION).replace("v302", "v303")
    new_contract.write_text(contract, encoding="utf-8")

changelog = read("CHANGELOG.md")
entry = """## v3.0.3 (2026-08-04)
### Analytics 单页容器重新挂载修复
- 修复 AstrBot 管理后台复用同一个页面窗口时，旧版全局 ready 标志残留，导致新 DOM 没有 `analyticsSuite` 却跳过初始化的问题。
- Analytics 现在以当前 DOM 是否实际挂载为准，并使用版本化启动状态；旧状态或缺失挂载会自动重新初始化。
- 刷新按钮按当前 DOM 元素去重绑定，hashchange 监听全局只注册一次，避免重复进入页面后叠加请求。
- 不修改 Analytics 只读 API、SQLite 单一权威、数据结构或其他管理业务流程。

"""
if entry not in changelog:
    if not changelog.startswith("# 更新\n"):
        raise SystemExit("CHANGELOG.md: missing heading")
    changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
write("CHANGELOG.md", changelog)

test_content = '''from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pages" / "pig-manager" / "ui-analytics.js"


def test_spa_remount_contract_is_versioned_and_dom_aware():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "const BOOTSTRAP_VERSION = '3.0.3'" in source
    assert "const mounted = () => Boolean(document.getElementById('analyticsSuite'))" in source
    assert "previousState?.version === BOOTSTRAP_VERSION" in source
    assert "window[READY_KEY] = false" in source
    assert "refreshBtn.dataset.rollpigAnalyticsBound" in source
    assert "window.__rollpigAnalyticsHashHandler" in source
'''
write("tests/test_analytics_spa_remount.py", test_content)

for temporary in (
    ROOT / "scripts/apply_analytics_spa_fix_v303.py",
    ROOT / ".github/workflows/apply-analytics-spa-fix-v303.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.0.3 Analytics SPA remount fix applied")
