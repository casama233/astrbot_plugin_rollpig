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
    if (first?.status === 'error') throw new Error(first.message || "操作未生效");
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
      local: "本地 EX 差分",
      'local-base-block': "本地基础覆写（未套用公共 EX）",
      cloud: "云端 EX 差分", bundled: "内置 EX 差分", baseline: "安全保底配置", base: "默认基础设定"
    })[source] || source || "默认基础设定";
  }

  function imageSourceLabel(source) {
    return ({
      local: "本地 EX 立绘", cloud: "云端 EX 立绘", bundled: "内置 EX 立绘",
      baseline: "安全保底立绘", base: "默认基础立绘", pending: "未存档的本地立绘"
    })[source] || source || "默认基础立绘";
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
          <div><div class="eyebrow">EX 焕装工坊</div><h2 id="exManagerTitle">配置 EX 形态 1–5</h2></div>
          <button class="close" type="button" id="exManagerClose" aria-label="关闭">×</button>
        </div>
        <div id="exManagerBody"><div class="empty">正在同步 EX 进阶阶段…</div></div>
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

    const make = (tag, className = '', text = '') => {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== '') node.textContent = text;
      return node;
    };
    const dataAttr = (node, name) => node.setAttribute(`data-${name}`, '');
    body.replaceChildren();

    if (!pig) {
      body.append(make('div', 'empty', "这只猪猪还没录入当前图鉴，暂时无法定制本地 EX 差分。"));
      return;
    }

    const local = localLevel(pig, state.level);
    const localCount = [1,2,3,4,5].filter(level => levelHasLocal(pig, level)).length;

    const head = make('div', 'ex-manager-head');
    const identity = make('div');
    identity.append(make('h2', '', pig.name || "无名小猪仔"));
    identity.append(make('div', 'ex-manager-id', pig.id || ''));
    const base = make('div', 'ex-manager-base');
    base.append(make('b', '', "基础简介："));
    base.append(document.createTextNode(pig.description || '—'));
    base.append(document.createElement('br'));
    base.append(make('b', '', "基础完整档案："));
    base.append(document.createTextNode(pig.analysis || '—'));
    identity.append(base);

    const badges = make('div', 'ex-manager-badges');
    badges.append(make('span', `ex-manager-badge${localCount ? ' local' : ''}`, localCount ? `已配 ${localCount} 层本地 EX` : "暂无本地 EX 差分"));
    badges.append(make('span', 'ex-manager-badge', pig.base_overridden ? "基础档案已启用本地覆写" : "基础档案同步自当前图鉴"));
    head.append(identity, badges);

    const tabs = make('div', 'ex-level-tabs');
    tabs.setAttribute('role', 'tablist');
    tabs.setAttribute('aria-label', "EX 阶数");
    [1,2,3,4,5].forEach(level => {
      const active = level === state.level;
      const hasLocal = levelHasLocal(pig, level);
      const button = make('button', `ex-level-tab${active ? ' active' : ''}${hasLocal ? ' has-local' : ''}`, `Lv.${level}`);
      button.type = 'button';
      button.dataset.exLevel = String(level);
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-selected', String(active));
      button.append(document.createElement('i'));
      tabs.append(button);
    });

    const card = make('article', 'ex-level-card');
    const title = make('div', 'ex-level-title');
    title.append(make('strong', '', `EX Lv.${state.level}`));
    title.append(make('span', '', levelHasLocal(pig, state.level) ? "已启用本地差分" : "留空即沿用上一阶／官方原设"));
    card.append(title);

    const editor = make('div', 'ex-editor-grid');
    const descriptionField = make('div', 'ex-field');
    descriptionField.append(make('label', '', "简短介绍"));
    const description = make('textarea');
    description.id = 'exDescription';
    description.maxLength = 120;
    description.placeholder = "留空即沿用";
    description.value = local.description || '';
    descriptionField.append(description, make('small', '', "仅替换当前 EX 阶数的简短介绍。"));

    const imageField = make('div', 'ex-field');
    imageField.append(make('label', '', "差分立绘"));
    const imageRow = make('div', 'ex-image-row');
    const fileInput = make('input');
    fileInput.id = 'exImageFile';
    fileInput.type = 'file';
    fileInput.accept = 'image/png,image/jpeg,image/webp,image/gif';
    const removeLabel = make('label');
    const removeInput = make('input');
    removeInput.id = 'exRemoveImage';
    removeInput.type = 'checkbox';
    removeInput.disabled = !local.image;
    removeLabel.append(removeInput, document.createTextNode(" 撤下当前立绘"));
    imageRow.append(fileInput, removeLabel);
    imageField.append(imageRow);
    imageField.append(make('small', '', local.image ? `当前来源：${local.image}；下方展示实际生效立绘` : "暂未上传本地差分立绘；下方展示继承／基础立绘。"));

    const analysisField = make('div', 'ex-field full');
    analysisField.append(make('label', '', "完整档案文案"));
    const analysis = make('textarea', 'ex-analysis');
    analysis.id = 'exAnalysis';
    analysis.maxLength = 800;
    analysis.placeholder = "留空即沿用";
    analysis.value = local.analysis || '';
    analysisField.append(analysis, make('small', '', "EX 仅赋予猪猪新外观与文案，不会改变猪猪编号、抽中概率、保底机制或任何玩法属性。"));
    editor.append(descriptionField, imageField, analysisField);
    card.append(editor);

    const effectiveWrap = make('div', 'ex-effective');
    const previewHead = make('div', 'ex-preview-head');
    const previewTitle = make('div');
    previewTitle.append(make('strong', '', "群聊卡片实装预览"));
    previewTitle.append(make('span', '', "当前实际生效效果；支持展开 Base ↔ EX 双形态对照"));
    const compareToggle = make('button', 'ex-preview-toggle', "Base ↔ EX 形态对照");
    compareToggle.type = 'button';
    dataAttr(compareToggle, 'compare-toggle');
    previewHead.append(previewTitle, compareToggle);

    const stage = make('div', 'ex-preview-stage');
    dataAttr(stage, 'preview-stage');
    const effectiveCard = make('article', 'ex-preview-card ex-preview-card-effective');
    const effectiveZoom = make('button', 'ex-preview-rendered');
    effectiveZoom.type = 'button';
    effectiveZoom.disabled = true;
    dataAttr(effectiveZoom, 'effective-zoom');
    const effectiveImage = make('img');
    effectiveImage.alt = "群聊实发 EX 卡片";
    dataAttr(effectiveImage, 'effective-card-image');
    const effectivePlaceholder = make('span', 'ex-preview-placeholder', "正在渲染群聊实发卡片…");
    dataAttr(effectivePlaceholder, 'effective-placeholder');
    effectiveZoom.append(effectiveImage, effectivePlaceholder);
    const effectiveMeta = make('div', 'ex-preview-runtime-meta');
    const effectiveMetaText = make('span', '', "实发渲染器 · 正在绘卡");
    dataAttr(effectiveMetaText, 'effective-card-meta');
    effectiveMeta.append(effectiveMetaText);
    effectiveCard.append(effectiveZoom, effectiveMeta);

    const baseCard = make('article', 'ex-preview-card ex-preview-card-base');
    dataAttr(baseCard, 'base-card');
    baseCard.hidden = true;
    const baseZoom = make('button', 'ex-preview-rendered');
    baseZoom.type = 'button';
    baseZoom.disabled = true;
    dataAttr(baseZoom, 'base-zoom');
    const baseImage = make('img');
    baseImage.alt = "群聊实发 Base 原版卡片";
    dataAttr(baseImage, 'base-card-image');
    const basePlaceholder = make('span', 'ex-preview-placeholder', "正在渲染 Base 原版卡片…");
    dataAttr(basePlaceholder, 'base-placeholder');
    baseZoom.append(baseImage, basePlaceholder);
    const baseMeta = make('div', 'ex-preview-runtime-meta');
    const baseMetaText = make('span', '', "Base 原版 · 实发渲染器");
    dataAttr(baseMetaText, 'base-card-meta');
    baseMeta.append(baseMetaText);
    baseCard.append(baseZoom, baseMeta);
    stage.append(effectiveCard, baseCard);
    effectiveWrap.append(previewHead, stage);
    card.append(effectiveWrap);

    const actions = make('div', 'ex-level-actions');
    const reset = make('button', 'btn ghost', "清空本阶配置");
    reset.type = 'button';
    reset.id = 'exResetLevel';
    const save = make('button', 'btn', `保存 EX Lv.${state.level}`);
    save.type = 'button';
    save.id = 'exSaveLevel';
    actions.append(reset, save);
    card.append(actions);

    body.append(head, tabs, card);

    body.querySelectorAll('[data-ex-level]').forEach(button => {
      button.onclick = () => { state.level = Number(button.dataset.exLevel); renderModal(); };
    });
    $('exSaveLevel').onclick = saveCurrentLevel;
    $('exResetLevel').onclick = resetCurrentLevel;
    bindPreviewControls(card, pig);
    loadEffectiveCard(card, pig);
    fileInput.onchange = async () => {
      try {
        const dataUrl = await fileData(fileInput);
        if (!dataUrl) {
          await loadEffectiveCard(card, pig);
          return;
        }
        removeInput.checked = false;
        markPreviewPending(card, fileInput.files?.[0]?.name || "新立绘");
      } catch (error) {
        fileInput.value = '';
        toast(error.message || String(error));
        await loadEffectiveCard(card, pig, {silent: false});
      }
    };
    removeInput.onchange = async () => {
      if (removeInput.checked) {
        fileInput.value = '';
        markPreviewPending(card, "撤下立绘");
      } else {
        await loadEffectiveCard(card, pig, {silent: false});
      }
    };
    [description, analysis].forEach(field => {
      field.addEventListener('input', () => markPreviewPending(card, "文案调整"));
    });
  }

  async function fileData(input) {
    const file = input?.files?.[0];
    if (!file) return '';
    if (file.size > 10 * 1024 * 1024) throw new Error("图片体积超标啦，请控制在 10MB 以内");
    return await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error("图片加载异常，读取失败"));
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
      toast(`已保存「${pig.name}」EX Lv.${state.level} 配置`);
    } catch (error) {
      toast(error.message || String(error));
    } finally {
      busy(false);
    }
  }

  async function resetCurrentLevel() {
    const pig = currentPig();
    if (!pig || !window.confirm(`确定要清空「${pig.name}」EX Lv.${state.level} 的全部本地差分并恢复默认吗？`)) return;
    busy(true);
    try {
      state.snapshot = await post('ex/variants/delete', {id: pig.id, level: state.level});
      renderModal();
      renderPublicSourceSummary(pig.id).catch(() => {});
      toast(`已还原「${pig.name}」EX Lv.${state.level} 配置`);
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
      placeholder.textContent = "群聊实发卡片渲染失败";
      zoom.disabled = true;
      delete zoom.dataset.zoomSrc;
    }
    const level = Number(variant_level || 0);
    meta.textContent = `实发渲染器 · ${sourceLabel(source)}${level ? ` · 差分 Lv.${level}` : ''}`;
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
      placeholder.textContent = "Base 原版卡片渲染失败";
      zoom.disabled = true;
      delete zoom.dataset.zoomSrc;
    }
    meta.textContent = "Base 原版 · 实发渲染器";
  }

  function markPreviewPending(card, detail = '') {
    const meta = card.querySelector('[data-effective-card-meta]');
    if (meta) meta.textContent = `检测到未保存的修改${detail ? ` · ${detail}` : ''}；点击保存后将同步刷新群聊实发样式`;
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
      toggle.textContent = opening ? "收起 Base 原版对照" : "基础形态 ↔ 觉醒 EX 对比";
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
    $('exManagerBody').innerHTML = "<div class=\"empty\">正在调取 EX 1–5 形态档案…</div>";
    busy(true);
    try {
      await loadSnapshot(true);
      state.pigId = id;
      state.level = 1;
      renderModal();
    } catch (error) {
      $('exManagerBody').innerHTML = `<div class="empty">EX 形态档案读取失败：${esc(error.message || error)}</div>`;
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
      button.textContent = "调教 EX 1–5";
      actions.insertBefore(button, actions.firstChild);
      button.onclick = () => {
        const id = String($('originalId')?.value || '').trim();
        if (!id) return toast("得先把基础小猪落户存档，才能解锁调教它的 EX 形态哦");
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
    root.innerHTML = "<strong>本实例生效 EX 1–5</strong><small>正在读取本实例实际生效的形态配置…</small>";
    try {
      const snapshot = await loadSnapshot(true);
      const pig = (snapshot.items || []).find(item => item.id === pigId);
      if (!pig) {
        root.innerHTML = "<strong>本实例生效 EX 1–5</strong><small>这只公共图鉴编号还没同步进本实例有效名册，先拉取一次资源就能开始管理啦。</small>";
        return;
      }
      root.innerHTML = `<strong>本实例生效 EX 1–5</strong><small>以下展示的是本实例实际生效的内容；若该小猪存在本地 EX 差分，会优先展示本地配置。</small><div class="public-source-ex-levels">${[1,2,3,4,5].map(level => {
        const item = effectiveLevel(pig, level);
        return `<div class="public-source-ex-level" title="${esc(item.description || '')}"><b>Lv.${level} · ${esc(sourceLabel(item.source))}</b><span>${esc(item.description || "（沿用基础设定）")}</span></div>`;
      }).join('')}</div>`;
    } catch (error) {
      root.innerHTML = `<strong>本实例生效 EX 1–5</strong><small>读取失败：${esc(error.message || error)}</small>`;
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
