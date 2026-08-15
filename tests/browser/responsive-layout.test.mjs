import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const PAGE = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/index.html'), 'utf8');
const CSS = PAGE.match(/<style>([\s\S]*?)<\/style>/)?.[1] || '';

function mediaBlock(width) {
  const marker = `@media(max-width:${width}px)`;
  const start = CSS.indexOf(marker);
  assert.notEqual(start, -1, `missing ${marker}`);
  const next = CSS.indexOf('@media(', start + marker.length);
  return CSS.slice(start, next === -1 ? CSS.length : next);
}

test('tablet navigation can shrink without forcing the page wider than the viewport', () => {
  const tablet = mediaBlock(900);
  assert.match(tablet, /\.brand\{[^}]*max-width:calc\(100% - 54px\)/);
  assert.match(tablet, /\.brand-title,\.brand-sub\{[^}]*text-overflow:ellipsis/);
  assert.match(tablet, /\.nav\{[^}]*overflow-x:auto/);
  assert.match(tablet, /\.nav-btn\{[^}]*min-width:max-content/);
  assert.match(tablet, /\.legend\{[^}]*flex-wrap:wrap/);
});

test('phone layout stacks high-risk and long-label operation groups', () => {
  const phone = mediaBlock(680);
  assert.match(phone, /\.update-panel\{[^}]*display:flex[^}]*flex-direction:column/);
  assert.match(phone, /\.update-actions\{[^}]*width:100%[^}]*justify-content:stretch/);
  assert.match(phone, /\.layer-note\{[^}]*flex-direction:column/);
  assert.match(phone, /\.dialog-actions\{[^}]*flex-wrap:wrap/);
  assert.match(phone, /\.upload-actions \.btn\{[^}]*flex:1 1 140px/);
});

test('small-phone layout becomes single-column and keeps dialogs inside the viewport', () => {
  const compact = mediaBlock(440);
  assert.match(compact, /\.metrics\{grid-template-columns:1fr\}/);
  assert.match(compact, /\.pig-grid,\.hub-grid\{grid-template-columns:1fr\}/);
  assert.match(compact, /\.update-actions,\.dialog-actions\{display:grid;grid-template-columns:1fr\}/);
  assert.match(compact, /\.dialog\{[^}]*max-height:calc\(100dvh - 20px\)/);
  assert.match(compact, /\.toast\{[^}]*max-width:calc\(100% - 16px\)/);
});

test('responsive fix stays inline and does not add unauthenticated style requests', () => {
  assert.doesNotMatch(PAGE, /<link[^>]+rel=["']stylesheet["']/i);
  assert.doesNotMatch(CSS, /@import\s+/i);
  assert.match(CSS, /@media\(pointer:coarse\)/);
});
