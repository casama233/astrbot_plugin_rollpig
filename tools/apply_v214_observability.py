from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sqlite_path = ROOT / "storage" / "sqlite_storage.py"
sqlite = sqlite_path.read_text(encoding="utf-8")
count = sqlite.count("sql-primary-v2.13")
if count < 1:
    raise RuntimeError("expected legacy v2.13 SQL authority markers")
sqlite = sqlite.replace("sql-primary-v2.13", "sql-primary-v2.14")
sqlite_path.write_text(sqlite, encoding="utf-8")

page_path = ROOT / "pages" / "pig-manager" / "index.html"
page = page_path.read_text(encoding="utf-8")
pattern = re.compile(
    r"function renderStorageStatus\(d\)\{.*?\}\nasync function loadStorageStatus",
    re.DOTALL,
)
replacement = '''function renderStorageStatus(d){storageSnapshot=d;const h=d.health||{},sqlite=d.active_backend==='sqlite',ok=Boolean(h.ok),mode=d.configured_mode||'auto',sqlAnalytics=h.analytics_source==='normalized-sql',repair=formatStorageRepair(h),authority=String(h.write_authority||'compatibility-documents');$('storageStatus').innerHTML=`<span class="pill ${sqlite?'ok':''}">当前 ${esc(d.active_backend||'json')}</span><span class="pill">配置 ${esc(mode)}</span><span class="pill ${ok?'ok':'warn'}">${d.database_exists?(ok?'数据库完整':'数据库需检查'):'尚未建库'}</span>${h.schema_version?`<span class="pill">Schema ${h.schema_version}</span>`:''}${sqlAnalytics?'<span class="pill ok">统计 SQL</span>':'<span class="pill">统计 JSON</span>'}${sqlite?`<span class="pill">写入权威 ${esc(authority)}</span>`:''}${h.documents!==undefined?`<span class="pill">文档 ${h.documents}</span>`:''}${h.users!==undefined?`<span class="pill">用户 ${h.users}</span>`:''}${h.last_repair_action?`<span class="pill">最近修复 ${esc(h.last_repair_reason||'manual')}</span>`:''}`;$('storageMigrateBtn').disabled=sqlite||mode==='json';$('storageRollbackBtn').disabled=!sqlite;$('storageVerifyBtn').disabled=!d.database_exists;$('storageRebuildBtn').disabled=!d.database_exists;if(d.last_error)setStorageFeedback(`后端已安全降级：${d.last_error}`);else if(sqlite)setStorageFeedback(`SQLite 正在使用 WAL 与事务；统计来源：${sqlAnalytics?'规范化 SQL':'兼容快照'}；写入权威：${authority}；最近修复：${repair}；最近 JSON 备份：${d.latest_backup||'无'}。`);else if(mode==='json')setStorageFeedback('配置已强制使用 JSON；需要改为 auto 后才能从面板迁移。');else setStorageFeedback('当前继续使用 JSON；迁移会先备份、临时建库、哈希对账并通过完整性检查后才切换。')}
async function loadStorageStatus'''
page, replaced = pattern.subn(replacement, page, count=1)
if replaced != 1:
    raise RuntimeError(f"expected one storage status renderer, found {replaced}")
page_path.write_text(page, encoding="utf-8")

regression_path = ROOT / "tests" / "test_source_regressions.py"
regression = regression_path.read_text(encoding="utf-8")
old = '''    assert "last_repair_reason" in storage_source
    assert "统计 SQL" in page
    assert "最近修复" in page
'''
new = '''    assert "last_repair_reason" in storage_source
    assert "sql-primary-v2.14" in storage_source
    assert "统计 SQL" in page
    assert "写入权威" in page
    assert "最近修复" in page
'''
if regression.count(old) != 1:
    raise RuntimeError("v2.14 regression block not found")
regression = regression.replace(old, new, 1)
regression_path.write_text(regression, encoding="utf-8")

for path in (sqlite_path, regression_path):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

print(f"updated {count} SQL authority markers and storage UI")
