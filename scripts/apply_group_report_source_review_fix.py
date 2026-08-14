from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


# --- Daily report: per-group opt-in -----------------------------------------
path = "daily_report_feature.py"
text = read(path)
insert = '''    def _daily_report_group_manager(self, event: AstrMessageEvent, actor_id: str) -> bool:\n        """Allow AstrBot admins and native group owner/admin roles to manage push state."""\n        try:\n            if self._is_admin_id(event, actor_id):\n                return True\n        except Exception:\n            pass\n        roles: list[str] = []\n        message_obj = getattr(event, "message_obj", None)\n        sender = getattr(message_obj, "sender", None)\n        raw = getattr(message_obj, "raw_message", None)\n        if sender is not None:\n            roles.append(str(getattr(sender, "role", "") or ""))\n        if isinstance(raw, dict):\n            raw_sender = raw.get("sender")\n            if isinstance(raw_sender, dict):\n                roles.append(str(raw_sender.get("role") or ""))\n            roles.append(str(raw.get("role") or ""))\n        return any(role.strip().lower() in {"owner", "admin", "administrator"} for role in roles)\n\n    def _daily_report_group_auto_enabled(self, group_id: str) -> bool:\n        with self._data_lock:\n            group = self.daily_report_state.get("groups", {}).get(str(group_id), {})\n            return bool(group.get("auto_enabled", False)) if isinstance(group, dict) else False\n\n    def _set_daily_report_group_auto(\n        self, group_id: str, enabled: bool, *, actor_id: str = ""\n    ) -> None:\n        now = int(time.time())\n        today = self._today().isoformat()\n        with self._data_lock:\n            groups = self.daily_report_state.setdefault("groups", {})\n            group = groups.setdefault(str(group_id), {})\n            was_enabled = bool(group.get("auto_enabled", False))\n            group["auto_enabled"] = bool(enabled)\n            group["auto_updated_at"] = now\n            group["auto_updated_by"] = str(actor_id or "")\n            if enabled and not was_enabled:\n                group["auto_enabled_since"] = today\n            self._save_daily_report_state_locked()\n\n'''
needle = "    def _init_daily_report_feature(self) -> None:\n"
if insert not in text:
    text = replace_once(text, needle, insert + needle, "insert report group helpers")
text = replace_once(
    text,
    '            group = groups.setdefault(str(group_id), {})\n            if umo:\n',
    '            group = groups.setdefault(str(group_id), {})\n            group.setdefault("auto_enabled", False)\n            if umo:\n',
    "default group push off",
)
text = replace_once(
    text,
    '                due = due_datetime(\n                    report_date,\n                    self.daily_report_send_hour,\n                    self.daily_report_send_minute,\n                    self.timezone,\n                    delay,\n                )\n',
    '                due = due_datetime(\n                    report_date,\n                    self.daily_report_send_hour,\n                    self.daily_report_send_minute,\n                    self.timezone,\n                    delay,\n                )\n                # Automatic reports belong to the report natural day. Random\n                # delay may approach midnight but must never schedule after it.\n                day_end = datetime.datetime.combine(\n                    report_date + datetime.timedelta(days=1),\n                    datetime.time.min,\n                    tzinfo=self.timezone,\n                ) - datetime.timedelta(seconds=5)\n                if due > day_end:\n                    due = day_end\n',
    "clamp report due to natural day",
)
text = replace_once(
    text,
    '                if isinstance(value, dict) and str(value.get("umo") or "").strip()\n',
    '                if isinstance(value, dict)\n                and str(value.get("umo") or "").strip()\n                and bool(value.get("auto_enabled", False))\n',
    "scheduler only enabled groups",
)
text = replace_once(
    text,
    '            for group_id in groups:\n                members = self._daily_group_members(group_id, date_key)\n',
    '            for group_id, group_meta in groups.items():\n                enabled_since = str(group_meta.get("auto_enabled_since") or "")\n                if enabled_since and date_key < enabled_since:\n                    continue\n                members = self._daily_group_members(group_id, date_key)\n',
    "do not backfill before group opt-in",
)
pattern = re.compile(
    r'    async def pigsty_daily_report\(self, event: AstrMessageEvent\):\n.*?\n    async def terminate\(self\):',
    re.S,
)
replacement = '''    async def pigsty_daily_report(self, event: AstrMessageEvent, args: str = ""):\n        """Manual report plus per-group automatic-push management."""\n        self._claim_command_event(event)\n        if not self.enable_daily_report:\n            await event.send(event.plain_result("猪圈日报功能已在配置中关闭。"))\n            return\n        group_id = self._event_group_id(event)\n        if not group_id:\n            await event.send(event.plain_result("猪圈日报只能在群聊中使用。"))\n            return\n        actor_id = self._event_sender_id(event)\n        action = str(args or "").strip().lower()\n        enable_actions = {"开启", "開啟", "启用", "啟用", "on", "enable"}\n        disable_actions = {"关闭", "關閉", "停用", "off", "disable"}\n        status_actions = {"状态", "狀態", "status"}\n        if action in enable_actions | disable_actions | status_actions:\n            enabled = self._daily_report_group_auto_enabled(group_id)\n            if action in status_actions:\n                global_state = "开启" if self.daily_report_auto_send else "关闭"\n                group_state = "已开启" if enabled else "未开启（默认）"\n                await event.send(\n                    event.plain_result(\n                        f"本群猪圈日报自动推送：{group_state}\\n"\n                        f"全局自动推送总开关：{global_state}\\n"\n                        f"计划时间：{self.daily_report_send_time}，随机延迟最多 "\n                        f"{self.daily_report_random_delay_minutes} 分钟（不会跨自然日）"\n                    )\n                )\n                return\n            if not self._daily_report_group_manager(event, actor_id):\n                await event.send(\n                    event.plain_result("只有群主、群管理员或 AstrBot 管理员可以修改日报自动推送。")\n                )\n                return\n            target = action in enable_actions\n            self._set_daily_report_group_auto(group_id, target, actor_id=actor_id)\n            if target:\n                suffix = "" if self.daily_report_auto_send else "；但全局自动推送总开关目前关闭"\n                await event.send(\n                    event.plain_result(\n                        f"已开启本群猪圈日报自动推送。将在自然日结束前按 "\n                        f"{self.daily_report_send_time} + 随机延迟发送{suffix}。"\n                    )\n                )\n            else:\n                await event.send(event.plain_result("已关闭本群猪圈日报自动推送。手动 /猪圈日报 仍可使用。"))\n            return\n        if action:\n            await event.send(\n                event.plain_result("用法：/猪圈日报、/猪圈日报 开启、/猪圈日报 关闭、/猪圈日报 状态")\n            )\n            return\n\n        draw_date = self._today().isoformat()\n        members = self._daily_group_members(group_id, draw_date)\n        if not members:\n            await event.send(event.plain_result("今天本群还没有 RollPig 数据，晚点再来看看吧。"))\n            return\n        output = None\n        try:\n            report = await self._build_daily_report_payload(group_id, draw_date)\n            output = await asyncio.to_thread(self.render_daily_report_image, report)\n            await event.send(event.image_result(str(output.absolute())))\n        except Exception as exc:\n            logger.error(f"生成猪圈日报失败：{exc}", exc_info=True)\n            await event.send(event.plain_result("猪圈日报生成失败，请稍后再试。"))\n        finally:\n            if output:\n                output.unlink(missing_ok=True)\n\n    async def terminate(self):'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(f"replace pigsty_daily_report: {count}")
write(path, text)

path = "main.py"
text = read(path)
text = replace_once(
    text,
    '    async def pigsty_daily_report(self, event: AstrMessageEvent):\n        """Render the current group\'s rich report; manual views never sacrifice."""\n        return await super().pigsty_daily_report(event)\n',
    '    async def pigsty_daily_report(self, event: AstrMessageEvent, args: str=\'\'):\n        """查看日报，或由群管理开启/关闭本群自动推送。"""\n        return await super().pigsty_daily_report(event, args)\n',
    "main report wrapper args",
)
write(path, text)

# --- Local review proxy: image bug + sensitive read CSRF --------------------
path = "legacy_main.py"
text = read(path)
text = replace_once(
    text,
    '            return (\n                str(payload.get("__rollpig_csrf", "") or "")\n                if isinstance(payload, dict)\n                else ""\n            )\n',
    '            if isinstance(payload, dict):\n                token = str(payload.get("__rollpig_csrf", "") or "")\n                if token:\n                    return token\n            query = getattr(request_obj, "query", None)\n            if query is not None:\n                return str(query.get("__rollpig_csrf", "") or "")\n            return ""\n',
    "allow csrf in sensitive GET query",
)
text = replace_once(
    text,
    '    async def page_public_source_reviews(self):\n        """Only the maintainer instance may list the server-side review queue."""\n        try:\n            if not self._public_source_admin_token():\n',
    '    async def page_public_source_reviews(self):\n        """Only the maintainer instance may list the server-side review queue."""\n        try:\n            if not self._is_authorized_write_request(request):\n                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})\n            if not self._public_source_admin_token():\n',
    "protect review list proxy",
)
text = replace_once(
    text,
    '            submission_id = str(request.args.get("id") or "").strip()\n            data = await self._public_source_review_image_payload(submission_id)\n',
    '            if not self._is_authorized_write_request(request):\n                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})\n            submission_id = str(request.query.get("id") or "").strip()\n            data = await self._public_source_review_image_payload(submission_id)\n',
    "fix review image query and protect proxy",
)
write(path, text)

# --- Review service: abuse ceiling + suspicious duplicate hints ------------
path = "source_service/app.py"
text = read(path)
text = replace_once(text, "import datetime as dt\n", "import datetime as dt\nfrom difflib import SequenceMatcher\n", "difflib import")
text = replace_once(
    text,
    "MAX_PENDING_PER_DAY = 5\n",
    "MAX_PENDING_PER_DAY = 5\nMAX_PENDING_TOTAL = 200\nDUPLICATE_NAME_THRESHOLD = 0.82\nDUPLICATE_IMAGE_DISTANCE = 8\n",
    "review safety constants",
)
helpers = '''\n\ndef _name_key(value: object) -> str:\n    text = str(value or "").strip().lower().replace("豬", "猪")\n    return re.sub(r"[^0-9a-z\\u4e00-\\u9fff]+", "", text)\n\n\ndef _image_dhash(raw: bytes) -> int:\n    with Image.open(io.BytesIO(raw)) as image:\n        method = getattr(Image, "Resampling", Image).LANCZOS\n        pixels = list(image.convert("L").resize((9, 8), method).getdata())\n    value = 0\n    for y in range(8):\n        row = y * 9\n        for x in range(8):\n            value = (value << 1) | int(pixels[row + x] > pixels[row + x + 1])\n    return value\n\n\ndef _duplicate_hints(\n    record: dict[str, str], image: bytes, catalog_index: list[dict[str, object]]\n) -> list[dict[str, object]]:\n    name_key = _name_key(record.get("name"))\n    image_hash = _image_dhash(image)\n    hints: list[dict[str, object]] = []\n    for item in catalog_index:\n        reasons: list[str] = []\n        candidate_name = str(item.get("name") or "")\n        candidate_key = str(item.get("name_key") or "")\n        ratio = SequenceMatcher(None, name_key, candidate_key).ratio() if name_key and candidate_key else 0.0\n        if name_key and name_key == candidate_key:\n            reasons.append("名称相同")\n        elif ratio >= DUPLICATE_NAME_THRESHOLD:\n            reasons.append(f"名称相似 {round(ratio * 100)}%")\n        distance = 64\n        candidate_hash = item.get("image_dhash")\n        if isinstance(candidate_hash, int):\n            distance = (image_hash ^ candidate_hash).bit_count()\n            if distance <= DUPLICATE_IMAGE_DISTANCE:\n                reasons.append(f"图片相似 dHash={distance}")\n        if reasons:\n            hints.append(\n                {\n                    "id": str(item.get("id") or ""),\n                    "name": candidate_name,\n                    "reasons": reasons,\n                    "name_similarity": round(ratio, 3),\n                    "image_distance": distance if distance < 64 else None,\n                }\n            )\n    hints.sort(\n        key=lambda item: (\n            int(item.get("image_distance") if item.get("image_distance") is not None else 99),\n            -float(item.get("name_similarity") or 0),\n            str(item.get("id") or ""),\n        )\n    )\n    return hints[:5]\n'''
needle = "\n\nclass ReviewApplication:\n"
if helpers not in text:
    text = replace_once(text, needle, helpers + needle, "duplicate helper insertion")
methods = '''\n    def _catalog_records(self) -> list[dict]:\n        path = self.config.catalog_root / "pig.json"\n        try:\n            records = json.loads(path.read_text(encoding="utf-8-sig"))\n        except Exception as exc:\n            raise APIError(HTTPStatus.SERVICE_UNAVAILABLE, "公共豬源目錄暫不可用") from exc\n        return [dict(item) for item in records if isinstance(item, dict)]\n\n    def _catalog_duplicate_index(self) -> list[dict[str, object]]:\n        image_root = self.config.catalog_root / "image"\n        index: list[dict[str, object]] = []\n        for record in self._catalog_records():\n            pig_id = str(record.get("id") or "")\n            item: dict[str, object] = {\n                "id": pig_id,\n                "name": str(record.get("name") or pig_id),\n                "name_key": _name_key(record.get("name")),\n                "image_dhash": None,\n            }\n            for path in sorted(image_root.glob(f"{pig_id}.*")):\n                if not path.is_file():\n                    continue\n                try:\n                    item["image_dhash"] = _image_dhash(path.read_bytes())\n                    break\n                except Exception:\n                    continue\n            index.append(item)\n        return index\n\n'''
needle = "    def _catalog_ids(self) -> set[str]:\n"
if methods not in text:
    text = replace_once(text, needle, methods + needle, "catalog duplicate methods")
text = replace_once(
    text,
    '        with self._connect() as connection:\n            recent = connection.execute(\n',
    '        with self._connect() as connection:\n            pending_total = int(\n                connection.execute("SELECT COUNT(*) FROM submissions WHERE status = \'pending\'").fetchone()[0]\n            )\n            if pending_total >= MAX_PENDING_TOTAL:\n                raise APIError(HTTPStatus.TOO_MANY_REQUESTS, "公共豬源待审核队列已满，请稍后再试")\n            recent = connection.execute(\n',
    "global pending ceiling",
)
old_list = '''        with self._connect() as connection:\n            rows = connection.execute(\n                "SELECT submission_id,pig_id,name,description,analysis,image_sha256,"\n                "client_version,status,reviewer_note,resource_version,submitted_at,reviewed_at "\n                "FROM submissions WHERE status = ? ORDER BY submitted_at DESC LIMIT 50",\n                (status,),\n            ).fetchall()\n        return [dict(row) for row in rows]\n'''
new_list = '''        with self._connect() as connection:\n            rows = connection.execute(\n                "SELECT submission_id,pig_id,name,description,analysis,image_path,image_sha256,"\n                "client_version,status,reviewer_note,resource_version,submitted_at,reviewed_at "\n                "FROM submissions WHERE status = ? ORDER BY submitted_at DESC LIMIT 50",\n                (status,),\n            ).fetchall()\n        catalog_index = self._catalog_duplicate_index()\n        items: list[dict] = []\n        for row in rows:\n            item = dict(row)\n            image_path = Path(str(item.pop("image_path", "")))\n            try:\n                item["duplicate_hints"] = _duplicate_hints(\n                    {"name": str(item.get("name") or "")},\n                    image_path.read_bytes(),\n                    catalog_index,\n                )\n            except Exception:\n                item["duplicate_hints"] = []\n            items.append(item)\n        return items\n'''
text = replace_once(text, old_list, new_list, "review list duplicate hints")
write(path, text)

# --- Admin UI ---------------------------------------------------------------
path = "pages/pig-manager/index.html"
text = read(path)
css = '''\n    .review-dup{margin-top:10px;padding:9px 10px;border:1px solid color-mix(in srgb,var(--orange) 32%,var(--line));border-radius:10px;background:color-mix(in srgb,var(--orange) 8%,transparent);font-size:10px;color:var(--muted)}\n    .review-dup b{color:var(--orange)}.review-dup-item{margin-top:4px}\n'''
if css not in text:
    text = replace_once(text, "</style>", css + "  </style>", "review duplicate css")
text = replace_once(
    text,
    "async function paintReviewCanvas(canvas,submissionId){const d=await get('source/reviews/image',{id:submissionId}),",
    "async function paintReviewCanvas(canvas,submissionId){const d=await get('source/reviews/image',{id:submissionId,__rollpig_csrf:csrfToken}),",
    "review image csrf",
)
old_fn = re.search(r"function renderSourceReviews\(\)\{.*?\}\nasync function loadSourceReviews\(\)\{.*?\}\n", text, re.S)
if not old_fn:
    raise RuntimeError("review render functions not found")
new_fn = '''function reviewDuplicateHtml(p){const hints=Array.isArray(p.duplicate_hints)?p.duplicate_hints:[];if(!hints.length)return'';return`<div class="review-dup"><b>疑似重复 ${hints.length} 项</b>${hints.map(h=>`<div class="review-dup-item">${esc(h.name||h.id)} · ${esc((h.reasons||[]).join(' / '))}</div>`).join('')}</div>`}\nfunction renderSourceReviews(){const panel=$('sourceReviewPanel');panel.hidden=false;$('sourceReviewMeta').textContent=`${reviewItems.length} 只待审核 · 批准后立即生成新资源版本并原子发布`;if(!reviewItems.length){$('sourceReviewGrid').innerHTML='<div class="empty">目前没有待审核投稿</div>';return}$('sourceReviewGrid').innerHTML=reviewItems.map((p,i)=>`<article class="pig-card" style="--delay:${Math.min(i,18)*35}ms"><div class="pig-thumb"><canvas width="192" height="192" data-review-canvas="${i}" aria-label="${esc(p.name)}"></canvas><div class="image-fallback">🐽</div></div><div class="pig-name">${esc(p.name)}</div><div class="pig-id">${esc(p.pig_id)}</div><div class="pig-desc">${esc(p.description)}</div><div class="review-analysis">${esc(p.analysis)}</div>${reviewDuplicateHtml(p)}<div class="pig-meta"><span>${esc(p.client_version||'未知版本')}</span><span>${esc(formatTime(p.submitted_at))}</span></div><div class="pig-actions"><button class="btn ghost" data-review-reject="${i}">拒绝</button><button class="btn" data-review-approve="${i}">批准发布</button></div></article>`).join('');document.querySelectorAll('[data-review-canvas]').forEach(canvas=>paintReviewCanvas(canvas,reviewItems[Number(canvas.dataset.reviewCanvas)].submission_id).catch(()=>canvas.closest('.pig-thumb').classList.add('broken')));document.querySelectorAll('[data-review-reject]').forEach(b=>b.onclick=()=>reviewPublicSource(reviewItems[Number(b.dataset.reviewReject)],'reject'));document.querySelectorAll('[data-review-approve]').forEach(b=>b.onclick=()=>reviewPublicSource(reviewItems[Number(b.dataset.reviewApprove)],'approve'))}\nasync function loadSourceReviews(){const d=await get('source/reviews',{__rollpig_csrf:csrfToken});if(!d.enabled){$('sourceReviewPanel').hidden=true;reviewItems=[];return d}reviewItems=Array.isArray(d.items)?d.items:[];renderSourceReviews();return d}\n'''
text = text[: old_fn.start()] + new_fn + text[old_fn.end() :]
old_boot = "if(!bridge){document.body.innerHTML='<div class=\"empty\">AstrBot Plugin Page Bridge 不可用</div>'}else{await bridge.ready();busy(true);try{const [,,,,sync]=await Promise.all([loadOverview(),loadPigs(),loadLayers(),loadSourceReviews(),loadResourceStatus(),loadUpdateStatus(),loadStorageStatus()]);if(sync.running)pollSyncCompletion()}catch(e){toast(e.message)}finally{busy(false)}}"
new_boot = "if(!bridge){document.body.innerHTML='<div class=\"empty\">AstrBot Plugin Page Bridge 不可用</div>'}else{await bridge.ready();busy(true);try{await loadOverview();const [,,,sync]=await Promise.all([loadPigs(),loadLayers(),loadSourceReviews(),loadResourceStatus(),loadUpdateStatus(),loadStorageStatus()]);if(sync.running)pollSyncCompletion()}catch(e){toast(e.message)}finally{busy(false)}}"
text = replace_once(text, old_boot, new_boot, "load csrf before sensitive review reads")
write(path, text)

# --- systemd hardening ------------------------------------------------------
path = "deploy/rollpig-source-review.service"
text = read(path)
text = replace_once(
    text,
    "NoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=strict\n",
    "NoNewPrivileges=true\nPrivateTmp=true\nPrivateDevices=true\nProtectSystem=strict\nProtectHome=true\nProtectKernelTunables=true\nProtectKernelModules=true\nProtectControlGroups=true\nLockPersonality=true\nMemoryDenyWriteExecute=true\nRestrictAddressFamilies=AF_UNIX AF_INET AF_INET6\n",
    "systemd hardening",
)
write(path, text)

# --- Documentation ---------------------------------------------------------
path = "docs/DAILY-REPORT.md"
text = read(path)
section = '''\n\n## 群組自動推送（預設關閉）\n\n自動推送採 **per-group opt-in**。即使插件全局 `enable_daily_report` / `daily_report_auto_send` 開啟，新群與既有未標記群也一律視為未開啟，不會因曾經記錄到 `unified_msg_origin` 就自動收到日報。\n\n- `/豬圈日報`：手動查看本群今日報告，不改推送設定；\n- `/豬圈日報 開啟`：群主、群管理員或 AstrBot 管理員開啟本群自動推送；\n- `/豬圈日報 關閉`：關閉本群自動推送；\n- `/豬圈日報 狀態`：查看本群與全局 master switch 狀態。\n\n群組今天才開啟時不會補發開啟日前的舊日報；隨機延遲也會被限制在報告自然日結束前。重啟 catch-up 僅對當時已 opt-in 的群生效。\n'''
if "## 群組自動推送（預設關閉）" not in text:
    text += section
write(path, text)

path = "docs/RESOURCE-SOURCE-MAINTENANCE.md"
text = read(path)
section = '''\n\n## 公開投稿與審核安全邊界\n\n投稿端的 `User-Agent` / `X-RollPig-*` 標頭只是協議門檻，**不是安裝身份認證**；開源客戶端的標頭可以被模擬。因此服務端安全依賴內容校驗、來源 HMAC 指紋節流、全局待審上限與人工批准。管理端另有獨立 Bearer token，token 僅存在維護者主機檔案，不寫入插件配置，也不回傳瀏覽器。\n\n審核頁會提供名稱相似與圖片 dHash 相似的「疑似重複」提示，但不以感知相似自動拒絕，避免誤傷合理變體；同 ID 與待審完全相同圖片仍為硬拒絕。review service 應只監聽 loopback，外部只能經受控 Nginx 反代。\n'''
if "## 公開投稿與審核安全邊界" not in text:
    text += section
write(path, text)

path = "CHANGELOG.md"
text = read(path)
marker = "## [Unreleased]"
entry = '''\n\n### Fixed\n- 豬圈日報自動推送改為群組顯式 opt-in；既有/新群預設關閉，新增 `/豬圈日報 開啟|關閉|狀態`，並限制群主/群管理員/AstrBot 管理員修改。\n- 修復公共源審核圖片因 AstrBot GET query 取參錯誤只顯示 🐽 fallback。\n- 公共源審核新增現役 catalog 名稱與圖片感知相似提示、全局 pending 上限與敏感審核代理 CSRF 防護。\n'''
if "豬圈日報自動推送改為群組顯式 opt-in" not in text:
    text = replace_once(text, marker, marker + entry, "changelog unreleased")
write(path, text)

# --- Regression tests ------------------------------------------------------
test = r'''from __future__ import annotations

import ast
from pathlib import Path

from source_service.app import _duplicate_hints, _image_dhash, _name_key

ROOT = Path(__file__).resolve().parents[1]


def test_daily_report_scheduler_is_per_group_opt_in():
    source = (ROOT / "daily_report_feature.py").read_text(encoding="utf-8")
    assert 'group.setdefault("auto_enabled", False)' in source
    assert 'and bool(value.get("auto_enabled", False))' in source
    assert 'auto_enabled_since' in source
    assert 'date_key < enabled_since' in source
    assert 'day_end = datetime.datetime.combine' in source


def test_daily_report_command_exposes_group_controls_from_main_entrypoint():
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin")
    fn = next(node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "pigsty_daily_report")
    assert [arg.arg for arg in fn.args.args][-1] == "args"
    source = (ROOT / "daily_report_feature.py").read_text(encoding="utf-8")
    for word in ("开启", "关闭", "状态", "群主、群管理员或 AstrBot 管理员"):
        assert word in source


def test_review_image_uses_astrbot_query_and_sensitive_get_csrf():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    assert 'submission_id = str(request.query.get("id") or "").strip()' in source
    assert 'request.args.get("id")' not in source
    assert 'query.get("__rollpig_csrf"' in source
    html = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    assert "source/reviews/image',{id:submissionId,__rollpig_csrf:csrfToken}" in html
    assert "source/reviews',{__rollpig_csrf:csrfToken}" in html


def test_duplicate_hints_find_name_and_visual_similarity():
    from PIL import Image
    import io

    image = Image.new("RGB", (32, 32), "white")
    for x in range(16):
        for y in range(32):
            image.putpixel((x, y), (0, 0, 0))
    buf = io.BytesIO()
    image.save(buf, "PNG")
    raw = buf.getvalue()
    index = [{"id": "old-pig", "name": "测试猪", "name_key": _name_key("测试猪"), "image_dhash": _image_dhash(raw)}]
    hints = _duplicate_hints({"name": "测试豬"}, raw, index)
    assert hints and hints[0]["id"] == "old-pig"
    assert "名称相同" in hints[0]["reasons"]
    assert any("图片相似" in reason for reason in hints[0]["reasons"])


def test_review_service_has_global_pending_ceiling_and_hardened_unit():
    source = (ROOT / "source_service/app.py").read_text(encoding="utf-8")
    assert "MAX_PENDING_TOTAL = 200" in source
    assert "待审核队列已满" in source
    unit = (ROOT / "deploy/rollpig-source-review.service").read_text(encoding="utf-8")
    for directive in ("PrivateDevices=true", "ProtectHome=true", "ProtectKernelTunables=true", "MemoryDenyWriteExecute=true"):
        assert directive in unit
'''
write("tests/test_group_report_source_review_hardening.py", test)

print("applied group report + source review hardening")
