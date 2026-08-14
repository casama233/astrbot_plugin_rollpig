(() => {
  'use strict';
  const STATE_KEY = '__rollpigAnalyticsUiState';
  const VERSION = '3.2.0';
  const pageRoot = document.querySelector('.shell');
  const bridge = window.AstrBotPluginPage;
  if (!pageRoot || !bridge?.apiGet) throw new Error('深度分析缺少页面根节点或管理桥接');

  const previous = window[STATE_KEY];
  if (
    previous?.version === VERSION &&
    previous.root === pageRoot &&
    pageRoot.querySelector('#analyticsSuite')
  ) {
    previous.refresh?.();
    return;
  }
  previous?.abortController?.abort();

  const abortController = new AbortController();
  const state = {
    version: VERSION,
    root: pageRoot,
    mounted: false,
    refresh: null,
    abortController,
  };
  window[STATE_KEY] = state;
  const number = new Intl.NumberFormat('zh-CN', {maximumFractionDigits: 1});
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  const finePointer = window.matchMedia?.('(pointer: fine)')?.matches ?? false;
  const percent = value => `${number.format(Number(value || 0))}%`;
  const format = value => number.format(Number(value || 0));
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);

  const unwrap = response => {
    const first = response?.data ?? response;
    return first?.data ?? first;
  };

  const signed = value => {
    const numeric = Number(value || 0);
    if (!Number.isFinite(numeric)) return '—';
    return `${numeric > 0 ? '+' : ''}${number.format(numeric)}%`;
  };

  const deltaClass = value => {
    const numeric = Number(value || 0);
    if (numeric > 0.05) return 'is-up';
    if (numeric < -0.05) return 'is-down';
    return 'is-flat';
  };

  function ensureSuite() {
    let suite = document.getElementById('analyticsSuite');
    if (suite) return suite;
    const anchor = document.querySelector('#view-overview .metrics');
    if (!anchor) return null;
    suite = document.createElement('section');
    suite.id = 'analyticsSuite';
    suite.className = 'analytics-suite';
    suite.setAttribute('aria-labelledby', 'analyticsSuiteTitle');
    suite.innerHTML = `
      <header class="analytics-suite__head">
        <div>
          <div class="eyebrow">Growth Intelligence</div>
          <h2 id="analyticsSuiteTitle">猪圈深度分析</h2>
          <p>比较最近两个 7 日周期，观察回访、解锁效率、图鉴覆盖与玩法运行健康。</p>
        </div>
        <div class="analytics-suite__meta">
          <span class="analytics-live"><i></i><span id="analyticsSource">读取中</span></span>
          <span id="analyticsLatency">—</span>
        </div>
      </header>
      <div class="analytics-kpis" id="analyticsKpis" aria-live="polite">
        ${Array.from({length: 4}, () => '<div class="analytics-kpi is-loading"><i></i><i></i><i></i></div>').join('')}
      </div>
      <div class="analytics-grid" id="analyticsGrid">
        <article class="analytics-card analytics-card--wide" id="analyticsActivity">
          <div class="analytics-skeleton analytics-skeleton--chart"></div>
        </article>
        <article class="analytics-card" id="analyticsComparison">
          <div class="analytics-skeleton analytics-skeleton--chart"></div>
        </article>
        <article class="analytics-card" id="analyticsRetention">
          <div class="analytics-skeleton analytics-skeleton--chart"></div>
        </article>
        <article class="analytics-card" id="analyticsCoverage">
          <div class="analytics-skeleton analytics-skeleton--chart"></div>
        </article>
        <article class="analytics-card" id="analyticsPlatforms">
          <div class="analytics-skeleton analytics-skeleton--chart"></div>
        </article>
        <article class="analytics-card analytics-card--wide" id="analyticsRising">
          <div class="analytics-skeleton analytics-skeleton--chart"></div>
        </article>
        <article class="analytics-card" id="analyticsOperations">
          <div class="analytics-skeleton analytics-skeleton--chart"></div>
        </article>
      </div>`;
    anchor.insertAdjacentElement('afterend', suite);
    return suite;
  }

  function cardHead(eyebrow, title, note = '') {
    return `<header class="analytics-card__head"><div><span>${esc(eyebrow)}</span><h3>${esc(title)}</h3></div>${note ? `<small>${esc(note)}</small>` : ''}</header>`;
  }

  function renderKpis(data) {
    const current = data.periods?.current || {};
    const delta = data.deltas || {};
    const retention = data.retention || {};
    const catalog = data.catalog || {};
    const items = [
      {
        label: '7 日活跃用户', value: format(current.active_users),
        delta: signed(delta.active_users), className: deltaClass(delta.active_users),
        note: `上周期 ${format(data.periods?.previous?.active_users)}`
      },
      {
        label: '7 日新解锁', value: format(current.new_unlocks),
        delta: signed(delta.new_unlocks), className: deltaClass(delta.new_unlocks),
        note: `解锁效率 ${percent(current.unlock_efficiency)}`
      },
      {
        label: '上期→本期回访率', value: percent(retention.rate),
        delta: `${format(retention.returning_users)} 人回访`, className: 'is-accent',
        note: `本期独有活跃 ${format(retention.new_current_users)} 人`
      },
      {
        label: '零收藏猪猪', value: format(catalog.zero_collector_count),
        delta: `中位解锁 ${format(catalog.median_unlocked)}`, className: catalog.zero_collector_count ? 'is-warning' : 'is-up',
        note: `P90 ${format(catalog.p90_unlocked)} / ${format(catalog.catalog_count)}`
      }
    ];
    document.getElementById('analyticsKpis').innerHTML = items.map(item => `
      <article class="analytics-kpi">
        <div class="analytics-kpi__label">${esc(item.label)}</div>
        <div class="analytics-kpi__row"><strong>${esc(item.value)}</strong><span class="analytics-delta ${item.className}">${esc(item.delta)}</span></div>
        <div class="analytics-kpi__note">${esc(item.note)}</div>
      </article>`).join('');
  }

  function renderActivity(data) {
    const rows = Array.isArray(data.activity) ? data.activity : [];
    const maxUsers = Math.max(1, ...rows.map(item => Number(item.users || 0)));
    const cells = rows.map(item => {
      const intensity = Math.max(.07, Number(item.users || 0) / maxUsers);
      const title = `${item.date} · 活跃 ${item.users || 0} · 新解锁 ${item.new_unlocks || 0} · 烧烤 ${item.roasts || 0} · 被吃 ${item.eats || 0}`;
      return `<div class="activity-cell" style="--intensity:${intensity.toFixed(3)}" title="${esc(title)}"><i></i><span>${esc(String(item.date || '').slice(5))}</span></div>`;
    }).join('');
    const current = data.periods?.current || {};
    document.getElementById('analyticsActivity').innerHTML = `
      ${cardHead('28 Day Activity', '活跃热力与玩法脉冲', `${format(current.avg_daily_users)} 日均活跃`)}
      <div class="activity-legend"><span>低</span><i></i><i></i><i></i><i></i><span>高</span></div>
      <div class="activity-heatmap">${cells || '<div class="analytics-empty">暂时没有可展示的每日活动</div>'}</div>
      <div class="activity-summary">
        <span><b>${format(current.draws)}</b> 抽取</span>
        <span><b>${format(current.new_unlocks)}</b> 新解锁</span>
        <span><b>${format(data.operations?.roasts)}</b> 烧烤</span>
        <span><b>${format(data.operations?.eats)}</b> 被吃事件</span>
      </div>`;
  }

  function renderComparison(data) {
    const current = data.periods?.current || {};
    const previous = data.periods?.previous || {};
    const rows = [
      ['活跃用户', current.active_users, previous.active_users],
      ['周期抽取', current.draws, previous.draws],
      ['新解锁', current.new_unlocks, previous.new_unlocks]
    ];
    document.getElementById('analyticsComparison').innerHTML = `
      ${cardHead('Period Compare', '双周期增长对比', '最近 7 日 vs 上一周期')}
      <div class="compare-list">${rows.map(([label, now, before]) => {
        const max = Math.max(1, Number(now || 0), Number(before || 0));
        return `<div class="compare-row"><div class="compare-row__top"><span>${esc(label)}</span><b>${format(now)} <small>/ ${format(before)}</small></b></div><div class="compare-bars"><i style="width:${(Number(now || 0) / max * 100).toFixed(2)}%"></i><i style="width:${(Number(before || 0) / max * 100).toFixed(2)}%"></i></div></div>`;
      }).join('')}</div>
      <div class="compare-legend"><span><i class="is-current"></i>当前周期</span><span><i class="is-previous"></i>上一周期</span></div>`;
  }

  function renderRetention(data) {
    const retention = data.retention || {};
    const rate = Math.max(0, Math.min(100, Number(retention.rate || 0)));
    document.getElementById('analyticsRetention').innerHTML = `
      ${cardHead('Audience', '回访与周期独有活跃')}
      <div class="retention-layout">
        <div class="retention-ring" style="--rate:${rate}"><div><strong>${percent(rate)}</strong><span>上期→本期回访率</span></div></div>
        <dl class="analytics-dl">
          <div><dt>回访用户</dt><dd>${format(retention.returning_users)}</dd></div>
          <div><dt>本期独有活跃</dt><dd>${format(retention.new_current_users)}</dd></div>
          <div><dt>上期活跃基数</dt><dd>${format(retention.previous_active_users)}</dd></div>
        </dl>
      </div>`;
  }

  function renderCoverage(data) {
    const catalog = data.catalog || {};
    const buckets = Array.isArray(catalog.distribution) ? catalog.distribution : [];
    const total = Math.max(1, buckets.reduce((sum, item) => sum + Number(item.users || 0), 0));
    document.getElementById('analyticsCoverage').innerHTML = `
      ${cardHead('Collection Coverage', '图鉴覆盖分布', `Top 5 占抽取 ${percent(catalog.top5_draw_share)}`)}
      <div class="coverage-strip">${buckets.map((item, index) => `<i class="coverage-tone-${index + 1}" style="width:${(Number(item.users || 0) / total * 100).toFixed(2)}%" title="${esc(item.label)}：${format(item.users)} 人"></i>`).join('')}</div>
      <div class="coverage-list">${buckets.map((item, index) => `<div><span><i class="coverage-tone-${index + 1}"></i>${esc(item.label)}</span><b>${format(item.users)}</b></div>`).join('')}</div>
      <footer class="analytics-card__footer"><span>长尾猪猪 ${format(catalog.long_tail_count)}</span><span>零收藏 ${format(catalog.zero_collector_count)}</span></footer>`;
  }

  function renderPlatforms(data) {
    const rows = Array.isArray(data.platforms) ? data.platforms : [];
    const max = Math.max(1, ...rows.map(item => Number(item.users || 0)));
    document.getElementById('analyticsPlatforms').innerHTML = `
      ${cardHead('Audience Mix', '平台身份构成', `${format(rows.reduce((sum, item) => sum + Number(item.users || 0), 0))} 个身份`)}
      <div class="platform-list">${rows.length ? rows.map(item => `<div class="platform-row"><div><span>${esc(item.platform || 'unknown')}</span><b>${format(item.users)}</b></div><i><em style="width:${(Number(item.users || 0) / max * 100).toFixed(2)}%"></em></i></div>`).join('') : '<div class="analytics-empty">暂无平台分布数据</div>'}</div>`;
  }

  function renderRising(data) {
    const rows = Array.isArray(data.rising_pigs) ? data.rising_pigs : [];
    document.getElementById('analyticsRising').innerHTML = `
      ${cardHead('Momentum', '上升最快的猪猪', '当前 7 日与上一周期抽中次数差值')}
      <div class="rising-table" role="table">
        <div class="rising-table__head" role="row"><span>猪猪</span><span>本期</span><span>上期</span><span>变化</span></div>
        ${rows.length ? rows.map((item, index) => `<div class="rising-table__row" role="row"><span><i>${index + 1}</i><b>${esc(item.name || item.id)}</b><small>${esc(item.id)}</small></span><span>${format(item.current)}</span><span>${format(item.previous)}</span><span class="analytics-delta ${Number(item.delta || 0) >= 0 ? 'is-up' : 'is-down'}">${Number(item.delta || 0) > 0 ? '+' : ''}${format(item.delta)}</span></div>`).join('') : '<div class="analytics-empty">还没有足够的双周期数据</div>'}
      </div>`;
  }

  function renderOperations(data) {
    const ops = data.operations || {};
    const ai = ops.ai || {};
    const completedAi = Number(ai.ready || 0) + Number(ai.failed || 0);
    const success = completedAi ? Number(ai.ready || 0) / completedAi * 100 : 0;
    document.getElementById('analyticsOperations').innerHTML = `
      ${cardHead('Runtime Signals', '玩法运行健康', '最近 7 日')}
      <div class="operations-grid">
        <div><span>烧烤次数</span><strong>${format(ops.roasts)}</strong></div>
        <div><span>被吃事件</span><strong>${format(ops.eats)}</strong></div>
        <div><span>AI 成功</span><strong>${format(ai.ready)}</strong></div>
        <div><span>AI 失败</span><strong>${format(ai.failed)}</strong></div>
      </div>
      <div class="ai-health"><div><span>AI 文案成功率 · 已完成样本</span><b>${percent(success)}</b></div><i><em style="width:${Math.max(0, Math.min(100, success)).toFixed(2)}%"></em></i><small>生成中 ${format(ai.generating)} 次，不计入成功率分母</small></div>`;
  }

  function installAnalyticsMotion() {
    if (reducedMotion || !finePointer) return;
    document.querySelectorAll('#analyticsSuite .analytics-card, #analyticsSuite .analytics-kpi').forEach(card => {
      if (card.dataset.motionBound === '1') return;
      card.dataset.motionBound = '1';
      let frame = 0;
      card.addEventListener('pointermove', event => {
        if (frame) cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          const rect = card.getBoundingClientRect();
          const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
          const y = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
          card.style.setProperty('--spot-x', `${x}px`);
          card.style.setProperty('--spot-y', `${y}px`);
          const tiltX = ((y / Math.max(1, rect.height)) - .5) * -2.2;
          const tiltY = ((x / Math.max(1, rect.width)) - .5) * 2.2;
          card.style.setProperty('--tilt-x', `${tiltX.toFixed(2)}deg`);
          card.style.setProperty('--tilt-y', `${tiltY.toFixed(2)}deg`);
        });
      }, {passive: true, signal: abortController.signal});
      card.addEventListener('pointerleave', () => {
        card.style.setProperty('--tilt-x', '0deg');
        card.style.setProperty('--tilt-y', '0deg');
      }, {passive: true, signal: abortController.signal});
    });
  }

  function render(data) {
    if (window[STATE_KEY] !== state || !pageRoot.isConnected) return;
    ensureSuite();
    renderKpis(data);
    renderActivity(data);
    renderComparison(data);
    renderRetention(data);
    renderCoverage(data);
    renderPlatforms(data);
    renderRising(data);
    renderOperations(data);
    installAnalyticsMotion();
    const source = document.getElementById('analyticsSource');
    const latency = document.getElementById('analyticsLatency');
    if (source) source.textContent = data.source === 'normalized-sql' ? 'SQL 事实聚合' : 'JSON 兼容统计';
    if (latency) latency.textContent = `${number.format(data.observability?.query_elapsed_ms || 0)} ms`;
  }

  function renderError(error) {
    if (window[STATE_KEY] !== state || !pageRoot.isConnected) return;
    const suite = ensureSuite();
    if (!suite) return;
    const grid = document.getElementById('analyticsGrid');
    const kpis = document.getElementById('analyticsKpis');
    if (kpis) kpis.innerHTML = '';
    if (grid) grid.innerHTML = `<div class="analytics-error"><strong>深度分析暂时不可用</strong><span>${esc(error?.message || error || '读取失败')}</span><button type="button" class="btn ghost" id="analyticsRetry">重新读取</button></div>`;
    document.getElementById('analyticsRetry')?.addEventListener('click', loadInsights, {once: true});
    const source = document.getElementById('analyticsSource');
    if (source) source.textContent = '读取失败';
  }

  let pending = null;
  async function loadInsights() {
    ensureSuite();
    if (pending) return pending;
    pending = (async () => {
      try {
        const response = await bridge.apiGet('analytics/insights', {});
        const data = unwrap(response);
        if (!data || typeof data !== 'object') throw new Error('分析接口返回格式无效');
        render(data);
      } catch (error) {
        renderError(error);
      } finally {
        pending = null;
      }
    })();
    return pending;
  }


  const mount = () => {
    const suite = ensureSuite();
    if (!suite) throw new Error('深度分析挂载点不存在');
    state.mounted = true;
    state.refresh = loadInsights;

    const refreshButton = pageRoot.querySelector('#refreshBtn');
    refreshButton?.addEventListener('click', () => {
      if (window[STATE_KEY] === state) loadInsights();
    }, {signal: abortController.signal});

    loadInsights();
  };

  mount();
})();
