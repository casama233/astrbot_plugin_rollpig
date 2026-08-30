import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {JSDOM} from 'jsdom';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const INTEGRATION = fs.readFileSync(
  path.join(ROOT, 'pages/pig-manager/dashboard-trend-integration.js'),
  'utf8',
);

const FIXTURE = `<!doctype html>
<html lang="zh-CN">
<body>
  <section class="panel" id="trendPanel">
    <header class="panel-head"><div class="panel-desc">原始趋势说明</div></header>
    <div class="legend">
      <span><i class="dot"></i>新解锁</span>
      <span><i class="dot"></i>使用人数</span>
      <span><i class="dot"></i>抽取次数</span>
    </div>
    <div id="trendChart">
      <svg aria-label="原始抽取趋势">
        <line class="gridline" x1="0" y1="10" x2="100" y2="10"></line>
        <line class="gridline" x1="0" y1="110" x2="100" y2="110"></line>
        <text class="chart-label" x="5">10</text>
        <rect class="chart-draw-bar" height="50" y="60"></rect>
        <rect class="chart-draw-bar" height="50" y="60"></rect>
        <rect class="chart-draw-bar" height="50" y="60"></rect>
      </svg>
      <div id="trendTip">
        <div class="tooltip-date">08-14</div>
        <div class="tooltip-row"><span>新解锁</span><b>2</b></div>
        <div class="tooltip-row"><span>使用人数</span><b>5</b></div>
        <div class="tooltip-row"><span>抽取次数</span><b>5</b></div>
      </div>
    </div>
    <div id="trendSummary">
      <div class="trend-summary-item"><span>活跃峰值</span><strong>6 人</strong></div>
      <div class="trend-summary-item"><span>14 日新解锁</span><strong>12 次</strong></div>
      <div class="trend-summary-item"><span>日均活跃</span><strong>5 人</strong></div>
      <div class="trend-summary-item"><span>14 日抽取</span><strong>12 次</strong></div>
    </div>
  </section>
</body>
</html>`;

const overview = {
  status: 'ok',
  data: {
    trend: [
      {date: '08-14', users: 5, draws: 5, new_unlocks: 2},
      {date: '08-15', users: 4, draws: 1, new_unlocks: 4},
      {date: '08-16', users: 6, draws: 6, new_unlocks: 6},
    ],
  },
};

function createDom(response) {
  const dom = new JSDOM(FIXTURE, {
    url: 'https://astrbot.test/#/overview',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
  });
  const {window} = dom;
  const calls = [];
  const warnings = [];
  window.console.warn = (...args) => warnings.push(args);
  window.AstrBotPluginPage = {
    ready: async () => {},
    apiGet: async pathName => {
      calls.push(pathName);
      return response;
    },
  };
  window.eval(INTEGRATION);
  return {dom, window, calls, warnings};
}

async function waitFor(predicate, timeout = 1000) {
  const started = Date.now();
  while (!predicate()) {
    if (Date.now() - started > timeout) throw new Error('condition timed out');
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}

test('repeat-draw integration patches reordered metric DOM by identity', async t => {
  const {dom, window, calls, warnings} = createDom({data: overview});
  t.after(() => dom.window.close());

  const panel = window.document.getElementById('trendPanel');
  await waitFor(() => panel.dataset.rollpigRepeatDrawState === 'ready');

  assert.deepEqual(calls, ['overview']);
  assert.deepEqual(warnings, []);
  assert.equal(
    window.document.querySelector('.panel-desc').textContent,
    '移动到折线可查看每日使用人数、重复抽中与新解锁',
  );

  const repeatLegend = window.document.querySelector(
    '.legend span[data-rollpig-metric="repeat-draws"]',
  );
  assert.ok(repeatLegend);
  assert.equal(repeatLegend.textContent.trim(), '重复抽中');
  assert.deepEqual(
    [...window.document.querySelectorAll('.legend span')].map(node => node.textContent.trim()),
    ['新解锁', '使用人数', '重复抽中'],
  );

  const svg = window.document.querySelector('#trendChart svg');
  assert.equal(svg.getAttribute('aria-label'), '近十四日使用人数、重复抽中与新解锁趋势');
  const bars = [...svg.querySelectorAll('.chart-draw-bar')];
  assert.deepEqual(bars.map(bar => bar.getAttribute('height')), ['30.000', '0.000', '0.000']);
  assert.deepEqual(bars.map(bar => bar.getAttribute('y')), ['80.000', '110.000', '110.000']);
  assert.deepEqual(
    bars.map(bar => bar.getAttribute('aria-label')),
    ['重复抽中 3 次', '重复抽中 0 次', '重复抽中 0 次'],
  );
  assert.ok(bars.every(bar => bar.getAttribute('data-rollpig-metric') === 'repeat-draws'));

  const repeatSummary = window.document.querySelector(
    '#trendSummary .trend-summary-item[data-rollpig-metric="repeat-draws"]',
  );
  assert.ok(repeatSummary);
  assert.equal(repeatSummary.querySelector('span').textContent, '14 日重复抽中');
  assert.equal(repeatSummary.querySelector('strong').textContent, '3 次');

  const repeatTooltip = window.document.querySelector(
    '#trendTip .tooltip-row[data-rollpig-metric="repeat-draws"]',
  );
  assert.ok(repeatTooltip);
  assert.equal(repeatTooltip.querySelector('span').textContent, '重复抽中');
  assert.equal(repeatTooltip.querySelector('b').textContent, '3');
});

test('application-level overview errors are reported without relabelling stale draws', async t => {
  const {dom, window, calls, warnings} = createDom({
    data: {status: 'error', message: 'overview unavailable'},
  });
  t.after(() => dom.window.close());

  const panel = window.document.getElementById('trendPanel');
  await waitFor(() => panel.dataset.rollpigRepeatDrawState === 'error');

  assert.deepEqual(calls, ['overview']);
  assert.equal(panel.dataset.rollpigRepeatDrawError, 'overview unavailable');
  assert.equal(window.document.querySelector('.panel-desc').textContent, '原始趋势说明');
  assert.equal(
    window.document.querySelector('.legend span:last-child').textContent.trim(),
    '抽取次数',
  );
  assert.equal(window.document.querySelector('[data-rollpig-metric="repeat-draws"]'), null);
  assert.equal(window.document.querySelector('#trendChart svg').getAttribute('aria-label'), '原始抽取趋势');
  assert.equal(window.document.querySelector('.chart-draw-bar').getAttribute('height'), '50');
  assert.equal(warnings.length, 1);
  assert.match(String(warnings[0][0]), /重复抽中趋势增强失败/);
  assert.match(String(warnings[0][1]?.message || warnings[0][1]), /overview unavailable/);
});
