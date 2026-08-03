(() => {
  const THEME_MARKER = 'data-rollpig-enterprise-theme';

  if (!document.querySelector(`link[${THEME_MARKER}]`)) {
    const theme = document.createElement('link');
    theme.rel = 'stylesheet';
    theme.href = './enterprise-theme.css';
    theme.setAttribute(THEME_MARKER, '');
    document.head.appendChild(theme);
  }

  if (document.readyState === 'loading') {
    document.write(
      '<script src="./ui-feedback-core.js"><\/script>' +
      '<script src="./ui-enterprise.js"><\/script>'
    );
    return;
  }

  const loadScript = src => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`无法载入管理页脚本：${src}`));
    document.head.appendChild(script);
  });

  loadScript('./ui-feedback-core.js')
    .then(() => loadScript('./ui-enterprise.js'))
    .catch(error => console.error('[rollpig] UI bootstrap failed', error));
})();
