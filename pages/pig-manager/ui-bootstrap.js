(() => {
  'use strict';

  const VERSION = '3.10.1';
  const STATE_KEY = '__rollpigUiBootstrapState';
  const BOOTSTRAP_URL = document.currentScript?.src || document.baseURI;
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

  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);

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

  const installDashboardOverhaulStyles = () => {
    if (document.querySelector('style[data-rollpig-dashboard-overhaul]')) return;
    const style = document.createElement('style');
    style.dataset.rollpigDashboardOverhaul = VERSION;
    style.textContent = `
      #view-overview .metrics{gap:14px}
      #view-overview .metric{min-height:146px;padding:16px 16px 14px;border-radius:16px;background:linear-gradient(155deg,color-mix(in srgb,var(--surface-strong) 96%,transparent),color-mix(in srgb,var(--tone,var(--pink)) 4%,var(--surface)));box-shadow:0 7px 22px rgba(0,0,0,.08)}
      #view-overview .metric .value{margin-top:10px;font-size:29px}
      #view-overview .metric .note{margin-top:2px}
      #view-overview .metric-viz{left:14px;right:14px;bottom:11px;height:30px;opacity:.88}
      #view-overview .metric-snapshot-viz{justify-content:flex-start;height:24px;padding:0 8px;border:1px solid color-mix(in srgb,var(--tone,var(--pink)) 15%,var(--line));border-radius:999px;background:color-mix(in srgb,var(--tone,var(--pink)) 5%,transparent);font-size:9px;font-weight:650}
      #view-overview .metric-snapshot-viz:before{width:5px;height:5px;box-shadow:none}
      #view-overview .metric-growth-viz{justify-content:space-between;color:var(--muted)}
      #view-overview .metric-growth-viz b{color:var(--tone,var(--violet));font-size:12px;font-weight:850;font-variant-numeric:tabular-nums}
      #view-overview .metric-trend-caption{position:absolute;right:1px;bottom:-1px;padding:2px 6px;border-radius:999px;background:color-mix(in srgb,var(--surface-strong) 82%,transparent);color:var(--muted);font-size:8px;font-weight:650;backdrop-filter:blur(6px)}
      #view-overview .dashboard-grid{align-items:start;gap:14px}
      #view-overview .overview-trend-panel,#view-overview .collection-health-panel,#view-overview .popularity-panel{border-radius:16px;background:linear-gradient(155deg,color-mix(in srgb,var(--surface-strong) 96%,transparent),color-mix(in srgb,var(--pink-soft) 12%,var(--surface)));box-shadow:0 10px 30px rgba(0,0,0,.08)}
      #view-overview .overview-trend-panel .trend-summary-item{border-radius:10px;background:color-mix(in srgb,var(--surface-strong) 90%,var(--bg));box-shadow:none}
      #view-overview .popularity-panel{padding:18px;overflow:visible}
      #view-overview .popularity-panel .panel-head{margin-bottom:12px;align-items:center}
      #view-overview .popularity-panel .panel-desc{max-width:420px}
      #view-overview .leaderboard-summary{display:flex;align-items:center;gap:6px;padding:6px 9px;border:1px solid var(--line);border-radius:999px;background:color-mix(in srgb,var(--surface-strong) 78%,transparent);color:var(--muted);font-size:9px;white-space:nowrap}
      #view-overview .leaderboard-summary b{color:var(--ink);font-size:10px}
      #view-overview #barChart.leaderboard{height:auto!important;display:block;margin:0;padding:0}
      #view-overview .leaderboard-list{display:grid;gap:8px}
      #view-overview .leaderboard-row{position:relative;display:grid;grid-template-columns:38px minmax(0,1fr) auto;grid-template-areas:'rank copy value' 'rank track value';column-gap:11px;row-gap:7px;align-items:center;min-height:66px;padding:11px 12px;border:1px solid var(--line);border-radius:12px;background:color-mix(in srgb,var(--surface-strong) 88%,var(--bg));overflow:hidden;transition:transform .18s var(--ease),border-color .18s var(--ease),background .18s var(--ease)}
      #view-overview .leaderboard-row:hover{transform:translateY(-1px);border-color:color-mix(in srgb,var(--pink) 30%,var(--line));background:color-mix(in srgb,var(--pink-soft) 14%,var(--surface-strong))}
      #view-overview .leaderboard-row::after{content:'';position:absolute;inset:0 auto 0 0;width:2px;background:color-mix(in srgb,var(--pink) 55%,transparent)}
      #view-overview .leaderboard-rank{grid-area:rank;width:34px;height:34px;display:grid;place-items:center;border:1px solid var(--line);border-radius:10px;background:var(--surface-strong);color:var(--muted);font:800 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace}
      #view-overview .leaderboard-row:nth-child(1) .leaderboard-rank{color:var(--pink);border-color:color-mix(in srgb,var(--pink) 30%,var(--line));background:color-mix(in srgb,var(--pink) 8%,var(--surface-strong))}
      #view-overview .leaderboard-row:nth-child(2) .leaderboard-rank{color:var(--violet)}
      #view-overview .leaderboard-row:nth-child(3) .leaderboard-rank{color:var(--orange)}
      #view-overview .leaderboard-copy{grid-area:copy;min-width:0;display:flex;align-items:baseline;gap:8px}
      #view-overview .leaderboard-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;font-weight:780;color:var(--ink)}
      #view-overview .leaderboard-share{flex:none;color:var(--muted);font-size:8.5px;font-variant-numeric:tabular-nums}
      #view-overview .leaderboard-value{grid-area:value;align-self:center;text-align:right;font-variant-numeric:tabular-nums}
      #view-overview .leaderboard-value strong{display:block;font-size:18px;line-height:1;font-weight:850;color:var(--ink)}
      #view-overview .leaderboard-value small{display:block;margin-top:4px;color:var(--muted);font-size:8px}
      #view-overview .leaderboard-track{grid-area:track;height:5px;border-radius:999px;background:color-mix(in srgb,var(--muted) 15%,var(--line));overflow:hidden}
      #view-overview .leaderboard-track i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--pink),var(--pink-2));box-shadow:0 0 12px color-mix(in srgb,var(--pink) 24%,transparent)}
      #view-overview .sync-panel,#view-overview .update-panel{border-radius:16px;box-shadow:0 7px 22px rgba(0,0,0,.06)}
      @media(max-width:980px){#view-overview .leaderboard-summary{display:none}}
      @media(max-width:760px){#view-overview .metrics{grid-template-columns:repeat(2,minmax(0,1fr))}#view-overview .leaderboard-row{grid-template-columns:34px minmax(0,1fr) auto;padding:10px}#view-overview .leaderboard-share{display:none}}
    `;
    document.head.appendChild(style);
  };

  const makeDocLink = (icon, title, detail, href) => {
    const link = document.createElement('a');
    link.className = 'rollpig-doc-link';
    link.href = href;
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

  const installPigStudio = () => {
    if (document.querySelector('script[data-rollpig-pig-studio-loader]')) return;
    const script = document.createElement('script');
    script.type = 'module';
    script.dataset.rollpigPigStudioLoader = '1';
    script.src = new URL('./studio-integration.js', BOOTSTRAP_URL).href;
    script.addEventListener('error', () => {
      console.error('[rollpig] AI 小猪工坊前端加载失败');
    }, {once: true});
    document.head.appendChild(script);
  };

  const upgradePopularityBoard = () => {
    const root = pageRoot.querySelector('#barChart');
    if (!root) return;
    const panel = root.closest('.panel');
    panel?.classList.add('popularity-panel');
    if (root.querySelector('.leaderboard-list')) return;
    const rows = Array.from(root.querySelectorAll(':scope > .bar-row'));
    if (!rows.length) return;
    const items = rows.map((row, index) => {
      const rawName = String(row.querySelector('.bar-name')?.textContent || '').trim();
      const name = rawName.replace(/^\s*\d+\.\s*/, '') || `小猪 ${index + 1}`;
      const count = Number(String(row.querySelector('.bar-value')?.textContent || '0').replace(/[^0-9.-]/g, '')) || 0;
      return {name, count, rank: index + 1};
    });
    const total = items.reduce((sum, item) => sum + item.count, 0);
    const max = Math.max(1, ...items.map(item => item.count));
    const top3 = items.slice(0, 3).reduce((sum, item) => sum + item.count, 0);
    root.classList.add('leaderboard');
    root.innerHTML = `<div class="leaderboard-list">${items.map(item => {
      const share = total ? item.count / total * 100 : 0;
      return `<div class="leaderboard-row" data-rank="${item.rank}">
        <div class="leaderboard-rank">#${item.rank}</div>
        <div class="leaderboard-copy"><span class="leaderboard-name">${esc(item.name)}</span><span class="leaderboard-share">${share.toFixed(1)}%</span></div>
        <div class="leaderboard-value"><strong>${item.count}</strong><small>次抽中</small></div>
        <div class="leaderboard-track" aria-hidden="true"><i style="width:${Math.max(4, item.count / max * 100).toFixed(1)}%"></i></div>
      </div>`;
    }).join('')}</div>`;
    const head = panel?.querySelector('.panel-head');
    if (head) {
      let summary = head.querySelector('.leaderboard-summary');
      if (!summary) {
        summary = document.createElement('div');
        summary.className = 'leaderboard-summary';
        head.appendChild(summary);
      }
      summary.innerHTML = `上榜 <b>${items.length}</b> · TOP3 <b>${total ? (top3 / total * 100).toFixed(0) : '0'}%</b>`;
      const desc = head.querySelector('.panel-desc');
      if (desc) desc.textContent = '按累计抽中次数排序 · 同步展示热度占比';
    }
  };

  const upgradeKpiSemantics = () => {
    pageRoot.querySelector('#trendChart')?.closest('.panel')?.classList.add('overview-trend-panel');
    pageRoot.querySelector('#rateRing')?.closest('.panel')?.classList.add('collection-health-panel');
    const summaryItems = Array.from(pageRoot.querySelectorAll('#trendSummary .trend-summary-item'));
    const drawsItem = summaryItems.find(item => String(item.querySelector('span')?.textContent || '').includes('14 日抽取'));
    const drawValue = String(drawsItem?.querySelector('strong')?.textContent || '').trim();
    const drawsViz = pageRoot.querySelector('#vDraws');
    if (drawsViz && drawValue) {
      drawsViz.classList.add('metric-snapshot-viz', 'metric-growth-viz');
      drawsViz.setAttribute('aria-label', `近 14 日新增 ${drawValue} 次抽取`);
      drawsViz.innerHTML = `<span>近 14 日新增</span><b>+${esc(drawValue)}</b>`;
    }
    const todayViz = pageRoot.querySelector('#vToday');
    if (todayViz && todayViz.querySelector('svg') && !todayViz.querySelector('.metric-trend-caption')) {
      const caption = document.createElement('span');
      caption.className = 'metric-trend-caption';
      caption.textContent = '近 14 日每日活跃';
      todayViz.appendChild(caption);
    }
  };

  const upgradeDashboardCore = () => {
    if (window[STATE_KEY] !== state || !pageRoot.isConnected) return;
    upgradeKpiSemantics();
    upgradePopularityBoard();
  };

  const scheduleDashboardUpgrade = () => {
    [0, 80, 240, 700].forEach(delay => {
      window.setTimeout(upgradeDashboardCore, delay);
    });
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
    if (!state.errors.some(item => item.name === asset.name)) state.assets[name] = 'ready';
  };

  const withTimeout = (promise, milliseconds, message) => Promise.race([
    promise,
    new Promise((_, reject) => window.setTimeout(() => reject(new Error(message)), milliseconds)),
  ]);

  installWikiStyles();
  installDashboardOverhaulStyles();
  installWikiMenu();
  installPigStudio();
  scheduleDashboardUpgrade();

  const initialSync = pageRoot.querySelector('#syncFeedback');
  if (initialSync) state.setResourceSyncFeedback(initialSync, initialSync.textContent || '');

  const refreshButton = pageRoot.querySelector('#refreshBtn');
  refreshButton?.addEventListener('click', scheduleDashboardUpgrade, {signal: abortController.signal});
  pageRoot.querySelector('[data-route="overview"]')?.addEventListener('click', scheduleDashboardUpgrade, {signal: abortController.signal});

  let button = pageRoot.querySelector('#analyticsLoadBtn');
  if (!button) {
    button = document.createElement('button');
    button.id = 'analyticsLoadBtn';
    button.type = 'button';
    button.className = 'btn ghost';
    button.textContent = '深度分析';
    button.title = '按需载入回访、覆盖、运行健康等深度指标';
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
      scheduleDashboardUpgrade();
      return;
    }
    if (state.loadPromise) return state.loadPromise;

    state.status = 'loading';
    state.errors = [];
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.textContent = '载入中…';
    showStatus('loading', '正在通过认证桥接读取深度分析代码与聚合数据；核心总览不会被阻塞。');

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
      scheduleDashboardUpgrade();
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