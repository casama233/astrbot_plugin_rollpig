(() => {
  'use strict';
  const VERSION = '3.1.1';
  const pageRoot = document.querySelector('.shell');
  if (!pageRoot || pageRoot.dataset.rollpigEnterprise === VERSION) return;
  pageRoot.dataset.rollpigEnterprise = VERSION;
  document.documentElement.classList.add('enterprise-ui');
  document.documentElement.dataset.uiVersion = VERSION;

  pageRoot.querySelectorAll('.sync-panel,.update-panel').forEach(panel => {
    panel.classList.add('operation-card');
  });
  pageRoot.querySelectorAll('.metric').forEach(metric => {
    const label = metric.querySelector('.label')?.textContent?.trim();
    if (label) metric.setAttribute('aria-label', label);
  });
  pageRoot.querySelectorAll('.sync-feedback,[role="status"]').forEach(node => {
    node.setAttribute('aria-live', 'polite');
    node.setAttribute('aria-atomic', 'true');
  });
})();
