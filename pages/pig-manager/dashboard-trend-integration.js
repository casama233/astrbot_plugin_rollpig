(() => {
  'use strict';

  const bridge = window.AstrBotPluginPage;
  const chart = document.getElementById('trendChart');
  const panel = chart?.closest('.panel');
  if (!bridge?.apiGet || !chart || !panel) return;

  const REPEAT_METRIC_ID = 'repeat-draws';
  const repeatMetricSelector = `[data-rollpig-metric="${REPEAT_METRIC_ID}"]`;

  let rows = [];
  let refreshPromise = null;
  let refreshQueued = false;
  let tooltipObserver = null;

  const normalizedText = value => String(value ?? '').replace(/\s+/g, ' ').trim();

  const findMetricNode = (root, selector, labelSelector, labels) => {
    if (!root) return null;
    const identified = root.querySelector(`${selector}${repeatMetricSelector}`);
    if (identified) return identified;

    const expected = new Set(labels);
    const candidate = Array.from(root.querySelectorAll(selector)).find(node => {
      const label = labelSelector ? node.querySelector(labelSelector) : node;
      return expected.has(normalizedText(label?.textContent));
    });
    if (candidate) candidate.setAttribute('data-rollpig-metric', REPEAT_METRIC_ID);
    return candidate || null;
  };

  const setRefreshState = (state, error = null) => {
    panel.dataset.rollpigRepeatDrawState = state;
    if (error) {
      panel.dataset.rollpigRepeatDrawError = normalizedText(error?.message || error);
    } else {
      delete panel.dataset.rollpigRepeatDrawError;
    }
  };

  const unwrap = response => {
    const first = response?.data ?? response;
    if (first?.status === 'error') throw new Error(first.message || '操作失败');
    const payload = first?.data ?? first;
    if (payload?.status === 'error') throw new Error(payload.message || '操作失败');
    return payload;
  };

  const numberValue = value => {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  };

  const normalizeRows = data => (Array.isArray(data?.trend) ? data.trend : []).map(entry => {
    const draws = numberValue(entry?.draws);
    const unlocks = numberValue(entry?.new_unlocks);
    return {
      date: String(entry?.date || ''),
      users: numberValue(entry?.users),
      draws,
      unlocks,
      repeats: Math.max(0, draws - unlocks),
    };
  });

  function replaceLegendCopy() {
    const description = panel.querySelector('.panel-head .panel-desc');
    if (description) {
      description.textContent = '移动到折线可查看每日使用人数、重复抽中与新解锁';
    }

    const repeatLegend = findMetricNode(
      panel,
      '.legend span',
      null,
      ['抽取次数', '重复抽中'],
    );
    if (!repeatLegend) return;

    const textNode = Array.from(repeatLegend.childNodes).find(
      node => node.nodeType === Node.TEXT_NODE && normalizedText(node.textContent),
    );
    if (textNode && normalizedText(textNode.textContent) !== '重复抽中') {
      textNode.textContent = '重复抽中';
    } else if (!textNode) {
      repeatLegend.append(document.createTextNode('重复抽中'));
    }
  }

  function patchChart() {
    const svg = chart.querySelector('svg');
    if (!svg || !rows.length) return;

    svg.setAttribute('aria-label', '近十四日使用人数、重复抽中与新解锁趋势');

    const bars = Array.from(svg.querySelectorAll('.chart-draw-bar'));
    const gridlines = Array.from(svg.querySelectorAll('.gridline'));
    if (!bars.length || gridlines.length < 2) return;

    const top = numberValue(gridlines[0].getAttribute('y1'));
    const base = numberValue(gridlines[gridlines.length - 1].getAttribute('y1'));
    const plotHeight = Math.max(0, base - top);
    const axisLabels = Array.from(svg.querySelectorAll('.chart-label'))
      .filter(node => node.getAttribute('x') === '5');
    const renderedMax = numberValue(axisLabels[0]?.textContent);
    const fallbackMax = Math.max(1, ...rows.flatMap(row => [row.users, row.draws, row.unlocks]));
    const max = renderedMax > 0 ? renderedMax : fallbackMax;

    bars.forEach((bar, index) => {
      const repeatCount = rows[index]?.repeats ?? 0;
      const height = Math.max(0, repeatCount / max * plotHeight);
      bar.setAttribute('data-rollpig-metric', REPEAT_METRIC_ID);
      bar.setAttribute('height', height.toFixed(3));
      bar.setAttribute('y', (base - height).toFixed(3));
      bar.setAttribute('aria-label', `重复抽中 ${repeatCount} 次`);
    });
  }

  function patchSummary() {
    const summary = document.getElementById('trendSummary');
    const repeatItem = findMetricNode(
      summary,
      '.trend-summary-item',
      'span',
      ['14 日抽取', '14 日重复抽中'],
    );
    if (!repeatItem) return;

    const totalRepeats = rows.reduce((sum, row) => sum + row.repeats, 0);
    const label = repeatItem.querySelector('span');
    const value = repeatItem.querySelector('strong');
    if (label && label.textContent !== '14 日重复抽中') label.textContent = '14 日重复抽中';
    if (value) {
      const next = `${totalRepeats.toLocaleString()} 次`;
      if (value.textContent !== next) value.textContent = next;
    }
  }

  function patchTooltip() {
    const tip = document.getElementById('trendTip');
    if (!tip || !rows.length) return;

    const date = normalizedText(tip.querySelector('.tooltip-date')?.textContent);
    if (!date) return;
    const row = rows.find(item => item.date === date);
    if (!row) return;

    const repeatRow = findMetricNode(
      tip,
      '.tooltip-row',
      'span',
      ['抽取次数', '重复抽中'],
    );
    if (!repeatRow) return;

    const label = repeatRow.querySelector('span');
    const value = repeatRow.querySelector('b');
    if (label && label.textContent !== '重复抽中') label.textContent = '重复抽中';
    if (value && value.textContent !== String(row.repeats)) value.textContent = String(row.repeats);
  }

  function observeTooltip() {
    tooltipObserver?.disconnect();
    const tip = document.getElementById('trendTip');
    if (!tip) return;
    tooltipObserver = new MutationObserver(patchTooltip);
    tooltipObserver.observe(tip, {childList: true, subtree: true, characterData: true});
  }

  function patchAll() {
    replaceLegendCopy();
    patchChart();
    patchSummary();
    observeTooltip();
    patchTooltip();
  }

  function scheduleRefresh() {
    if (refreshPromise) {
      refreshQueued = true;
      return;
    }
    setRefreshState('loading');
    refreshPromise = (async () => {
      if (typeof bridge.ready === 'function') await bridge.ready();
      const nextRows = normalizeRows(unwrap(await bridge.apiGet('overview')));
      rows = nextRows;
      patchAll();
      setRefreshState('ready');
    })().catch(error => {
      setRefreshState('error', error);
      console.warn('[rollpig] 重复抽中趋势增强失败，保留原始趋势展示', error);
    }).finally(() => {
      refreshPromise = null;
      if (refreshQueued) {
        refreshQueued = false;
        scheduleRefresh();
      }
    });
  }

  const chartObserver = new MutationObserver(() => scheduleRefresh());
  chartObserver.observe(chart, {childList: true});

  const panelObserver = new MutationObserver(() => {
    patchSummary();
    observeTooltip();
  });
  panelObserver.observe(panel, {childList: true, subtree: true});

  scheduleRefresh();
})();
