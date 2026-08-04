const fs = require('fs');
const vm = require('vm');
const path = require('path');
const source = fs.readFileSync(
  path.join(__dirname, '..', 'pages', 'pig-manager', 'ui-analytics.js'),
  'utf8'
);

function context() {
  let now = 0;
  const timers = [];
  const listeners = {};
  const elements = new Map();
  const anchor = {insertAdjacentElement(_where, node) { elements.set(node.id, node); }};
  const document = {
    readyState: 'loading',
    querySelector(selector) { return selector === '#view-overview .metrics' ? anchor : null; },
    getElementById(id) { return elements.get(id) || null; },
    createElement() { return {id: '', className: '', innerHTML: '', addEventListener() {}}; },
    addEventListener(name, fn) { listeners[name] = fn; }
  };
  const window = {
    setTimeout(fn) { timers.push(fn); return timers.length; },
    addEventListener() {}
  };
  const sandbox = {
    window,
    document,
    performance: {now: () => now},
    console,
    Intl,
    Promise,
    Array,
    Number,
    String,
    Math,
    Object,
    Error
  };
  vm.createContext(sandbox);
  return {
    sandbox,
    window,
    timers,
    listeners,
    advance(ms) {
      now += ms;
      const fn = timers.shift();
      if (fn) fn();
    }
  };
}

const delayed = context();
vm.runInContext(source, delayed.sandbox);
if (delayed.window.__rollpigAnalyticsUiReady) throw new Error('ready set before bridge');
if (delayed.timers.length !== 1) throw new Error('expected one wait timer');
vm.runInContext(source, delayed.sandbox);
if (delayed.timers.length !== 1) throw new Error('duplicate injection scheduled another timer');
delayed.window.AstrBotPluginPage = {apiGet: async () => ({data: {}})};
delayed.advance(100);
if (!delayed.window.__rollpigAnalyticsUiReady) throw new Error('bridge arrival did not initialize');

const missing = context();
vm.runInContext(source, missing.sandbox);
for (let i = 0; i < 80; i += 1) missing.advance(100);
if (missing.window.__rollpigAnalyticsUiReady) throw new Error('timeout marked analytics ready');
if (!missing.window.__rollpigAnalyticsUiState.timedOut) throw new Error('timeout state not recorded');
if (missing.timers.length !== 0) throw new Error('polling continued after timeout');
