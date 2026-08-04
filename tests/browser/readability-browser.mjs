import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright-core';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const CSS = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/analytics-theme.css'), 'utf8');
const executablePath = process.env.CHROME_PATH;
assert.ok(executablePath, 'CHROME_PATH is required');

const browser = await chromium.launch({executablePath, headless: true, args: ['--no-sandbox']});
const page = await browser.newPage({viewport: {width: 1366, height: 900}});
const cells = Array.from({length: 28}, (_, index) => `<div class="activity-cell"><i style="--intensity:.6"></i><span>08-${String(index + 1).padStart(2, '0')}</span></div>`).join('');
const html = `<!doctype html><meta charset="utf-8"><style>:root{--line:#493941;--surface:#261e23;--surface-strong:#2c2228;--bg:#191317;--pink:#e873a4;--pink-2:#ef9aba;--pink-soft:#321d27;--violet:#8b83f5;--muted:#b9abb3;--ink:#fff;--green:#67d9a6;--danger:#f77;--orange:#fa5;--ease:ease;--shadow-soft:none;--radius-md:12px}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Arial,sans-serif}${CSS}</style><section class="analytics-suite"><header class="analytics-suite__head"><div><h2>猪圈深度分析</h2><p>用于观察活跃趋势、收藏覆盖与运行健康。</p></div><div class="analytics-suite__meta"><span>最近 28 日</span></div></header><div class="analytics-grid"><article class="analytics-card analytics-card--wide"><header class="analytics-card__head"><div><span>28 Day Activity</span><h3>活跃热力与玩法脉冲</h3></div><small>8.6 日均活跃</small></header><div class="activity-legend">低<i></i><i></i><i></i><i></i>高</div><div class="activity-heatmap">${cells}</div><div class="activity-summary"><span><b>60</b>抽取</span><span><b>60</b>新解锁</span><span><b>15</b>烧烤</span><span><b>3</b>被吃事件</span></div></article><article class="analytics-card"><header class="analytics-card__head"><div><span>Audience Mix</span><h3>平台用户构成</h3></div><small>32 个身份</small></header><div class="platform-list"><div class="platform-row"><div><span>aiocqhttp@default</span><b>18</b></div><i><em style="width:80%"></em></i></div></div></article><article class="analytics-card analytics-card--wide"><header class="analytics-card__head"><div><span>Momentum</span><h3>上升最快的猪猪</h3></div><small>当前 7 日与上一周期绝对差值</small></header><div class="rising-table"><div class="rising-table__head"><span>猪猪</span><span>本期</span><span>上期</span><span>变化</span></div><div class="rising-table__row"><span><i>1</i><b>三叉泰克司</b><small>sailor-sushi-pig</small></span><span>3</span><span>0</span><span>+3</span></div></div></article><article class="analytics-card"><header class="analytics-card__head"><div><span>Runtime Signals</span><h3>玩法运行健康</h3></div><small>最近 7 日</small></header><div class="operations-grid"><div><span>烧烤次数</span><strong>15</strong></div><div><span>被吃事件</span><strong>3</strong></div></div></article></div></section>`;
await page.setContent(html);

async function metrics() {
  return page.evaluate(() => {
    const size = selector => parseFloat(getComputedStyle(document.querySelector(selector)).fontSize);
    const height = selector => parseFloat(getComputedStyle(document.querySelector(selector)).minHeight);
    return {
      viewport: innerWidth,
      suite: size('.analytics-suite'),
      title: size('.analytics-card__head h3'),
      helper: size('.analytics-card__head small'),
      date: size('.activity-cell span'),
      platform: size('.platform-row > div'),
      row: size('.rising-table__row'),
      rowHeight: height('.rising-table__row'),
      alias: size('.rising-table__row small'),
      operationLabel: size('.operations-grid span'),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    };
  });
}

const desktop = await metrics();
assert.ok(desktop.suite >= 14, desktop);
assert.ok(desktop.title >= 16, desktop);
assert.ok(desktop.helper >= 12, desktop);
assert.ok(desktop.date >= 10.5, desktop);
assert.ok(desktop.platform >= 12, desktop);
assert.ok(desktop.row >= 13, desktop);
assert.ok(desktop.rowHeight >= 48, desktop);
assert.ok(desktop.alias >= 11, desktop);
assert.ok(desktop.operationLabel >= 12, desktop);
assert.ok(desktop.scrollWidth <= desktop.clientWidth, desktop);

await page.setViewportSize({width: 430, height: 1000});
const mobile = await metrics();
assert.ok(mobile.date >= 10, mobile);
assert.ok(mobile.scrollWidth <= mobile.clientWidth, mobile);

const report = {desktop, mobile};
fs.mkdirSync(path.join(ROOT, 'docs'), {recursive: true});
fs.writeFileSync(path.join(ROOT, 'docs/readability-v3.1.2.json'), `${JSON.stringify(report, null, 2)}
`);
console.log(JSON.stringify(report, null, 2));
await browser.close();
