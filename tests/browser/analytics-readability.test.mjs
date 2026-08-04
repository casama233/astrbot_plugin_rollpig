import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {JSDOM} from 'jsdom';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const CSS = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/analytics-theme.css'), 'utf8');

const html = `<!doctype html><style>:root{--line:#444;--surface:#222;--surface-strong:#282228;--bg:#181318;--pink:#e973a4;--pink-2:#ef9aba;--pink-soft:#321d27;--violet:#8b83f5;--muted:#b8abb3;--ink:#fff;--green:#67d9a6;--danger:#f77;--orange:#fa5;--ease:ease;--shadow-soft:none}${CSS}</style><section class="analytics-suite"><header class="analytics-card__head"><div><span>Audience</span><h3>平台用户构成</h3></div><small>最近 7 日</small></header><div class="activity-cell"><i></i><span>08-05</span></div><div class="platform-row"><div><span>aiocqhttp@default</span><b>18</b></div><i><em></em></i></div><div class="rising-table__row"><span><i>1</i><b>测试猪猪</b><small>sample-pig</small></span><span>3</span><span>0</span><span>+3</span></div><div class="operations-grid"><div><span>烧烤次数</span><strong>15</strong></div></div></section>`;

test('representative analytics text uses readable computed sizes', () => {
  const dom = new JSDOM(html, {pretendToBeVisual: true});
  const {window} = dom;
  const size = selector => parseFloat(window.getComputedStyle(window.document.querySelector(selector)).fontSize);
  const minHeight = selector => parseFloat(window.getComputedStyle(window.document.querySelector(selector)).minHeight);
  assert.ok(size('.analytics-suite') >= 14);
  assert.ok(size('.analytics-card__head h3') >= 16);
  assert.ok(size('.analytics-card__head small') >= 12);
  assert.ok(size('.platform-row > div') >= 12);
  assert.ok(size('.rising-table__row') >= 13);
  assert.ok(minHeight('.rising-table__row') >= 48);
  assert.ok(size('.operations-grid span') >= 12);
  dom.window.close();
});
