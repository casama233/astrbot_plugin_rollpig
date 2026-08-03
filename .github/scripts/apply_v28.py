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
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {text.count(old)}")
    return text.replace(old, new, 1)


main = read("main.py")
main = replace_once(
    main,
    "from PIL import ImageDraw, ImageFont, ImageOps\n",
    "from PIL import ImageDraw, ImageFont, ImageOps\n\n"
    "try:\n"
    "    from .storage import JSONStorage\n"
    "    from .updater import PluginUpdateManager, UpdateError\n"
    "except ImportError:  # pragma: no cover - direct module loading compatibility\n"
    "    from storage import JSONStorage\n"
    "    from updater import PluginUpdateManager, UpdateError\n",
    "main imports",
)
main = main.replace(
    '"AstrBot-RollPig/2.6.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
    '"AstrBot-RollPig/2.8.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
)
main = replace_once(
    main,
    "        self.resource_max_file_size = min(50, max(1, max_file_mb)) * 1024 * 1024\n",
    "        self.resource_max_file_size = min(50, max(1, max_file_mb)) * 1024 * 1024\n"
    "        self.panel_update_enabled = bool(self.config.get(\"panel_update_enabled\", True))\n"
    "        try:\n"
    "            panel_update_timeout = float(self.config.get(\"panel_update_timeout\", 30))\n"
    "        except (TypeError, ValueError):\n"
    "            panel_update_timeout = 30\n"
    "        self.panel_update_timeout = min(120.0, max(5.0, panel_update_timeout))\n",
    "update config",
)
main = replace_once(
    main,
    "        self._data_lock = threading.RLock()\n",
    "        self._data_lock = threading.RLock()\n"
    "        self.storage = JSONStorage(lock=self._data_lock)\n",
    "storage initialization",
)
main = replace_once(
    main,
    "        self.pighub_thumbnail_dir.mkdir(parents=True, exist_ok=True)\n\n        # 初始化数据\n",
    "        self.pighub_thumbnail_dir.mkdir(parents=True, exist_ok=True)\n"
    "        self.update_manager = PluginUpdateManager(\n"
    "            self.plugin_dir,\n"
    "            self.plugin_data_dir,\n"
    "            timeout=self.panel_update_timeout,\n"
    "            trust_env=self.resource_use_system_proxy,\n"
    "            logger=logger,\n"
    "        )\n\n"
    "        # 初始化数据\n",
    "updater initialization",
)
resource_route = '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/resources/sync",
            self.page_resource_sync,
            ["POST"],
            "同步今日小猪云资源",
        )
'''
update_routes = resource_route + '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/updates/status",
            self.page_update_status,
            ["GET"],
            "今日小猪版本与存储状态",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/updates/check",
            self.page_update_check,
            ["POST"],
            "检查今日小猪官方稳定版更新",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/updates/apply",
            self.page_update_apply,
            ["POST"],
            "安全安装今日小猪官方稳定版",
        )
'''
main = replace_once(main, resource_route, update_routes, "update routes")

start = main.index("\n    def load_json(")
batch = main.index("\n    def save_json_batch(", start)
end = main.index("\n    def ", batch + 10)
storage_wrappers = '''
    def load_json(self, path: Path, default):
        """Compatibility facade for the configured storage backend."""
        return self.storage.load_json(path, default)

    def save_json(self, path: Path, data):
        self.storage.save_json(path, data)

    def save_json_batch(self, updates: dict[Path, object]) -> None:
        self.storage.save_json_batch(updates)
'''
main = main[:start] + storage_wrappers + main[end:]

page_marker = "    async def page_resource_status(self):\n"
page_methods = '''    async def page_update_status(self):
        """管理面板：返回本地版本、存储后端与最近更新状态。"""
        try:
            data = self.update_manager.status()
            data["storage"] = self.storage.health()
            data["enabled"] = self.panel_update_enabled
            return self._jsonify({"status": "ok", "data": data})
        except UpdateError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})

    async def page_update_check(self):
        """管理面板：仅检查官方仓库最新稳定 Release。"""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not self.panel_update_enabled:
                return self._jsonify({"status": "error", "message": "管理面板更新功能已关闭"})
            data = await self.update_manager.check_for_update()
            data["storage"] = self.storage.health()
            return self._jsonify({"status": "ok", "data": data})
        except UpdateError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.exception("检查插件更新失败")
            return self._jsonify({"status": "error", "message": f"检查更新失败：{exc}"})

    async def page_update_apply(self):
        """管理面板：校验、备份并安装官方稳定 Release，不自动重启。"""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not self.panel_update_enabled:
                return self._jsonify({"status": "error", "message": "管理面板更新功能已关闭"})
            data = await self.update_manager.apply_update(
                confirm_unsigned=bool(payload.get("confirm_unsigned", False))
            )
            return self._jsonify({"status": "ok", "data": data})
        except UpdateError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.exception("安全更新插件失败")
            return self._jsonify({"status": "error", "message": f"安全更新失败：{exc}"})

'''
main = replace_once(main, page_marker, page_methods + page_marker, "update handlers")
write("main.py", main)

metadata = read("metadata.yaml")
metadata = re.sub(r'^version:\s*"[^"]+"', 'version: "2.8.0"', metadata, count=1, flags=re.MULTILINE)
write("metadata.yaml", metadata)

schema_path = ROOT / "_conf_schema.json"
schema = json.loads(schema_path.read_text(encoding="utf-8"))
schema["panel_update_enabled"] = {
    "description": "开启管理面板安全更新",
    "hint": "仅检查并安装 casama233/astrbot_plugin_rollpig 的最新稳定 GitHub Release；不接受任意 URL、分支或预发布版本",
    "type": "bool",
    "default": True,
}
schema["panel_update_timeout"] = {
    "description": "管理面板更新网络超时（秒）",
    "hint": "范围 5-120，默认 30；下载包另有 64 MiB、文件数量与解压体积限制",
    "type": "float",
    "default": 30,
}
schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

html = read("pages/pig-manager/index.html")
html = replace_once(
    html,
    "    .catalog-hero{",
    "    .update-panel{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:20px;margin-top:18px}.update-actions{display:flex;gap:9px;flex-wrap:wrap;justify-content:flex-end}.update-notes{max-width:900px;margin-top:8px;color:var(--muted);font-size:11px;white-space:pre-wrap;max-height:90px;overflow:auto}.pill.warn{color:var(--orange)}\n"
    "    .catalog-hero{",
    "update css",
)
sync_markup = '''    <section class="panel sync-panel">
      <div class="sync-copy"><div class="sync-icon">☁️</div><div><h2>云端公共猪猪资源</h2><div class="panel-desc">云端作为基础层；本地新增与编辑优先覆盖，删除会屏蔽对应云端条目。</div><div class="status-row" id="syncStatus"><span class="pill">读取状态中…</span></div><div class="sync-feedback" id="syncFeedback" role="status">正在读取同步状态…</div></div></div>
      <button class="btn ghost" id="syncBtn">立即同步</button>
    </section>
'''
update_markup = sync_markup + '''
    <section class="panel update-panel">
      <div class="sync-copy"><div class="sync-icon">🛡️</div><div><h2>插件安全更新</h2><div class="panel-desc">只连接官方仓库的最新稳定 Release；下载后先校验、解压检查并备份，再替换插件代码。不会覆盖插件数据，也不会自动重启 AstrBot。</div><div class="status-row" id="updateStatus"><span class="pill">读取版本中…</span></div><div class="sync-feedback" id="updateFeedback" role="status">正在读取版本与存储状态…</div><div class="update-notes" id="updateNotes"></div></div></div>
      <div class="update-actions"><button class="btn ghost" id="updateCheckBtn">检查更新</button><button class="btn" id="updateApplyBtn" disabled>安全更新</button></div>
    </section>
'''
html = replace_once(html, sync_markup, update_markup, "update panel markup")
js_anchor = "const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));"
update_js = r'''let updateSnapshot=null;
const setUpdateFeedback=message=>$('updateFeedback').textContent=message;
function renderUpdateStatus(d){const p=d.pending||d;updateSnapshot=p;const current=d.current_version||p.current_version||'—',latest=p.latest_version||current,available=Boolean(p.update_available),signed=Boolean(p.checksum_available),storage=d.storage||p.storage||{};$('updateStatus').innerHTML=`<span class="pill ok">当前 ${esc(current)}</span><span class="pill ${available?'warn':''}">${available?`可更新 ${esc(latest)}`:'已是最新稳定版'}</span><span class="pill ${signed?'ok':'warn'}">${signed?'SHA-256 可验证':'未附校验文件'}</span><span class="pill">存储 ${esc(storage.backend||'json')}</span>`;$('updateCheckBtn').disabled=Boolean(d.busy)||d.enabled===false;$('updateApplyBtn').disabled=!available||Boolean(d.busy)||d.enabled===false;$('updateApplyBtn').textContent=available?`更新到 ${latest}`:'安全更新';$('updateNotes').textContent=p.notes||'';if(d.enabled===false)setUpdateFeedback('管理面板更新功能已在插件配置中关闭。');else if(d.last_result?.restart_required)setUpdateFeedback(`已安装 ${d.last_result.to_version}；请在合适时机重启 AstrBot 载入新版本。`);else if(available)setUpdateFeedback(signed?'Release 提供 SHA-256，更新时会强制核对。':'Release 未提供 SHA-256；点击更新后必须再次人工确认。');else setUpdateFeedback('只会检查官方仓库的最新稳定 Release，不会自动更新或自动重启。')}
async function loadUpdateStatus(){const d=await get('updates/status');renderUpdateStatus(d);return d}
async function checkPluginUpdate(){const d=await post('updates/check',{});renderUpdateStatus(d);toast(d.update_available?`发现稳定版 ${d.latest_version}`:'当前已是最新稳定版');return d}
async function applyPluginUpdate(){if(!updateSnapshot?.update_available){toast('请先检查更新');return}const unsigned=!updateSnapshot.checksum_available;if(unsigned&&!window.confirm('这个官方 Release 没有附带 SHA-256 校验文件。系统仍会执行仓库身份、HTTPS、ZIP 路径、文件数量、体积、metadata 与 Python 语法检查，并在替换前完整备份。确定继续吗？'))return;busy(true);$('updateApplyBtn').disabled=true;setUpdateFeedback('正在下载、校验、备份并替换插件代码…');try{const d=await post('updates/apply',{confirm_unsigned:unsigned});toast(`已安装 ${d.to_version}，请重启 AstrBot`);setUpdateFeedback(`安装完成，备份已保留。请在合适时机重启 AstrBot 载入 ${d.to_version}。`);await loadUpdateStatus()}catch(e){setUpdateFeedback(`更新失败：${e.message}；现有插件与数据已保留或回滚。`);toast(e.message);try{await loadUpdateStatus()}catch{}}finally{busy(false)}}
'''
html = replace_once(html, js_anchor, update_js + js_anchor, "update javascript")
sync_handler = "$('syncBtn').onclick=async()=>{$('syncBtn').disabled=true;setSyncFeedback('正在启动云资源同步任务…');try{await post('resources/sync',{});toast('云资源同步已在后台开始');await loadResourceStatus();pollSyncCompletion()}catch(e){setSyncFeedback(`同步启动失败：${e.message}`);toast(e.message);try{await loadResourceStatus()}catch{}}};"
html = replace_once(
    html,
    sync_handler,
    sync_handler + "$('updateCheckBtn').onclick=async()=>{busy(true);try{await checkPluginUpdate()}catch(e){setUpdateFeedback(`检查失败：${e.message}`);toast(e.message)}finally{busy(false)}};$('updateApplyBtn').onclick=applyPluginUpdate;",
    "update handlers javascript",
)
html = replace_once(
    html,
    "await Promise.all([loadOverview(),loadPigs(),loadResourceStatus()]);toast('数据已刷新')",
    "await Promise.all([loadOverview(),loadPigs(),loadResourceStatus(),loadUpdateStatus()]);toast('数据已刷新')",
    "refresh update status",
)
html = replace_once(
    html,
    "const [,,sync]=await Promise.all([loadOverview(),loadPigs(),loadResourceStatus()]);if(sync.running)pollSyncCompletion()",
    "const [,,sync]=await Promise.all([loadOverview(),loadPigs(),loadResourceStatus(),loadUpdateStatus()]);if(sync.running)pollSyncCompletion()",
    "initial update status",
)
write("pages/pig-manager/index.html", html)

readme = read("README.md")
readme = replace_once(
    readme,
    "- 查看云资源版本与同步状态，并可在管理面板手动立即同步\n",
    "- 查看云资源版本与同步状态，并可在管理面板手动立即同步\n- 检查并安全安装官方稳定 Release；更新前校验、备份，完成后由管理员手动重启 AstrBot\n",
    "readme panel bullet",
)
readme = replace_once(
    readme,
    "公共资源默认每 24 小时检查一次，单文件限制 10 MiB。下载会校验 manifest 中的尺寸与 SHA-256，并在整包通过后才原子替换；任何失败都继续使用旧缓存或内置资源。\n",
    "公共资源默认每 24 小时检查一次，单文件限制 10 MiB。下载会校验 manifest 中的尺寸与 SHA-256，并在整包通过后才原子替换；任何失败都继续使用旧缓存或内置资源。\n\n"
    "### 管理面板安全更新\n\n"
    "版本更新入口固定连接 `casama233/astrbot_plugin_rollpig` 的最新稳定 GitHub Release，不接受自定义 URL、分支或预发布版本。更新包限制为 64 MiB、最多 3000 个文件和 256 MiB 解压体积，并拒绝路径穿越、符号链接及异常压缩比。若 Release 提供 SHA-256 文件会强制核对；若未提供，管理面板会明确警告并要求二次确认。代码替换前会在插件数据目录创建备份，失败自动回滚，且不会覆盖图鉴、历史、惩罚、本地图片或 AstrBot 配置。安装完成后不会自动重启。\n\n"
    "当前运行数据仍使用兼容旧版本的 JSON 文件，但所有读写已经经由 `StorageBackend`／`JSONStorage` 统一接口处理，为后续 SQLite 迁移保留边界。\n",
    "readme update section",
)
write("README.md", readme)

changelog = read("CHANGELOG.md")
entry = '''# 更新
## v2.8.0 (2026-08-03)
### 存储架构与安全更新
- 新增 `StorageBackend` 抽象与兼容旧数据格式的 `JSONStorage` 后端；现有命令继续读取原 JSON，损坏恢复、批量落盘和回滚集中到统一持久化层，为 SQLite 迁移预留接口。
- 猪圈管理面板新增官方稳定版检查与安全更新按钮；来源固定为 `casama233/astrbot_plugin_rollpig`，拒绝任意 URL、分支和预发布版本。
- 更新包执行 HTTPS／仓库身份、大小、文件数、解压体积、路径穿越、符号链接、异常压缩比、metadata 与 Python 语法检查；Release 提供 SHA-256 时强制核对，未提供时要求二次确认。
- 替换代码前自动备份插件目录，失败恢复旧文件；AstrBot 插件数据与配置不在替换范围，安装完成后只提示手动重启，不自动控制宿主进程。

'''
if not changelog.startswith("# 更新\n"):
    raise RuntimeError("unexpected changelog header")
changelog = entry + changelog[len("# 更新\n"):]
write("CHANGELOG.md", changelog)

ci = read(".github/workflows/ci.yml")
ci = replace_once(
    ci,
    "run: python -m compileall -q main.py rollpig_core.py",
    "run: python -m compileall -q main.py rollpig_core.py updater.py storage",
    "ci compile targets",
)
write(".github/workflows/ci.yml", ci)

regressions = read("tests/test_source_regressions.py")
old_test = '''def test_batch_rollback_removes_newly_created_files():
    method = ast.get_source_segment(SOURCE, _method("save_json_batch")) or ""
    assert "path.unlink(missing_ok=True)" in method
'''
new_test = '''def test_main_delegates_persistence_to_storage_backend():
    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""
    load = ast.get_source_segment(SOURCE, _method("load_json")) or ""
    batch = ast.get_source_segment(SOURCE, _method("save_json_batch")) or ""
    assert "self.storage = JSONStorage" in init
    assert "self.storage.load_json" in load
    assert "self.storage.save_json_batch" in batch


def test_panel_updater_keeps_csrf_and_explicit_unsigned_confirmation():
    check = ast.get_source_segment(SOURCE, _method("page_update_check")) or ""
    apply = ast.get_source_segment(SOURCE, _method("page_update_apply")) or ""
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    assert "_is_authorized_write_request" in check
    assert "_is_authorized_write_request" in apply
    assert "confirm_unsigned" in apply
    assert "window.confirm" in page
    assert "updates/apply" in page
'''
regressions = replace_once(regressions, old_test, new_test, "source regression update")
write("tests/test_source_regressions.py", regressions)

updater = read("updater.py")
updater = updater.replace(
    '''        try:
            archive = zipfile.ZipFile(Path(tempfile.mkstemp(suffix=".zip")[1]))
            archive.close()
        except Exception:
            pass
''',
    "",
)
updater = updater.replace(
    '            return self._clone(default)\n\n    def save_json(self, path: Path, data: Any) -> None:',
    '            self.save_json(path, default)\n            return self._clone(default)\n\n    def save_json(self, path: Path, data: Any) -> None:',
)
# The previous replacement belongs in JSONStorage, not updater; keep updater clean.
write("updater.py", updater)

json_storage = read("storage/json_storage.py")
json_storage = json_storage.replace(
    "            return self._clone(default)\n\n    def save_json(self, path: Path, data: Any) -> None:",
    "            self.save_json(path, default)\n            return self._clone(default)\n\n    def save_json(self, path: Path, data: Any) -> None:",
)
write("storage/json_storage.py", json_storage)

# Remove one-shot integration machinery from the resulting branch.
for relative in (
    ".github/scripts/apply_v28.py",
    ".github/workflows/apply-v28.yml",
):
    path = ROOT / relative
    if path.exists():
        path.unlink()
