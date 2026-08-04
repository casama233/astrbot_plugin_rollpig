(() => {
  'use strict';

  const VERSION = '3.1.1';
  const STATE_KEY = '__rollpigUiBootstrapState';
  const ALLOWED = new Map([
    ['analytics-theme', 'style'],
    ['ui-analytics', 'script'],
  ]);
  const pageRoot = document.querySelector('.shell');
  if (!pageRoot) return;

  if (pageRoot.dataset.rollpigBootstrap === VERSION) return;
  pageRoot.dataset.rollpigBootstrap = VERSION;

  const previous = window[STATE_KEY];
  previous?.abortController?.abort();

  const abortController = new AbortController();
  const state = {
    version: VERSION,
    root: pageRoot,
    status: 'idle',
    loadPromise: null,
    assets: {},
    errors: [],
    abortController,
    reportModuleError: null,
  };
  window[STATE_KEY] = state;

  const unwrap = response => {
    if (response?.status === 'error') throw new Error(response.message || '后端拒绝读取深度分析资源');
    const first = response?.data ?? response;
    if (first?.status === 'error') throw new Error(first.message || '深度分析资源返回错误');
    return first?.data ?? first;
  };

  const validateBundle = bundle => {
    if (!bundle || bundle.version !== VERSION || !Array.isArray(bundle.assets)) {
      throw Object.assign(new Error(`深度分析资源版本不匹配：期望 ${VERSION}`), {code: 'version-mismatch'});
    }
    const seen = new Set();
    let total = 0;
    for (const asset of bundle.assets) {
      if (!asset || ALLOWED.get(asset.name) !== asset.kind || typeof asset.source !== 'string') {
        throw Object.assign(new Error(`深度分析资源清单包含未知项目：${asset?.name || 'unknown'}`), {code: 'invalid-manifest'});
      }
      if (seen.has(asset.name)) {
        throw Object.assign(new Error(`深度分析资源重复：${asset.name}`), {code: 'duplicate-asset'});
      }
      seen.add(asset.name);
      total += asset.source.length;
    }
    for (const name of ALLOWED.keys()) {
      if (!seen.has(name)) {
        throw Object.assign(new Error(`深度分析资源缺失：${name}`), {code: 'missing-asset'});
      }
    }
    if (total > 768_000) {
      throw Object.assign(new Error('深度分析资源总量超出安全限制'), {code: 'bundle-too-large'});
    }
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
      throw Object.assign(new Error(`深度分析资源校验失败：${asset.name}`), {code: 'checksum-mismatch'});
    }
  };

  const statusHost = () => {
    let host = pageRoot.querySelector('#analyticsLoadStatus');
    if (host) return host;
    host = document.createElement('section');
    host.id = 'analyticsLoadStatus';
    host.className = 'panel';
    host.setAttribute('role', 'status');
    host.setAttribute('aria-live', 'polite');
    host.style.cssText = 'display:none;margin:0 0 18px;padding:14px 18px;border-style:dashed';
    pageRoot.querySelector('.topbar')?.insertAdjacentElement('afterend', host);
    return host;
  };

  const showStatus = (kind, message) => {
    const host = statusHost();
    host.dataset.kind = kind;
    host.style.display = '';
    host.innerHTML = '<strong></strong><div class="panel-desc" style="margin-top:5px"></div>';
    host.querySelector('strong').textContent =
      kind === 'loading' ? '正在载入深度分析' : '深度分析未载入';
    host.querySelector('.panel-desc').textContent = message;
  };

  const hideStatus = () => {
    const host = pageRoot.querySelector('#analyticsLoadStatus');
    if (host) host.style.display = 'none';
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
    script.textContent = `try {\n${asset.source}\n} catch (error) { window.${STATE_KEY}?.reportModuleError(${JSON.stringify(asset.name)}, error); }\n//# sourceURL=rollpig-${asset.name}-${VERSION}.js`;
    document.body.appendChild(script);
    if (!state.errors.some(item => item.name === asset.name)) state.assets[asset.name] = 'ready';
  };

  const withTimeout = (promise, milliseconds, message) => Promise.race([
    promise,
    new Promise((_, reject) => window.setTimeout(() => reject(new Error(message)), milliseconds)),
  ]);

  const topActions = pageRoot.querySelector('.top-actions');
  if (!topActions) return;

  let button = pageRoot.querySelector('#analyticsLoadBtn');
  if (!button) {
    button = document.createElement('button');
    button.id = 'analyticsLoadBtn';
    button.type = 'button';
    button.className = 'btn ghost';
    button.textContent = '深度分析';
    button.title = '点击后才载入深度分析资源与数据';
    const refreshButton = pageRoot.querySelector('#refreshBtn');
    topActions.insertBefore(button, refreshButton || null);
  }

  const load = async () => {
    const activeAnalytics = window.__rollpigAnalyticsUiState;
    if (
      activeAnalytics?.version === VERSION &&
      activeAnalytics.root === pageRoot &&
      pageRoot.querySelector('#analyticsSuite')
    ) {
      await activeAnalytics.refresh?.();
      return;
    }
    if (state.loadPromise) return state.loadPromise;

    state.status = 'loading';
    state.errors = [];
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = '载入中…';
    showStatus('loading', '仅本次点击会通过认证桥接读取 Analytics 代码与聚合数据；核心页面不会等待它。');

    state.loadPromise = (async () => {
      const bridge = window.AstrBotPluginPage;
      if (!bridge?.apiGet) {
        throw Object.assign(new Error('AstrBot Plugin Page Bridge 不存在'), {code: 'bridge-missing'});
      }
      if (typeof bridge.ready === 'function') {
        await withTimeout(bridge.ready(), 6000, '管理桥接在 6 秒内没有就绪');
      }
      const bundle = validateBundle(unwrap(await bridge.apiGet('ui/assets', {version: VERSION})));
      const byName = new Map(bundle.assets.map(asset => [asset.name, asset]));
      for (const name of ALLOWED.keys()) await verifyAsset(byName.get(name));
      injectStyle(byName.get('analytics-theme'));
      injectScript(byName.get('ui-analytics'));
      if (state.errors.length) throw new Error(state.errors.map(item => item.message).join('；'));
      state.status = 'ready';
      hideStatus();
      button.textContent = '刷新深度分析';
      button.title = '重新读取深度分析聚合数据';
    })().catch(error => {
      state.status = 'error';
      showStatus('error', `原因：${error?.message || error}。数据总览、猪猪图鉴和管理操作不受影响。`);
      button.textContent = '重试深度分析';
    }).finally(() => {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      state.loadPromise = null;
    });

    return state.loadPromise;
  };

  button.addEventListener('click', load, {signal: abortController.signal});
})();
