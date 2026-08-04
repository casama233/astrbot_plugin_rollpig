import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright-core';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const PAGE = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/index.html'), 'utf8');
const BOOTSTRAP = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/ui-bootstrap.js'), 'utf8');
const BODY = PAGE
  .replace('<script src="/api/plugin/page/bridge-sdk.js"></script>', '')
  .replace(/<script data-rollpig-bootstrap="3\.1\.1">[\s\S]*?<\/script>/, '')
  .replace(/<script type="module">[\s\S]*?<\/script>/, '');
const BODY_INNER = BODY.match(/<body>([\s\S]*?)<\/body>/)?.[1] || BODY;
const ASSETS = [
  ['analytics-theme', 'style', 'analytics-theme.css'],
  ['ui-analytics', 'script', 'ui-analytics.js'],
].map(([name, kind, filename]) => ({
  name, kind, source: fs.readFileSync(path.join(ROOT, 'pages/pig-manager', filename), 'utf8'), sha256: '',
}));
const INSIGHTS = {
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

const executablePath = process.env.CHROME_PATH;
assert.ok(executablePath, 'CHROME_PATH is required');
const browser = await chromium.launch({
  executablePath,
  headless: true,
  args: ['--enable-precise-memory-info', '--js-flags=--expose-gc', '--no-sandbox'],
});
const page = await browser.newPage();
const cdp = await page.context().newCDPSession(page);

try {
  await page.setContent(BODY, {waitUntil: 'domcontentloaded'});
  await page.evaluate(({assets, insights}) => {
    window.__rollpigCalls = [];
    const NativeObserver = window.MutationObserver;
    window.__rollpigObserverCount = 0;
    window.MutationObserver = class extends NativeObserver {
      constructor(callback) {
        window.__rollpigObserverCount += 1;
        super(callback);
      }
    };
    const nativeInterval = window.setInterval.bind(window);
    window.__rollpigIntervalCount = 0;
    window.setInterval = (...args) => {
      window.__rollpigIntervalCount += 1;
      return nativeInterval(...args);
    };
    window.AstrBotPluginPage = {
      ready: async () => {},
      apiGet: async pathName => {
        window.__rollpigCalls.push(pathName);
        if (pathName === 'ui/assets') return {status: 'ok', data: {version: '3.1.1', assets}};
        if (pathName === 'analytics/insights') return {status: 'ok', data: insights};
        throw new Error(`unexpected path ${pathName}`);
      },
    };
  }, {assets: ASSETS, insights: INSIGHTS});

  await page.addScriptTag({content: BOOTSTRAP});
  const defaultState = await page.evaluate(() => ({
    calls: [...window.__rollpigCalls],
    suites: document.querySelectorAll('#analyticsSuite').length,
    styles: document.querySelectorAll('style[data-rollpig-ui-asset]').length,
    buttons: document.querySelectorAll('#analyticsLoadBtn').length,
  }));
  assert.deepEqual(defaultState.calls, []);
  assert.equal(defaultState.suites, 0);
  assert.equal(defaultState.styles, 0);
  assert.equal(defaultState.buttons, 1);

  await page.click('#analyticsLoadBtn');
  await page.waitForSelector('#analyticsSuite', {state: 'attached'});
  await cdp.send('HeapProfiler.collectGarbage');
  const before = await cdp.send('Runtime.getHeapUsage');

  const cycles = 20;
  for (let index = 0; index < cycles; index += 1) {
    await page.evaluate(body => { document.body.innerHTML = body; }, BODY_INNER);
    await page.addScriptTag({content: BOOTSTRAP});
    await page.click('#analyticsLoadBtn');
    await page.waitForSelector('#analyticsSuite', {state: 'attached'});
  }

  await cdp.send('HeapProfiler.collectGarbage');
  const after = await cdp.send('Runtime.getHeapUsage');
  const metrics = await page.evaluate(() => ({
    observer_instances: window.__rollpigObserverCount,
    interval_instances: window.__rollpigIntervalCount,
    asset_requests: window.__rollpigCalls.filter(item => item === 'ui/assets').length,
    analytics_requests: window.__rollpigCalls.filter(item => item === 'analytics/insights').length,
    analytics_suites: document.querySelectorAll('#analyticsSuite').length,
    analytics_buttons: document.querySelectorAll('#analyticsLoadBtn').length,
    style_assets: document.querySelectorAll('style[data-rollpig-ui-asset="analytics-theme"]').length,
    script_assets: document.querySelectorAll('script[data-rollpig-ui-asset="ui-analytics"]').length,
    dom_nodes: document.querySelectorAll('*').length,
  }));
  metrics.spa_cycles = cycles;
  metrics.heap_before_bytes = before.usedSize;
  metrics.heap_after_bytes = after.usedSize;
  metrics.heap_growth_bytes = after.usedSize - before.usedSize;

  assert.equal(metrics.observer_instances, 0);
  assert.equal(metrics.interval_instances, 0);
  assert.equal(metrics.analytics_suites, 1);
  assert.equal(metrics.analytics_buttons, 1);
  assert.equal(metrics.style_assets, 1);
  assert.equal(metrics.script_assets, 1);
  assert.equal(metrics.asset_requests, cycles + 1);
  assert.equal(metrics.analytics_requests, cycles + 1);
  assert.ok(metrics.heap_growth_bytes < 24 * 1024 * 1024, `heap grew by ${metrics.heap_growth_bytes} bytes`);

  fs.mkdirSync(path.join(ROOT, 'docs'), {recursive: true});
  fs.writeFileSync(path.join(ROOT, 'docs/performance-v3.1.1.json'), JSON.stringify(metrics, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify(metrics, null, 2));
} finally {
  await browser.close();
}
