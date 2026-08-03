(() => {
  const bridge = window.AstrBotPluginPage;
  if (!bridge || bridge.__rollpigFeedbackPatched) return;
  bridge.__rollpigFeedbackPatched = true;

  const $ = id => document.getElementById(id);
  const originalGet = bridge.apiGet.bind(bridge);
  const originalPost = bridge.apiPost.bind(bridge);
  const mutationButtons = [
    'syncBtn', 'storageVerifyBtn', 'storageRebuildBtn', 'storageExportBtn',
    'storageMigrateBtn', 'storageRollbackBtn', 'updateCheckBtn', 'updateApplyBtn'
  ];
  const operations = {
    'resources/sync': {button: 'syncBtn', pending: '启动中…', feedback: 'syncFeedback', message: '正在请求后端启动云资源同步'},
    'storage/migrate': {button: 'storageMigrateBtn', pending: '迁移中…', feedback: 'storageFeedback', message: '正在备份 JSON、建立临时数据库并执行对账'},
    'storage/verify': {button: 'storageVerifyBtn', pending: '验证中…', feedback: 'storageFeedback', message: '正在执行 SQLite 完整性、外键与投影检查'},
    'storage/rebuild': {button: 'storageRebuildBtn', pending: '重建中…', feedback: 'storageFeedback', message: '正在从兼容文档事务性重建 SQLite 查询索引'},
    'storage/export': {button: 'storageExportBtn', pending: '导出中…', feedback: 'storageFeedback', message: '正在生成 JSON 备份压缩包'},
    'storage/rollback': {button: 'storageRollbackBtn', pending: '回滚中…', feedback: 'storageFeedback', message: '正在把 SQLite 最新数据安全写回 JSON'},
    'updates/check': {button: 'updateCheckBtn', pending: '检查中…', feedback: 'updateFeedback', message: '正在连接官方仓库检查稳定版本'},
    'updates/apply': {button: 'updateApplyBtn', pending: '安装中…', feedback: 'updateFeedback', message: '正在下载、校验、备份并替换插件代码'}
  };
  const state = {restartRequired: false, active: new Map(), restartTimer: null};

  function errorText(error) {
    if (error instanceof Error && error.message) return error.message;
    if (typeof error === 'string') return error;
    try { return JSON.stringify(error); } catch { return '未知错误'; }
  }

  function isMissingRoute(message) {
    return /未找到该路由|route\s*not\s*found|404|not found/i.test(String(message || ''));
  }

  function ensureRestartBanner() {
    let banner = $('runtimeRestartNotice');
    if (banner) return banner;
    const topbar = document.querySelector('.topbar');
    if (!topbar) return null;
    banner = document.createElement('section');
    banner.id = 'runtimeRestartNotice';
    banner.className = 'panel';
    banner.setAttribute('role', 'alert');
    banner.style.cssText = 'display:none;margin-top:14px;border-color:rgba(255,174,82,.55);background:rgba(255,174,82,.10);padding:16px 20px';
    banner.innerHTML = '<div style="display:flex;gap:14px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap"><div><strong style="font-size:16px">⚠️ 插件代码已更新，AstrBot 仍在运行旧后端</strong><div class="panel-desc" style="margin-top:6px">请先重启 AstrBot，再使用迁移、验证、重建、同步或安全更新。否则新页面会请求尚未注册的路由。</div></div><span class="pill warn">等待重启</span></div>';
    topbar.insertAdjacentElement('afterend', banner);
    return banner;
  }

  function applyRestartLocks() {
    if (!state.restartRequired) return;
    const banner = ensureRestartBanner();
    if (banner) banner.style.display = '';
    mutationButtons.forEach(id => {
      const button = $(id);
      if (!button) return;
      button.disabled = true;
      button.setAttribute('aria-disabled', 'true');
      button.title = '插件代码已更新，请先重启 AstrBot';
    });
    const storage = $('storageFeedback');
    if (storage && !/重启 AstrBot/.test(storage.textContent || '')) {
      storage.textContent = '插件代码已更新，但后端路由仍是旧版本。请先重启 AstrBot，再执行存储操作。';
    }
  }

  function markRestartRequired(reason = '') {
    state.restartRequired = true;
    applyRestartLocks();
    clearInterval(state.restartTimer);
    state.restartTimer = setInterval(applyRestartLocks, 400);
    const update = $('updateFeedback');
    if (update) update.textContent = reason || '更新已安装到磁盘；请重启 AstrBot 后再继续操作。';
  }

  function routeError(path, error) {
    const raw = errorText(error);
    if (isMissingRoute(raw)) {
      markRestartRequired(`接口「${path}」尚未注册。若刚完成插件更新，请先重启 AstrBot。`);
      return new Error(`接口「${path}」未注册；当前页面与运行中的插件后端版本不一致。请重启 AstrBot 后重试。`);
    }
    return new Error(`请求「${path}」失败：${raw}`);
  }

  function setFeedback(id, message) {
    const node = $(id);
    if (node) node.textContent = message;
  }

  function beginOperation(path) {
    const config = operations[path];
    if (!config) return null;
    if (state.restartRequired) throw new Error('插件正在等待重启，当前操作已阻止。请先重启 AstrBot。');
    if (state.active.size) throw new Error('已有管理任务正在执行，请等待当前任务完成。');
    const button = $(config.button);
    const record = {
      config,
      button,
      originalText: button?.textContent || '',
      startedAt: Date.now(),
      timer: null
    };
    state.active.set(path, record);
    mutationButtons.forEach(id => {
      const item = $(id);
      if (item) item.disabled = true;
    });
    if (button) {
      button.textContent = config.pending;
      button.setAttribute('aria-busy', 'true');
    }
    const update = () => {
      const seconds = Math.max(0, Math.floor((Date.now() - record.startedAt) / 1000));
      setFeedback(config.feedback, `${config.message}… 已等待 ${seconds} 秒，请勿重复点击。`);
    };
    update();
    record.timer = setInterval(update, 1000);
    return record;
  }

  function finishOperation(path, outcome, detail = '') {
    const record = state.active.get(path);
    if (!record) return;
    clearInterval(record.timer);
    state.active.delete(path);
    if (record.button) {
      record.button.textContent = record.originalText;
      record.button.removeAttribute('aria-busy');
    }
    mutationButtons.forEach(id => {
      const item = $(id);
      if (item) item.disabled = false;
    });
    const elapsed = ((Date.now() - record.startedAt) / 1000).toFixed(1);
    if (outcome === 'success') {
      setFeedback(record.config.feedback, `${detail || '操作完成'}（耗时 ${elapsed} 秒）。状态正在自动刷新。`);
    } else {
      setFeedback(record.config.feedback, `${detail || '操作失败'}（耗时 ${elapsed} 秒）。`);
    }
    if (state.restartRequired) applyRestartLocks();
  }

  bridge.apiGet = async function(path, params) {
    try {
      const response = await originalGet(path, params || {});
      const payload = response?.data ?? response;
      if (path === 'updates/status' && payload?.last_result?.restart_required) {
        markRestartRequired(`已安装 ${payload.last_result.to_version || '新版本'}；必须重启 AstrBot 才能注册新路由并载入新代码。`);
      }
      return response;
    } catch (error) {
      if (path === 'storage/status' && isMissingRoute(errorText(error))) {
        markRestartRequired('存储接口尚未注册。页面文件比当前运行的插件后端更新，请先重启 AstrBot。');
        return {
          status: 'ok',
          data: {
            configured_mode: '等待重启',
            active_backend: '旧后端',
            database_exists: false,
            last_error: '页面已更新，但运行中的插件后端尚未重启',
            health: {ok: false}
          }
        };
      }
      throw routeError(path, error);
    }
  };

  bridge.apiPost = async function(path, payload) {
    let started = false;
    try {
      beginOperation(path);
      started = true;
      const response = await originalPost(path, payload || {});
      if (response?.status === 'error') throw new Error(response.message || '后端返回操作失败');
      const data = response?.data ?? response;
      if (path === 'updates/apply' && data?.restart_required !== false) {
        markRestartRequired(`已安装 ${data?.to_version || '新版本'}；请立即重启 AstrBot 后再继续管理操作。`);
      }
      finishOperation(path, 'success', path === 'updates/check' ? '版本检查完成' : '操作完成');
      return response;
    } catch (error) {
      const normalized = routeError(path, error);
      if (started) finishOperation(path, 'error', normalized.message);
      throw normalized;
    }
  };

  document.addEventListener('click', event => {
    if (!state.restartRequired) return;
    const button = event.target.closest('button');
    if (!button || !mutationButtons.includes(button.id)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    markRestartRequired('当前页面对应的新代码尚未在 AstrBot 进程中载入。请先重启 AstrBot。');
  }, true);

  const refreshButton = $('refreshBtn');
  const loadingOverlay = $('loading');
  let refreshStartedAt = 0;
  let refreshResetTimer = null;
  function finishRefresh(message) {
    if (!refreshStartedAt || !refreshButton) return;
    const elapsed = ((Date.now() - refreshStartedAt) / 1000).toFixed(1);
    refreshStartedAt = 0;
    clearTimeout(refreshResetTimer);
    refreshButton.disabled = false;
    refreshButton.textContent = '↻';
    refreshButton.removeAttribute('aria-busy');
    refreshButton.title = `${message}（耗时 ${elapsed} 秒）`;
    const live = document.querySelector('.live');
    if (live) live.innerHTML = `<i class="live-dot"></i>${message} · ${elapsed}s`;
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || button.id !== 'refreshBtn' || state.restartRequired) return;
    refreshStartedAt = Date.now();
    button.disabled = true;
    button.textContent = '…';
    button.setAttribute('aria-busy', 'true');
    button.title = '正在刷新总览、图鉴、资源、版本与存储状态';
    const live = document.querySelector('.live');
    if (live) live.innerHTML = '<i class="live-dot"></i>正在刷新全部数据…';
    refreshResetTimer = setTimeout(() => finishRefresh('刷新超时，请查看各状态卡片'), 30000);
  }, true);
  if (loadingOverlay) {
    new MutationObserver(() => {
      if (refreshStartedAt && !loadingOverlay.classList.contains('show')) {
        setTimeout(() => finishRefresh('数据已刷新'), 50);
      }
    }).observe(loadingOverlay, {attributes: true, attributeFilter: ['class']});
  }

  const toast = $('toast');
  if (toast) {
    new MutationObserver(() => {
      if (toast.classList.contains('show') && isMissingRoute(toast.textContent)) {
        toast.textContent = '后端路由尚未载入：请重启 AstrBot 后重试';
      }
    }).observe(toast, {attributes: true, childList: true, subtree: true});
  }

  function ensurePageConfirmDialog() {
    let overlay = $('pageConfirmDialog');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'pageConfirmDialog';
    overlay.setAttribute('role', 'presentation');
    overlay.style.cssText = 'display:none;position:fixed;inset:0;z-index:10050;background:rgba(7,10,18,.68);backdrop-filter:blur(8px);align-items:center;justify-content:center;padding:24px';
    overlay.innerHTML = `
      <section role="dialog" aria-modal="true" aria-labelledby="pageConfirmTitle" style="width:min(460px,100%);border:1px solid rgba(255,255,255,.18);border-radius:22px;background:var(--panel,#171a24);box-shadow:0 28px 80px rgba(0,0,0,.48);padding:24px">
        <div class="eyebrow">Confirm Action</div>
        <h2 id="pageConfirmTitle" style="margin:8px 0 10px">确认操作</h2>
        <p id="pageConfirmMessage" class="panel-desc" style="white-space:pre-wrap;line-height:1.7;margin-bottom:22px"></p>
        <div class="dialog-actions">
          <button class="btn ghost" type="button" id="pageConfirmCancel">取消</button>
          <button class="btn" type="button" id="pageConfirmAccept">继续</button>
        </div>
      </section>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  function showPageConfirm({title, message, confirmText = '继续', dangerous = false}) {
    const overlay = ensurePageConfirmDialog();
    const titleNode = $('pageConfirmTitle');
    const messageNode = $('pageConfirmMessage');
    const cancel = $('pageConfirmCancel');
    const accept = $('pageConfirmAccept');
    titleNode.textContent = title;
    messageNode.textContent = message;
    accept.textContent = confirmText;
    accept.classList.toggle('danger', dangerous);
    overlay.style.display = 'flex';
    return new Promise(resolve => {
      let settled = false;
      const finish = value => {
        if (settled) return;
        settled = true;
        overlay.style.display = 'none';
        overlay.removeEventListener('click', onOverlay);
        document.removeEventListener('keydown', onKey, true);
        resolve(value);
      };
      const onOverlay = event => { if (event.target === overlay) finish(false); };
      const onKey = event => {
        if (event.key === 'Escape') {
          event.preventDefault();
          finish(false);
        }
      };
      cancel.onclick = () => finish(false);
      accept.onclick = () => finish(true);
      overlay.addEventListener('click', onOverlay);
      document.addEventListener('keydown', onKey, true);
      requestAnimationFrame(() => accept.focus());
    });
  }

  const sandboxConfirmActions = {
    storageMigrateBtn: {
      title: '迁移到 SQLite',
      message: '系统会先完整备份关键 JSON，再建立临时数据库、导入、哈希对账并执行完整性检查。任何一步失败都会继续使用原 JSON。',
      confirmText: '开始迁移',
      bypassCount: 1
    },
    storageRebuildBtn: {
      title: '重建 SQLite 索引',
      message: '将从 SQLite 内的兼容文档事务性重建查询索引。不会改变现有抽取结果，但重建期间会暂时锁定数据库写入。',
      confirmText: '开始重建',
      bypassCount: 1
    },
    storageRollbackBtn: {
      title: '回滚到 JSON',
      message: 'SQLite 中的最新数据将先原子写回 JSON 并完成哈希对账，原数据库会改名保留而不会删除。回滚后当前实例会立即改用 JSON。',
      confirmText: '确认回滚',
      dangerous: true,
      bypassCount: 2
    },
    updateApplyBtn: {
      title: '安装稳定版更新',
      message: '更新器会下载官方稳定 Release，执行来源、校验和、压缩包、metadata 与 Python 语法检查，并在替换代码前完整备份。安装后必须重启 AstrBot。',
      confirmText: '安装更新',
      bypassCount: 1
    },
    aiDraftBtn: {
      title: '覆盖现有 AI 文案',
      message: '当前描述或完整文案已有内容。继续后，AI 生成结果会覆盖这些字段，但在保存小猪前仍可手动修改。',
      confirmText: '覆盖并生成',
      bypassCount: 1,
      when: () => Boolean(
        ($('pigDescription')?.value || '').trim() ||
        ($('pigAnalysis')?.value || '').trim()
      )
    }
  };

  function invokeLegacyConfirmedHandler(button, bypassCount) {
    const handler = button?.onclick;
    if (typeof handler !== 'function') throw new Error('操作处理器尚未载入，请刷新页面后重试。');
    const previousConfirm = window.confirm;
    let remaining = Math.max(0, Number(bypassCount) || 0);
    window.confirm = () => {
      if (remaining <= 0) return false;
      remaining -= 1;
      return true;
    };
    try {
      const result = handler.call(button, new MouseEvent('click', {cancelable: true}));
      if (result && typeof result.catch === 'function') {
        result.catch(error => console.error('[rollpig] confirmed action failed', error));
      }
    } finally {
      window.confirm = previousConfirm;
    }
  }

  let pageConfirmBusy = false;
  document.addEventListener('click', async event => {
    const button = event.target.closest('button');
    const config = button && sandboxConfirmActions[button.id];
    if (!config || button.disabled || (config.when && !config.when())) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (pageConfirmBusy) return;
    pageConfirmBusy = true;
    try {
      const accepted = await showPageConfirm(config);
      if (accepted) invokeLegacyConfirmedHandler(button, config.bypassCount);
    } catch (error) {
      const message = errorText(error);
      setFeedback(config.feedback || 'storageFeedback', `无法启动操作：${message}`);
      console.error('[rollpig] page confirmation failed', error);
    } finally {
      pageConfirmBusy = false;
    }
  }, true);

})();
