from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1.0"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one occurrence of {old!r}, found {count}")
    write(path, text.replace(old, new, 1))


BOOTSTRAP = r'''(() => {
  'use strict';
  const VERSION = '3.1.0';
  const STATE_KEY = '__rollpigUiBootstrapState';
  const CACHE_KEY = `rollpig:authenticated-ui:${VERSION}`;
  const ALLOWED = new Map([
    ['enterprise-theme', 'style'],
    ['analytics-theme', 'style'],
    ['ui-feedback-core', 'script'],
    ['ui-enterprise', 'script'],
    ['ui-analytics', 'script'],
  ]);
  const SCRIPT_ORDER = ['ui-feedback-core', 'ui-enterprise', 'ui-analytics'];
  const STYLE_ORDER = ['enterprise-theme', 'analytics-theme'];
  const pageRoot = document.querySelector('.shell') || document.body;
  const pageToken = pageRoot.dataset.rollpigPageToken ||
    `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  pageRoot.dataset.rollpigPageToken = pageToken;

  const previous = window[STATE_KEY];
  if (
    previous?.version === VERSION &&
    previous.pageToken === pageToken &&
    ['loading', 'ready', 'partial'].includes(previous.status)
  ) return;

  let resolveReady;
  const state = {
    version: VERSION,
    pageToken,
    status: 'loading',
    errorCode: '',
    errors: [],
    assets: {},
    retry: null,
    reportModuleError: null,
    ready: new Promise(resolve => { resolveReady = resolve; }),
  };
  window[STATE_KEY] = state;

  const unwrap = response => {
    if (response?.status === 'error') throw new Error(response.message || '后端拒绝读取增强资源');
    const first = response?.data ?? response;
    if (first?.status === 'error') throw new Error(first.message || '增强资源返回错误');
    return first?.data ?? first;
  };

  const diagnosticHost = () => {
    let host = document.getElementById('uiEnhancementStatus');
    if (host) return host;
    host = document.createElement('section');
    host.id = 'uiEnhancementStatus';
    host.className = 'panel';
    host.setAttribute('role', 'status');
    host.setAttribute('aria-live', 'polite');
    host.style.cssText = 'display:none;margin:0 0 18px;padding:14px 18px;border-style:dashed';
    const topbar = document.querySelector('.topbar');
    if (topbar) topbar.insertAdjacentElement('afterend', host);
    else document.body.prepend(host);
    return host;
  };

  const showDiagnostic = (kind, message, retry = false) => {
    const host = diagnosticHost();
    host.style.display = '';
    host.dataset.kind = kind;
    const title = kind === 'loading'
      ? '正在连接增强界面'
      : kind === 'partial'
        ? '部分增强模块未加载'
        : '增强界面未加载';
    host.innerHTML = `<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap"><div><strong>${title}</strong><div class="panel-desc" style="margin-top:5px"></div></div>${retry ? '<button type="button" class="btn ghost" id="uiEnhancementRetry">重试增强界面</button>' : ''}</div>`;
    host.querySelector('.panel-desc').textContent = `${message} 核心数据总览、猪猪图鉴和管理操作不受影响。`;
    host.querySelector('#uiEnhancementRetry')?.addEventListener('click', () => state.retry?.(), {once: true});
  };

  const clearDiagnostic = () => {
    const host = document.getElementById('uiEnhancementStatus');
    if (host) host.style.display = 'none';
  };

  const validateBundle = bundle => {
    if (!bundle || bundle.version !== VERSION || !Array.isArray(bundle.assets)) {
      throw Object.assign(new Error(`增强资源版本不匹配：期望 ${VERSION}`), {code: 'version-mismatch'});
    }
    const seen = new Set();
    let total = 0;
    for (const asset of bundle.assets) {
      if (!asset || ALLOWED.get(asset.name) !== asset.kind || typeof asset.source !== 'string') {
        throw Object.assign(new Error(`增强资源清单包含未知项目：${asset?.name || 'unknown'}`), {code: 'invalid-manifest'});
      }
      if (seen.has(asset.name)) throw Object.assign(new Error(`增强资源重复：${asset.name}`), {code: 'duplicate-asset'});
      seen.add(asset.name);
      total += asset.source.length;
    }
    for (const name of ALLOWED.keys()) {
      if (!seen.has(name)) throw Object.assign(new Error(`增强资源缺失：${name}`), {code: 'missing-asset'});
    }
    if (total > 1_500_000) throw Object.assign(new Error('增强资源总量超出安全限制'), {code: 'bundle-too-large'});
    return bundle;
  };

  const sha256 = async source => {
    if (!window.crypto?.subtle || typeof TextEncoder === 'undefined') return '';
    const digest = await window.crypto.subtle.digest('SHA-256', new TextEncoder().encode(source));
    return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
  };

  const verifyAsset = async asset => {
    if (!asset.sha256) return;
    const actual = await sha256(asset.source);
    if (actual && actual !== asset.sha256) {
      throw Object.assign(new Error(`增强资源校验失败：${asset.name}`), {code: 'checksum-mismatch'});
    }
  };

  const injectStyle = asset => {
    const selector = `style[data-rollpig-ui-asset="${asset.name}"]`;
    const existing = document.querySelector(selector);
    if (existing?.dataset.version === VERSION) {
      state.assets[asset.name] = 'ready';
      return;
    }
    existing?.remove();
    const style = document.createElement('style');
    style.dataset.rollpigUiAsset = asset.name;
    style.dataset.version = VERSION;
    style.textContent = asset.source;
    document.head.appendChild(style);
    state.assets[asset.name] = 'ready';
  };

  state.reportModuleError = (name, error) => {
    const message = error instanceof Error ? error.message : String(error || '未知脚本错误');
    state.assets[name] = 'error';
    state.errors.push({name, message});
    console.error(`[rollpig] ${name} failed`, error);
  };

  const injectScript = asset => {
    document.querySelectorAll(`script[data-rollpig-ui-asset="${asset.name}"]`).forEach(node => node.remove());
    const script = document.createElement('script');
    script.dataset.rollpigUiAsset = asset.name;
    script.dataset.version = VERSION;
    script.dataset.pageToken = pageToken;
    script.textContent = `try {\n${asset.source}\n} catch (error) { window.${STATE_KEY}?.reportModuleError(${JSON.stringify(asset.name)}, error); }\n//# sourceURL=rollpig-${asset.name}-${VERSION}.js`;
    document.body.appendChild(script);
    if (!state.errors.some(item => item.name === asset.name)) state.assets[asset.name] = 'ready';
  };

  const applyBundle = async bundle => {
    const byName = new Map(bundle.assets.map(asset => [asset.name, asset]));
    for (const name of [...STYLE_ORDER, ...SCRIPT_ORDER]) await verifyAsset(byName.get(name));
    STYLE_ORDER.forEach(name => injectStyle(byName.get(name)));
    SCRIPT_ORDER.forEach(name => injectScript(byName.get(name)));
    state.status = state.errors.length ? 'partial' : 'ready';
    document.documentElement.dataset.rollpigEnhancedUi = state.status;
    if (state.status === 'ready') clearDiagnostic();
    else showDiagnostic('partial', state.errors.map(item => `${item.name}: ${item.message}`).join('；'), true);
    resolveReady(state);
  };

  const readCache = () => {
    try {
      const cached = window.sessionStorage?.getItem(CACHE_KEY);
      return cached ? validateBundle(JSON.parse(cached)) : null;
    } catch {
      return null;
    }
  };

  const saveCache = bundle => {
    try { window.sessionStorage?.setItem(CACHE_KEY, JSON.stringify(bundle)); } catch { /* sandboxed storage is optional */ }
  };

  const fetchBundle = async ignoreCache => {
    if (!ignoreCache) {
      const cached = readCache();
      if (cached) return cached;
    }
    const bridge = window.AstrBotPluginPage;
    if (!bridge?.apiGet) throw Object.assign(new Error('AstrBot Plugin Page Bridge 不存在'), {code: 'bridge-missing'});
    if (typeof bridge.ready === 'function') await bridge.ready();
    const bundle = validateBundle(unwrap(await bridge.apiGet('ui/assets', {version: VERSION})));
    saveCache(bundle);
    return bundle;
  };

  const load = async ({ignoreCache = false} = {}) => {
    state.status = 'loading';
    state.errors = [];
    state.errorCode = '';
    showDiagnostic('loading', '正在通过 AstrBot 认证桥接读取企业主题与深度分析资源。');
    try {
      await applyBundle(await fetchBundle(ignoreCache));
    } catch (error) {
      state.status = 'error';
      state.errorCode = error?.code || 'asset-request-failed';
      state.errors.push({name: 'bootstrap', message: error?.message || String(error)});
      document.documentElement.dataset.rollpigEnhancedUi = 'error';
      showDiagnostic('error', `原因：${error?.message || error}（${state.errorCode}）。`, true);
      resolveReady(state);
    }
  };

  state.retry = () => {
    try { window.sessionStorage?.removeItem(CACHE_KEY); } catch { /* optional */ }
    load({ignoreCache: true});
  };
  load();
})();'''

if "</script>" in BOOTSTRAP.lower():
    raise SystemExit("bootstrap source must not contain a closing script tag")

# Version contract.
replace_once("metadata.yaml", 'version: "3.0.5"', f'version: "{VERSION}"')
replace_once(
    "main.py",
    '"AstrBot-RollPig/3.0.5 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
    f'"AstrBot-RollPig/{VERSION} (+https://github.com/casama233/astrbot_plugin_rollpig)"',
)
updater = read("updater.py")
updater, count = re.subn(
    r"AstrBot-RollPig-Safe-Updater/\d+\.\d+\.\d+",
    f"AstrBot-RollPig-Safe-Updater/{VERSION}",
    updater,
)
if count < 1:
    raise SystemExit("updater.py: updater User-Agent not found")
write("updater.py", updater)

# Authenticated, fixed-whitelist UI asset endpoint.
main = read("main.py")
user_agent_end = '''    USER_AGENT = (
        "AstrBot-RollPig/3.1.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"
    )
'''
if user_agent_end not in main:
    raise SystemExit("main.py: updated USER_AGENT anchor missing")
constants = user_agent_end + '''    UI_ASSET_VERSION = "3.1.0"
    UI_ASSET_MAX_FILE_BYTES = 512 * 1024
    UI_ASSET_MAX_TOTAL_BYTES = 2 * 1024 * 1024
    UI_ASSET_FILES = (
        ("enterprise-theme", "style", "enterprise-theme.css"),
        ("analytics-theme", "style", "analytics-theme.css"),
        ("ui-feedback-core", "script", "ui-feedback-core.js"),
        ("ui-enterprise", "script", "ui-enterprise.js"),
        ("ui-analytics", "script", "ui-analytics.js"),
    )
'''
main = main.replace(user_agent_end, constants, 1)
registration = '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/analytics/insights",
            self.page_analytics_insights,
            ["GET"],
            "今日小猪深度分析",
        )
'''
if main.count(registration) != 1:
    raise SystemExit("main.py: analytics registration anchor mismatch")
main = main.replace(
    registration,
    registration
    + '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/ui/assets",
            self.page_ui_assets,
            ["GET"],
            "今日小猪认证管理页增强资源",
        )
''',
    1,
)
method_anchor = "    async def page_analytics_insights(self):\n"
if main.count(method_anchor) != 1:
    raise SystemExit("main.py: analytics method anchor mismatch")
ui_methods = '''    def _build_ui_asset_bundle(self) -> dict:
        """Return fixed, local UI sources through the authenticated plugin bridge."""
        root = (self.plugin_dir / "pages" / "pig-manager").resolve()
        assets = []
        total_bytes = 0
        bundle_digest = hashlib.sha256()
        for name, kind, filename in self.UI_ASSET_FILES:
            path = (root / filename).resolve()
            if path.parent != root or not path.is_file():
                raise RuntimeError(f"管理页增强资源不存在：{filename}")
            raw = path.read_bytes()
            size = len(raw)
            total_bytes += size
            if size > self.UI_ASSET_MAX_FILE_BYTES:
                raise RuntimeError(f"管理页增强资源过大：{filename}")
            if total_bytes > self.UI_ASSET_MAX_TOTAL_BYTES:
                raise RuntimeError("管理页增强资源总量超过安全限制")
            try:
                source = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RuntimeError(f"管理页增强资源不是 UTF-8：{filename}") from exc
            digest = hashlib.sha256(raw).hexdigest()
            bundle_digest.update(f"{name}:{kind}:{digest}\\n".encode("utf-8"))
            assets.append(
                {
                    "name": name,
                    "kind": kind,
                    "source": source,
                    "sha256": digest,
                    "bytes": size,
                }
            )
        bundle_sha256 = bundle_digest.hexdigest()
        return {
            "version": self.UI_ASSET_VERSION,
            "cache_key": f"{self.UI_ASSET_VERSION}-{bundle_sha256[:16]}",
            "bundle_sha256": bundle_sha256,
            "assets": assets,
        }

    async def page_ui_assets(self):
        """Read-only authenticated delivery for the fixed admin UI asset whitelist."""
        try:
            data = await asyncio.to_thread(self._build_ui_asset_bundle)
            return self._jsonify({"status": "ok", "data": data})
        except Exception as exc:
            logger.error(f"读取管理页增强资源失败：{exc}")
            return self._jsonify(
                {"status": "error", "message": "无法读取管理页增强资源；核心页面仍可使用"}
            )

'''
main = main.replace(method_anchor, ui_methods + method_anchor, 1)
write("main.py", main)

# Small inline bootstrap; the large assets stay modular and travel through ui/assets.
write("pages/pig-manager/ui-bootstrap.js", BOOTSTRAP + "\n")
page = read("pages/pig-manager/index.html")
bridge_anchor = '<script src="/api/plugin/page/bridge-sdk.js"></script>\n<script type="module">'
if page.count(bridge_anchor) != 1:
    raise SystemExit("index.html: bridge/module anchor mismatch")
inline_bootstrap = (
    '<script src="/api/plugin/page/bridge-sdk.js"></script>\n'
    f'<script data-rollpig-bootstrap="{VERSION}">\n{BOOTSTRAP}\n</script>\n'
    '<script type="module">'
)
page = page.replace(bridge_anchor, inline_bootstrap, 1)
write("pages/pig-manager/index.html", page)

# Version modular sources and make enterprise decoration refreshable on SPA remount.
loader = read("pages/pig-manager/ui-feedback.js")
loader = re.sub(r"const ASSET_VERSION = '[^']+'", f"const ASSET_VERSION = '{VERSION}'", loader, count=1)
loader = re.sub(r"\?v=\d+\.\d+\.\d+", f"?v={VERSION}", loader)
write("pages/pig-manager/ui-feedback.js", loader)

analytics = read("pages/pig-manager/ui-analytics.js")
analytics, count = re.subn(
    r"const BOOTSTRAP_VERSION = '[^']+'",
    f"const BOOTSTRAP_VERSION = '{VERSION}'",
    analytics,
    count=1,
)
if count != 1:
    raise SystemExit("ui-analytics.js: BOOTSTRAP_VERSION missing")
write("pages/pig-manager/ui-analytics.js", analytics)

enterprise = read("pages/pig-manager/ui-enterprise.js")
enterprise = enterprise.replace(
    "  if (window.__rollpigEnterpriseUiReady) return;\n  window.__rollpigEnterpriseUiReady = true;",
    "  if (window.__rollpigEnterpriseUiReady) {\n    window.__rollpigEnterpriseUiRefresh?.();\n    return;\n  }\n  window.__rollpigEnterpriseUiReady = true;",
    1,
)
enterprise = enterprise.replace("root.dataset.uiVersion = '2.14';", "root.dataset.uiVersion = '3.1';", 1)
enterprise = enterprise.replace(
    "  addSkipLink();\n  decorateStructure();\n  syncBusyState();",
    "  window.__rollpigEnterpriseUiRefresh = () => {\n    addSkipLink();\n    decorateStructure();\n    syncBusyState();\n  };\n  window.__rollpigEnterpriseUiRefresh();",
    1,
)
if "window.__rollpigEnterpriseUiRefresh" not in enterprise:
    raise SystemExit("ui-enterprise.js: SPA refresh patch failed")
write("pages/pig-manager/ui-enterprise.js", enterprise)

# Release notes.
changelog = read("CHANGELOG.md")
entry = f'''## v{VERSION} (2026-08-04)
### 认证桥接企业 UI 与浏览器级回归
- 核心数据总览、猪猪图鉴、同步、SQLite 管理和安全更新继续由轻量主模块独立运行，不等待任何增强资源。
- 新增只读 `ui/assets` 接口，只从插件目录固定白名单读取企业主题、反馈增强和 Analytics 源码，并通过 AstrBot Plugin Page Bridge 携带认证返回；浏览器不再直接请求会 401 的相对子资源。
- 主页面仅内联小型启动器，使用版本化会话缓存、SHA-256 校验、模块独立错误边界、可见诊断与重试；增强层失败不会隐藏或阻断核心视图。
- 恢复 v2.15.0 商业级企业主题与深度 Analytics，并支持 AstrBot 单页容器二次进入时重新挂载。
- 新增 jsdom 浏览器行为测试，覆盖核心视图切换、认证资源注入、资源失败降级、Analytics API 局部失败和 SPA 重挂载。

'''
if not changelog.startswith("# 更新\n"):
    raise SystemExit("CHANGELOG.md: heading missing")
changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
write("CHANGELOG.md", changelog)
write(
    "docs/admin-ui-authenticated-assets-v310.md",
    f'''# v{VERSION} 管理页增强资源架构

## 不可破坏的核心层

`pages/pig-manager/index.html` 内的原始 ES 模块独立负责数据总览、猪猪图鉴、云资源同步、SQLite 管理和安全更新。即使增强资源接口、企业主题或 Analytics 全部失败，核心层仍必须可以初始化和切换视图。

## 认证增强层

- 浏览器仅直接加载 AstrBot 官方 `/api/plugin/page/bridge-sdk.js`。
- 小型内联 bootstrap 调用 `bridge.apiGet('ui/assets')`。
- 后端只读取 `UI_ASSET_FILES` 固定白名单，不接受文件名或路径参数。
- 返回内容包含版本、整包哈希、每项 SHA-256、类型和 UTF-8 源码。
- 客户端按 style → feedback → enterprise → analytics 顺序注入，并以 `{VERSION}` 作为会话缓存键。

## 故障边界

- Bridge 或 `ui/assets` 失败：显示增强层诊断，核心页面继续运行。
- 单一增强脚本异常：记录具体模块，其他模块继续加载。
- `analytics/insights` 失败：只在深度分析区域显示重试，不影响普通总览和管理操作。
- AstrBot SPA 重新进入：新的页面令牌会触发脚本重挂载；样式复用，Analytics 根据当前 DOM 重新建立。
''',
)

# Browser-level jsdom tests.
package = {
    "name": "astrbot-plugin-rollpig-ui-tests",
    "private": True,
    "type": "module",
    "scripts": {"test": "node --test tests/browser/*.test.mjs"},
    "devDependencies": {"jsdom": "^26.1.0"},
}
write("package.json", json.dumps(package, ensure_ascii=False, indent=2) + "\n")

write(
    "tests/browser/admin-ui.test.mjs",
    r'''import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {JSDOM} from 'jsdom';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const PAGE = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/index.html'), 'utf8');
const BOOTSTRAP = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/ui-bootstrap.js'), 'utf8');
const CORE = PAGE.match(/<script type="module">([\s\S]*?)<\/script>/)?.[1] || '';
const BODY = PAGE
  .replace('<script src="/api/plugin/page/bridge-sdk.js"></script>', '')
  .replace(/<script data-rollpig-bootstrap="3\.1\.0">[\s\S]*?<\/script>/, '')
  .replace(/<script type="module">[\s\S]*?<\/script>/, '');
const ASSETS = [
  ['enterprise-theme', 'style', 'enterprise-theme.css'],
  ['analytics-theme', 'style', 'analytics-theme.css'],
  ['ui-feedback-core', 'script', 'ui-feedback-core.js'],
  ['ui-enterprise', 'script', 'ui-enterprise.js'],
  ['ui-analytics', 'script', 'ui-analytics.js'],
].map(([name, kind, filename]) => ({
  name, kind, source: fs.readFileSync(path.join(ROOT, 'pages/pig-manager', filename), 'utf8'), sha256: '',
}));

const insights = {
  source: 'normalized-sql', observability: {query_elapsed_ms: 1.2},
  periods: {
    current: {active_users: 4, draws: 7, new_unlocks: 3, unlock_efficiency: 42.9, avg_daily_users: 1.2},
    previous: {active_users: 3, draws: 5, new_unlocks: 2},
  },
  deltas: {active_users: 33.3, draws: 40, new_unlocks: 50},
  retention: {rate: 50, returning_users: 2, new_current_users: 2, previous_active_users: 4},
  catalog: {
    zero_collector_count: 1, median_unlocked: 2, p90_unlocked: 4, catalog_count: 6,
    top5_draw_share: 80, long_tail_count: 2, distribution: [{label: '0-20%', users: 2}],
  },
  activity: [], platforms: [{platform: 'test', users: 4}], rising_pigs: [],
  operations: {roasts: 1, eats: 0, ai: {ready: 1, failed: 0, generating: 0}},
};

function overview() {
  return {
    csrf_token: 'test-token',
    metrics: {total_users: 4, total_draws: 7, today_users: 2, catalog_count: 6, average_unlocked: 2, average_unlock_rate: 33.3},
    trend: [], top_pigs: [],
  };
}

function createDom({assetFailure = false, analyticsFailure = false} = {}) {
  const dom = new JSDOM(BODY, {
    url: 'https://astrbot.test/#/overview',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
  });
  const {window} = dom;
  window.matchMedia = () => ({matches: true, addEventListener() {}, removeEventListener() {}});
  window.scrollTo = () => {};
  window.confirm = () => true;
  window.requestAnimationFrame = callback => window.setTimeout(() => callback(window.performance.now()), 0);
  window.cancelAnimationFrame = id => window.clearTimeout(id);
  window.SVGElement.prototype.getTotalLength = () => 100;
  window.HTMLCanvasElement.prototype.getContext = () => ({clearRect() {}, drawImage() {}});
  window.Image.prototype.decode = async () => {};
  const calls = [];
  window.AstrBotPluginPage = {
    ready: async () => {},
    apiGet: async pathName => {
      calls.push(pathName);
      if (pathName === 'ui/assets') {
        if (assetFailure) throw new Error('401 Unauthorized');
        return {status: 'ok', data: {version: '3.1.0', bundle_sha256: 'test', assets: ASSETS}};
      }
      if (pathName === 'analytics/insights') {
        if (analyticsFailure) throw new Error('analytics unavailable');
        return {status: 'ok', data: insights};
      }
      if (pathName === 'overview') return {status: 'ok', data: overview()};
      if (pathName === 'pigs') return {status: 'ok', data: {items: [], page: 1, pages: 1, total: 0}};
      if (pathName === 'resources/status') return {status: 'ok', data: {running: false, source: 'bundled', version: 'test', last_success: 0, last_attempt: 0, local_overrides: 0, deleted_count: 0, last_error: ''}};
      if (pathName === 'updates/status') return {status: 'ok', data: {current_version: '3.1.0', enabled: true, busy: false, storage: {backend: 'sqlite'}}};
      if (pathName === 'storage/status') return {status: 'ok', data: {configured_mode: 'auto', active_backend: 'sqlite', database_exists: true, latest_backup: '', health: {ok: true, schema_version: 6, analytics_source: 'normalized-sql', write_authority: 'sql-primary-v3.0', compatibility_mode: 'on-demand', documents: 0, users: 4}}};
      throw new Error(`unexpected GET ${pathName}`);
    },
    apiPost: async pathName => ({status: 'ok', data: {path: pathName}}),
  };
  return {dom, window, calls};
}

async function runCore(window) {
  assert.ok(CORE.includes('await bridge.ready()'));
  return window.eval(`(async () => {${CORE}\n})()`);
}

async function runBootstrap(window) {
  window.eval(BOOTSTRAP);
  return window.__rollpigUiBootstrapState.ready;
}

async function waitFor(predicate, timeout = 1500) {
  const started = Date.now();
  while (!predicate()) {
    if (Date.now() - started > timeout) throw new Error('condition timed out');
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}

test('core overview and catalog remain usable when authenticated enhancement loading fails', async () => {
  const {window} = createDom({assetFailure: true});
  const [state] = await Promise.all([runBootstrap(window), runCore(window)]);
  assert.equal(state.status, 'error');
  assert.match(window.document.getElementById('uiEnhancementStatus').textContent, /401 Unauthorized/);
  assert.ok(window.document.getElementById('view-overview').classList.contains('active'));
  window.document.querySelector('[data-route="catalog"]').click();
  assert.ok(window.document.getElementById('view-catalog').classList.contains('active'));
});

test('authenticated bundle restores enterprise UI and deep analytics without relative subrequests', async () => {
  const {window, calls} = createDom();
  const [state] = await Promise.all([runBootstrap(window), runCore(window)]);
  await waitFor(() => window.document.getElementById('analyticsSuite'));
  assert.equal(state.status, 'ready');
  assert.ok(window.document.documentElement.classList.contains('enterprise-ui'));
  assert.equal(window.document.querySelectorAll('style[data-rollpig-ui-asset]').length, 2);
  assert.equal(window.document.getElementById('analyticsSuiteTitle').textContent, '猪圈深度分析');
  assert.ok(calls.includes('ui/assets'));
  assert.ok(calls.includes('analytics/insights'));
  assert.equal(window.document.querySelectorAll('script[src*="ui-"]').length, 0);
  assert.equal(window.document.querySelectorAll('link[href*="theme.css"]').length, 0);
});

test('analytics API failure stays inside the analytics card and does not break the core page', async () => {
  const {window} = createDom({analyticsFailure: true});
  await Promise.all([runBootstrap(window), runCore(window)]);
  await waitFor(() => window.document.querySelector('#analyticsSuite .analytics-error'));
  assert.match(window.document.querySelector('#analyticsSuite .analytics-error').textContent, /深度分析暂时不可用/);
  assert.ok(window.document.getElementById('view-overview').classList.contains('active'));
  window.document.querySelector('[data-route="catalog"]').click();
  assert.ok(window.document.getElementById('view-catalog').classList.contains('active'));
});

test('SPA re-entry receives a new page token and remounts enterprise decorations and analytics', async () => {
  const {window} = createDom();
  await Promise.all([runBootstrap(window), runCore(window)]);
  await waitFor(() => window.document.getElementById('analyticsSuite'));
  const firstToken = window.document.querySelector('.shell').dataset.rollpigPageToken;
  const fresh = new JSDOM(BODY).window.document.body.innerHTML;
  window.document.body.innerHTML = fresh;
  await runBootstrap(window);
  await waitFor(() => window.document.getElementById('analyticsSuite'));
  const secondToken = window.document.querySelector('.shell').dataset.rollpigPageToken;
  assert.notEqual(secondToken, firstToken);
  assert.ok(window.document.getElementById('storageStatus').closest('.update-panel').classList.contains('operation-card'));
  assert.equal(window.document.querySelectorAll('style[data-rollpig-ui-asset]').length, 2);
});
''',
)

# Permanent CI gains an independent browser behavior job.
ci = read(".github/workflows/ci.yml")
if "  frontend:" not in ci:
    ci += '''
  frontend:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Node 22
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm

      - name: Install browser test dependencies
        run: npm ci --ignore-scripts

      - name: Check frontend source syntax
        run: |
          node --check pages/pig-manager/ui-bootstrap.js
          node --check pages/pig-manager/ui-feedback.js
          node --check pages/pig-manager/ui-feedback-core.js
          node --check pages/pig-manager/ui-enterprise.js
          node --check pages/pig-manager/ui-analytics.js

      - name: Run jsdom browser behavior tests
        run: npm test
'''
write(".github/workflows/ci.yml", ci)

# Python contracts for the authenticated delivery architecture.
write(
    "tests/test_ui_cache_busting.py",
    f'''from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "{VERSION}"
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8").strip()
LOADER = (ROOT / "pages/pig-manager/ui-feedback.js").read_text(encoding="utf-8")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids: set[str] = set()
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts += 1
        for key, value in attrs:
            if key == "id" and value:
                self.ids.add(value)


def test_admin_page_is_lightweight_parseable_and_keeps_core_views():
    parser = PageParser()
    parser.feed(PAGE)
    parser.close()
    assert len(PAGE.encode("utf-8")) < 550_000
    assert {{"view-overview", "view-catalog", "refreshBtn", "storageStatus", "updateStatus"}} <= parser.ids
    assert parser.scripts >= 3


def test_page_uses_only_bridge_as_external_script_and_inlines_the_small_bootstrap():
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', PAGE)
    assert scripts == ["/api/plugin/page/bridge-sdk.js"]
    assert "rollpig-inline-assets:start" not in PAGE
    assert 'src="./ui-feedback.js' not in PAGE
    match = re.search(r'<script data-rollpig-bootstrap="{VERSION}">(.*?)</script>', PAGE, re.S)
    assert match and match.group(1).strip() == BOOTSTRAP
    assert len(BOOTSTRAP.encode("utf-8")) < 20_000
    assert "bridge.apiGet('ui/assets'" in BOOTSTRAP


def test_modular_sources_are_versioned_and_delivered_by_authenticated_api():
    assert f"const ASSET_VERSION = '{{VERSION}}'" in LOADER
    assert "ui/assets" in (ROOT / "main.py").read_text(encoding="utf-8")
    for asset in (
        "ui-feedback-core.js", "ui-enterprise.js", "ui-analytics.js",
        "enterprise-theme.css", "analytics-theme.css",
    ):
        assert asset in (ROOT / "main.py").read_text(encoding="utf-8")
''',
)

dashboard = read("tests/test_dashboard_feedback.py")
dashboard = re.sub(
    r"def test_feedback_layer_is_kept_as_a_maintenance_source_only\(\):\n.*?\n\ndef test_feedback_layer_explains_stale_runtime_routes",
    '''def test_feedback_layer_is_delivered_through_the_authenticated_bridge():
    bridge = '<script src="/api/plugin/page/bridge-sdk.js"></script>'
    bootstrap = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")
    assert bridge in PAGE
    assert 'src="./ui-feedback.js' not in PAGE
    assert "bridge.apiGet('ui/assets'" in bootstrap
    assert "/ui/assets" in MAIN
    assert "UI_ASSET_FILES" in MAIN
    assert "./ui-feedback-core.js" in LOADER
    assert "./ui-enterprise.js" in LOADER
    assert "./ui-analytics.js" in LOADER


def test_feedback_layer_explains_stale_runtime_routes''',
    dashboard,
    count=1,
    flags=re.S,
)
write("tests/test_dashboard_feedback.py", dashboard)

source = read("tests/test_source_regressions.py")
source = re.sub(
    r"def test_dashboard_feedback_covers_restart_and_projection_rebuild\(\):\n.*?\n\ndef test_main_delegates_sql_primary_hot_writes",
    '''def test_dashboard_feedback_covers_restart_and_projection_rebuild():
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages" / "pig-manager" / "ui-bootstrap.js").read_text(
        encoding="utf-8"
    )
    feedback = (ROOT / "pages" / "pig-manager" / "ui-feedback-core.js").read_text(
        encoding="utf-8"
    )
    assert "rollpig-inline-assets:start" not in page
    assert 'src="./ui-feedback.js' not in page
    assert "bridge.apiGet('ui/assets'" in bootstrap
    assert "storageRebuildBtn" in feedback
    assert "'storage/rebuild'" in feedback
    assert "restartRequired" in feedback
    assert "已有管理任务正在执行" in feedback


def test_main_delegates_sql_primary_hot_writes''',
    source,
    count=1,
    flags=re.S,
)
write("tests/test_source_regressions.py", source)

# Update current-version assertions across tests, then replace the old release contract.
for path in (ROOT / "tests").glob("*.py"):
    text = path.read_text(encoding="utf-8")
    text = text.replace("3.0.5", VERSION)
    path.write_text(text, encoding="utf-8")
old_contract = ROOT / "tests/test_v305_release_contract.py"
old_contract.unlink(missing_ok=True)
write(
    "tests/test_v310_release_contract.py",
    f'''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v310_release_contract_uses_authenticated_progressive_enhancement():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    page = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")
    assert 'version: "{VERSION}"' in metadata
    assert 'AstrBot-RollPig/{VERSION}' in main
    assert 'AstrBot-RollPig-Safe-Updater/{VERSION}' in updater
    assert '/analytics/insights' in main
    assert '/ui/assets' in main
    assert 'UI_ASSET_FILES' in main
    assert 'page_ui_assets' in main
    assert '<script data-rollpig-bootstrap="{VERSION}">' in page
    assert 'src="./ui-feedback.js' not in page
    assert "bridge.apiGet('ui/assets'" in bootstrap
    assert "core data" not in bootstrap.lower()
''',
)
write(
    "tests/test_ui_asset_delivery.py",
    f'''from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")


def method(name: str):
    tree = ast.parse(MAIN)
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin")
    return next(node for node in plugin.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)


def test_ui_asset_endpoint_is_read_only_and_uses_a_fixed_whitelist():
    builder = ast.get_source_segment(MAIN, method("_build_ui_asset_bundle")) or ""
    endpoint = ast.get_source_segment(MAIN, method("page_ui_assets")) or ""
    assert "self.UI_ASSET_FILES" in builder
    assert ".resolve()" in builder
    assert "path.parent != root" in builder
    assert "UI_ASSET_MAX_FILE_BYTES" in builder
    assert "UI_ASSET_MAX_TOTAL_BYTES" in builder
    assert "asyncio.to_thread(self._build_ui_asset_bundle)" in endpoint
    assert len(method("page_ui_assets").args.args) == 1
    for filename in (
        "enterprise-theme.css", "analytics-theme.css", "ui-feedback-core.js",
        "ui-enterprise.js", "ui-analytics.js",
    ):
        assert filename in MAIN


def test_inline_bootstrap_matches_maintenance_source_and_has_failure_boundaries():
    match = re.search(r'<script data-rollpig-bootstrap="{VERSION}">(.*?)</script>', PAGE, re.S)
    assert match and match.group(1).strip() == BOOTSTRAP.strip()
    for marker in (
        "uiEnhancementStatus", "reportModuleError", "sessionStorage",
        "checksum-mismatch", "核心数据总览、猪猪图鉴和管理操作不受影响",
        "bridge.apiGet('ui/assets'", "pageToken",
    ):
        assert marker in BOOTSTRAP
    assert 'src="./ui-' not in PAGE
    assert 'href="./enterprise-theme.css' not in PAGE
''',
)

# Remove one-shot applicator and workflow from the validated product commit.
for temporary in (
    ROOT / "scripts/apply_authenticated_admin_ui_v310.py",
    ROOT / ".github/workflows/apply-authenticated-admin-ui-v310.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.1.0 authenticated admin UI applied")
