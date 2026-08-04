from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "pages" / "pig-manager"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


# Rebuild Analytics around an explicit click-triggered, root-bound lifecycle.
analytics_path = UI / "ui-analytics.js"
analytics = read(analytics_path)
start = analytics.index("  const number = new Intl.NumberFormat")
end = analytics.index("\n  const start = () => {", start)
core = analytics[start:end]
core = core.replace(
    "  function render(data) {\n    ensureSuite();",
    "  function render(data) {\n    if (window[STATE_KEY] !== state || !pageRoot.isConnected) return;\n    ensureSuite();",
)
core = core.replace(
    "  function renderError(error) {\n    const suite = ensureSuite();",
    "  function renderError(error) {\n    if (window[STATE_KEY] !== state || !pageRoot.isConnected) return;\n    const suite = ensureSuite();",
)
header = """(() => {
  'use strict';
  const STATE_KEY = '__rollpigAnalyticsUiState';
  const VERSION = '3.1.1';
  const pageRoot = document.querySelector('.shell');
  const bridge = window.AstrBotPluginPage;
  if (!pageRoot || !bridge?.apiGet) throw new Error('深度分析缺少页面根节点或管理桥接');

  const previous = window[STATE_KEY];
  if (
    previous?.version === VERSION &&
    previous.root === pageRoot &&
    pageRoot.querySelector('#analyticsSuite')
  ) {
    previous.refresh?.();
    return;
  }
  previous?.abortController?.abort();

  const abortController = new AbortController();
  const state = {
    version: VERSION,
    root: pageRoot,
    mounted: false,
    refresh: null,
    abortController,
  };
  window[STATE_KEY] = state;
"""
footer = """

  const mount = () => {
    const suite = ensureSuite();
    if (!suite) throw new Error('深度分析挂载点不存在');
    state.mounted = true;
    state.refresh = loadInsights;

    const refreshButton = pageRoot.querySelector('#refreshBtn');
    refreshButton?.addEventListener('click', () => {
      if (window[STATE_KEY] === state) loadInsights();
    }, {signal: abortController.signal});

    loadInsights();
  };

  mount();
})();
"""
write(analytics_path, header + core + footer)

# Keep the inline bootstrap byte-for-byte aligned with its maintenance source.
bootstrap = read(UI / "ui-bootstrap.js").strip()
index_path = UI / "index.html"
page = read(index_path)
page, count = re.subn(
    r'<script data-rollpig-bootstrap="3\.1\.0">[\s\S]*?</script>',
    '<script data-rollpig-bootstrap="3.1.1">\n' + bootstrap + '\n</script>',
    page,
    count=1,
)
if count != 1:
    raise RuntimeError(f"expected one inline bootstrap, found {count}")
page, count = re.subn(
    r'async function pollSyncCompletion\(\)\{[\s\S]*?\}\nfunction renderHub',
    "async function pollSyncCompletion(){setSyncFeedback('同步任务已启动；已关闭自动轮询，请点击右上角刷新查看最新状态。')}\nfunction renderHub",
    page,
    count=1,
)
if count != 1:
    raise RuntimeError(f"expected one sync polling loop, found {count}")
write(index_path, page)

# Deliver only the two Analytics assets through the authenticated endpoint.
main_path = ROOT / "main.py"
main = read(main_path).replace("AstrBot-RollPig/3.1.0", "AstrBot-RollPig/3.1.1")
main, count = re.subn(
    r'    UI_ASSET_VERSION = "3\.1\.0"[\s\S]*?    \)\n\n    def __init__',
    '''    UI_ASSET_VERSION = "3.1.1"
    UI_ASSET_MAX_FILE_BYTES = 512 * 1024
    UI_ASSET_MAX_TOTAL_BYTES = 768 * 1024
    UI_ASSET_FILES = (
        ("analytics-theme", "style", "analytics-theme.css"),
        ("ui-analytics", "script", "ui-analytics.js"),
    )

    def __init__''',
    main,
    count=1,
)
if count != 1:
    raise RuntimeError(f"expected one UI asset block, found {count}")
write(main_path, main)

metadata_path = ROOT / "metadata.yaml"
write(metadata_path, read(metadata_path).replace('version: "3.1.0"', 'version: "3.1.1"'))
updater_path = ROOT / "updater.py"
write(
    updater_path,
    read(updater_path).replace(
        "AstrBot-RollPig-Safe-Updater/3.1.0",
        "AstrBot-RollPig-Safe-Updater/3.1.1",
    ),
)

changelog_path = ROOT / "CHANGELOG.md"
changelog = read(changelog_path)
entry = """# 更新
## v3.1.1 (2026-08-05)
### 管理页按需加载与性能修复
- 管理页默认只运行轻量核心模块，不再自动请求或注入企业增强与 Analytics 整包资源。
- 新增“深度分析”按钮；只有点击后才通过认证桥接加载 Analytics 样式、脚本与聚合数据。
- 删除大体积源码的 `sessionStorage` 缓存、100ms Bridge 轮询、持续 DOM `MutationObserver` 与同步状态自动轮询。
- Analytics 按当前 `.shell` 根节点绑定，旧 SPA 根节点通过 `AbortController` 解除事件，避免重复挂载和重复刷新。
- 新增 jsdom 回归和真实 Chromium 性能测试，覆盖默认零增强请求、单实例挂载、SPA 多次重入、观察器/定时器数量与 JS 堆增长。

"""
if not changelog.startswith("# 更新\n"):
    raise RuntimeError("unexpected changelog header")
write(changelog_path, entry + changelog[len("# 更新\n"):])

# Update legacy source contracts without weakening unrelated regression coverage.
source_path = ROOT / "tests" / "test_source_regressions.py"
source = read(source_path)
source = source.replace('version: "3.1.0"', 'version: "3.1.1"')
source = source.replace("AstrBot-RollPig/3.1.0", "AstrBot-RollPig/3.1.1")
source, count = re.subn(
    r'def test_dashboard_feedback_covers_restart_and_projection_rebuild\(\):[\s\S]*?(?=\ndef test_main_delegates_sql_primary_hot_writes)',
    '''def test_dashboard_feedback_is_click_only_and_has_no_continuous_watchers():
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages" / "pig-manager" / "ui-bootstrap.js").read_text(
        encoding="utf-8"
    )
    assert "rollpig-inline-assets:start" not in page
    assert "analyticsLoadBtn" in bootstrap
    assert "sessionStorage" not in bootstrap
    assert "MutationObserver" not in bootstrap
    assert "setInterval" not in bootstrap

''',
    source,
    count=1,
)
if count != 1:
    raise RuntimeError(f"expected one legacy feedback contract, found {count}")
write(source_path, source)

legacy = ROOT / "tests" / "test_v310_release_contract.py"
if legacy.exists():
    legacy.unlink()

for test_path in (ROOT / "tests").rglob("*.py"):
    text = read(test_path)
    if "3.1.0" in text:
        write(test_path, text.replace("3.1.0", "3.1.1"))

# Static release gates before external test runners execute.
for filename in ("ui-bootstrap.js", "ui-enterprise.js", "ui-feedback-core.js", "ui-analytics.js"):
    source = read(UI / filename)
    if "MutationObserver" in source or "setInterval" in source:
        raise RuntimeError(f"continuous watcher remains in {filename}")
if "sessionStorage" in bootstrap:
    raise RuntimeError("bootstrap still contains sessionStorage")
if "pollSyncCompletion(){if(syncPolling)" in page:
    raise RuntimeError("sync polling loop remains")
