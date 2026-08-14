(() => {
  const PIG_GLYPH = '🐷';
  const UI_SELECTOR = [
    '.pig-mascot',
    '.pig-kicker',
    '.pig-card__icon',
    '.pig-badge',
    '.pig-versus__label',
    '.md-nav__link',
    '.md-tabs__link',
    '.md-typeset h1',
    '.md-typeset h2',
    '.md-typeset h3',
    '.md-typeset h4',
    '.md-typeset .admonition-title',
    '.md-typeset summary'
  ].join(', ');

  function logoUrl() {
    const headerLogo = document.querySelector('.md-header__button.md-logo img');
    if (headerLogo?.src) return headerLogo.src;
    return new URL('assets/plugin-logo.png', document.baseURI).href;
  }

  function makeLogo(className = 'pig-brand-icon') {
    const image = document.createElement('img');
    image.className = className;
    image.src = logoUrl();
    image.alt = '';
    image.setAttribute('aria-hidden', 'true');
    image.decoding = 'async';
    return image;
  }

  function replaceGlyphsIn(element) {
    if (!element || element.closest('pre, code, textarea, input, script, style')) return;
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      if (walker.currentNode.nodeValue?.includes(PIG_GLYPH)) nodes.push(walker.currentNode);
    }

    nodes.forEach((node) => {
      const parts = node.nodeValue.split(PIG_GLYPH);
      const fragment = document.createDocumentFragment();
      parts.forEach((part, index) => {
        if (part) fragment.appendChild(document.createTextNode(part));
        if (index < parts.length - 1) fragment.appendChild(makeLogo());
      });
      node.replaceWith(fragment);
    });
  }

  function brandStaticPigIcons(root = document) {
    root.querySelectorAll?.(UI_SELECTOR).forEach(replaceGlyphsIn);
  }

  function brandSpark(node) {
    if (!(node instanceof HTMLElement) || !node.classList.contains('pig-spark')) return;
    if (node.textContent?.trim() !== PIG_GLYPH) return;
    node.textContent = '';
    node.appendChild(makeLogo());
  }

  function installSparkObserver() {
    if (document.documentElement.dataset.pigBrandObserver === '1') return;
    document.documentElement.dataset.pigBrandObserver = '1';
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof HTMLElement)) return;
          brandSpark(node);
          node.querySelectorAll?.('.pig-spark').forEach(brandSpark);
          brandStaticPigIcons(node);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function initPigBranding() {
    brandStaticPigIcons();
    document.querySelectorAll('.pig-spark').forEach(brandSpark);
    installSparkObserver();
  }

  if (typeof document$ !== 'undefined' && document$?.subscribe) {
    document$.subscribe(initPigBranding);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPigBranding, { once: true });
  } else {
    initPigBranding();
  }
})();
