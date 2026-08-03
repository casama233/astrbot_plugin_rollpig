from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


main = read("main.py")
main = replace_once(
    main,
    '''try:
    from .storage import JSONStorage
    from .updater import PluginUpdateManager, UpdateError
except ImportError:  # pragma: no cover - direct module loading compatibility
    from storage import JSONStorage
    from updater import PluginUpdateManager, UpdateError
''',
    '''try:
    from .storage import StorageManager, StorageMigrationError
    from .updater import PluginUpdateManager, UpdateError
except ImportError:  # pragma: no cover - direct module loading compatibility
    from storage import StorageManager, StorageMigrationError
    from updater import PluginUpdateManager, UpdateError
''',
    "storage imports",
)
main = main.replace(
    '"AstrBot-RollPig/2.8.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
    '"AstrBot-RollPig/2.9.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
)
main = replace_once(
    main,
    '''        self.panel_update_timeout = min(120.0, max(5.0, panel_update_timeout))

        # 初始化路径
''',
    '''        self.panel_update_timeout = min(120.0, max(5.0, panel_update_timeout))
        storage_backend = str(self.config.get("storage_backend", "auto") or "auto").strip().lower()
        self.storage_backend_mode = (
            storage_backend if storage_backend in {"auto", "json", "sqlite"} else "auto"
        )
        try:
            storage_busy_timeout = int(self.config.get("storage_busy_timeout_ms", 5000))
        except (TypeError, ValueError):
            storage_busy_timeout = 5000
        self.storage_busy_timeout_ms = min(30000, max(1000, storage_busy_timeout))

        # 初始化路径
''',
    "storage configuration",
)
main = replace_once(
    main,
    '''        self._data_lock = threading.RLock()
        self.storage = JSONStorage(lock=self._data_lock)
        self._thumbnail_cache: dict[str, tuple[int, dict]] = {}
''',
    '''        self._data_lock = threading.RLock()
        self.storage_manager = StorageManager(
            self.plugin_data_dir,
            mode=self.storage_backend_mode,
            lock=self._data_lock,
            busy_timeout_ms=self.storage_busy_timeout_ms,
        )
        self.storage = self.storage_manager.backend
        self._storage_admin_lock = asyncio.Lock()
        self._thumbnail_cache: dict[str, tuple[int, dict]] = {}
''',
    "storage manager initialization",
)
update_route = '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/updates/apply",
            self.page_update_apply,
            ["POST"],
            "安全安装今日小猪官方稳定版",
        )
'''
storage_routes = update_route + '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/storage/status",
            self.page_storage_status,
            ["GET"],
            "今日小猪存储后端状态",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/storage/migrate",
            self.page_storage_migrate,
            ["POST"],
            "迁移今日小猪 JSON 数据到 SQLite",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/storage/verify",
            self.page_storage_verify,
            ["POST"],
            "验证今日小猪 SQLite 完整性",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/storage/export",
            self.page_storage_export,
            ["POST"],
            "导出今日小猪 JSON 备份",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/storage/rollback",
            self.page_storage_rollback,
            ["POST"],
            "将今日小猪存储安全回滚到 JSON",
        )
'''
main = replace_once(main, update_route, storage_routes, "storage routes")
page_marker = "    async def page_resource_status(self):\n"
storage_methods = '''    async def page_storage_status(self):
        """管理面板：返回当前后端、数据库版本和最近迁移结果。"""
        try:
            return self._jsonify(
                {"status": "ok", "data": self.storage_manager.status()}
            )
        except Exception as exc:
            logger.exception("读取存储状态失败")
            return self._jsonify(
                {"status": "error", "message": f"读取存储状态失败：{exc}"}
            )

    async def page_storage_migrate(self):
        """管理面板：备份、对账并原子迁移 JSON 到 SQLite。"""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not bool(payload.get("confirm")):
                return self._jsonify({"status": "error", "message": "需要明确确认迁移"})
            async with self._storage_admin_lock:
                data = await asyncio.to_thread(self.storage_manager.migrate_to_sqlite)
                self.storage = self.storage_manager.backend
            logger.info(
                f"存储迁移完成：backend={self.storage.backend_name} "
                f"documents={data.get('documents', 0)}"
            )
            return self._jsonify({"status": "ok", "data": data})
        except StorageMigrationError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.exception("SQLite 迁移失败")
            return self._jsonify({"status": "error", "message": f"SQLite 迁移失败：{exc}"})

    async def page_storage_verify(self):
        """管理面板：执行 SQLite integrity_check 与 foreign_key_check。"""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            async with self._storage_admin_lock:
                data = await asyncio.to_thread(self.storage_manager.verify)
            return self._jsonify({"status": "ok", "data": data})
        except Exception as exc:
            logger.exception("验证存储失败")
            return self._jsonify({"status": "error", "message": f"验证存储失败：{exc}"})

    async def page_storage_export(self):
        """管理面板：导出固定目录中的 JSON ZIP，不接受自定义路径。"""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            async with self._storage_admin_lock:
                data = await asyncio.to_thread(
                    self.storage_manager.export_json_backup
                )
            logger.info(f"存储 JSON 备份已导出：{data.get('filename')}")
            return self._jsonify({"status": "ok", "data": data})
        except StorageMigrationError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.exception("导出 JSON 备份失败")
            return self._jsonify({"status": "error", "message": f"导出失败：{exc}"})

    async def page_storage_rollback(self):
        """管理面板：先把 SQLite 最新文档写回 JSON，再停用数据库。"""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not bool(payload.get("confirm")):
                return self._jsonify({"status": "error", "message": "需要明确确认回滚"})
            async with self._storage_admin_lock:
                data = await asyncio.to_thread(self.storage_manager.rollback_to_json)
                self.storage = self.storage_manager.backend
            logger.warning(
                f"存储已回滚到 JSON：disabled={data.get('disabled_database', '')}"
            )
            return self._jsonify({"status": "ok", "data": data})
        except StorageMigrationError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.exception("回滚 JSON 存储失败")
            return self._jsonify({"status": "error", "message": f"回滚失败：{exc}"})

'''
main = replace_once(main, page_marker, storage_methods + page_marker, "storage handlers")
write("main.py", main)

metadata = read("metadata.yaml")
metadata = re.sub(
    r'^version:\s*"[^"]+"',
    'version: "2.9.0"',
    metadata,
    count=1,
    flags=re.MULTILINE,
)
write("metadata.yaml", metadata)

schema_path = ROOT / "_conf_schema.json"
schema = json.loads(schema_path.read_text(encoding="utf-8"))
schema["storage_backend"] = {
    "description": "数据存储后端",
    "hint": "auto：存在且验证通过的 rollpig.db 使用 SQLite，否则继续 JSON；json：强制 JSON；sqlite：要求已完成迁移，数据库无效时安全回退 JSON",
    "type": "string",
    "default": "auto",
}
schema["storage_busy_timeout_ms"] = {
    "description": "SQLite 写锁等待时间（毫秒）",
    "hint": "范围 1000-30000，默认 5000；仅 SQLite 后端生效",
    "type": "int",
    "default": 5000,
}
schema_path.write_text(
    json.dumps(schema, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
)

html = read("pages/pig-manager/index.html")
update_markup = '''    <section class="panel update-panel">
      <div class="sync-copy"><div class="sync-icon">🛡️</div><div><h2>插件安全更新</h2><div class="panel-desc">只连接官方仓库的最新稳定 Release；下载后先校验、解压检查并备份，再替换插件代码。不会覆盖插件数据，也不会自动重启 AstrBot。</div><div class="status-row" id="updateStatus"><span class="pill">读取版本中…</span></div><div class="sync-feedback" id="updateFeedback" role="status">正在读取版本与存储状态…</div><div class="update-notes" id="updateNotes"></div></div></div>
      <div class="update-actions"><button class="btn ghost" id="updateCheckBtn">检查更新</button><button class="btn" id="updateApplyBtn" disabled>安全更新</button></div>
    </section>
'''
storage_markup = '''    <section class="panel update-panel">
      <div class="sync-copy"><div class="sync-icon">🗄️</div><div><h2>数据存储与迁移</h2><div class="panel-desc">SQLite 使用 WAL、外键与事务保存关键数据；迁移前自动备份全部旧 JSON，失败不会切换后端。可随时导出 JSON ZIP 或安全回滚。</div><div class="status-row" id="storageStatus"><span class="pill">读取存储中…</span></div><div class="sync-feedback" id="storageFeedback" role="status">正在检查后端与数据库完整性…</div></div></div>
      <div class="update-actions"><button class="btn ghost" id="storageVerifyBtn">验证</button><button class="btn ghost" id="storageExportBtn">导出 JSON</button><button class="btn" id="storageMigrateBtn">迁移 SQLite</button><button class="btn danger" id="storageRollbackBtn" disabled>回滚 JSON</button></div>
    </section>

''' + update_markup
html = replace_once(html, update_markup, storage_markup, "storage panel markup")
update_js_anchor = "async function applyPluginUpdate(){"
storage_js = r'''let storageSnapshot=null;
const setStorageFeedback=message=>$('storageFeedback').textContent=message;
function renderStorageStatus(d){storageSnapshot=d;const h=d.health||{},sqlite=d.active_backend==='sqlite',ok=Boolean(h.ok),mode=d.configured_mode||'auto';$('storageStatus').innerHTML=`<span class="pill ${sqlite?'ok':''}">当前 ${esc(d.active_backend||'json')}</span><span class="pill">配置 ${esc(mode)}</span><span class="pill ${ok?'ok':'warn'}">${d.database_exists?(ok?'数据库完整':'数据库需检查'):'尚未建库'}</span>${h.schema_version?`<span class="pill">Schema ${h.schema_version}</span>`:''}${h.documents!==undefined?`<span class="pill">文档 ${h.documents}</span>`:''}${h.users!==undefined?`<span class="pill">用户 ${h.users}</span>`:''}`;$('storageMigrateBtn').disabled=sqlite||mode==='json';$('storageRollbackBtn').disabled=!sqlite;$('storageVerifyBtn').disabled=!d.database_exists;if(d.last_error)setStorageFeedback(`后端已安全降级：${d.last_error}`);else if(sqlite)setStorageFeedback(`SQLite 正在使用 WAL 与事务；最近 JSON 备份：${d.latest_backup||'无'}。`);else if(mode==='json')setStorageFeedback('配置已强制使用 JSON；需要改为 auto 后才能从面板迁移。');else setStorageFeedback('当前继续使用 JSON；迁移会先备份、临时建库、哈希对账并通过完整性检查后才切换。')}
async function loadStorageStatus(){const d=await get('storage/status');renderStorageStatus(d);return d}
async function migrateStorage(){if(storageSnapshot?.configured_mode==='json'){toast('请先把 storage_backend 改为 auto');return}if(!window.confirm('确定把现有关键 JSON 数据迁移到 SQLite 吗？系统会先完整备份，任何对账或完整性检查失败都不会切换。'))return;busy(true);setStorageFeedback('正在备份 JSON、建立临时数据库并逐文件对账…');try{const d=await post('storage/migrate',{confirm:true});toast(`已迁移 ${d.documents||0} 份文档到 SQLite`);await Promise.all([loadStorageStatus(),loadUpdateStatus()])}catch(e){setStorageFeedback(`迁移失败：${e.message}；仍使用原 JSON。`);toast(e.message);try{await loadStorageStatus()}catch{}}finally{busy(false)}}
async function verifyStorage(){busy(true);setStorageFeedback('正在执行 integrity_check 与 foreign_key_check…');try{const d=await post('storage/verify',{});toast(d.ok?'数据库完整性正常':'数据库验证未通过');await loadStorageStatus()}catch(e){toast(e.message)}finally{busy(false)}}
async function exportStorage(){busy(true);try{const d=await post('storage/export',{});toast(`已导出 ${d.filename}`);setStorageFeedback(`JSON ZIP 已保存为 ${d.filename}；SHA-256：${d.sha256}`);await loadStorageStatus()}catch(e){toast(e.message)}finally{busy(false)}}
async function rollbackStorage(){if(!window.confirm('确定把 SQLite 中的最新数据写回 JSON 并停用数据库吗？原数据库会改名保留，不会删除。'))return;if(!window.confirm('再次确认：回滚完成后当前运行实例会立即改用 JSON。'))return;busy(true);setStorageFeedback('正在导出 SQLite 最新文档、原子写回 JSON 并对账…');try{const d=await post('storage/rollback',{confirm:true});toast('已安全回滚到 JSON');await Promise.all([loadStorageStatus(),loadUpdateStatus()])}catch(e){setStorageFeedback(`回滚失败：${e.message}`);toast(e.message);try{await loadStorageStatus()}catch{}}finally{busy(false)}}
'''
html = replace_once(html, update_js_anchor, storage_js + update_js_anchor, "storage javascript")
handlers = "$('syncBtn').onclick=async()=>{$('syncBtn').disabled=true;setSyncFeedback('正在启动云资源同步任务…');try{await post('resources/sync',{});toast('云资源同步已在后台开始');await loadResourceStatus();pollSyncCompletion()}catch(e){setSyncFeedback(`同步启动失败：${e.message}`);toast(e.message);try{await loadResourceStatus()}catch{}}};$('updateCheckBtn').onclick=async()=>{busy(true);try{await checkPluginUpdate()}catch(e){setUpdateFeedback(`检查失败：${e.message}`);toast(e.message)}finally{busy(false)}};$('updateApplyBtn').onclick=applyPluginUpdate;"
new_handlers = handlers + "$('storageMigrateBtn').onclick=migrateStorage;$('storageVerifyBtn').onclick=verifyStorage;$('storageExportBtn').onclick=exportStorage;$('storageRollbackBtn').onclick=rollbackStorage;"
html = replace_once(html, handlers, new_handlers, "storage event handlers")
html = replace_once(
    html,
    "await Promise.all([loadOverview(),loadPigs(),loadResourceStatus(),loadUpdateStatus()]);toast('数据已刷新')",
    "await Promise.all([loadOverview(),loadPigs(),loadResourceStatus(),loadUpdateStatus(),loadStorageStatus()]);toast('数据已刷新')",
    "storage refresh",
)
html = replace_once(
    html,
    "const [,,sync]=await Promise.all([loadOverview(),loadPigs(),loadResourceStatus(),loadUpdateStatus()]);if(sync.running)pollSyncCompletion()",
    "const [,,sync]=await Promise.all([loadOverview(),loadPigs(),loadResourceStatus(),loadUpdateStatus(),loadStorageStatus()]);if(sync.running)pollSyncCompletion()",
    "storage initial load",
)
write("pages/pig-manager/index.html", html)

readme = read("README.md")
readme_anchor = "当前运行数据仍使用兼容旧版本的 JSON 文件，但所有读写已经经由 `StorageBackend`／`JSONStorage` 统一接口处理，为后续 SQLite 迁移保留边界。\n"
readme_replacement = '''### SQLite 存储与安全迁移

v2.9.0 新增可选 SQLite 后端。默认 `storage_backend=auto`：只有 `rollpig.db` 已存在且通过 `PRAGMA integrity_check` 与 `foreign_key_check` 时才会启用 SQLite，否则继续使用原 JSON。旧安装不会静默忽略旧数据。

管理面板可执行迁移、验证、导出 JSON ZIP 与回滚。迁移会先备份七份关键 JSON，建立临时数据库，导入完整兼容文档并刷新正交投影表，逐文件核对 SHA-256 后才原子替换为 `rollpig.db`。失败会保留原 JSON 且不切换。SQLite 使用 `WAL`、`foreign_keys=ON`、`synchronous=NORMAL` 与可配置的 `busy_timeout`。

v2.9 的完整 JSON 文档仍是兼容权威层，`daily_draws`、`user_pigs`、`user_stats`、被吃事件、冷却、AI 文案和图鉴覆盖等表作为同事务投影；后续版本会逐步把高频查询迁移为直接 SQL。
'''
readme = replace_once(readme, readme_anchor, readme_replacement, "readme sqlite section")
write("README.md", readme)

changelog = read("CHANGELOG.md")
entry = '''# 更新
## v2.9.0 (2026-08-03)
### SQLite 存储与可回滚迁移
- 新增 `SQLiteStorage` 与 `StorageManager`；默认 `auto` 只在数据库存在且完整时启用 SQLite，旧安装继续安全使用 JSON。
- 迁移流程先备份七份关键 JSON，临时建库、刷新正交投影、逐文件 SHA-256 对账并执行 SQLite 完整性与外键检查，全部通过后才原子切换。
- 新增 `schema_migrations`、兼容文档表及每日抽取、用户图鉴／统计、猪快照、被吃惩罚／事件、冷却、每日烤猪、后门、AI 文案、图鉴覆盖／删除投影表。
- 管理面板新增存储状态、迁移、验证、JSON ZIP 导出和安全回滚；所有写操作沿用同源与 CSRF 校验，不接受自定义文件路径。
- SQLite 使用 WAL、外键、`synchronous=NORMAL` 和可配置写锁等待；云资源与 PigHub 缓存继续使用 JSON，不纳入关键事务数据库。

'''
if not changelog.startswith("# 更新\n"):
    raise RuntimeError("unexpected changelog header")
changelog = entry + changelog[len("# 更新\n"):]
write("CHANGELOG.md", changelog)

Path(__file__).unlink()
