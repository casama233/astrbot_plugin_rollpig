(() => {
  'use strict';

  const bridge = window.AstrBotPluginPage;
  const shell = document.querySelector('.shell');
  if (!bridge || !shell || window.__rollpigPigStudioInstalled) return;
  window.__rollpigPigStudioInstalled = true;

  const state = {
    csrf: '',
    ready: null,
    status: null,
    tasks: [],
    activeIndex: -1,
    busy: false,
  };

  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[char]);
  const unwrap = response => {
    const first = response?.data ?? response;
    if (first?.status === 'error') throw new Error(first.message || '操作失败');
    return first?.data ?? first;
  };
  const get = async (path, params = {}) => unwrap(await bridge.apiGet(path, params));
  const post = async (path, payload = {}) => unwrap(await bridge.apiPost(path, {
    ...payload,
    __rollpig_csrf: state.csrf,
  }));
  const toast = message => {
    const node = $('toast');
    if (!node) return;
    node.textContent = String(message || '');
    node.classList.add('show');
    window.setTimeout(() => node.classList.remove('show'), 2800);
  };

  function installStyles() {
    if (document.querySelector('style[data-rollpig-pig-studio]')) return;
    const style = document.createElement('style');
    style.dataset.rollpigPigStudio = '1';
    style.textContent = `
      .pig-studio-modal{z-index:90;padding:18px;align-items:flex-start;overflow:auto;background:color-mix(in srgb,#120c16 70%,transparent);backdrop-filter:blur(22px) saturate(120%)}
      .pig-studio-modal .dialog{width:min(1180px,calc(100vw - 36px));max-width:1180px;margin:18px auto 60px;padding:0;overflow:hidden;border:1px solid color-mix(in srgb,var(--pink) 18%,var(--line));background:color-mix(in srgb,var(--surface-strong) 96%,transparent);box-shadow:0 32px 100px rgba(0,0,0,.38)}
      .studio-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;padding:30px 34px 25px;border-bottom:1px solid var(--line);background:radial-gradient(circle at 12% 0%,color-mix(in srgb,var(--pink) 15%,transparent),transparent 42%),linear-gradient(135deg,color-mix(in srgb,var(--surface) 96%,transparent),color-mix(in srgb,var(--violet) 4%,var(--surface)))}
      .studio-head h2{margin:5px 0 7px;font-size:28px}.studio-head p{max-width:760px;margin:0;color:var(--muted);font-size:12px;line-height:1.75}
      .studio-head-actions{display:flex;align-items:flex-start;gap:8px}.studio-status-dot{display:inline-flex;align-items:center;gap:7px;padding:8px 11px;border:1px solid var(--line);border-radius:999px;font-size:10px;color:var(--muted);white-space:nowrap}.studio-status-dot i{width:7px;height:7px;border-radius:50%;background:var(--muted)}.studio-status-dot.ok i{background:var(--green);box-shadow:0 0 12px color-mix(in srgb,var(--green) 55%,transparent)}
      .studio-body{display:grid;grid-template-columns:310px minmax(0,1fr);min-height:620px}.studio-sidebar{padding:22px;border-right:1px solid var(--line);background:color-mix(in srgb,var(--surface-muted) 54%,transparent)}.studio-main{padding:24px 26px 30px;min-width:0}
      .studio-section{padding:17px;border:1px solid var(--line);border-radius:18px;background:color-mix(in srgb,var(--surface) 90%,transparent);box-shadow:inset 0 1px rgba(255,255,255,.025)}.studio-section+.studio-section{margin-top:14px}.studio-section h3{margin:0 0 5px;font-size:13px}.studio-section p{margin:0 0 13px;color:var(--muted);font-size:10px;line-height:1.55}
      .studio-field{display:grid;gap:6px;margin-top:10px}.studio-field label{font-size:10px;font-weight:750;color:var(--secondary)}.studio-field input,.studio-field textarea,.studio-field select{width:100%;box-sizing:border-box;border:1px solid var(--line);border-radius:11px;padding:10px 11px;background:var(--surface-muted);color:var(--ink);font:inherit;font-size:11px;outline:none}.studio-field textarea{min-height:72px;resize:vertical;line-height:1.5}.studio-field input:focus,.studio-field textarea:focus,.studio-field select:focus{border-color:color-mix(in srgb,var(--pink) 55%,var(--line));box-shadow:0 0 0 3px color-mix(in srgb,var(--pink) 8%,transparent)}
      .studio-inline{display:grid;grid-template-columns:1fr 82px;gap:8px}.studio-inline .btn{height:38px;align-self:end}.studio-config-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.studio-config-meta .pill{font-size:9px}
      .studio-callout{padding:11px 12px;border-radius:12px;border:1px solid color-mix(in srgb,var(--blue) 20%,var(--line));background:color-mix(in srgb,var(--blue) 6%,transparent);color:var(--secondary);font-size:9px;line-height:1.55;margin-top:10px}
      .studio-toolbar{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:16px}.studio-toolbar h3{margin:0;font-size:17px}.studio-toolbar small{display:block;margin-top:4px;color:var(--muted);font-size:10px}.studio-progress{font:700 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--pink)}
      .studio-empty{display:grid;place-items:center;min-height:420px;padding:30px;text-align:center;border:1px dashed var(--line);border-radius:20px;color:var(--muted);background:linear-gradient(135deg,color-mix(in srgb,var(--pink) 3%,transparent),transparent)}.studio-empty strong{display:block;color:var(--ink);font-size:20px;margin-bottom:7px}.studio-empty span{max-width:460px;font-size:11px;line-height:1.7}
      .studio-task-list{display:grid;gap:12px}.studio-task{position:relative;display:grid;grid-template-columns:178px minmax(0,1fr);gap:17px;padding:16px;border:1px solid var(--line);border-radius:19px;background:color-mix(in srgb,var(--surface) 94%,transparent);transition:border-color .2s var(--ease),transform .2s var(--spring),box-shadow .2s var(--ease)}.studio-task:hover{border-color:color-mix(in srgb,var(--pink) 26%,var(--line));box-shadow:0 14px 34px rgba(0,0,0,.12)}.studio-task.generating{border-color:color-mix(in srgb,var(--pink) 45%,var(--line));animation:studioPulse 1.7s ease-in-out infinite}.studio-task.imported{opacity:.68}
      .studio-preview{display:grid;place-items:center;aspect-ratio:1;border:1px solid var(--line);border-radius:15px;overflow:hidden;background:radial-gradient(circle at center,color-mix(in srgb,var(--pink) 9%,transparent),transparent 60%),var(--surface-muted)}.studio-preview img{width:100%;height:100%;object-fit:contain}.studio-preview-placeholder{text-align:center;color:var(--muted);font-size:10px;line-height:1.55;padding:15px}.studio-preview-placeholder b{display:block;font-size:34px;margin-bottom:5px;filter:saturate(.7)}
      .studio-task-head{display:flex;justify-content:space-between;gap:12px}.studio-task-title{min-width:0}.studio-task-title strong{font-size:16px}.studio-task-id{margin-top:4px;color:var(--muted);font:650 9px/1 ui-monospace,SFMono-Regular,Menlo,monospace}.studio-task-features{margin:10px 0 8px;color:var(--secondary);font-size:11px}.studio-task-copy{font-size:10px;line-height:1.6;color:var(--muted)}.studio-task-copy b{color:var(--secondary)}
      .studio-task-controls{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px 10px;margin-top:12px}.studio-task-controls .studio-field{margin:0}.studio-task-controls .full{grid-column:1/-1}.studio-task-actions{display:flex;flex-wrap:wrap;align-items:center;gap:7px;margin-top:12px}.studio-task-actions .btn{font-size:10px;padding:8px 11px}.studio-task-state{margin-left:auto;color:var(--muted);font-size:9px}.studio-task-state.ok{color:var(--green)}.studio-task-state.err{color:var(--red,var(--pink))}
      .studio-config-drawer{display:none;margin-top:10px}.studio-config-drawer.open{display:block}.studio-secret-note{font-size:9px;color:var(--muted);line-height:1.5;margin-top:6px}
      @keyframes studioPulse{50%{box-shadow:0 0 0 4px color-mix(in srgb,var(--pink) 7%,transparent)}}
      @media(max-width:900px){.studio-body{grid-template-columns:1fr}.studio-sidebar{border-right:0;border-bottom:1px solid var(--line)}.studio-task{grid-template-columns:140px minmax(0,1fr)}}
      @media(max-width:620px){.pig-studio-modal{padding:0}.pig-studio-modal .dialog{width:100%;margin:0;min-height:100vh;border-radius:0}.studio-head{padding:22px 18px;grid-template-columns:1fr}.studio-head-actions{position:absolute;right:14px;top:14px}.studio-status-dot{display:none}.studio-sidebar,.studio-main{padding:17px}.studio-task{grid-template-columns:1fr}.studio-preview{max-width:220px;margin:auto;width:100%}.studio-task-controls{grid-template-columns:1fr}.studio-task-actions .btn{flex:1}.studio-task-state{width:100%;margin:3px 0 0}}
      @media(prefers-reduced-motion:reduce){.studio-task.generating{animation:none}.studio-task{transition:none}}
    `;
    document.head.appendChild(style);
  }

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

  function ensureModal() {
    let modal = $('pigStudioModal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'pigStudioModal';
    modal.className = 'modal pig-studio-modal';
    modal.innerHTML = `
      <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="pigStudioTitle">
        <header class="studio-head">
          <div>
            <div class="eyebrow">AI Pig Workshop · AutoPig-inspired</div>
            <h2 id="pigStudioTitle">AI 小猪工坊</h2>
            <p>让 AstrBot 先批量策划，再拿当前图鉴中的小猪当画风／体态参考生成候选。生成图先留在服务端草稿区，确认后才写进本地图鉴。</p>
          </div>
          <div class="studio-head-actions">
            <span class="studio-status-dot" id="studioStatusDot"><i></i><span>读取中</span></span>
            <button class="close" type="button" id="pigStudioClose" aria-label="关闭">×</button>
          </div>
        </header>
        <div class="studio-body">
          <aside class="studio-sidebar">
            <section class="studio-section">
              <h3>01 · 批量策划</h3>
              <p>文字策划直接复用 AstrBot 当前 AI Provider，不需要第二份聊天模型 Key。</p>
              <div class="studio-inline">
                <div class="studio-field"><label for="studioStyle">风格方向</label><input id="studioStyle" value="趣味职业、生活与轻幻想" maxlength="120"></div>
                <div class="studio-field"><label for="studioCount">数量</label><select id="studioCount"><option>1</option><option>2</option><option selected>3</option><option>4</option></select></div>
              </div>
              <div class="studio-field"><label for="studioGuidance">补充要求</label><textarea id="studioGuidance" maxlength="300" placeholder="例：主题一眼能认出，只加 1–2 个配饰，不要和现有图鉴撞题"></textarea></div>
              <button class="btn" type="button" id="studioPlanBtn" style="width:100%;margin-top:11px">让 AI 开策划会</button>
            </section>
            <section class="studio-section">
              <h3>02 · 生图通道</h3>
              <p id="studioProviderSummary">读取配置中…</p>
              <div class="studio-config-meta" id="studioConfigMeta"></div>
              <button class="btn ghost" type="button" id="studioConfigToggle" style="width:100%;margin-top:10px">配置生图 Provider</button>
              <div class="studio-config-drawer" id="studioConfigDrawer">
                <div class="studio-field"><label for="studioBaseUrl">OpenAI-compatible Base URL</label><input id="studioBaseUrl" placeholder="https://example.com/v1" autocomplete="off"></div>
                <div class="studio-field"><label for="studioModel">图像模型</label><input id="studioModel" value="gemini-3.1-flash-image-preview" maxlength="128" autocomplete="off"></div>
                <div class="studio-field"><label for="studioApiKey">API Key</label><input id="studioApiKey" type="password" placeholder="留空＝保留服务端现有 Key" autocomplete="new-password"></div>
                <div class="studio-secret-note">Key 只提交到插件服务端；状态接口不会把它读回浏览器。保存新 Key 后输入框也会立即清空。</div>
                <button class="btn" type="button" id="studioConfigSave" style="width:100%;margin-top:10px">保存服务端配置</button>
              </div>
              <div class="studio-callout">V1 只允许生图服务返回 data URL，或与 API Base URL 同 hostname 的图片地址，避免把 AstrBot 变成任意 URL 下载器。</div>
            </section>
          </aside>
          <main class="studio-main">
            <div class="studio-toolbar">
              <div><h3>候选任务</h3><small id="studioTaskSummary">还没有策划任务</small></div>
              <span class="studio-progress" id="studioProgress">READY</span>
            </div>
            <div id="studioTaskRoot" class="studio-empty"><div><strong>先让猪策划开会</strong><span>AI 会参照当前有效图鉴避开撞题，生成名称、ID、视觉特征、短描述和完整文案。你可以逐只改，再决定是否生图和入库。</span></div></div>
          </main>
        </div>
      </div>`;
    document.body.appendChild(modal);
    $('pigStudioClose').onclick = closeStudio;
    modal.addEventListener('click', event => {
      if (event.target === modal) closeStudio();
    });
    $('studioConfigToggle').onclick = () => $('studioConfigDrawer').classList.toggle('open');
    $('studioConfigSave').onclick = saveConfig;
    $('studioPlanBtn').onclick = planTasks;
    return modal;
  }

  function closeStudio() {
    $('pigStudioModal')?.classList.remove('open');
  }

  function statusPill(label, ok) {
    return `<span class="pill ${ok ? 'ok' : ''}">${esc(label)}</span>`;
  }

  function renderStatus() {
    const status = state.status || {};
    const dot = $('studioStatusDot');
    if (dot) {
      const ok = Boolean(status.enabled && status.planning_available);
      dot.classList.toggle('ok', ok);
      dot.querySelector('span').textContent = ok ? '策划可用' : '需要配置';
    }
    const summary = $('studioProviderSummary');
    if (summary) {
      summary.textContent = status.image_configured
        ? `生图已连接 ${status.image_host || 'Provider'} · ${status.image_model || '模型已配置'}`
        : '文字策划可以独立使用；要生成图片，再配置一个 OpenAI-compatible 生图端。';
    }
    const meta = $('studioConfigMeta');
    if (meta) meta.innerHTML = [
      statusPill(status.planning_available ? 'AstrBot 文案 AI ✓' : 'AstrBot 文案 AI 未配置', status.planning_available),
      statusPill(status.api_key_present ? '生图 Key ✓' : '生图 Key 未配置', status.api_key_present),
      statusPill(`草稿 ${Number(status.draft_ttl_minutes || 360)} 分钟`, true),
    ].join('');
    if ($('studioModel') && status.image_model) $('studioModel').value = status.image_model;
    const count = Math.min(8, Math.max(1, Number(status.max_batch || 4)));
    const select = $('studioCount');
    if (select) {
      select.innerHTML = Array.from({length: count}, (_, i) => `<option ${i + 1 === Math.min(3, count) ? 'selected' : ''}>${i + 1}</option>`).join('');
    }
  }

  async function refreshStatus() {
    await ensureReady();
    state.status = await get('studio/status');
    renderStatus();
    return state.status;
  }

  async function saveConfig() {
    if (state.busy) return;
    const baseUrl = $('studioBaseUrl').value.trim();
    if (!baseUrl) return toast('请填写 Base URL；为了不向浏览器回传配置，修改时需要重新填写一次');
    state.busy = true;
    $('studioConfigSave').disabled = true;
    $('studioProgress').textContent = 'SAVING';
    try {
      const data = await post('studio/config', {
        enabled: true,
        base_url: baseUrl,
        model: $('studioModel').value.trim(),
        api_key: $('studioApiKey').value,
        max_batch: Number($('studioCount').value || 4),
      });
      $('studioApiKey').value = '';
      state.status = data;
      renderStatus();
      $('studioConfigDrawer').classList.remove('open');
      toast('生图 Provider 已安全保存');
    } catch (error) {
      toast(error.message || String(error));
    } finally {
      state.busy = false;
      $('studioConfigSave').disabled = false;
      $('studioProgress').textContent = 'READY';
    }
  }

  function referenceOptions(selected = '') {
    const refs = state.status?.references || [];
    if (!refs.length) return '<option value="">当前图鉴没有可用参考图</option>';
    return refs.map(item => `<option value="${esc(item.id)}" ${item.id === selected ? 'selected' : ''}>${esc(item.name)} · ${esc(item.id)}</option>`).join('');
  }

  function taskStateText(task) {
    if (task.imported) return ['已入库', 'ok'];
    if (task.error) return [task.error, 'err'];
    if (task.generating) return ['主厨正在画…', ''];
    if (task.draft_id) return ['草稿待确认', 'ok'];
    return ['等待生图', ''];
  }

  function taskCard(task, index) {
    const [statusText, statusClass] = taskStateText(task);
    const preview = task.preview
      ? `<img src="${esc(task.preview)}" alt="${esc(task.name)} AI 草稿预览">`
      : `<div class="studio-preview-placeholder"><b>🐽</b>还没开画<br>先挑一只参考猪</div>`;
    return `<article class="studio-task ${task.generating ? 'generating' : ''} ${task.imported ? 'imported' : ''}" data-studio-task="${index}">
      <div class="studio-preview">${preview}</div>
      <div>
        <div class="studio-task-head"><div class="studio-task-title"><strong>${esc(task.name)}</strong><div class="studio-task-id">${esc(task.id)}</div></div><span class="pill">#${index + 1}</span></div>
        <div class="studio-task-features">${esc(task.features || '极简主题配饰')}</div>
        <div class="studio-task-copy"><b>短描述：</b>${esc(task.description || '—')}<br><b>完整文案：</b>${esc(task.analysis || '—')}</div>
        <div class="studio-task-controls">
          <div class="studio-field"><label>参考小猪</label><select data-studio-ref>${referenceOptions(task.reference_pig_id || '')}</select></div>
          <div class="studio-field"><label>视觉特征</label><input data-studio-features value="${esc(task.features || '')}" maxlength="160"></div>
          <div class="studio-field full"><label>微调反馈</label><input data-studio-feedback value="${esc(task.feedback || '')}" maxlength="300" placeholder="例：帽子再小一点，保留粉色猪鼻，不要背景"></div>
        </div>
        <div class="studio-task-actions">
          <button class="btn ${task.draft_id ? 'ghost' : ''}" type="button" data-studio-render ${task.imported ? 'disabled' : ''}>${task.draft_id ? '按反馈重画' : '生成小猪'}</button>
          ${task.draft_id && !task.imported ? '<button class="btn" type="button" data-studio-import>确认并入库</button>' : ''}
          <span class="studio-task-state ${statusClass}">${esc(statusText)}</span>
        </div>
      </div>
    </article>`;
  }

  function renderTasks() {
    const root = $('studioTaskRoot');
    if (!root) return;
    if (!state.tasks.length) {
      root.className = 'studio-empty';
      root.innerHTML = '<div><strong>先让猪策划开会</strong><span>AI 会参照当前有效图鉴避开撞题，生成名称、ID、视觉特征、短描述和完整文案。你可以逐只改，再决定是否生图和入库。</span></div>';
      $('studioTaskSummary').textContent = '还没有策划任务';
      return;
    }
    root.className = 'studio-task-list';
    root.innerHTML = state.tasks.map(taskCard).join('');
    const imported = state.tasks.filter(task => task.imported).length;
    const drafted = state.tasks.filter(task => task.draft_id && !task.imported).length;
    $('studioTaskSummary').textContent = `${state.tasks.length} 个候选 · ${drafted} 个草稿待确认 · ${imported} 个已入库`;
    root.querySelectorAll('[data-studio-task]').forEach(card => {
      const index = Number(card.dataset.studioTask);
      card.querySelector('[data-studio-render]')?.addEventListener('click', () => generateTask(index, card));
      card.querySelector('[data-studio-import]')?.addEventListener('click', () => importTask(index));
    });
  }

  async function planTasks() {
    if (state.busy) return;
    state.busy = true;
    $('studioPlanBtn').disabled = true;
    $('studioProgress').textContent = 'PLANNING';
    try {
      const data = await post('studio/plan', {
        count: Number($('studioCount').value || 3),
        style_vibe: $('studioStyle').value.trim(),
        guidance: $('studioGuidance').value.trim(),
      });
      const firstReference = state.status?.references?.[0]?.id || '';
      state.tasks = (data.tasks || []).map(item => ({
        ...item,
        reference_pig_id: firstReference,
        feedback: '',
        draft_id: '',
        preview: '',
        imported: false,
        generating: false,
        error: '',
      }));
      renderTasks();
      toast(`策划会结束：拿到 ${state.tasks.length} 个候选`);
    } catch (error) {
      toast(error.message || String(error));
    } finally {
      state.busy = false;
      $('studioPlanBtn').disabled = false;
      $('studioProgress').textContent = 'READY';
    }
  }

  async function generateTask(index, card) {
    const task = state.tasks[index];
    if (!task || task.imported || task.generating) return;
    if (!state.status?.image_configured) {
      $('studioConfigDrawer').classList.add('open');
      return toast('先配置生图 Provider，再让主厨开画');
    }
    const reference = card.querySelector('[data-studio-ref]')?.value || '';
    const features = card.querySelector('[data-studio-features]')?.value.trim() || task.features;
    const feedback = card.querySelector('[data-studio-feedback]')?.value.trim() || '';
    if (!reference) return toast('请先选择一只参考小猪');
    task.reference_pig_id = reference;
    task.features = features;
    task.feedback = feedback;
    task.generating = true;
    task.error = '';
    renderTasks();
    $('studioProgress').textContent = `DRAW ${index + 1}/${state.tasks.length}`;
    try {
      const data = await post('studio/render', {
        theme: task.name,
        features: task.features,
        feedback: task.feedback,
        reference_pig_id: task.reference_pig_id,
      });
      task.draft_id = data.draft_id || '';
      task.preview = data.preview || '';
      task.model = data.model || '';
      toast(`${task.name} 草稿出炉，可以继续重画或入库`);
    } catch (error) {
      task.error = error.message || String(error);
    } finally {
      task.generating = false;
      renderTasks();
      $('studioProgress').textContent = 'READY';
    }
  }

  async function importTask(index) {
    const task = state.tasks[index];
    if (!task?.draft_id || task.imported) return;
    const confirmed = window.confirm(`把「${task.name}」写入本地图鉴层吗？\n\nID：${task.id}\n写入后可以继续在图鉴管理里改文案、做 EX，或投稿公共源。`);
    if (!confirmed) return;
    $('studioProgress').textContent = `IMPORT ${index + 1}`;
    try {
      await post('studio/import', {
        draft_id: task.draft_id,
        id: task.id,
        name: task.name,
        description: task.description,
        analysis: task.analysis,
      });
      task.imported = true;
      task.draft_id = '';
      renderTasks();
      toast(`${task.name} 已正式住进本地猪圈`);
      document.getElementById('refreshBtn')?.click();
    } catch (error) {
      task.error = error.message || String(error);
      renderTasks();
      toast(task.error);
    } finally {
      $('studioProgress').textContent = 'READY';
    }
  }

  async function openStudio() {
    const modal = ensureModal();
    modal.classList.add('open');
    $('studioProgress').textContent = 'CONNECT';
    try {
      await refreshStatus();
      renderTasks();
      $('studioProgress').textContent = 'READY';
    } catch (error) {
      $('studioProgress').textContent = 'ERROR';
      toast(`AI 小猪工坊连接失败：${error.message || error}`);
    }
  }

  function installButton() {
    const topActions = shell.querySelector('.top-actions');
    if (!topActions || $('pigStudioBtn')) return;
    const button = document.createElement('button');
    button.id = 'pigStudioBtn';
    button.type = 'button';
    button.className = 'btn ghost';
    button.textContent = 'AI 小猪工坊';
    button.title = '批量策划、参考现有小猪生图并安全入库';
    const refresh = $('refreshBtn');
    topActions.insertBefore(button, refresh || null);
    button.addEventListener('click', openStudio);
  }

  installStyles();
  installButton();
})();
