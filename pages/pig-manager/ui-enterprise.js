(() => {
  if (window.__rollpigEnterpriseUiReady) {
    window.__rollpigEnterpriseUiRefresh?.();
    return;
  }
  window.__rollpigEnterpriseUiReady = true;

  const root = document.documentElement;
  root.classList.add('enterprise-ui');
  root.dataset.uiVersion = '3.1';

  const STATUS_RULES = [
    {className: 'is-danger', pattern: /失败|错误|异常|损坏|不可用|未注册|需重启|等待重启|回滚/},
    {className: 'is-warning', pattern: /警告|等待|检查中|读取中|同步中|迁移中|验证中|重建中|导出中|安装中|处理中|正在|未配置/},
    {className: 'is-success', pattern: /成功|完成|正常|健康|已连接|已同步|可用|最新|通过/},
  ];

  const classifyStatus = node => {
    if (!(node instanceof HTMLElement)) return;
    const text = (node.textContent || '').trim();
    node.classList.remove('is-success', 'is-warning', 'is-danger', 'is-neutral');
    const match = STATUS_RULES.find(rule => rule.pattern.test(text));
    node.classList.add(match?.className || 'is-neutral');
  };

  const decorateStatusNodes = scope => {
    const nodes = [];
    if (scope instanceof HTMLElement && scope.matches('.pill,.sync-feedback,[role="status"]')) {
      nodes.push(scope);
    }
    scope.querySelectorAll?.('.pill,.sync-feedback,[role="status"]').forEach(node => nodes.push(node));
    nodes.forEach(classifyStatus);
  };

  const addSkipLink = () => {
    if (document.querySelector('.skip-link')) return;
    const link = document.createElement('a');
    link.className = 'skip-link';
    link.href = '#view-overview';
    link.textContent = '跳到主要内容';
    document.body.prepend(link);
  };

  const decorateStructure = () => {
    document.querySelectorAll('.sync-panel,.update-panel').forEach(panel => {
      panel.classList.add('operation-card');
    });

    const storagePanel = document.getElementById('storageStatus')?.closest('.update-panel');
    const updatePanel = document.getElementById('updateStatus')?.closest('.update-panel');
    storagePanel?.classList.add('operation-card--storage');
    updatePanel?.classList.add('operation-card--update');

    document.querySelectorAll('.metric').forEach(metric => {
      const label = metric.querySelector('.label')?.textContent?.trim();
      if (label) metric.setAttribute('aria-label', label);
    });

    document.querySelectorAll('.panel').forEach(panel => {
      if (!panel.hasAttribute('aria-label')) {
        const heading = panel.querySelector('h2');
        if (heading?.textContent?.trim()) panel.setAttribute('aria-label', heading.textContent.trim());
      }
    });

    const toast = document.getElementById('toast');
    if (toast) {
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.setAttribute('aria-atomic', 'true');
    }

    const loading = document.getElementById('loading');
    if (loading) {
      loading.setAttribute('role', 'status');
      loading.setAttribute('aria-live', 'polite');
      loading.setAttribute('aria-label', '正在处理，请稍候');
    }

    document.querySelectorAll('.sync-feedback').forEach(node => {
      node.setAttribute('aria-live', 'polite');
      node.setAttribute('aria-atomic', 'true');
    });

    document.querySelectorAll('.modal').forEach(modal => {
      modal.setAttribute('aria-hidden', modal.classList.contains('open') ? 'false' : 'true');
      const dialog = modal.querySelector('.dialog');
      if (dialog) {
        dialog.setAttribute('role', 'dialog');
        dialog.setAttribute('aria-modal', 'true');
        const heading = dialog.querySelector('h2');
        if (heading?.id) dialog.setAttribute('aria-labelledby', heading.id);
        else if (heading?.textContent?.trim()) dialog.setAttribute('aria-label', heading.textContent.trim());
      }
    });

    document.querySelectorAll('button').forEach(button => {
      if (!button.hasAttribute('type') && !button.closest('form')) button.type = 'button';
    });

    decorateStatusNodes(document);
  };

  let lastFocused = null;
  const syncModalState = modal => {
    if (!(modal instanceof HTMLElement) || !modal.classList.contains('modal')) return;
    const isOpen = modal.classList.contains('open');
    modal.setAttribute('aria-hidden', isOpen ? 'false' : 'true');

    if (isOpen) {
      lastFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      requestAnimationFrame(() => {
        const target = modal.querySelector(
          '[autofocus],button:not(:disabled),input:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])'
        );
        target?.focus({preventScroll: true});
      });
    } else if (lastFocused?.isConnected) {
      lastFocused.focus({preventScroll: true});
      lastFocused = null;
    }
  };

  const syncBusyState = () => {
    if (!document?.body) return;
    const busy = Boolean(document.querySelector('[aria-busy="true"],.loading.show'));
    document.body.classList.toggle('has-busy-operation', busy);
  };

  window.__rollpigEnterpriseUiRefresh = () => {
    if (!document?.body) return;
    addSkipLink();
    decorateStructure();
    syncBusyState();
  };
  window.__rollpigEnterpriseUiRefresh();
  window.addEventListener('pagehide', () => {
    observer.disconnect();
    window.__rollpigEnterpriseUiReady = false;
    window.__rollpigEnterpriseUiRefresh = null;
  }, {once: true});

  const observer = new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'childList') {
        record.addedNodes.forEach(node => {
          if (node instanceof HTMLElement) {
            decorateStatusNodes(node);
            if (node.matches('.modal')) syncModalState(node);
          }
        });
        if (record.target instanceof HTMLElement) classifyStatus(record.target);
      }

      if (record.type === 'attributes' && record.target instanceof HTMLElement) {
        if (record.attributeName === 'class') {
          if (record.target.matches('.modal')) syncModalState(record.target);
          if (record.target.matches('.pill,.sync-feedback,[role="status"]')) classifyStatus(record.target);
        }
        if (record.attributeName === 'aria-busy') syncBusyState();
      }
    }
    syncBusyState();
  });

  observer.observe(document.body, {
    subtree: true,
    childList: true,
    characterData: true,
    attributes: true,
    attributeFilter: ['class', 'aria-busy'],
  });
})();
