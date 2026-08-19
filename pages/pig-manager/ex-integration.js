(() => {
  'use strict';

  const bridge = window.AstrBotPluginPage;
  if (!bridge) return;

  const state = {csrf: '', snapshot: null, pigId: '', level: 1, ready: null};
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
  const unwrap = response => {
    const first = response?.data ?? response;
    if (first?.status === 'error') throw new Error(first.message || '操作失败');
    return first?.data ?? first;
  };
  const toast = message => {
    const node = $('toast');
    if (!node) return;
    node.textContent = message;
    node.classList.add('show');
    window.setTimeout(() => node.classList.remove('show'), 2600);
  };
  const busy = value => $('loading')?.classList.toggle('show', Boolean(value));
  const post = async (path, payload = {}) => unwrap(await bridge.apiPost(path, {...payload, __rollpig_csrf: state.csrf}));
  const get = async (path, params = {}) => unwrap(await bridge.apiGet(path, params));

  async function ensureReady() {
    if (state.ready) return state.ready;
    state.ready = (async () => {
      if (typeof bridge.ready === 'function') await bridge.ready();
      const overview = await get('overview');
      state.csrf = String(overview?.csrf_token || '');
      return true;
    })().catch(error => {
      state.ready = null;
      throw error;
    });
    return state.ready;
  }

  async function loadSnapshot(force = false) {
    await ensureReady();
    if (!state.snapshot || force) state.snapshot = await get('ex/variants');
    return state.snapshot;
  }

  function sourceLabel(source) {
    return ({
      local: '本地 EX',
      'local-base-block': '本地基础覆盖（未套公共 EX）',
      cloud: '云端 EX', bundled: '内置 EX', baseline: '安全基线', base: '基础内容'
    })[source] || source || '基础内容';
  }

  function imageSourceLabel(source) {
    return ({
      local: '本地 EX 图片', cloud: '云端 EX 图片', bundled: '内置 EX 图片',
      baseline: '安全基线图片', base: '基础图片', pending: '未保存本地图片'
    })[source] || source || '基础图片';
  }

  function ensurePreviewLightbox() {
    let lightbox = $('exPreviewLightbox');
    if (lightbox) return lightbox;
    lightbox = document.createElement('div');
    lightbox.id = 'exPreviewLightbox';
    lightbox.className = 'ex-preview-lightbox';
    lightbox.setAttribute('aria-hidden', 'true');
    lightbox.innerHTML = `<div class="ex-preview-lightbox-card"><button class="ex-preview-lightbox-close" id="exPreviewLightboxClose" type="button" aria-label="关闭">×</button><img id="exPreviewLightboxImage" alt="EX 图片放大预览"><div class="ex-preview-lightbox-caption" id="exPreviewLightboxCaption"></div></div>`;
    document.body.appendChild(lightbox);
    $('exPreviewLightboxClose').onclick = closePreviewLightbox;
    lightbox.addEventListener('click', event => { if (event.target === lightbox) closePreviewLightbox(); });
    return lightbox;
  }

  function openPreviewLightbox(src, caption = '') {
    if (!src) return;
    ensurePreviewLightbox();
    $('exPreviewLightboxImage').src = src;
    $('exPreviewLightboxCaption').textContent = caption;
    $('exPreviewLightbox').classList.add('show');
    $('exPreviewLightbox').setAttribute('aria-hidden', 'false');
  }

  function closePreviewLightbox() {
    const lightbox = $('exPreviewLightbox');
    if (!lightbox) return;
    lightbox.classList.remove('show');
    lightbox.setAttribute('aria-hidden', 'true');
    $('exPreviewLightboxImage')?.removeAttribute('src');
  }

  function ensureModal() {
    let modal = $('exManagerModal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'exManagerModal';
    modal.className = 'modal ex-manager-modal';
    modal.innerHTML = `
      <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="exManagerTitle">
        <div class="dialog-head">
          <div><div class="eyebrow">EX Growth Studio</div><h2 id="exManagerTitle">管理 EX 1–5</h2></div>
          <button class="close" type="button" id="exManagerClose" aria-label="关闭">×</button>
        </div>
        <div id="exManagerBody"><div class="empty">正在读取 EX 阶段…</div></div>
      </div>`;
    document.body.appendChild(modal);
    ensurePreviewLightbox();
    $('exManagerClose').onclick = closeExManager;
    modal.addEventListener('click', event => { if (event.target === modal) closeExManager(); });
    return modal;
  }

  function closeExManager() {
    closePreviewLightbox();
    $('exManagerModal')?.classList.remove('open');
  }

  function currentPig() {
    return (state.snapshot?.items || []).find(item => item.id === state.pigId) || null;
  }

  function localLevel(pig, level) {
    return pig?.local_levels?.[String(level)] || {};
  }

  function effectiveLevel(pig, level) {
    return (pig?.effective || []).find(item => Number(item.level) === Number(level)) || {};
  }

  function levelHasLocal(pig, level) {
    const item = localLevel(pig, level);
    return Boolean(item.description || item.analysis || item.image);
  }

  function renderModal() {
    const pig = currentPig();
    const body = $('exManagerBody');
    if (!body) return;
    if (!pig) {
      body.innerHTML = '<div class="empty">这只小猪不在当前实例的有效图鉴中，无法建立本地 EX 差分。</div>';
      return;
    }
    const local = localLevel(pig, state.level);
    const effective = effectiveLevel(pig, state.level);
    const localCount = [1,2,3,4,5].filter(level => levelHasLocal(pig, level)).length;
    body.innerHTML = `
      <div class="ex-manager-head">
        <div><h2>${esc(pig.name)}</h2><div class="ex-manager-id">${esc(pig.id)}</div>
          <div class="ex-manager-base"><b>基础描述：</b>${esc(pig.description || '—')}<br><b>基础完整文案：</b>${esc(pig.analysis || '—')}</div>
        </div>
        <div class="ex-manager-badges">
          <span class="ex-manager-badge ${localCount ? 'local' : ''}">${localCount ? `${localCount} 层本地 EX` : '尚无本地 EX'}</span>
          ${pig.base_overridden ? '<span class="ex-manager-badge">基础资料已有本地覆盖</span>' : '<span class="ex-manager-badge">基础资料来自当前图鉴</span>'}
        </div>
      </div>
      <div class="ex-level-tabs" role="tablist" aria-label="EX 等级">
        ${[1,2,3,4,5].map(level => `<button type="button" class="ex-level-tab ${level === state.level ? 'active' : ''} ${levelHasLocal(pig, level) ? 'has-local' : ''}" data-ex-level="${level}" role="tab" aria-selected="${level === state.level}">Lv.${level}<i></i></button>`).join('')}
      </div>
      <article class="ex-level-card">
        <div class="ex-level-title"><strong>EX Lv.${state.level}</strong><span>${levelHasLocal(pig, state.level) ? '已设置本地差分' : '留空＝继承上一层／官方内容'}</span></div>
        <div class="ex-editor-grid">
          <div class="ex-field"><label>短描述</label><textarea id="exDescription" maxlength="120" placeholder="留空＝继承">${esc(local.description || '')}</textarea><small>只覆盖这一层的短描述。</small></div>
          <div class="ex-field"><label>差分图片</label><div class="ex-image-row"><input id="exImageFile" type="file" accept="image/png,image/jpeg,image/webp,image/gif"><label><input id="exRemoveImage" type="checkbox" ${local.image ? '' : 'disabled'}> 移除当前图片</label></div><small>${local.image ? `当前：${esc(local.image)}；下方会显示真正生效图片` : '尚未设置本地差分图片；下方会显示继承／基础图片。'}</small></div>
          <div class="ex-field full"><label>完整文案</label><textarea class="ex-analysis" id="exAnalysis" maxlength="800" placeholder="留空＝继承">${esc(local.analysis || '')}</textarea><small>EX 只改变展示内容，不改变小猪 ID、抽取概率、保底或玩法身份。</small></div>
        </div>
        <div class="ex-effective">
          <div class="ex-preview-head"><div><strong>聊天卡效果预览</strong><span>当前实际生效内容；可展开 Base ↔ EX 对比</span></div><button class="ex-preview-toggle" type="button" data-compare-toggle>Base ↔ EX 对比</button></div>
          <div class="ex-preview-stage" data-preview-stage>
            <article class="ex-preview-card ex-preview-card-effective">
              <button class="ex-preview-rendered" type="button" data-effective-zoom disabled><img data-effective-card-image alt="真实发送的 EX 聊天卡"><span class="ex-preview-placeholder" data-effective-placeholder>正在生成真实发送卡片…</span></button>
              <div class="ex-preview-runtime-meta"><span data-effective-card-meta>真实发送 renderer · 正在生成</span></div>
            </article>
            <article class="ex-preview-card ex-preview-card-base" data-base-card hidden>
              <button class="ex-preview-rendered" type="button" data-base-zoom disabled><img data-base-card-image alt="真实发送的 Base 聊天卡"><span class="ex-preview-placeholder" data-base-placeholder>正在生成 Base 卡片…</span></button>
              <div class="ex-preview-runtime-meta"><span data-base-card-meta>Base · 真实发送 renderer</span></div>
            </article>
          </div>
        </div>
        <div class="ex-level-actions"><button class="btn ghost" type="button" id="exResetLevel">重置此层</button><button class="btn" type="button" id="exSaveLevel">保存 EX Lv.${state.level}</button></div>
      </article>`;

    body.querySelectorAll('[data-ex-level]').forEach(button => {
      button.onclick = () => { state.level = Number(button.dataset.exLevel); renderModal(); };
    });
    $('exSaveLevel').onclick = saveCurrentLevel;
    $('exResetLevel').onclick = resetCurrentLevel;
    const card = body.querySelector('.ex-level-card');
    if (card) {
      bindPreviewControls(card, pig);
      loadEffectiveCard(card, pig);
      const fileInput = $('exImageFile');
      const removeInput = $('exRemoveImage');
      fileInput.onchange = async () => {
        try {
          const dataUrl = await fileData(fileInput);
          if (!dataUrl) {
            await loadEffectiveCard(card, pig);
            return;
          }
          if (removeInput) removeInput.checked = false;
          markPreviewPending(card, fileInput.files?.[0]?.name || '新图片');
        } catch (error) {
          fileInput.value = '';
          toast(error.message || String(error));
          await loadEffectiveCard(card, pig, {silent: false});
        }
      };
      if (removeInput) removeInput.onchange = async () => {
        if (removeInput.checked) {
          fileInput.value = '';
          markPreviewPending(card, '移除图片');
        } else {
          await loadEffectiveCard(card, pig, {silent: false});
        }
      };
      ['exDescription', 'exAnalysis'].forEach(id => {
        const field = $(id);
        if (field) field.addEventListener('input', () => markPreviewPending(card, '文案修改'));
      });
    }
  }

  async function fileData(input) {
    const file = input?.files?.[0];
    if (!file) return '';
    if (file.size > 10 * 1024 * 1024) throw new Error('图片不能超过 10MB');
    return await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('读取图片失败'));
      reader.readAsDataURL(file);
    });
  }

  async function saveCurrentLevel() {
    const pig = currentPig();
    if (!pig) return;
    busy(true);
    try {
      const image = await fileData($('exImageFile'));
      state.snapshot = await post('ex/variants/save', {
        id: pig.id,
        level: state.level,
        description: $('exDescription').value,
        analysis: $('exAnalysis').value,
        image,
        remove_image: Boolean($('exRemoveImage')?.checked),
      });
      renderModal();
      renderPublicSourceSummary(pig.id).catch(() => {});
      toast(`已保存 ${pig.name} EX Lv.${state.level}`);
    } catch (error) {
      toast(error.message || String(error));
    } finally {
      busy(false);
    }
  }

  async function resetCurrentLevel() {
    const pig = currentPig();
    if (!pig || !window.confirm(`重置「${pig.name}」EX Lv.${state.level} 的全部本地差分吗？`)) return;
    busy(true);
    try {
      state.snapshot = await post('ex/variants/delete', {id: pig.id, level: state.level});
      renderModal();
      renderPublicSourceSummary(pig.id).catch(() => {});
      toast(`已重置 ${pig.name} EX Lv.${state.level}`);
    } catch (error) {
      toast(error.message || String(error));
    } finally {
      busy(false);
    }
  }

  function setEffectiveCard(card, {src = '', source = 'base', variant_level = 0} = {}) {
    const image = card.querySelector('[data-effective-card-image]');
    const placeholder = card.querySelector('[data-effective-placeholder]');
    const meta = card.querySelector('[data-effective-card-meta]');
    const zoom = card.querySelector('[data-effective-zoom]');
    if (src) {
      image.src = src;
      image.classList.add('show');
      placeholder.hidden = true;
      zoom.disabled = false;
      zoom.dataset.zoomSrc = src;
    } else {
      image.removeAttribute('src');
      image.classList.remove('show');
      placeholder.hidden = false;
      placeholder.textContent = '真实发送卡片生成失败';
      zoom.disabled = true;
      delete zoom.dataset.zoomSrc;
    }
    const level = Number(variant_level || 0);
    meta.textContent = `真实发送 renderer · ${sourceLabel(source)}${level ? ` · 差分 Lv.${level}` : ''}`;
    card.classList.remove('preview-pending');
  }

  function setBaseCard(card, {src = ''} = {}) {
    const image = card.querySelector('[data-base-card-image]');
    const placeholder = card.querySelector('[data-base-placeholder]');
    const meta = card.querySelector('[data-base-card-meta]');
    const zoom = card.querySelector('[data-base-zoom]');
    if (src) {
      image.src = src;
      image.classList.add('show');
      placeholder.hidden = true;
      zoom.disabled = false;
      zoom.dataset.zoomSrc = src;
    } else {
      image.removeAttribute('src');
      image.classList.remove('show');
      placeholder.hidden = false;
      placeholder.textContent = 'Base 真实发送卡片生成失败';
      zoom.disabled = true;
      delete zoom.dataset.zoomSrc;
    }
    meta.textContent = 'Base · 真实发送 renderer';
  }

  function markPreviewPending(card, detail = '') {
    const meta = card.querySelector('[data-effective-card-meta]');
    if (meta) meta.textContent = `有未保存修改${detail ? ` · ${detail}` : ''}；保存后按真实发送样式重新生成`;
    card.classList.add('preview-pending');
  }

  async function loadEffectiveCard(card, pig, {silent = true} = {}) {
    try {
      const data = await post('ex/variants/card', {id: pig.id, level: state.level, effective: true});
      setEffectiveCard(card, {...data, src: `data:${data.mime_type || 'image/png'};base64,${data.base64 || ''}`});
    } catch (error) {
      setEffectiveCard(card, {src: '', source: 'base'});
      if (!silent) toast(error.message || String(error));
    }
  }

  async function loadBaseCard(card, pig) {
    if (card.dataset.baseLoaded === '1') return;
    try {
      const data = await post('ex/variants/card', {id: pig.id, level: state.level, base: true});
      setBaseCard(card, {...data, src: `data:${data.mime_type || 'image/png'};base64,${data.base64 || ''}`});
      card.dataset.baseLoaded = '1';
    } catch (error) {
      setBaseCard(card, {src: ''});
      toast(error.message || String(error));
    }
  }

  function bindPreviewControls(card, pig) {
    const toggle = card.querySelector('[data-compare-toggle]');
    const stage = card.querySelector('[data-preview-stage]');
    const baseCard = card.querySelector('[data-base-card]');
    const effectiveZoom = card.querySelector('[data-effective-zoom]');
    const baseZoom = card.querySelector('[data-base-zoom]');
    toggle.onclick = async () => {
      const opening = baseCard.hidden;
      baseCard.hidden = !opening;
      stage.classList.toggle('comparing', opening);
      toggle.classList.toggle('active', opening);
      toggle.textContent = opening ? '收起 Base 对比' : 'Base ↔ EX 对比';
      if (opening) await loadBaseCard(card, pig);
    };
    effectiveZoom.onclick = () => openPreviewLightbox(effectiveZoom.dataset.zoomSrc || '', `${pig.name} · EX Lv.${state.level}`);
    baseZoom.onclick = () => openPreviewLightbox(baseZoom.dataset.zoomSrc || '', `${pig.name} · Base`);
  }

  async function openExManager(pigId) {
    const id = String(pigId || '').trim();
    if (!id) return;
    const modal = ensureModal();
    modal.classList.add('open');
    $('exManagerBody').innerHTML = '<div class="empty">正在读取 EX 1–5 阶段…</div>';
    busy(true);
    try {
      await loadSnapshot(true);
      state.pigId = id;
      state.level = 1;
      renderModal();
    } catch (error) {
      $('exManagerBody').innerHTML = `<div class="empty">EX 数据读取失败：${esc(error.message || error)}</div>`;
    } finally {
      busy(false);
    }
  }
  window.__rollpigOpenExManager = openExManager;

  function installEditModalEntry() {
    const actions = $('saveBtn')?.closest('.dialog-actions');
    if (!actions) return;
    let button = $('editExBtn');
    if (!button) {
      button = document.createElement('button');
      button.id = 'editExBtn';
      button.type = 'button';
      button.className = 'btn ghost ex-entry';
      button.textContent = '管理 EX 1–5';
      actions.insertBefore(button, actions.firstChild);
      button.onclick = () => {
        const id = String($('originalId')?.value || '').trim();
        if (!id) return toast('请先保存基础小猪，再管理 EX 阶段');
        openExManager(id);
      };
    }
    const editing = Boolean(String($('originalId')?.value || '').trim());
    button.hidden = !editing;
  }

  async function renderPublicSourceSummary(pigId) {
    const root = $('publicSourceExSummary');
    if (!root) return;
    root.className = 'public-source-ex-summary';
    root.innerHTML = '<strong>当前实例 EX 1–5</strong><small>正在读取当前实例实际生效阶段…</small>';
    try {
      const snapshot = await loadSnapshot(true);
      const pig = (snapshot.items || []).find(item => item.id === pigId);
      if (!pig) {
        root.innerHTML = '<strong>当前实例 EX 1–5</strong><small>这个公共源 ID 尚未出现在当前实例的有效图鉴中；同步资源后即可管理。</small>';
        return;
      }
      root.innerHTML = `<strong>当前实例 EX 1–5</strong><small>以下为当前实例实际生效内容；若存在本地差分，会优先显示本地结果。</small><div class="public-source-ex-levels">${[1,2,3,4,5].map(level => {
        const item = effectiveLevel(pig, level);
        return `<div class="public-source-ex-level" title="${esc(item.description || '')}"><b>Lv.${level} · ${esc(sourceLabel(item.source))}</b><span>${esc(item.description || '（继承基础）')}</span></div>`;
      }).join('')}</div>`;
    } catch (error) {
      root.innerHTML = `<strong>当前实例 EX 1–5</strong><small>读取失败：${esc(error.message || error)}</small>`;
    }
  }

  function currentPublicSourceId() {
    return String($('publicSourceDetailId')?.textContent || '').trim();
  }

  function locatePublicPigLocally() {
    const id = currentPublicSourceId();
    if (!id) return;
    $('publicSourceDetailModal')?.classList.remove('open');
    const route = document.querySelector('[data-route="catalog"]');
    route?.click();
    const search = $('searchInput');
    if (search) {
      search.value = id;
      search.dispatchEvent(new Event('input', {bubbles: true}));
      window.setTimeout(() => search.scrollIntoView({behavior: 'smooth', block: 'center'}), 320);
    }
  }

  function bindStaticActions() {
    $('publicSourceManageEx')?.addEventListener('click', () => openExManager(currentPublicSourceId()));
    $('publicSourceLocateLocal')?.addEventListener('click', locatePublicPigLocally);
  }

  document.addEventListener('click', event => {
    const exButton = event.target.closest('[data-ex-manager]');
    if (exButton) {
      event.preventDefault();
      event.stopPropagation();
      openExManager(exButton.dataset.exManager);
      return;
    }
    if (event.target.closest('[data-edit],[data-layer-edit]')) {
      window.setTimeout(installEditModalEntry, 0);
    }
    if (event.target.closest('#addBtn')) {
      window.setTimeout(installEditModalEntry, 0);
    }
    if (event.target.closest('[data-public-source-card]')) {
      window.setTimeout(() => {
        const id = currentPublicSourceId();
        if (id) renderPublicSourceSummary(id);
      }, 0);
    }
  });

  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if ($('exPreviewLightbox')?.classList.contains('show')) {
      closePreviewLightbox();
      return;
    }
    closeExManager();
  });

  ensureReady().then(() => bindStaticActions()).catch(error => console.warn('[rollpig] EX integration init failed', error));
})();
