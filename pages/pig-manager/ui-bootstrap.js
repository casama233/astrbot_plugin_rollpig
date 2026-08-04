(() => {
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
})();
