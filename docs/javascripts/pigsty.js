(() => {
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;

  function setupSearchPlaceholder() {
    const input = document.querySelector('[data-md-component="search-query"] input, .md-search__input');
    if (input) {
      input.setAttribute('placeholder', '搜尋一隻豬、一條指令，或者「怎麼烤群友」…');
      input.setAttribute('aria-label', '搜尋今日小豬 Wiki');
    }
  }

  function setupReveal() {
    const nodes = document.querySelectorAll('.pig-card, .pig-highlight, .pig-versus, .pig-step, .pig-charge-panel');
    if (!nodes.length) return;
    if (reduceMotion || !('IntersectionObserver' in window)) {
      nodes.forEach((node) => node.classList.add('is-visible'));
      return;
    }
    nodes.forEach((node) => node.classList.add('pig-reveal'));
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -36px 0px' });
    nodes.forEach((node) => observer.observe(node));
  }

  function setupTilt() {
    if (reduceMotion || !window.matchMedia?.('(pointer: fine)')?.matches) return;
    document.querySelectorAll('.pig-card').forEach((card) => {
      if (card.dataset.tiltReady === '1') return;
      card.dataset.tiltReady = '1';
      card.addEventListener('pointermove', (event) => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `perspective(760px) rotateX(${(-y * 4).toFixed(2)}deg) rotateY(${(x * 5).toFixed(2)}deg) translateY(-2px)`;
      });
      card.addEventListener('pointerleave', () => {
        card.style.transform = '';
      });
    });
  }

  function pigBurst(origin) {
    if (reduceMotion) return;
    const rect = origin.getBoundingClientRect();
    const glyphs = ['🐷', '✨', '🔥', '⭐', '🪵', '⚡'];
    for (let i = 0; i < 18; i += 1) {
      const spark = document.createElement('span');
      spark.className = 'pig-spark';
      spark.textContent = glyphs[Math.floor(Math.random() * glyphs.length)];
      spark.style.left = `${rect.left + rect.width / 2}px`;
      spark.style.top = `${rect.top + rect.height / 2}px`;
      spark.style.setProperty('--dx', `${(Math.random() - 0.5) * 260}px`);
      spark.style.setProperty('--dy', `${-50 - Math.random() * 210}px`);
      spark.style.setProperty('--rot', `${(Math.random() - 0.5) * 420}deg`);
      document.body.appendChild(spark);
      window.setTimeout(() => spark.remove(), 950);
    }
  }

  function setupMascot() {
    document.querySelectorAll('.pig-mascot').forEach((mascot) => {
      if (mascot.dataset.pigReady === '1') return;
      mascot.dataset.pigReady = '1';
      mascot.setAttribute('role', 'button');
      mascot.setAttribute('tabindex', '0');
      mascot.setAttribute('aria-label', '戳一下小豬');
      const trigger = () => pigBurst(mascot);
      mascot.addEventListener('click', trigger);
      mascot.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          trigger();
        }
      });
    });
  }

  function setupAmbient() {
    if (reduceMotion || document.querySelector('.pig-ambient')) return;
    const layer = document.createElement('div');
    layer.className = 'pig-ambient';
    layer.setAttribute('aria-hidden', 'true');
    for (let i = 0; i < 24; i += 1) {
      const dot = document.createElement('i');
      dot.style.left = `${Math.random() * 100}%`;
      dot.style.top = `${Math.random() * 100}%`;
      dot.style.setProperty('--dur', `${14 + Math.random() * 18}s`);
      dot.style.setProperty('--drift', `${-50 + Math.random() * 100}px`);
      dot.style.animationDelay = `${-Math.random() * 18}s`;
      layer.appendChild(dot);
    }
    document.body.appendChild(layer);
  }

  function setupChargeMeters() {
    document.querySelectorAll('[data-charge-demo]').forEach((meter) => {
      if (meter.dataset.chargeReady === '1') return;
      meter.dataset.chargeReady = '1';
      if (reduceMotion) return;
      const cells = [...meter.querySelectorAll('.pig-charge-cell')];
      if (!cells.length) return;
      let full = cells.length;
      window.setInterval(() => {
        full = full <= 0 ? cells.length : full - 1;
        cells.forEach((cell, index) => cell.classList.toggle('is-full', index < full));
      }, 2200);
    });
  }

  function initPigstyWiki() {
    setupSearchPlaceholder();
    setupReveal();
    setupTilt();
    setupMascot();
    setupAmbient();
    setupChargeMeters();
  }

  if (typeof document$ !== 'undefined' && document$?.subscribe) {
    document$.subscribe(initPigstyWiki);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPigstyWiki, { once: true });
  } else {
    initPigstyWiki();
  }
})();
