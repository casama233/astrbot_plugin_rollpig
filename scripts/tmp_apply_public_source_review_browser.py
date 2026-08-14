from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "legacy_main.py"
HTML = ROOT / "pages" / "pig-manager" / "index.html"
TEST_UI = ROOT / "tests" / "test_public_source_ui_confirmation.py"
TEST_BROWSER = ROOT / "tests" / "test_public_source_browser_contract.py"
TEST_REVIEW = ROOT / "tests" / "test_public_source_review.py"
CHANGELOG = ROOT / "CHANGELOG.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Backend: authenticated local proxy for the official public source catalog.
# ---------------------------------------------------------------------------
legacy = LEGACY.read_text(encoding="utf-8")
registration_marker = '''        context.register_web_api(\n            f"/{self.PLUGIN_NAME}/source/reviews",\n            self.page_public_source_reviews,\n            ["GET"],\n            "查看 AstrBot 公共豬源待审核投稿",\n        )\n'''
registration_new = '''        context.register_web_api(\n            f"/{self.PLUGIN_NAME}/source/catalog",\n            self.page_public_source_catalog,\n            ["GET"],\n            "浏览 AstrBot 官方公共豬源",\n        )\n        context.register_web_api(\n            f"/{self.PLUGIN_NAME}/source/catalog/image",\n            self.page_public_source_catalog_image,\n            ["GET"],\n            "预览 AstrBot 官方公共豬源图片",\n        )\n''' + registration_marker
legacy = replace_once(legacy, registration_marker, registration_new, "register public catalog routes")

methods_marker = '''    async def page_public_source_reviews(self):\n        """Only the maintainer instance may list the server-side review queue."""\n'''
methods_new = r'''    async def _official_public_source_snapshot(self, *, force: bool = False) -> dict:
        """Load a short-lived, validated snapshot of the official public source."""
        now = time.monotonic()
        cached = getattr(self, "_official_public_source_cache", None)
        if (
            not force
            and isinstance(cached, dict)
            and now - float(cached.get("loaded_at", 0.0) or 0.0) < 30.0
        ):
            return cached

        manifest_url = self.OFFICIAL_RESOURCE_MANIFEST_URL
        self._validate_remote_url(manifest_url, "AstrBot 官方公共豬源")
        async with self._new_http_client(
            follow_redirects=True,
            extra_headers=self._resource_request_headers(),
        ) as client:
            manifest_raw = await self._download_limited(
                client,
                manifest_url,
                self.RESOURCE_MANIFEST_MAX_SIZE,
            )
            manifest = json.loads(manifest_raw.decode("utf-8-sig"))
            if not isinstance(manifest, dict):
                raise ValueError("公共豬源 manifest 必须是 JSON 对象")
            if manifest.get("schema_version") not in (1, "1"):
                raise ValueError("公共豬源 manifest 协议版本不受支持")
            if str(manifest.get("client") or "").strip() != self.RESOURCE_CLIENT_ID:
                raise ValueError("公共豬源客户端标识不匹配")
            pig_meta = manifest.get("pig_json")
            if not isinstance(pig_meta, dict):
                raise ValueError("公共豬源 manifest 缺少 pig_json")
            catalog_raw = await self._download_manifest_item(
                client,
                manifest_url,
                pig_meta,
                self.PUBLIC_SOURCE_RESPONSE_MAX_SIZE,
            )

        records_raw = json.loads(catalog_raw.decode("utf-8-sig"))
        if not isinstance(records_raw, list):
            raise ValueError("公共豬源 pig.json 必须是数组")
        records: list[dict[str, str]] = []
        seen: set[str] = set()
        for raw in records_raw:
            if not isinstance(raw, dict):
                continue
            pig_id = str(raw.get("id") or "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id) or pig_id in seen:
                continue
            seen.add(pig_id)
            records.append(
                {
                    "id": pig_id,
                    "name": str(raw.get("name") or pig_id),
                    "description": str(raw.get("description") or ""),
                    "analysis": str(raw.get("analysis") or ""),
                }
            )

        image_by_id: dict[str, dict] = {}
        images = manifest.get("images")
        if isinstance(images, list):
            for raw in images:
                if not isinstance(raw, dict):
                    continue
                filename = str(raw.get("filename") or "").strip()
                path = str(raw.get("path") or "").strip()
                candidate = filename or Path(path).name
                pig_id = Path(candidate).stem
                if pig_id in seen and pig_id not in image_by_id:
                    image_by_id[pig_id] = dict(raw)

        snapshot = {
            "loaded_at": now,
            "resource_version": str(manifest.get("resource_version") or "").strip(),
            "records": records,
            "image_by_id": image_by_id,
        }
        self._official_public_source_cache = snapshot
        return snapshot

    async def page_public_source_catalog(self):
        """Browse only the official public cloud catalog; never mix local overrides."""
        try:
            if not self._is_authorized_write_request(request):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            query = str(request.query.get("search") or "").strip().lower()[:120]
            try:
                page = max(1, int(request.query.get("page", 1)))
            except (TypeError, ValueError):
                page = 1
            force = str(request.query.get("refresh") or "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            snapshot = await self._official_public_source_snapshot(force=force)
            records = list(snapshot.get("records") or [])
            if query:
                records = [
                    item
                    for item in records
                    if query
                    in "\n".join(
                        str(item.get(key) or "").lower()
                        for key in ("id", "name", "description", "analysis")
                    )
                ]
            page_size = 24
            total = len(records)
            pages = max(1, math.ceil(total / page_size))
            page = min(page, pages)
            start = (page - 1) * page_size
            image_by_id = snapshot.get("image_by_id") or {}
            items = []
            for item in records[start : start + page_size]:
                public_item = dict(item)
                public_item["image_available"] = item.get("id") in image_by_id
                items.append(public_item)
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "items": items,
                        "page": page,
                        "pages": pages,
                        "total": total,
                        "resource_version": snapshot.get("resource_version") or "",
                    },
                }
            )
        except (ValueError, json.JSONDecodeError, UnicodeError) as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except (httpx.TimeoutException, httpx.TransportError):
            return self._jsonify(
                {"status": "error", "message": "公共豬源暂时无法连接"}
            )

    async def page_public_source_catalog_image(self):
        """Proxy one official catalog image so the sandbox never needs cross-origin access."""
        try:
            if not self._is_authorized_write_request(request):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            pig_id = str(request.query.get("id") or "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError("公共豬源小猪 ID 无效")
            snapshot = await self._official_public_source_snapshot()
            meta = (snapshot.get("image_by_id") or {}).get(pig_id)
            if not isinstance(meta, dict):
                raise ValueError("公共豬源没有这只小猪的图片")
            async with self._new_http_client(
                follow_redirects=True,
                extra_headers=self._resource_request_headers(),
            ) as client:
                raw = await self._download_manifest_item(
                    client,
                    self.OFFICIAL_RESOURCE_MANIFEST_URL,
                    meta,
                    self.resource_max_file_size,
                )
            filename = str(meta.get("filename") or Path(str(meta.get("path") or "")).name)
            ext = Path(filename).suffix.lower().lstrip(".")
            mime = self.IMAGE_MIME_TYPES.get(ext, "application/octet-stream")
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "base64": base64.b64encode(raw).decode("ascii"),
                        "mime_type": mime,
                    },
                }
            )
        except (ValueError, json.JSONDecodeError, UnicodeError) as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except (httpx.TimeoutException, httpx.TransportError):
            return self._jsonify(
                {"status": "error", "message": "公共豬源图片暂时无法连接"}
            )

''' + methods_marker
legacy = replace_once(legacy, methods_marker, methods_new, "insert public catalog endpoints")
LEGACY.write_text(legacy, encoding="utf-8")


# ---------------------------------------------------------------------------
# Frontend: sandbox-safe review modal + PigHub-like official catalog browser.
# ---------------------------------------------------------------------------
html = HTML.read_text(encoding="utf-8")
layer_note_old = '''    <section class="panel layer-note"><div><h2>AstrBot 公共豬源投稿</h2><div class="panel-desc">把本地小猪的 ID、名称、描述、完整文案与图片提交到我们维护的审核队列；批准后会自动进入 AstrBot 专用公共豬源。每次投稿都需要再次确认，不会上传群友或聊天资料。</div></div><span class="pill ok">自建来源 · 人工审核</span></section>'''
layer_note_new = '''    <section class="panel layer-note"><div><h2>AstrBot 公共豬源投稿</h2><div class="panel-desc">把本地小猪的 ID、名称、描述、完整文案与图片提交到我们维护的审核队列；批准后会自动进入 AstrBot 专用公共豬源。每次投稿都需要再次确认，不会上传群友或聊天资料。</div></div><div class="top-actions"><span class="pill ok">自建来源 · 人工审核</span><button class="btn ghost" id="publicSourceBrowseBtn" type="button">浏览公共豬源</button></div></section>'''
html = replace_once(html, layer_note_old, layer_note_new, "add public source browser button")

modal_marker = '''<div class="modal" id="pighubModal"><div class="dialog hub-dialog">'''
modal_markup = '''<div class="modal" id="reviewModal"><form class="dialog" id="reviewForm" style="max-width:540px">
  <div class="dialog-head"><div><div class="eyebrow" id="reviewEyebrow">Public Source Review</div><h2 id="reviewTitle">审核公共豬源投稿</h2></div><button class="close" type="button" id="reviewClose" aria-label="关闭">×</button></div>
  <p class="panel-desc" id="reviewMessage"></p>
  <div class="field"><label for="reviewNote">审核备注（可选）</label><textarea id="reviewNote" maxlength="300" placeholder="最多 300 字；拒绝时建议说明原因"></textarea><div class="hint">备注只写入审核记录，不会修改投稿文案。</div></div>
  <div class="dialog-actions"><button class="btn ghost" type="button" id="reviewCancel">取消</button><button class="btn" type="submit" id="reviewConfirm">确认</button></div>
</form></div>
<div class="modal" id="publicSourceModal"><div class="dialog hub-dialog">
  <div class="dialog-head"><div><div class="eyebrow">Official Public Source</div><h2>AstrBot 公共豬源图鉴</h2><div class="panel-desc" id="publicSourceMeta">打开后读取当前正式 v1 资源；只显示公共源，不混入本地覆盖。</div></div><button class="close" type="button" id="publicSourceClose" aria-label="关闭">×</button></div>
  <div class="hub-toolbar"><div class="search-wrap"><span class="search-icon">⌕</span><input class="search" id="publicSourceSearch" placeholder="搜索 ID、名称、描述或完整文案"></div><button class="btn ghost" id="publicSourceRefresh" type="button">刷新公共源</button></div>
  <div class="hub-grid" id="publicSourceGrid"><div class="empty">打开后加载公共豬源…</div></div><div class="pagination"><button class="btn ghost" id="publicSourcePrev" type="button">上一页</button><span id="publicSourcePageText">1 / 1</span><button class="btn ghost" id="publicSourceNext" type="button">下一页</button></div>
</div></div>
<div class="modal" id="publicSourceDetailModal"><div class="dialog" style="max-width:720px">
  <div class="dialog-head"><div><div class="eyebrow">Public Pig Preview</div><h2 id="publicSourceDetailName">公共豬源预览</h2></div><button class="close" type="button" id="publicSourceDetailClose" aria-label="关闭">×</button></div>
  <div class="upload"><canvas class="preview" id="publicSourceDetailCanvas" width="192" height="192" aria-label="公共豬源图片预览"></canvas><div><div class="pig-id" id="publicSourceDetailId"></div><p class="panel-desc" id="publicSourceDetailDescription"></p></div></div>
  <div class="review-analysis" id="publicSourceDetailAnalysis" style="height:auto;max-height:260px;margin-top:16px"></div>
  <div class="dialog-actions"><button class="btn ghost" type="button" id="publicSourceDetailDone">关闭</button></div>
</div></div>
''' + modal_marker
html = replace_once(html, modal_marker, modal_markup, "insert review and public source modals")

state_old = "let page=1,pages=1,search='',items=[],localOverrides=[],blockedPigs=[],reviewItems=[],imageData='',pighubUrl='',pighubFilename='',hubPage=1,hubPages=1,hubSearch='',hubItems=[],syncPolling=false,hubRenderToken=0,aiProgressTimer=null,aiProgressHideTimer=null,overviewData=null;"
state_new = "let page=1,pages=1,search='',items=[],localOverrides=[],blockedPigs=[],reviewItems=[],publicSourcePage=1,publicSourcePages=1,publicSourceSearch='',publicSourceItems=[],publicSourceRenderToken=0,pendingReviewDecision=null,imageData='',pighubUrl='',pighubFilename='',hubPage=1,hubPages=1,hubSearch='',hubItems=[],syncPolling=false,hubRenderToken=0,aiProgressTimer=null,aiProgressHideTimer=null,overviewData=null;"
html = replace_once(html, state_old, state_new, "extend frontend state")

review_dup_pattern = r"function reviewDuplicateHtml\(p\)\{.*?\}\nfunction renderSourceReviews"
review_dup_replacement = '''function reviewDuplicateHtml(p){const hints=Array.isArray(p.duplicate_hints)?p.duplicate_hints:[];if(!hints.length)return'';return`<div class="review-dup"><b>疑似重复 ${hints.length} 项</b>${hints.map(h=>`<div class="review-dup-item"><span>${esc(h.name||h.id)} · ${esc((h.reasons||[]).join(' / '))}</span><button class="btn ghost" type="button" data-public-source-match="${esc(h.id)}">查看现有猪</button></div>`).join('')}</div>`}
function renderSourceReviews'''
html, count = re.subn(review_dup_pattern, review_dup_replacement, html, count=1, flags=re.S)
if count != 1:
    raise RuntimeError(f"replace duplicate hint UI: expected 1, got {count}")

browser_functions = r'''
async function paintPublicSourceCanvas(canvas,pigId){const d=await get('source/catalog/image',{id:pigId,__rollpig_csrf:csrfToken}),binary=atob(String(d.base64||'')),bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);const bitmap=await createImageBitmap(new Blob([bytes],{type:d.mime_type||'image/png'})),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close()}
function renderPublicSourceCatalog(){const token=++publicSourceRenderToken;$('publicSourcePageText').textContent=`${publicSourcePage} / ${publicSourcePages}`;$('publicSourcePrev').disabled=publicSourcePage<=1;$('publicSourceNext').disabled=publicSourcePage>=publicSourcePages;if(!publicSourceItems.length){$('publicSourceGrid').innerHTML='<div class="empty">没有找到符合条件的公共小猪</div>';return}$('publicSourceGrid').innerHTML=publicSourceItems.map((p,i)=>`<button class="hub-card" type="button" data-public-source-card="${i}" style="--delay:${Math.min(i,18)*30}ms"><div class="hub-thumb"><canvas width="160" height="160" data-public-source-canvas="${i}" aria-label="${esc(p.name)}"></canvas><div class="image-fallback">🐽</div></div><div class="hub-title">${esc(p.name)}</div><div class="hub-file">${esc(p.id)}</div><div class="pig-desc">${esc(p.description||'')}</div></button>`).join('');document.querySelectorAll('[data-public-source-canvas]').forEach(canvas=>{if(token!==publicSourceRenderToken)return;const p=publicSourceItems[Number(canvas.dataset.publicSourceCanvas)];if(!p?.image_available){canvas.closest('.hub-thumb').classList.add('broken');return}paintPublicSourceCanvas(canvas,p.id).catch(()=>canvas.closest('.hub-thumb').classList.add('broken'))});document.querySelectorAll('[data-public-source-card]').forEach(button=>button.onclick=()=>openPublicSourceDetail(publicSourceItems[Number(button.dataset.publicSourceCard)]))}
async function loadPublicSourceCatalog(force=false){const d=await get('source/catalog',{search:publicSourceSearch,page:publicSourcePage,refresh:force?'1':'0',__rollpig_csrf:csrfToken});publicSourceItems=Array.isArray(d.items)?d.items:[];publicSourcePage=Number(d.page||1);publicSourcePages=Math.max(1,Number(d.pages||1));$('publicSourceMeta').textContent=`${Number(d.total||0)} 只正式公共小猪 · 资源版本 ${d.resource_version||'未知'} · 搜索覆盖 ID / 名称 / 描述 / 完整文案`;renderPublicSourceCatalog();return d}
async function openPublicSourceBrowser(initialSearch=''){publicSourceSearch=String(initialSearch||'').trim();publicSourcePage=1;$('publicSourceSearch').value=publicSourceSearch;$('publicSourceModal').classList.add('open');busy(true);try{await loadPublicSourceCatalog(false)}catch(e){$('publicSourceGrid').innerHTML=`<div class="empty">公共豬源加载失败：${esc(e.message)}</div>`;toast(e.message)}finally{busy(false)}}
function openPublicSourceDetail(p){if(!p)return;$('publicSourceDetailName').textContent=p.name||p.id;$('publicSourceDetailId').textContent=p.id||'';$('publicSourceDetailDescription').textContent=p.description||'暂无描述';$('publicSourceDetailAnalysis').textContent=p.analysis||'暂无完整文案';const canvas=$('publicSourceDetailCanvas'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);$('publicSourceDetailModal').classList.add('open');if(p.image_available)paintPublicSourceCanvas(canvas,p.id).catch(()=>{})}
'''
html = replace_once(html, "function reviewDuplicateHtml", browser_functions + "function reviewDuplicateHtml", "insert browser functions")

review_pattern = r"async function reviewPublicSource\(p,decision\)\{.*?\}\nfunction updateFlow"
review_replacement = r'''function reviewPublicSource(p,decision){const approving=decision==='approve';pendingReviewDecision={pig:p,decision};$('reviewTitle').textContent=approving?'批准并发布':'拒绝投稿';$('reviewEyebrow').textContent=approving?'Publish Public Source':'Reject Submission';$('reviewMessage').textContent=approving?`确定批准「${p.name}」吗？确认后会创建新的公共资源版本并原子切换正式 v1。`:`确定拒绝「${p.name}」吗？拒绝不会修改当前正式公共资源。`;$('reviewNote').value='';$('reviewConfirm').textContent=approving?'批准并立即发布':'确认拒绝';$('reviewConfirm').classList.toggle('danger',!approving);$('reviewModal').classList.add('open');$('reviewNote').focus()}
function closeReviewModal(){pendingReviewDecision=null;$('reviewModal').classList.remove('open')}
$('reviewForm').onsubmit=async e=>{e.preventDefault();const pending=pendingReviewDecision;if(!pending)return;const approving=pending.decision==='approve',note=$('reviewNote').value.trim().slice(0,300);$('reviewModal').classList.remove('open');busy(true);try{const d=await post('source/reviews/decision',{id:pending.pig.submission_id,decision:pending.decision,note,confirm:true});pendingReviewDecision=null;toast(d.message||'审核完成');const refreshPublic=approving&&$('publicSourceModal').classList.contains('open')?loadPublicSourceCatalog(true):Promise.resolve();await Promise.all([loadSourceReviews(),loadResourceStatus(),refreshPublic])}catch(err){toast(err.message);pendingReviewDecision=pending;$('reviewModal').classList.add('open')}finally{busy(false)}};
function updateFlow'''
html, count = re.subn(review_pattern, review_replacement, html, count=1, flags=re.S)
if count != 1:
    raise RuntimeError(f"replace reviewPublicSource: expected 1, got {count}")

bindings_marker = "$('syncBtn').onclick=async()=>{"
bindings = r'''$('reviewClose').onclick=$('reviewCancel').onclick=closeReviewModal;$('reviewModal').onclick=e=>{if(e.target===$('reviewModal'))closeReviewModal()};$('publicSourceBrowseBtn').onclick=()=>openPublicSourceBrowser();$('publicSourceClose').onclick=()=>$('publicSourceModal').classList.remove('open');$('publicSourceModal').onclick=e=>{if(e.target===$('publicSourceModal'))$('publicSourceClose').click()};$('publicSourcePrev').onclick=()=>{if(publicSourcePage>1){publicSourcePage--;loadPublicSourceCatalog().catch(e=>toast(e.message))}};$('publicSourceNext').onclick=()=>{if(publicSourcePage<publicSourcePages){publicSourcePage++;loadPublicSourceCatalog().catch(e=>toast(e.message))}};$('publicSourceRefresh').onclick=async()=>{busy(true);try{publicSourcePage=1;await loadPublicSourceCatalog(true);toast('公共豬源已刷新')}catch(e){toast(e.message)}finally{busy(false)}};let publicSourceSearchTimer;$('publicSourceSearch').oninput=e=>{clearTimeout(publicSourceSearchTimer);publicSourceSearchTimer=setTimeout(()=>{publicSourceSearch=e.target.value.trim();publicSourcePage=1;loadPublicSourceCatalog().catch(err=>toast(err.message))},260)};$('publicSourceDetailClose').onclick=$('publicSourceDetailDone').onclick=()=>$('publicSourceDetailModal').classList.remove('open');$('publicSourceDetailModal').onclick=e=>{if(e.target===$('publicSourceDetailModal'))$('publicSourceDetailClose').click()};$('sourceReviewGrid').addEventListener('click',e=>{const button=e.target.closest('[data-public-source-match]');if(button)openPublicSourceBrowser(button.dataset.publicSourceMatch||'')});
'''
html = replace_once(html, bindings_marker, bindings + bindings_marker, "insert public source bindings")

escape_old = "document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeModal();$('pighubModal').classList.remove('open')}});"
escape_new = "document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeModal();closeReviewModal();$('pighubModal').classList.remove('open');$('publicSourceModal').classList.remove('open');$('publicSourceDetailModal').classList.remove('open')}});"
html = replace_once(html, escape_old, escape_new, "extend escape handling")
HTML.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: sandbox-safe UI, browse contract, and real reject mutation.
# ---------------------------------------------------------------------------
TEST_UI.write_text(
    '''from pathlib import Path\n\n\nROOT = Path(__file__).resolve().parents[1]\nPAGE = ROOT / "pages" / "pig-manager" / "index.html"\n\n\ndef test_public_source_submit_is_sandbox_safe_and_requires_explicit_second_click():\n    page = PAGE.read_text(encoding="utf-8")\n    start = page.index("async function submitPublicSource")\n    end = page.index("async function paintReviewCanvas", start)\n    submit_code = page[start:end]\n\n    assert "window.confirm" not in submit_code\n    assert "dataset.submitConfirm" in submit_code\n    assert "再次点击确认" in submit_code\n    assert "pigs/submit-public-source" in submit_code\n    assert "confirm:true" in submit_code\n    assert "submitPublicSource(localOverrides[Number(b.dataset.submit)],b)" in page\n    assert 'type="button" data-submit' in page\n\n\ndef test_public_source_review_decision_uses_in_page_modal_not_native_dialogs():\n    page = PAGE.read_text(encoding="utf-8")\n    start = page.index("function reviewPublicSource")\n    end = page.index("function updateFlow", start)\n    review_code = page[start:end]\n\n    assert "window.confirm" not in review_code\n    assert "window.prompt" not in review_code\n    assert 'id="reviewModal"' in page\n    assert 'id="reviewForm"' in page\n    assert 'id="reviewNote" maxlength="300"' in page\n    assert "source/reviews/decision" in review_code\n    assert "confirm:true" in review_code\n    assert "批准并立即发布" in review_code\n    assert "确认拒绝" in review_code\n''',
    encoding="utf-8",
)

TEST_BROWSER.write_text(
    '''from pathlib import Path\n\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef test_public_source_browser_has_authenticated_catalog_and_image_proxy():\n    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")\n    assert 'f"/{self.PLUGIN_NAME}/source/catalog"' in source\n    assert 'f"/{self.PLUGIN_NAME}/source/catalog/image"' in source\n    assert "self.OFFICIAL_RESOURCE_MANIFEST_URL" in source\n    assert "_official_public_source_snapshot" in source\n    assert 'for key in ("id", "name", "description", "analysis")' in source\n    assert "_download_manifest_item" in source\n    assert "_is_authorized_write_request(request)" in source\n\n\ndef test_public_source_browser_is_pighub_like_searchable_preview_ui():\n    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")\n    for marker in (\n        'id="publicSourceBrowseBtn"',\n        'id="publicSourceModal"',\n        'id="publicSourceSearch"',\n        'id="publicSourceGrid"',\n        'id="publicSourcePrev"',\n        'id="publicSourceNext"',\n        'id="publicSourceDetailModal"',\n    ):\n        assert marker in page\n    assert "source/catalog',{search:publicSourceSearch" in page\n    assert "source/catalog/image',{id:pigId,__rollpig_csrf:csrfToken}" in page\n    assert "data-public-source-match" in page\n    assert "查看现有猪" in page\n''',
    encoding="utf-8",
)

review_tests = TEST_REVIEW.read_text(encoding="utf-8")
if "test_public_source_submission_reject_mutates_pending_without_publishing" not in review_tests:
    review_tests += r'''


def test_public_source_submission_reject_mutates_pending_without_publishing(tmp_path):
    app = _application(tmp_path)
    upload = tmp_path / "reject.png"
    image = _png(upload, (90, 80, 70, 255))
    result = app.submit(
        {
            "record": {
                "id": "rejected-pig",
                "name": "被拒绝的小猪",
                "description": "不应发布",
                "analysis": "拒绝操作必须真正把 pending 改为 rejected。",
            },
            "image": base64.b64encode(image).decode("ascii"),
        },
        source_address="203.0.113.12",
        client_version="3.6.5",
    )
    submission_id = result["submission_id"]
    before = (app.config.publish_root / "v1").resolve()

    reviewed = app.review(submission_id, "reject", "内容不符合公共源要求")

    assert reviewed["status"] == "rejected"
    assert reviewed["reviewer_note"] == "内容不符合公共源要求"
    assert app.list_submissions("pending") == []
    rejected = app.list_submissions("rejected")
    assert rejected[0]["submission_id"] == submission_id
    assert (app.config.publish_root / "v1").resolve() == before
    current_catalog = json.loads((before / "pig.json").read_text(encoding="utf-8"))
    assert "rejected-pig" not in {item["id"] for item in current_catalog}
'''
TEST_REVIEW.write_text(review_tests, encoding="utf-8")


# ---------------------------------------------------------------------------
# Changelog.
# ---------------------------------------------------------------------------
changelog = CHANGELOG.read_text(encoding="utf-8")
changed_marker = "### Changed\n"
changed_add = "### Changed\n- 修復 AstrBot Plugin Page sandbox 下公共豬源「拒絕／批准發布」依賴原生 `window.confirm` / `window.prompt` 而可能無反應；改為頁內審核對話框，保留 300 字備註與明確二次確認。\n- 公共豬源管理新增 PigHub 風格正式源圖鑑：可搜尋 ID、名稱、描述、完整文案，分頁預覽圖片與完整資料；疑似重複提示可直接跳到現有公共豬。\n- 正式公共源圖鑑經 AstrBot 本地同源代理讀取官方 `v1`，圖片不由 sandbox 跨域直連；批准／拒絕補上真實 mutation 回歸測試。\n"
changelog = replace_once(changelog, changed_marker, changed_add, "update changelog")
CHANGELOG.write_text(changelog, encoding="utf-8")

print("public source review/browser patch applied")
