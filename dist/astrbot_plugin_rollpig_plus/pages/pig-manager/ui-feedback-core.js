(() => {
  'use strict';
  const VERSION = '3.1.1';
  const pageRoot = document.querySelector('.shell');
  if (!pageRoot || pageRoot.dataset.rollpigFeedback === VERSION) return;
  pageRoot.dataset.rollpigFeedback = VERSION;

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
})();
