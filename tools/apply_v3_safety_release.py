from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing replacement in {path}: {old[:120]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_primary_storage() -> None:
    path = Path("storage/sqlite_primary.py")
    text = path.read_text(encoding="utf-8")
    old_init = '''    def _initialize(self) -> None:
        # Run all historical migrations first, then promote the database to the
        # v3 contract. Existing v2 projections are already transactionally kept
        # in sync with their documents, so promotion must never replay a stale
        # document over non-empty normalized tables.
        super()._initialize()
        with self.transaction() as connection:
            migrated = {
                int(row[0])
                for row in connection.execute(
                    "SELECT version FROM schema_migrations"
                ).fetchall()
            }
            if 6 not in migrated:
                connection.execute("DELETE FROM documents")
                self._set_write_authority(connection)
                now = str(int(time.time()))
                for key, value in {
                    "compatibility_mode": "on-demand",
                    "v3_promoted_at": now,
                    "last_repair_action": "promoted-sql-single-authority",
                    "last_repair_reason": "schema-6",
                    "last_repair_at": now,
                }.items():
                    connection.execute(
                        "INSERT INTO projection_meta(key, value) VALUES (?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (key, value),
                    )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) "
                    "VALUES (6, unixepoch())"
                )
'''
    new_init = '''    def _initialize(self) -> None:
        # Run historical migrations first. Promotion is deliberately guarded:
        # stale compatibility documents may be discarded, but normalized table
        # damage must never be hidden by deleting the last recovery snapshot.
        super()._initialize()
        with self.transaction() as connection:
            migrated = {
                int(row[0])
                for row in connection.execute(
                    "SELECT version FROM schema_migrations"
                ).fetchall()
            }
            if 6 not in migrated:
                integrity = str(
                    connection.execute("PRAGMA integrity_check").fetchone()[0]
                )
                foreign_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
                if integrity != "ok" or foreign_rows:
                    raise RuntimeError(
                        "refusing v3 promotion of an invalid SQLite database"
                    )

                authority = self._write_authority(connection)
                health = self._projection_health(connection)
                table_mismatches = {
                    key: value
                    for key, value in health.get("projection_mismatches", {}).items()
                    if not str(key).startswith("document:")
                }
                if table_mismatches and not authority.startswith("sql-primary-"):
                    if health.get("projection_decode_errors"):
                        raise RuntimeError(
                            "refusing v3 promotion with invalid authority documents"
                        )
                    rows = connection.execute(
                        "SELECT key, payload FROM documents ORDER BY key"
                    ).fetchall()
                    documents = {
                        str(row["key"]): self._decode(str(row["payload"]))
                        for row in rows
                    }
                    self._clear_projections(connection)
                    for key, value in documents.items():
                        self._refresh_projection(connection, key, value)
                    health = self._projection_health(connection)
                    table_mismatches = {
                        key: value
                        for key, value in health.get(
                            "projection_mismatches", {}
                        ).items()
                        if not str(key).startswith("document:")
                    }
                if table_mismatches:
                    raise RuntimeError(
                        "refusing v3 promotion with inconsistent normalized tables"
                    )

                connection.execute("DELETE FROM documents")
                self._set_write_authority(connection)
                now = str(int(time.time()))
                for key, value in {
                    "compatibility_mode": "on-demand",
                    "v3_promoted_at": now,
                    "last_repair_action": "promoted-sql-single-authority",
                    "last_repair_reason": "schema-6",
                    "last_repair_at": now,
                }.items():
                    connection.execute(
                        "INSERT INTO projection_meta(key, value) VALUES (?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (key, value),
                    )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) "
                    "VALUES (6, unixepoch())"
                )
'''
    if old_init not in text:
        raise SystemExit("SQLitePrimaryStorage._initialize target missing")
    text = text.replace(old_init, new_init, 1)

    old_checks = '''            "missing_pig_snapshots": (
                "SELECT COUNT(*) FROM daily_draws LEFT JOIN pig_snapshots "
                "ON pig_snapshots.pig_id = daily_draws.pig_id "
                "WHERE pig_snapshots.pig_id IS NULL"
            ),
            "new_unlock_mismatches": (
'''
    new_checks = '''            "missing_pig_snapshots": (
                "SELECT COUNT(*) FROM daily_draws LEFT JOIN pig_snapshots "
                "ON pig_snapshots.pig_id = daily_draws.pig_id "
                "WHERE pig_snapshots.pig_id IS NULL"
            ),
            "stats_total_draw_mismatches": (
                "SELECT COUNT(*) FROM user_stats WHERE total_draws != COALESCE(("
                "SELECT SUM(user_pigs.draw_count) FROM user_pigs "
                "WHERE user_pigs.user_id = user_stats.user_id), 0)"
            ),
            "stats_active_day_mismatches": (
                "SELECT COUNT(*) FROM user_stats WHERE active_days != ("
                "SELECT COUNT(*) FROM daily_draws "
                "WHERE daily_draws.user_id = user_stats.user_id)"
            ),
            "new_unlock_mismatches": (
'''
    if old_checks not in text:
        raise SystemExit("normalized health checks target missing")
    text = text.replace(old_checks, new_checks, 1)

    old_users = '''            user_ids = [
                str(row[0])
                for row in connection.execute(
                    "SELECT user_id FROM user_pigs UNION SELECT user_id FROM daily_draws"
                ).fetchall()
            ]
            for user_id in user_ids:
                self._remember_identity(connection, user_id)
                existing = connection.execute(
                    "SELECT duplicate_streak, payload_json FROM user_stats WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if existing:
                    continue
                total_draws = int(
                    connection.execute(
                        "SELECT COALESCE(SUM(draw_count), 0) FROM user_pigs WHERE user_id = ?",
                        (user_id,),
                    ).fetchone()[0]
                )
                active_days = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM daily_draws WHERE user_id = ?",
                        (user_id,),
                    ).fetchone()[0]
                )
                payload = {
                    "total_draws": total_draws,
                    "active_days": active_days,
                    "duplicate_streak": 0,
                }
                connection.execute(
                    "INSERT INTO user_stats(" 
                    "user_id, total_draws, active_days, duplicate_streak, payload_json) "
                    "VALUES (?, ?, ?, 0, ?)",
                    (
                        user_id,
                        total_draws,
                        active_days,
                        json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    ),
                )
'''
    new_users = '''            user_ids = [
                str(row[0])
                for row in connection.execute(
                    "SELECT user_id FROM user_stats UNION SELECT user_id FROM user_pigs "
                    "UNION SELECT user_id FROM daily_draws"
                ).fetchall()
            ]
            for user_id in user_ids:
                self._remember_identity(connection, user_id)
                existing = connection.execute(
                    "SELECT duplicate_streak, payload_json FROM user_stats WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                total_draws = int(
                    connection.execute(
                        "SELECT COALESCE(SUM(draw_count), 0) FROM user_pigs WHERE user_id = ?",
                        (user_id,),
                    ).fetchone()[0]
                )
                active_days = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM daily_draws WHERE user_id = ?",
                        (user_id,),
                    ).fetchone()[0]
                )
                duplicate_streak = int(existing["duplicate_streak"]) if existing else 0
                try:
                    payload = (
                        json.loads(str(existing["payload_json"] or "{}"))
                        if existing
                        else {}
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    payload = {}
                payload = payload if isinstance(payload, dict) else {}
                payload.pop("pigs", None)
                payload.update(
                    {
                        "total_draws": total_draws,
                        "active_days": active_days,
                        "duplicate_streak": duplicate_streak,
                    }
                )
                connection.execute(
                    "INSERT INTO user_stats(" 
                    "user_id, total_draws, active_days, duplicate_streak, payload_json) "
                    "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
                    "total_draws = excluded.total_draws, "
                    "active_days = excluded.active_days, "
                    "duplicate_streak = excluded.duplicate_streak, "
                    "payload_json = excluded.payload_json",
                    (
                        user_id,
                        total_draws,
                        active_days,
                        duplicate_streak,
                        json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    ),
                )
'''
    if old_users not in text:
        raise SystemExit("normalized rebuild user stats target missing")
    text = text.replace(old_users, new_users, 1)
    path.write_text(text, encoding="utf-8")


def patch_manager() -> None:
    path = Path("storage/primary_manager.py")
    text = path.read_text(encoding="utf-8")
    old = '''            exported = target.export_documents()
            expected_facts = self._document_facts(documents)
            actual_facts = self._document_facts(exported)
'''
    new = '''            exported = target.export_documents()
            expected_documents = {
                str(key): self._clone(value) for key, value in documents.items()
            }
            expected_documents["pig_history.json"] = (
                SQLitePrimaryStorage._merge_today_into_history(
                    expected_documents.get("pig_history.json"),
                    expected_documents.get("rollpig_today.json"),
                )
            )
            expected_facts = self._document_facts(expected_documents)
            actual_facts = self._document_facts(exported)
'''
    if old not in text:
        raise SystemExit("migration fact comparison target missing")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_tests() -> None:
    path = Path("tests/test_sqlite_v3_primary.py")
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "from storage import SQLitePrimaryStorage, StorageManager",
        "from storage import (\n"
        "    JSONStorage,\n"
        "    SQLitePrimaryStorage,\n"
        "    SQLiteStorage,\n"
        "    StorageManager,\n"
        ")",
        1,
    )
    addition = r'''


def test_v3_auto_migration_accounts_for_orphan_today_document(tmp_path):
    history = {
        "version": 1,
        "users": {},
        "daily": {},
        "pig_snapshots": {},
    }
    today = {
        "date": "2026-08-04",
        "records": {
            "v2|qq|user|7": {"id": "pig-a", "name": "A"},
        },
    }
    (tmp_path / "pig_history.json").write_text(
        __import__("json").dumps(history, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "rollpig_today.json").write_text(
        __import__("json").dumps(today, ensure_ascii=False), encoding="utf-8"
    )

    manager = StorageManager(tmp_path, mode="auto")
    assert isinstance(manager.backend, SQLitePrimaryStorage)
    assert manager.verify()["ok"] is True
    exported = manager.backend.export_documents()["pig_history.json"]
    assert exported["daily"]["2026-08-04"]["records"]["v2|qq|user|7"] == "pig-a"
    assert exported["users"]["v2|qq|user|7"]["total_draws"] == 1


def test_v3_refuses_promotion_when_normalized_tables_are_inconsistent(tmp_path):
    history = {
        "version": 1,
        "users": {
            "v2|qq|user|1": {
                "total_draws": 1,
                "active_days": 1,
                "duplicate_streak": 0,
                "pigs": {
                    "pig-a": {
                        "first_unlocked": "2026-08-04",
                        "last_drawn": "2026-08-04",
                        "count": 1,
                    }
                },
            }
        },
        "daily": {
            "2026-08-04": {
                "draws": 1,
                "new_unlocks": 1,
                "users": ["v2|qq|user|1"],
                "records": {"v2|qq|user|1": "pig-a"},
            }
        },
        "pig_snapshots": {"pig-a": {"id": "pig-a", "name": "A"}},
    }
    legacy = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        set(StorageManager.MANAGED_PATHS),
        fallback=JSONStorage(),
    )
    legacy.save_json(tmp_path / "pig_history.json", history)
    with legacy.transaction() as connection:
        connection.execute("DELETE FROM user_stats")

    manager = StorageManager(tmp_path, mode="auto")
    assert manager.backend.backend_name == "json"
    assert "inconsistent normalized tables" in manager._last_error
    connection = sqlite3.connect(tmp_path / "rollpig.db")
    try:
        assert connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0] == 5
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM user_pigs").fetchone()[0] == 1
    finally:
        connection.close()


def test_v3_verify_and_rebuild_reconcile_user_stat_totals(tmp_path):
    storage = StorageManager(tmp_path, mode="auto").backend
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
    )
    with storage.transaction() as connection:
        connection.execute(
            "UPDATE user_stats SET total_draws = 99, active_days = 77 "
            "WHERE user_id = 'v2|qq|user|1'"
        )
    verification = storage.verify()
    assert verification["ok"] is False
    assert "stats_total_draw_mismatches" in verification["projection_mismatches"]
    assert "stats_active_day_mismatches" in verification["projection_mismatches"]

    repaired = storage.rebuild_projections(reason="test-stats")
    assert repaired["ok"] is True
    assert storage.verify()["ok"] is True
    collection = storage.get_user_collection(("v2|qq|user|1",))
    assert collection["total_draws"] == 1
    assert collection["active_days"] == 1
'''
    if "test_v3_auto_migration_accounts_for_orphan_today_document" in text:
        raise SystemExit("v3 safety tests already present")
    path.write_text(text.rstrip() + addition + "\n", encoding="utf-8")

    source = Path("tests/test_source_regressions.py")
    source_text = source.read_text(encoding="utf-8")
    source_addition = r'''


def test_v3_release_contract_uses_sql_single_authority_and_on_demand_json():
    primary = (ROOT / "storage" / "sqlite_primary.py").read_text(encoding="utf-8")
    manager = (ROOT / "storage" / "primary_manager.py").read_text(encoding="utf-8")
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    config = (ROOT / "_conf_schema.json").read_text(encoding="utf-8")
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'version: "3.0.0"' in metadata
    assert "AstrBot-RollPig/3.0.0" in SOURCE
    assert "sql-primary-v3.0" in primary
    assert '"compatibility_mode": "on-demand"' in primary
    assert 'connection.execute("DELETE FROM documents")' in primary
    assert "RUNTIME_MANAGED_PATHS" in manager
    assert "新安装直接建立 SQLite" in config
    assert "兼容 JSON" in page
    assert "按需生成" in page
'''
    if "test_v3_release_contract_uses_sql_single_authority" in source_text:
        raise SystemExit("v3 source contract test already present")
    source.write_text(source_text.rstrip() + source_addition + "\n", encoding="utf-8")


def patch_release_surface() -> None:
    replace_once("metadata.yaml", 'version: "2.15.0"', 'version: "3.0.0"')
    replace_once(
        "metadata.yaml",
        'desc: "獨立維護的今日小豬增強版 fork，保留原作者署名與 MIT License；支援安全更新與可回滾 SQLite 儲存"',
        'desc: "獨立維護的今日小豬增強版 fork，保留原作者署名與 MIT License；SQLite 單一權威、按需 JSON 備份與安全更新"',
    )
    replace_once(
        "main.py",
        "AstrBot-RollPig/2.15.0 (+https://github.com/casama233/astrbot_plugin_rollpig)",
        "AstrBot-RollPig/3.0.0 (+https://github.com/casama233/astrbot_plugin_rollpig)",
    )
    replace_once(
        "_conf_schema.json",
        "auto：存在且验证通过的 rollpig.db 使用 SQLite，否则继续 JSON；json：强制 JSON；sqlite：要求已完成迁移，数据库无效时安全回退 JSON",
        "auto：新安装直接建立 SQLite，旧 JSON 会先备份并完整对账后自动迁移；json：仅用于紧急灾难回退；sqlite：要求 SQLite，数据库无效时安全回退 JSON",
    )

    changelog = Path("CHANGELOG.md")
    text = changelog.read_text(encoding="utf-8")
    entry = '''## v3.0.0 (2026-08-04)
### SQLite 单一运行时权威
- 规范化 SQLite 表成为唯一运行时权威；每日抽取、吃猪、烤猪、AI 文案、身份映射和后台图鉴热写入不再重建或持久化整份兼容 JSON。
- schema 6 会在完整性、外键与规范化一致性检查通过后晋升既有数据库；旧文档损坏不会覆盖 SQL，规范化表损坏则拒绝晋升并保留恢复资料。
- 新安装在 `auto` 模式直接创建 SQLite；旧 JSON 安装会先完整备份，再导入临时数据库、执行事实级对账与完整性检查后原子切换。
- JSON 兼容文件只在导出、回滚或灾难恢复时从 SQL 按需生成，生成过程不会写回数据库；`storage_backend=json` 保留为显式紧急模式。
- 新增跨进程每日抽取唯一性、事务崩溃回滚、热路径零兼容文档、旧数据自动迁移、晋升拒绝与派生统计修复测试。

'''
    if not text.startswith("# 更新\n"):
        raise SystemExit("unexpected changelog header")
    changelog.write_text("# 更新\n" + entry + text[len("# 更新\n"):], encoding="utf-8")

    page = Path("pages/pig-manager/index.html")
    html = page.read_text(encoding="utf-8")
    replacements = [
        (
            '<div class="sync-copy"><div class="sync-icon">🗄️</div><div><h2>数据存储与迁移</h2><div class="panel-desc">SQLite 使用 WAL、外键与事务保存关键数据；迁移前自动备份全部旧 JSON，失败不会切换后端。可随时导出 JSON ZIP 或安全回滚。</div>',
            '<div class="sync-copy"><div class="sync-icon">🗄️</div><div><h2>数据存储与恢复</h2><div class="panel-desc">SQLite 规范化表是唯一运行时权威；旧 JSON 会先备份并自动迁移，兼容 JSON 仅在导出、回滚或灾难恢复时按需生成。</div>',
        ),
        ('id="storageRebuildBtn">重建索引</button>', 'id="storageRebuildBtn">修复状态</button>'),
        ('id="storageExportBtn">导出 JSON</button>', 'id="storageExportBtn">生成 JSON 备份</button>'),
        ('id="storageMigrateBtn">迁移 SQLite</button>', 'id="storageMigrateBtn">重试迁移</button>'),
        (
            "mode=d.configured_mode||'auto',sqlAnalytics=h.analytics_source==='normalized-sql',repair=formatStorageRepair(h),authority=String(h.write_authority||'compatibility-documents');",
            "mode=d.configured_mode||'auto',sqlAnalytics=h.analytics_source==='normalized-sql',repair=formatStorageRepair(h),authority=String(h.write_authority||'compatibility-documents'),onDemand=h.compatibility_mode==='on-demand';",
        ),
        (
            "${sqlite?`<span class=\"pill\">写入权威 ${esc(authority)}</span>`:''}",
            "${sqlite?`<span class=\"pill\">写入权威 ${esc(authority)}</span><span class=\"pill ${onDemand?'ok':''}\">兼容 JSON ${onDemand?'按需生成':'同步保存'}</span>`:''}",
        ),
        (
            "SQLite 正在使用 WAL 与事务；统计来源：${sqlAnalytics?'规范化 SQL':'兼容快照'}；写入权威：${authority}；最近修复：${repair}；最近 JSON 备份：${d.latest_backup||'无'}。",
            "SQLite 正在使用 WAL 与事务；运行时权威：${authority}；兼容 JSON：${onDemand?'仅在导出或回滚时按需生成':'仍同步保存'}；最近修复：${repair}；最近迁移备份：${d.latest_backup||'无'}。",
        ),
        (
            "当前继续使用 JSON；迁移会先备份、临时建库、哈希对账并通过完整性检查后才切换。",
            "当前已安全回退 JSON；重试迁移会先备份、临时建库、事实对账并通过完整性检查后才切换。",
        ),
        (
            "确定把现有关键 JSON 数据迁移到 SQLite 吗？系统会先完整备份，任何对账或完整性检查失败都不会切换。",
            "确定重试迁移到 SQLite 吗？系统会先完整备份旧 JSON，任何事实对账或完整性检查失败都不会切换。",
        ),
        (
            "正在备份 JSON、建立临时数据库并逐文件对账…",
            "正在备份旧 JSON、建立临时数据库并执行事实对账…",
        ),
        (
            "确定由 SQLite 内保存的兼容文档完整重建查询索引吗？该操作不会修改抽取结果，但期间会暂时锁定数据库写入。",
            "确定检查并修复 SQLite 规范化表的可推导状态吗？不会用旧 JSON 覆盖 SQL，但期间会暂时锁定数据库写入。",
        ),
        ("正在事务性清空并重建 SQL 投影…", "正在事务性检查并修复规范化派生状态…"),
        ("toast('SQLite 索引已重建')", "toast('SQLite 规范化状态已修复')"),
        (
            "JSON ZIP 已保存为 ${d.filename}；SHA-256：${d.sha256}",
            "已从当前 SQL 按需生成 ${d.filename}；SHA-256：${d.sha256}",
        ),
    ]
    for old, new in replacements:
        if old not in html:
            raise SystemExit(f"missing dashboard replacement: {old[:100]!r}")
        html = html.replace(old, new, 1)
    page.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    patch_primary_storage()
    patch_manager()
    patch_tests()
    patch_release_surface()
