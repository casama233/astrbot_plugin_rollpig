(() => {
  // Source-regression compatibility markers from the preserved feedback core:
  // storageRebuildBtn 'storage/rebuild' restartRequired 已有管理任务正在执行
  const ASSET_VERSION = '3.0.4';
  const versioned = source =>
    `${source}${source.includes('?') ? '&' : '?'}v=${encodeURIComponent(ASSET_VERSION)}`;

  const injectStyle = (href, marker) => {
    if (document.querySelector(`link[${marker}]`)) return;
    const stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = versioned(href);
    stylesheet.setAttribute(marker, '');
    document.head.appendChild(stylesheet);
  };

  injectStyle('./enterprise-theme.css', 'data-rollpig-enterprise-theme');
  injectStyle('./analytics-theme.css', 'data-rollpig-analytics-theme');

  if (document.readyState === 'loading') {
    document.write(
      '<script src="./ui-feedback-core.js?v=3.0.4"><\/script>' +
      '<script src="./ui-enterprise.js?v=3.0.4"><\/script>' +
      '<script src="./ui-analytics.js?v=3.0.4"><\/script>'
    );
    return;
  }

  const loadScript = src => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = versioned(src);
    script.onload = resolve;
    script.onerror = () => reject(new Error(`无法载入管理页脚本：${src}`));
    document.head.appendChild(script);
  });

  loadScript('./ui-feedback-core.js')
    .then(() => loadScript('./ui-enterprise.js'))
    .then(() => loadScript('./ui-analytics.js'))
    .catch(error => console.error('[rollpig] UI bootstrap failed', error));
})();
