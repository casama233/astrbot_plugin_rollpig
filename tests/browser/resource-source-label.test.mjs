import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { JSDOM } from 'jsdom';

const page = fs.readFileSync(new URL('../../pages/pig-manager/index.html', import.meta.url), 'utf8');
const start = page.indexOf('function renderResourceStatus(d){');
const end = page.indexOf('\nasync function loadResourceStatus', start);
assert.ok(start >= 0 && end > start, 'exercise the actual production renderer');
const source = page.slice(start, end);

function render(status) {
  const dom = new JSDOM('<div id="syncStatus"></div><button id="syncBtn"></button>');
  const document = dom.window.document;
  const context = {
    resourceSnapshot: null,
    $: id => document.getElementById(id),
    esc: value => {
      const element = document.createElement('span');
      element.textContent = String(value);
      return element.innerHTML;
    },
    formatTime: value => String(value),
    setSyncFeedback: () => {},
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  context.renderResourceStatus({ enabled: true, manifest_url: 'https://example.invalid/v1/manifest.json', ...status });
  return { dom, label: document.querySelector('#syncStatus .pill'), button: document.getElementById('syncBtn') };
}

for (const remote of ['primary', 'vercel', 'github', 'custom']) {
  for (const overlay of [false, true]) {
    test(`cloud ${remote}, Felis overlay=${overlay}`, () => {
      const { dom, label } = render({ source: overlay ? 'cloud+felis-direct' : 'cloud', active_remote_source: remote });
      const names = { primary: 'AstrBot 主源', vercel: 'Vercel 镜像', github: 'GitHub 镜像', custom: '私人源' };
      assert.ok(label.textContent.includes(names[remote] + '缓存'));
      assert.equal(label.textContent.includes('Felis 官方直读'), overlay);
      assert.equal(label.textContent.includes('内置兜底'), false);
      assert.ok(label.classList.contains('ok'));
      dom.window.close();
    });
  }
}
for (const overlay of [false, true]) {
  test(`bundled, Felis overlay=${overlay}`, () => {
    const { dom, label } = render({ source: overlay ? 'bundled+felis-direct' : 'bundled', active_remote_source: 'vercel' });
    assert.ok(label.textContent.includes('内置兜底'));
    assert.equal(label.textContent.includes('Felis 官方直读'), overlay);
    assert.equal(label.textContent.includes('Vercel'), false);
    assert.equal(label.classList.contains('ok'), false);
    dom.window.close();
  });
}
for (const state of [undefined, '', 'future-source', 'future-source+felis-direct']) {
  test(`unknown source is not labelled bundled: ${state}`, () => {
    const { dom, label } = render({ source: state });
    assert.ok(label.textContent.includes('来源状态未识别'));
    assert.equal(label.textContent.includes('内置兜底'), false);
    dom.window.close();
  });
}
test('cloud without remote provenance remains cloud and shows the uncertainty', () => {
  const { dom, label } = render({ source: 'cloud+felis-direct' });
  assert.ok(label.textContent.includes('云端缓存（来源未记录）'));
  assert.ok(label.textContent.includes('Felis 官方直读'));
  dom.window.close();
});
test('source text stays escaped and running state still disables sync', () => {
  const { dom, label, button } = render({ source: 'cloud+felis-direct', active_remote_source: '<img src=x onerror=alert(1)>', running: true });
  assert.equal(label.querySelector('img'), null);
  assert.ok(label.textContent.includes('<img'));
  assert.equal(button.disabled, true);
  dom.window.close();
});
