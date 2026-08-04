import test from 'node:test';
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

test('core overview and catalog remain usable when authenticated enhancement loading fails', async t => {
  const {dom, window} = createDom({assetFailure: true});
  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });
  const [state] = await Promise.all([runBootstrap(window), runCore(window)]);
  assert.equal(state.status, 'error');
  assert.match(window.document.getElementById('uiEnhancementStatus').textContent, /401 Unauthorized/);
  assert.ok(window.document.getElementById('view-overview').classList.contains('active'));
  window.document.querySelector('[data-route="catalog"]').click();
  assert.ok(window.document.getElementById('view-catalog').classList.contains('active'));
});

test('authenticated bundle restores enterprise UI and deep analytics without relative subrequests', async t => {
  const {dom, window, calls} = createDom();
  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });
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

test('analytics API failure stays inside the analytics card and does not break the core page', async t => {
  const {dom, window} = createDom({analyticsFailure: true});
  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });
  await Promise.all([runBootstrap(window), runCore(window)]);
  await waitFor(() => window.document.querySelector('#analyticsSuite .analytics-error'));
  assert.match(window.document.querySelector('#analyticsSuite .analytics-error').textContent, /深度分析暂时不可用/);
  assert.ok(window.document.getElementById('view-overview').classList.contains('active'));
  window.document.querySelector('[data-route="catalog"]').click();
  assert.ok(window.document.getElementById('view-catalog').classList.contains('active'));
});

test('SPA re-entry receives a new page token and remounts enterprise decorations and analytics', async t => {
  const {dom, window} = createDom();
  t.after(() => { window.dispatchEvent(new window.Event('pagehide')); dom.window.close(); });
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
