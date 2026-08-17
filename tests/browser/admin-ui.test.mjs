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
const BOOTSTRAP_VERSION = BOOTSTRAP.match(/const VERSION = '([^']+)'/)?.[1] || '';
const BODY = PAGE
  .replace('<script src="/api/plugin/page/bridge-sdk.js"></script>', '')
  .replace(/<script data-rollpig-bootstrap="[^"]+">[\s\S]*?<\/script>/, '')
  .replace(/<script type="module">[\s\S]*?<\/script>/, '');
const ASSETS = [
  ['analytics-theme', 'style', 'analytics-theme.css'],
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

function createDom({analyticsFailure = false} = {}) {
  const dom = new JSDOM(BODY, {
    url: 'https://astrbot.test/#/overview', runScripts: 'dangerously', pretendToBeVisual: true,
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
      if (pathName === 'ui/assets') return {status: 'ok', data: {version: BOOTSTRAP_VERSION, assets: ASSETS}};
      if (pathName === 'analytics/insights') {
        if (analyticsFailure) throw new Error('analytics unavailable');
        return {status: 'ok', data: insights};
      }
      if (pathName === 'overview') return {status: 'ok', data: {csrf_token: 'test', metrics: {total_users: 62, total_draws: 325, today_users: 16, catalog_count: 218, average_unlocked: 5.1, average_unlock_rate: 2.3}, trend: [{date: '08-14', users: 15, draws: 15, new_unlocks: 1}, {date: '08-15', users: 16, draws: 16, new_unlocks: 2}, {date: '08-16', users: 15, draws: 15, new_unlocks: 1}, {date: '08-17', users: 16, draws: 16, new_unlocks: 2}], top_pigs: []}};
      if (pathName === 'pigs') return {status: 'ok', data: {items: [], page: 1, pages: 1, total: 0}};
      if (pathName === 'resources/status') return {status: 'ok', data: {running: false, source: 'bundled', version: 'test', last_success: 0, last_attempt: 0, local_overrides: 0, deleted_count: 0, last_error: ''}};
      if (pathName === 'updates/status') return {status: 'ok', data: {current_version: '3.1.2', enabled: true, busy: false, storage: {backend: 'sqlite'}}};
      if (pathName === 'storage/status') return {status: 'ok', data: {configured_mode: 'auto', active_backend: 'sqlite', database_exists: true, health: {ok: true, schema_version: 6, analytics_source: 'normalized-sql', write_authority: 'sql-primary-v3.0', compatibility_mode: 'on-demand'}}};
      throw new Error(`unexpected GET ${pathName}`);
    },
    apiPost: async pathName => ({status: 'ok', data: {path: pathName}}),
  };
  return {dom, window, calls};
}

const runCore = window => window.eval(`(async () => {${CORE}\n})()`);
const runBootstrap = window => window.eval(BOOTSTRAP);
async function waitFor(predicate, timeout = 1500) {
  const started = Date.now();
  while (!predicate()) {
    if (Date.now() - started > timeout) throw new Error('condition timed out');
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}

test('default page runs only core and makes no enhancement request', async t => {
  const {dom, window, calls} = createDom();
  t.after(() => dom.window.close());
  runBootstrap(window);
  await runCore(window);
  assert.ok(window.document.getElementById('analyticsLoadBtn'));
  assert.equal(calls.filter(item => item === 'ui/assets').length, 0);
  assert.equal(calls.filter(item => item === 'analytics/insights').length, 0);
  assert.equal(window.document.getElementById('analyticsSuite'), null);
  assert.equal(window.document.querySelectorAll('style[data-rollpig-ui-asset]').length, 0);
  assert.equal(window.sessionStorage.length, 0);
});

test('overview KPI strip renders five useful cards and a smooth truthful activity sparkline', async t => {
  const {dom, window} = createDom();
  t.after(() => dom.window.close());
  runBootstrap(window);
  await runCore(window);
  const labels = [...window.document.querySelectorAll('#view-overview .metric .label')].map(node => node.textContent.trim());
  assert.deepEqual(labels, ['总使用人数', '累计抽取', '今日活跃', '人均解锁', '平均收藏率']);
  assert.equal(window.document.getElementById('mPigs'), null);
  assert.equal(window.document.querySelectorAll('#view-overview .metric').length, 5);
  assert.match(window.document.getElementById('cUsers').textContent, /占累计/);
  assert.match(window.document.getElementById('cDraws').textContent, /近 14 日/);
  assert.match(window.document.getElementById('cToday').textContent, /较昨日/);
  assert.match(window.document.getElementById('cAverage').textContent, /尚未探索/);
  const spark = window.document.querySelector('#vToday .spark-path');
  assert.ok(spark);
  assert.match(spark.getAttribute('d'), / C /);
  assert.equal(spark.getAttribute('d').includes(' L '), false);
  assert.ok(window.document.querySelector('#vToday .spark-endpoint'));
  assert.equal(window.document.querySelectorAll('.metric-snapshot-viz').length, 0);
  assert.equal(window.document.querySelectorAll('.metric-scope').length, 0);
  const pathNumbers = (spark.getAttribute('d').match(/-?\d+(?:\.\d+)?/g) || []).map(Number);
  const yValues = pathNumbers.filter((_, index) => index % 2 === 1);
  assert.ok(Math.max(...yValues) - Math.min(...yValues) < 18, 'a 15→16 fluctuation must not fill the sparkline height');
});

test('Analytics loads once on click and later clicks only refresh data', async t => {
  const {dom, window, calls} = createDom();
  t.after(() => dom.window.close());
  runBootstrap(window);
  window.document.getElementById('analyticsLoadBtn').click();
  await waitFor(() => window.document.getElementById('analyticsSuiteTitle'));
  assert.equal(calls.filter(item => item === 'ui/assets').length, 1);
  assert.equal(calls.filter(item => item === 'analytics/insights').length, 1);
  window.document.getElementById('analyticsLoadBtn').click();
  await waitFor(() => calls.filter(item => item === 'analytics/insights').length === 2);
  assert.equal(calls.filter(item => item === 'ui/assets').length, 1);
  assert.equal(window.document.querySelectorAll('#analyticsSuite').length, 1);
  assert.equal(window.document.querySelectorAll('style[data-rollpig-ui-asset="analytics-theme"]').length, 1);
});

test('Analytics failure stays local and core navigation remains usable', async t => {
  const {dom, window} = createDom({analyticsFailure: true});
  t.after(() => dom.window.close());
  runBootstrap(window);
  await runCore(window);
  window.document.getElementById('analyticsLoadBtn').click();
  await waitFor(() => window.document.querySelector('#analyticsSuite .analytics-error'));
  window.document.querySelector('[data-route="catalog"]').click();
  assert.ok(window.document.getElementById('view-catalog').classList.contains('active'));
});

test('SPA re-entry binds to the new root without duplicate mounts', async t => {
  const {dom, window, calls} = createDom();
  t.after(() => dom.window.close());
  runBootstrap(window);
  const firstRoot = window.document.querySelector('.shell');
  window.document.getElementById('analyticsLoadBtn').click();
  await waitFor(() => window.document.getElementById('analyticsSuite'));
  const fresh = new JSDOM(BODY).window.document.body.innerHTML;
  window.document.body.innerHTML = fresh;
  runBootstrap(window);
  assert.notEqual(window.document.querySelector('.shell'), firstRoot);
  window.document.getElementById('analyticsLoadBtn').click();
  await waitFor(() => window.document.getElementById('analyticsSuite'));
  assert.equal(window.document.querySelectorAll('#analyticsSuite').length, 1);
  assert.equal(window.document.querySelectorAll('#analyticsLoadBtn').length, 1);
  assert.equal(calls.filter(item => item === 'ui/assets').length, 2);
});

test('40 default SPA entries create no observers, intervals, requests or DOM accumulation', async t => {
  const {dom, window, calls} = createDom();
  t.after(() => dom.window.close());
  const NativeObserver = window.MutationObserver;
  let observers = 0;
  window.MutationObserver = class extends NativeObserver {
    constructor(callback) { observers += 1; super(callback); }
  };
  const nativeInterval = window.setInterval.bind(window);
  let intervals = 0;
  window.setInterval = (...args) => { intervals += 1; return nativeInterval(...args); };
  const fresh = new JSDOM(BODY).window.document.body.innerHTML;
  const started = window.performance.now();
  for (let index = 0; index < 40; index += 1) {
    window.document.body.innerHTML = fresh;
    runBootstrap(window);
  }
  const elapsed = window.performance.now() - started;
  assert.equal(calls.length, 0);
  assert.equal(observers, 0);
  assert.equal(intervals, 0);
  assert.equal(window.document.querySelectorAll('#analyticsLoadBtn').length, 1);
  assert.equal(window.document.querySelectorAll('#analyticsSuite').length, 0);
  assert.ok(elapsed < 1500, `default SPA bootstrap took ${elapsed.toFixed(1)} ms`);
});
