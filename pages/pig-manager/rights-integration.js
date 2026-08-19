(() => {
  'use strict';

  const bridge = window.AstrBotPluginPage;
  if (!bridge) return;

  const state = {
    version: '3.11.7',
    csrf: '',
    ready: null,
    submitPig: null,
    submitExCount: 0,
    reviewItem: null,
    reviewDecision: '',
    decorateTimer: 0,
  };
  window.__rollpigRightsUiState = state;

  const $ = id => document.getElementById(id);
  const unwrap = response => {
    const first = response?.data ?? response;
    if (first?.status === 'error') throw new Error(first.message || '操作失败');
    return first?.data ?? first;
  };
  const get = async (path, params = {}) => unwrap(await bridge.apiGet(path, params));
  const post = async (path, payload = {}) => unwrap(
    await bridge.apiPost(path, {...payload, __rollpig_csrf: state.csrf})
  );
  const toast = message => {
    const node = $('toast');
    if (!node) return;
    node.textContent = String(message || '操作完成');
    node.classList.add('show');
    window.setTimeout(() => node.classList.remove('show'), 3000);
  };
  const busy = value => $('loading')?.classList.toggle('show', Boolean(value));

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

  function installStyles() {
    if (document.querySelector('style[data-rollpig-rights-ui]')) return;
    const style = document.createElement('style');
    style.dataset.rollpigRightsUi = '1';
    style.textContent = `
      .rights-modal{position:fixed;inset:0;z-index:120;display:none;place-items:center;padding:18px;background:rgba(18,12,17,.58);backdrop-filter:blur(7px)}
      .rights-modal.open{display:grid}.rights-dialog{width:min(720px,100%);max-height:min(880px,92vh);overflow:auto;border:1px solid var(--line);border-radius:22px;background:var(--surface-strong,var(--surface,#fff));color:var(--ink);box-shadow:0 28px 100px rgba(0,0,0,.32);padding:20px}.rights-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:12px}.rights-head h2{margin:3px 0 0}.rights-kicker{font-size:10px;text-transform:uppercase;letter-spacing:.13em;color:var(--muted)}.rights-close{border:0;background:transparent;color:var(--muted);font-size:26px;cursor:pointer}.rights-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.rights-field{display:grid;gap:6px}.rights-field.full{grid-column:1/-1}.rights-field label{font-weight:760;font-size:12px}.rights-field input,.rights-field select,.rights-field textarea{width:100%;border:1px solid var(--line);border-radius:11px;padding:10px 11px;background:var(--surface);color:var(--ink)}.rights-field textarea{min-height:82px;resize:vertical}.rights-hint{font-size:10px;line-height:1.45;color:var(--muted)}.rights-check{display:flex;gap:9px;align-items:flex-start;padding:10px;border:1px solid var(--line);border-radius:12px;background:color-mix(in srgb,var(--pink-soft,var(--surface)) 35%,transparent)}.rights-check input{width:auto;margin-top:3px}.rights-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}.rights-summary{margin-top:10px;padding:10px;border:1px solid var(--line);border-radius:12px;background:color-mix(in srgb,var(--surface) 84%,var(--pink-soft,transparent));font-size:11px;line-height:1.55;overflow-wrap:anywhere}.rights-summary.missing{border-color:color-mix(in srgb,#d64b67 55%,var(--line));background:color-mix(in srgb,#d64b67 8%,var(--surface))}.rights-summary b{display:block;margin-bottom:4px}.rights-summary a{color:var(--pink);text-decoration:none}.rights-review-copy{white-space:pre-wrap;margin:10px 0;padding:10px;border:1px solid var(--line);border-radius:12px;color:var(--muted);font-size:11px}.rights-inline-note{padding:9px 10px;border-radius:11px;background:color-mix(in srgb,var(--violet,#7567cb) 8%,var(--surface));font-size:11px;color:var(--muted);margin-bottom:12px}@media(max-width:720px){.rights-grid{grid-template-columns:1fr}.rights-field.full{grid-column:auto}.rights-actions{flex-direction:column-reverse}.rights-actions .btn{width:100%}}
    `;
    document.head.appendChild(style);
  }

  function makeModal(id, body) {
    let modal = $(id);
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = id;
    modal.className = 'rights-modal';
    modal.innerHTML = body;
    document.body.appendChild(modal);
    modal.addEventListener('click', event => {
      if (event.target === modal) modal.classList.remove('open');
    });
    return modal;
  }

  function ensureSubmitModal() {
    const modal = makeModal('rightsSubmitModal', `
      <form class="rights-dialog" id="rightsSubmitForm">
        <div class="rights-head"><div><div class="rights-kicker">Rights-aware submission v3</div><h2>投稿权利资料</h2></div><button class="rights-close" type="button" data-rights-close>×</button></div>
        <div class="rights-inline-note" id="rightsSubmitIntro">投稿会进入内容与权利资料审核；管理员审核通过也不会自动发布，后续仍需独立 provenance-safe 发布流程。</div>
        <div class="rights-grid">
          <div class="rights-field"><label for="rightsBasis">权利依据</label><select id="rightsBasis" required><option value="original">本人／投稿者原创</option><option value="license">依据许可证再分发</option><option value="explicit_permission">已取得明确再分发授权</option></select></div>
          <div class="rights-field"><label for="rightsAuthor">作者／创作者</label><input id="rightsAuthor" maxlength="120" required></div>
          <div class="rights-field"><label for="rightsHolder">权利人</label><input id="rightsHolder" maxlength="120" required></div>
          <div class="rights-field"><label for="rightsSourceUrl">原始来源 URL</label><input id="rightsSourceUrl" type="url" inputmode="url" maxlength="1200" placeholder="https://..." required><div class="rights-hint">必须是可核验的 HTTPS 来源，不接受带帐号密码的 URL。</div></div>
          <div class="rights-field" id="rightsLicenseRow" hidden><label for="rightsLicenseId">许可证标识</label><input id="rightsLicenseId" maxlength="64" placeholder="例如 MIT / CC-BY-4.0"></div>
          <div class="rights-field" id="rightsEvidenceRow" hidden><label for="rightsEvidenceUrl">授权证据 URL</label><input id="rightsEvidenceUrl" type="url" maxlength="1200" placeholder="https://..."><div class="rights-hint">请提供能够核验明确再分发授权的 HTTPS 证据。</div></div>
          <div class="rights-field full"><label for="rightsAttribution">署名文本</label><textarea id="rightsAttribution" maxlength="600" required placeholder="后续 NOTICE / PROVENANCE 中应保留的作者与来源署名"></textarea></div>
          <div class="rights-field full"><label for="rightsNotes">补充说明（可选）</label><textarea id="rightsNotes" maxlength="1200" placeholder="授权范围、版本、上下文等"></textarea></div>
          <label class="rights-check full"><input id="rightsRedistribution" type="checkbox" required><span><b>确认允许公共源再分发</b><br><span class="rights-hint">我确认上述权利依据允许此资源由 RollPig 公共源复制并公开再分发。</span></span></label>
          <label class="rights-check full"><input id="rightsAttestation" type="checkbox" required><span><b>真实性声明</b><br><span class="rights-hint">我确认所填作者、权利人、来源和授权资料真实，并愿意接受管理员核验。</span></span></label>
          <label class="rights-check full" id="rightsExRow" hidden><input id="rightsIncludeEx" type="checkbox"><span><b id="rightsExLabel">同时提交本地 EX 差分</b><br><span class="rights-hint">EX 文案与图片将使用同一份权利声明进入同一次审核。</span></span></label>
        </div>
        <div class="rights-actions"><button class="btn ghost" type="button" data-rights-close>取消</button><button class="btn" type="submit">提交到权利审核队列</button></div>
      </form>`);
    modal.querySelectorAll('[data-rights-close]').forEach(button => {
      button.onclick = () => modal.classList.remove('open');
    });
    $('rightsBasis').onchange = updateBasisRows;
    $('rightsSubmitForm').onsubmit = submitRightsForm;
    return modal;
  }

  function updateBasisRows() {
    const basis = $('rightsBasis')?.value || 'original';
    const license = $('rightsLicenseRow');
    const evidence = $('rightsEvidenceRow');
    if (license) license.hidden = basis !== 'license';
    if (evidence) evidence.hidden = basis !== 'explicit_permission';
    if ($('rightsLicenseId')) $('rightsLicenseId').required = basis === 'license';
    if ($('rightsEvidenceUrl')) $('rightsEvidenceUrl').required = basis === 'explicit_permission';
  }

  function httpsUrl(value, label, required = true) {
    const text = String(value || '').trim();
    if (!text && !required) return '';
    if (!text) throw new Error(`${label}必填`);
    let parsed;
    try { parsed = new URL(text); } catch { throw new Error(`${label}不是有效 URL`); }
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password) {
      throw new Error(`${label}必须是无帐号密码的 HTTPS URL`);
    }
    return text;
  }

  function collectRights() {
    const basis = $('rightsBasis').value;
    const licenseId = $('rightsLicenseId').value.trim();
    const evidenceUrl = $('rightsEvidenceUrl').value.trim();
    if (basis === 'license' && !/^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$/.test(licenseId)) {
      throw new Error('许可证标识必填，且只能使用常见 SPDX 风格字符');
    }
    return {
      basis,
      author: $('rightsAuthor').value.trim(),
      rights_holder: $('rightsHolder').value.trim(),
      source_url: httpsUrl($('rightsSourceUrl').value, '原始来源 URL'),
      license_id: licenseId,
      permission_evidence_url: httpsUrl(
        evidenceUrl,
        '授权证据 URL',
        basis === 'explicit_permission'
      ),
      attribution: $('rightsAttribution').value.trim(),
      notes: $('rightsNotes').value.trim(),
      redistribution_authorized: $('rightsRedistribution').checked === true,
      attestation: $('rightsAttestation').checked === true,
    };
  }

  async function localExCount(pigId) {
    try {
      const snapshot = await get('ex/variants');
      const pig = (snapshot?.items || []).find(item => item.id === pigId);
      return Object.values(pig?.local_levels || {}).filter(item =>
        item && (item.description || item.analysis || item.image)
      ).length;
    } catch {
      return 0;
    }
  }

  async function openRightsSubmit(button) {
    await ensureReady();
    const card = button.closest('.pig-card');
    const pigId = String(card?.querySelector('.pig-id')?.textContent || '').trim();
    const pigName = String(card?.querySelector('.pig-name')?.textContent || pigId).trim();
    if (!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(pigId)) {
      throw new Error('无法识别要投稿的小猪 ID');
    }
    state.submitPig = {id: pigId, name: pigName};
    state.submitExCount = await localExCount(pigId);
    ensureSubmitModal();
    $('rightsSubmitForm').reset();
    $('rightsBasis').value = 'original';
    $('rightsAuthor').value = '';
    $('rightsHolder').value = '';
    $('rightsAttribution').value = '';
    $('rightsSubmitIntro').textContent = `正在投稿「${pigName}」；必须先提供可核验的权利与再分发依据。审核通过不会自动发布。`;
    $('rightsExRow').hidden = state.submitExCount <= 0;
    $('rightsExLabel').textContent = `同时提交 ${state.submitExCount} 个本地 EX 差分`;
    updateBasisRows();
    $('rightsSubmitModal').classList.add('open');
    $('rightsAuthor').focus();
  }

  async function submitRightsForm(event) {
    event.preventDefault();
    if (!state.submitPig) return;
    let rights;
    try {
      rights = collectRights();
      if (!rights.author || !rights.rights_holder || !rights.attribution) {
        throw new Error('作者、权利人和署名文本均为必填');
      }
      if (!rights.redistribution_authorized || !rights.attestation) {
        throw new Error('必须勾选再分发确认与真实性声明');
      }
    } catch (error) {
      toast(error.message || String(error));
      return;
    }
    const includeEx = state.submitExCount > 0 && $('rightsIncludeEx').checked;
    $('rightsSubmitModal').classList.remove('open');
    busy(true);
    try {
      const path = includeEx ? 'ex/submit-public-source' : 'pigs/submit-public-source';
      const result = await post(path, {
        id: state.submitPig.id,
        confirm: true,
        rights,
      });
      toast(result.message || '已进入内容与权利资料审核队列；尚未发布');
      state.submitPig = null;
      scheduleDecorate();
    } catch (error) {
      toast(`投稿失败：${error.message || error}`);
      $('rightsSubmitModal').classList.add('open');
    } finally {
      busy(false);
    }
  }

  function rightsSummary(item) {
    const rights = item?.rights;
    const wrapper = document.createElement('div');
    wrapper.className = `rights-summary${rights ? '' : ' missing'}`;
    if (!rights) {
      wrapper.innerHTML = '<b>⚠ 缺少 rights-v3 权利证据</b><span>此旧投稿不能批准，只能拒绝或重新按 v3 投稿。</span>';
      return wrapper;
    }
    const basis = ({original: '原创', license: '许可证', explicit_permission: '明确授权'})[rights.basis] || rights.basis || '未知';
    const title = document.createElement('b');
    title.textContent = `权利状态：${item.rights_status || 'unreviewed'} · ${basis}`;
    wrapper.appendChild(title);
    const rows = [
      `作者：${rights.author || '—'}`,
      `权利人：${rights.rights_holder || '—'}`,
      `署名：${rights.attribution || '—'}`,
    ];
    if (rights.license_id) rows.push(`许可证：${rights.license_id}`);
    rows.forEach(text => {
      const div = document.createElement('div'); div.textContent = text; wrapper.appendChild(div);
    });
    if (rights.source_url) {
      const row = document.createElement('div'); row.append('来源：');
      const link = document.createElement('a'); link.href = rights.source_url; link.target = '_self'; link.rel = 'noopener noreferrer'; link.textContent = rights.source_url; row.appendChild(link); wrapper.appendChild(row);
    }
    if (rights.permission_evidence_url) {
      const row = document.createElement('div'); row.append('授权证据：');
      const link = document.createElement('a'); link.href = rights.permission_evidence_url; link.target = '_self'; link.rel = 'noopener noreferrer'; link.textContent = rights.permission_evidence_url; row.appendChild(link); wrapper.appendChild(row);
    }
    return wrapper;
  }

  async function reviewQueue() {
    await ensureReady();
    const data = await get('source/reviews', {__rollpig_csrf: state.csrf});
    return Array.isArray(data?.items) ? data.items : [];
  }

  async function resolveReview(button) {
    const items = await reviewQueue();
    const card = button.closest('.pig-card');
    const pigId = String(card?.querySelector('.pig-id')?.textContent || '').trim();
    const matched = items.find(item => item.pig_id === pigId);
    if (matched) return matched;
    const rawIndex = button.dataset.reviewApprove ?? button.dataset.reviewReject;
    return items[Number(rawIndex)] || null;
  }

  async function decorateReviews() {
    const grid = $('sourceReviewGrid');
    if (!grid || !grid.querySelector('.pig-card:not([data-rights-decorated])')) return;
    let items;
    try { items = await reviewQueue(); } catch { return; }
    const meta = $('sourceReviewMeta');
    if (meta) meta.textContent = `${items.length} 只待审核 · 内容/权利审核与公开发布已分离；批准不会自动发布`;
    grid.querySelectorAll('.pig-card').forEach((card, index) => {
      if (card.dataset.rightsDecorated) return;
      const item = items[index];
      if (!item) return;
      const actions = card.querySelector('.pig-actions');
      const summary = rightsSummary(item);
      actions?.before(summary);
      const approve = card.querySelector('[data-review-approve]');
      if (approve) {
        approve.textContent = '审核权利（不发布）';
        const approvable = Boolean(item.rights) && item.rights_status === 'unreviewed';
        approve.disabled = !approvable;
        approve.title = approvable ? '核验权利资料并批准；不会自动发布' : '缺少未审核的 rights-v3 权利资料，禁止批准';
      }
      card.dataset.rightsDecorated = item.submission_id || String(index);
    });
  }

  function scheduleDecorate() {
    window.clearTimeout(state.decorateTimer);
    state.decorateTimer = window.setTimeout(() => {
      decorateReviews().catch(() => {});
    }, 60);
  }

  function ensureReviewModal() {
    const modal = makeModal('rightsReviewModal', `
      <form class="rights-dialog" id="rightsReviewForm">
        <div class="rights-head"><div><div class="rights-kicker" id="rightsReviewKicker">Rights review</div><h2 id="rightsReviewTitle">审核权利资料</h2></div><button class="rights-close" type="button" data-rights-review-close>×</button></div>
        <div class="rights-inline-note" id="rightsReviewMessage"></div>
        <div id="rightsReviewSummary"></div>
        <div class="rights-field full"><label for="rightsReviewNote">审核备注</label><textarea id="rightsReviewNote" maxlength="600" placeholder="批准时至少 8 字，说明核对了哪些来源／授权依据"></textarea><div class="rights-hint">批准只表示通过内容与权利证据审核，不会创建资源版本，也不会切换正式 v1。</div></div>
        <label class="rights-check" id="rightsVerifiedRow"><input id="rightsVerified" type="checkbox"><span><b>我已核验权利资料</b><br><span class="rights-hint">仅批准时需要。勾选后会发送 rights_verified=true。</span></span></label>
        <div class="rights-actions"><button class="btn ghost" type="button" data-rights-review-close>取消</button><button class="btn" id="rightsReviewConfirm" type="submit">确认审核（不发布）</button></div>
      </form>`);
    modal.querySelectorAll('[data-rights-review-close]').forEach(button => {
      button.onclick = () => modal.classList.remove('open');
    });
    $('rightsReviewForm').onsubmit = submitReviewForm;
    return modal;
  }

  async function openRightsReview(button, decision) {
    await ensureReady();
    const item = await resolveReview(button);
    if (!item) throw new Error('无法读取这条待审核投稿');
    if (decision === 'approve' && (!item.rights || item.rights_status !== 'unreviewed')) {
      throw new Error('缺少可核验的 rights-v3 权利资料，禁止批准；可选择拒绝');
    }
    state.reviewItem = item;
    state.reviewDecision = decision;
    ensureReviewModal();
    const approving = decision === 'approve';
    $('rightsReviewKicker').textContent = approving ? 'Rights verification' : 'Reject submission';
    $('rightsReviewTitle').textContent = approving ? '批准内容与权利审核' : '拒绝投稿';
    $('rightsReviewMessage').textContent = approving
      ? `正在审核「${item.name}」。通过后仍保持 not_published，必须等待独立 provenance-safe 发布。`
      : `拒绝「${item.name}」不会修改当前正式公共资源。`;
    $('rightsReviewSummary').replaceChildren(rightsSummary(item));
    $('rightsReviewNote').value = '';
    $('rightsVerified').checked = false;
    $('rightsVerifiedRow').hidden = !approving;
    $('rightsReviewConfirm').textContent = approving ? '确认审核通过（不发布）' : '确认拒绝';
    $('rightsReviewConfirm').classList.toggle('danger', !approving);
    $('rightsReviewModal').classList.add('open');
    $('rightsReviewNote').focus();
  }

  async function submitReviewForm(event) {
    event.preventDefault();
    const item = state.reviewItem;
    const decision = state.reviewDecision;
    if (!item || !decision) return;
    const approving = decision === 'approve';
    const note = $('rightsReviewNote').value.trim();
    const verified = $('rightsVerified').checked === true;
    if (approving && !verified) {
      toast('批准前必须勾选「我已核验权利资料」');
      return;
    }
    if (approving && note.length < 8) {
      toast('批准时必须留下至少 8 字的权利审核备注');
      return;
    }
    $('rightsReviewModal').classList.remove('open');
    busy(true);
    try {
      const result = await post('source/reviews/decision', {
        id: item.submission_id,
        decision,
        note,
        rights_verified: approving && verified,
        confirm: true,
      });
      toast(result.message || (approving ? '审核已通过；尚未发布' : '已拒绝投稿'));
      state.reviewItem = null;
      state.reviewDecision = '';
      window.setTimeout(() => window.location.reload(), 650);
    } catch (error) {
      toast(error.message || String(error));
      $('rightsReviewModal').classList.add('open');
    } finally {
      busy(false);
    }
  }

  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    const submit = target.closest('[data-submit]');
    if (submit && submit.closest('#overrideGrid')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      openRightsSubmit(submit).catch(error => toast(error.message || String(error)));
      return;
    }
    const approve = target.closest('[data-review-approve]');
    const reject = target.closest('[data-review-reject]');
    if (approve || reject) {
      event.preventDefault();
      event.stopImmediatePropagation();
      openRightsReview(approve || reject, approve ? 'approve' : 'reject')
        .catch(error => toast(error.message || String(error)));
    }
  }, true);

  function init() {
    installStyles();
    ensureSubmitModal();
    ensureReviewModal();
    const observer = new MutationObserver(records => {
      if (records.some(record =>
        record.target?.id === 'sourceReviewGrid'
        || Array.from(record.addedNodes || []).some(node =>
          node instanceof Element && (node.id === 'sourceReviewPanel' || node.querySelector?.('#sourceReviewPanel'))
        )
      )) scheduleDecorate();
    });
    observer.observe(document.body, {childList: true, subtree: true});
    scheduleDecorate();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
})();
