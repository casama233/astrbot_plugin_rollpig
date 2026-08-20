(() => {
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;

  function setupPityLab() {
    document.querySelectorAll('[data-pity-lab]').forEach((lab) => {
      if (lab.dataset.ready === '1') return;
      lab.dataset.ready = '1';

      const legacyInput = lab.querySelector('[data-pity-legacy]');
      const daysInput = lab.querySelector('[data-pity-days]');
      const legacyValue = lab.querySelector('[data-pity-legacy-value]');
      const daysValue = lab.querySelector('[data-pity-days-value]');
      const totalNode = lab.querySelector('[data-pity-total]');
      const breakdownNode = lab.querySelector('[data-pity-breakdown]');
      const gauge = lab.querySelector('[data-pity-gauge]');
      if (!legacyInput || !daysInput || !totalNode || !breakdownNode || !gauge) return;

      const update = () => {
        const legacy = Math.max(0, Number.parseInt(legacyInput.value, 10) || 0);
        const priorDays = Math.max(0, Number.parseInt(daysInput.value, 10) || 0);
        const base = legacy * 15;
        const currentDuplicateDay = priorDays + 1;
        const daily = currentDuplicateDay >= 2
          ? Math.min(15, (currentDuplicateDay - 1) * 5)
          : 0;
        const total = Math.min(80, base + daily);

        if (legacyValue) legacyValue.textContent = String(legacy);
        if (daysValue) daysValue.textContent = String(priorDays);
        totalNode.textContent = `${total}%`;
        breakdownNode.textContent = `${base}% 連續重複 + ${daily}% 跨日疲勞${base + daily > 80 ? ' → 80% 封頂' : ''}`;
        gauge.style.width = `${Math.min(100, total)}%`;
      };

      legacyInput.addEventListener('input', update);
      daysInput.addEventListener('input', update);
      update();
    });
  }

  function weightedRoastResult() {
    const roll = Math.random() * 100;
    if (roll < 70) {
      return { glyph: '🔥', label: '70%：燒烤成功', note: '目標成為這次真正 victim，記一次實際被烤。' };
    }
    if (roll < 90) {
      return { glyph: '💨', label: '20%：目標逃脫', note: '這次不增加目標的實際被烤次數。' };
    }
    return { glyph: '💥', label: '10%：烤架反噬', note: '如果主廚自己可料理，真正上桌的是主廚。' };
  }

  function setupRoastDemo() {
    document.querySelectorAll('[data-roast-demo]').forEach((demo) => {
      if (demo.dataset.ready === '1') return;
      demo.dataset.ready = '1';

      const button = demo.querySelector('[data-roast-fire]');
      const glyph = demo.querySelector('[data-roast-glyph]');
      const result = demo.querySelector('[data-roast-result]');
      const note = demo.querySelector('[data-roast-note]');
      const history = demo.querySelector('[data-roast-history]');
      if (!button || !glyph || !result || !note || !history) return;

      button.addEventListener('click', () => {
        const item = weightedRoastResult();
        if (!reduceMotion) {
          demo.classList.remove('is-fired');
          // Force a restart so repeated clicks still feel responsive.
          void demo.offsetWidth;
          demo.classList.add('is-fired');
        }
        glyph.textContent = item.glyph;
        result.textContent = item.label;
        note.textContent = item.note;

        const chip = document.createElement('span');
        chip.textContent = `${item.glyph} ${item.label.split('：')[1] || item.label}`;
        history.prepend(chip);
        while (history.children.length > 8) history.lastElementChild?.remove();
      });
    });
  }

  function initWikiV2() {
    setupPityLab();
    setupRoastDemo();
  }

  if (typeof document$ !== 'undefined' && document$?.subscribe) {
    document$.subscribe(initWikiV2);
  } else if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWikiV2, { once: true });
  } else {
    initWikiV2();
  }
})();
