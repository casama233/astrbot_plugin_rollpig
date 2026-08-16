(() => {
  'use strict';

  const VERSION = '3.2.0';
  const STATE_KEY = '__rollpigUiBootstrapState';
  const WIKI_BASE_URL = 'https://casama233.github.io/astrbot_plugin_rollpig/';
  const WIKI_LINKS = Object.freeze({
    player: new URL('gameplay/', WIKI_BASE_URL).href,
    admin: new URL('CONFIGURATION/', WIKI_BASE_URL).href,
    creator: new URL('creators/', WIKI_BASE_URL).href,
    resourceSync: new URL('troubleshooting/admin/#resource-sync', WIKI_BASE_URL).href,
    adminUi: new URL('troubleshooting/admin/#admin-ui', WIKI_BASE_URL).href,
  });
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
    setResourceSyncFeedback: null,
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

  const installWikiStyles = () => {
    if (document.querySelector('style[data-rollpig-wiki-bridge]')) return;
    const style = document.createElement('style');
    style.dataset.rollpigWikiBridge = '1';
    style.textContent = `
      .rollpig-doc-menu{position:relative}
      .rollpig-doc-menu>summary{list-style:none;display:flex;align-items:center;gap:6px;white-space:nowrap}
      .rollpig-doc-menu>summary::-webkit-details-marker{display:none}
      .rollpig-doc-popover{position:absolute;z-index:40;right:0;top:calc(100% + 9px);width:min(310px,calc(100vw - 36px));padding:8px;border:1px solid var(--line);border-radius:16px;background:color-mix(in srgb,var(--surface-strong) 96%,transparent);box-shadow:var(--shadow);backdrop-filter:blur(24px) saturate(145%)}
      .rollpig-doc-link{display:grid;grid-template-columns:34px 1fr;gap:9px;align-items:center;padding:10px;border-radius:12px;color:var(--ink);text-decoration:none;transition:background .2s var(--ease),transform .2s var(--spring)}
      .rollpig-doc-link:hover{background:var(--pink-soft);transform:translateX(2px)}
      .rollpig-doc-link>span:first-child{font-size:20px;text-align:center}
      .rollpig-doc-link strong{display:block;font-size:12px}.rollpig-doc-link small{display:block;margin-top:2px;color:var(--muted);font-size:10px;line-height:1.35}
      .rollpig-context-doc{display:inline-flex;align-items:center;gap:5px;margin-top:7px;padding:5px 9px;border:1px solid color-mix(in srgb,var(--orange) 28%,var(--line));border-radius:999px;color:var(--orange);font-size:10px;font-weight:750;text-decoration:none;background:color-mix(in srgb,var(--orange) 7%,transparent)}
      .rollpig-context-doc:hover{background:color-mix(in srgb,var(--orange) 13%,transparent)}
      @media(max-width:760px){.rollpig-doc-menu>summary{width:42px;height:42px;justify-content:center;padding:0;font-size:0}.rollpig-doc-menu>summary::before{content:'📚';font-size:18px}.rollpig-doc-popover{position:fixed;right:18px;top:76px}}
    `;
    document.head.appendChild(style);
  };

  const makeDocLink = (icon, title, detail, href) => {
    const link = document.createElement('a');
    link.className = 'rollpig-doc-link';
    link.href = href;
    // AstrBot Plugin Pages are sandboxed without allow-popups; _blank is blocked.
    link.target = '_self';
    link.rel = 'noopener noreferrer';
    const iconNode = document.createElement('span');
    iconNode.textContent = icon;
    const copy = document.createElement('span');
    const strong = document.createElement('strong');
    strong.textContent = title;
    const small = document.createElement('small');
    small.textContent = detail;
    copy.append(strong, small);
    link.append(iconNode, copy);
    return link;
  };

  const topActions = pageRoot.querySelector('.top-actions');
  if (!topActions) return;

  const installWikiMenu = () => {
    if (pageRoot.querySelector('#rollpigDocMenu')) return;
    const details = document.createElement('details');
    details.id = 'rollpigDocMenu';
    details.className = 'rollpig-doc-menu';
    const summary = document.createElement('summary');
    summary.className = 'btn ghost';
    summary.textContent = '📚 文档';
    summary.title = '打开今日小猪 Wiki';
    const popover = document.createElement('div');
    popover.className = 'rollpig-doc-popover';
    popover.append(
      makeDocLink('📖', '玩家 Wiki', '玩法、EX、烤箱、日报与保底', WIKI_LINKS.player),
      makeDocLink('⚙️', '管理员手册', '完整配置、资源、存储与运维', WIKI_LINKS.admin),
      makeDocLink('🎨', '投稿指南', '做一只自己的小猪，再交给管理员', WIKI_LINKS.creator),
    );
    details.append(summary, popover);
    const refreshButton = pageRoot.querySelector('#refreshBtn');
    topActions.insertBefore(details, refreshButton || null);
  };

  const ERROR_PATTERN = /(失败|失敗|错误|錯誤|不可用|403|401|超时|逾時|校验失败|校驗失敗|bridge|版本不匹配)/i;

  const setContextDoc = (host, key, show, label, href) => {
    if (!host) return;
    const selector = `[data-rollpig-context-doc="${key}"]`;
    const existing = host.querySelector(selector);
    if (!show) {
      existing?.remove();
      return;
    }
    if (existing) return;
    const link = document.createElement('a');
    link.dataset.rollpigContextDoc = key;
    link.className = 'rollpig-context-doc';
    link.href = href;
    link.target = '_self';
    link.rel = 'noopener noreferrer';
    link.textContent = `🧯 ${label}`;
    host.appendChild(link);
  };

  state.setResourceSyncFeedback = (host, message) => {
    setContextDoc(
      host,
      'resource-sync',
      ERROR_PATTERN.test(String(message || '')),
      '查看猪源同步排障',
      WIKI_LINKS.resourceSync,
    );
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
    setContextDoc(
      host,
      'admin-ui',
      kind === 'error',
      '查看管理页定向排障',
      WIKI_LINKS.adminUi,
    );
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

  installWikiStyles();
  installWikiMenu();
  const initialSync = pageRoot.querySelector('#syncFeedback');
  if (initialSync) state.setResourceSyncFeedback(initialSync, initialSync.textContent || '');

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
