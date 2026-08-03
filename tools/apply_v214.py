from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return source.replace(old, new, 1)


def replace_class_method(
    source: str, class_name: str, method_name: str, replacement: str
) -> str:
    tree = ast.parse(source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method = next(
        node
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
    )
    lines = source.splitlines(keepends=True)
    start = method.lineno - 1
    end = method.end_lineno
    return "".join(lines[:start]) + replacement.rstrip() + "\n\n" + "".join(lines[end:])


# Storage capability contract.
base_path = ROOT / "storage" / "base.py"
base = base_path.read_text(encoding="utf-8")
base = replace_once(
    base,
    "    supports_runtime_snapshot = False\n",
    "    supports_runtime_snapshot = False\n    supports_dashboard_analytics = False\n",
    "base analytics capability",
)
base = replace_once(
    base,
    "    # Transitional domain read API. JSONStorage keeps using the in-memory\n",
    "    def get_dashboard_overview(self, **kwargs: Any) -> dict[str, Any] | None:\n"
    "        return None\n\n"
    "    # Transitional domain read API. JSONStorage keeps using the in-memory\n",
    "base dashboard API",
)
base_path.write_text(base, encoding="utf-8")


# SQLite schema, indexes, aggregation and repair observability.
sqlite_path = ROOT / "storage" / "sqlite_storage.py"
sqlite = sqlite_path.read_text(encoding="utf-8")
sqlite = sqlite.replace(
    "v2.13 makes normalized tables authoritative for runtime startup snapshots.",
    "v2.14 also serves dashboard analytics directly from normalized SQL tables.",
    1,
)
sqlite = replace_once(
    sqlite,
    "    supports_runtime_snapshot = True\n    schema_version = 4\n",
    "    supports_runtime_snapshot = True\n"
    "    supports_dashboard_analytics = True\n"
    "    schema_version = 5\n",
    "sqlite capability and schema",
)
sqlite = replace_once(
    sqlite,
    "                CREATE INDEX IF NOT EXISTS idx_eaten_events_date_group\n"
    "                    ON eaten_events(event_date, group_id);\n",
    "                CREATE INDEX IF NOT EXISTS idx_eaten_events_date_group\n"
    "                    ON eaten_events(event_date, group_id);\n"
    "                CREATE INDEX IF NOT EXISTS idx_daily_draws_date_pig\n"
    "                    ON daily_draws(draw_date, pig_id);\n"
    "                CREATE INDEX IF NOT EXISTS idx_user_pigs_pig_user\n"
    "                    ON user_pigs(pig_id, user_id);\n"
    "                CREATE INDEX IF NOT EXISTS idx_user_pigs_first_unlocked\n"
    "                    ON user_pigs(first_unlocked, pig_id);\n",
    "dashboard indexes",
)
sqlite = replace_once(
    sqlite,
    "                    connection.execute(\n"
    "                        \"INSERT OR IGNORE INTO schema_migrations(version, applied_at) \"\n"
    "                        \"VALUES (4, unixepoch())\"\n"
    "                    )\n"
    "                connection.execute(\"COMMIT\")\n",
    "                    connection.execute(\n"
    "                        \"INSERT OR IGNORE INTO schema_migrations(version, applied_at) \"\n"
    "                        \"VALUES (4, unixepoch())\"\n"
    "                    )\n"
    "                if 5 not in migrated:\n"
    "                    connection.execute(\n"
    "                        \"INSERT OR IGNORE INTO schema_migrations(version, applied_at) \"\n"
    "                        \"VALUES (5, unixepoch())\"\n"
    "                    )\n"
    "                connection.execute(\"COMMIT\")\n",
    "schema v5 migration",
)

analytics_methods = '''    @staticmethod
    def _analytics_observability(
        connection: sqlite3.Connection,
    ) -> dict[str, Any]:
        metadata = {
            str(row["key"]): str(row["value"])
            for row in connection.execute(
                "SELECT key, value FROM projection_meta WHERE key IN ("
                "'write_authority', 'last_repair_action', 'last_repair_reason', "
                "'last_repair_at')"
            ).fetchall()
        }
        schema_row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()
        try:
            repaired_at = int(metadata.get("last_repair_at") or 0)
        except (TypeError, ValueError):
            repaired_at = 0
        return {
            "analytics_source": "normalized-sql",
            "schema_version": int(schema_row[0] if schema_row else 0),
            "write_authority": metadata.get("write_authority", ""),
            "last_repair_action": metadata.get("last_repair_action", ""),
            "last_repair_reason": metadata.get("last_repair_reason", ""),
            "last_repair_at": repaired_at,
        }

    def get_dashboard_overview(
        self,
        *,
        start_date: str,
        end_date: str,
        catalog_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        """Aggregate dashboard metrics without rebuilding the history document."""
        started = time.monotonic()
        catalog = {str(item) for item in catalog_ids if str(item)}
        with self._lock, self._connection() as connection:
            summary = connection.execute(
                "SELECT COUNT(*) AS users, "
                "COALESCE(SUM(total_draws), 0) AS draws FROM user_stats"
            ).fetchone()
            total_users = int(summary["users"] if summary else 0)
            total_draws = int(summary["draws"] if summary else 0)

            pig_rows = connection.execute(
                "SELECT pig_id, COALESCE(SUM(draw_count), 0) AS draws, "
                "COUNT(*) AS collectors FROM user_pigs GROUP BY pig_id"
            ).fetchall()
            pig_stats = [
                {
                    "id": str(row["pig_id"]),
                    "draws": int(row["draws"]),
                    "collectors": int(row["collectors"]),
                }
                for row in pig_rows
                if str(row["pig_id"]) in catalog
            ]
            unlocked_total = sum(item["collectors"] for item in pig_stats)
            average_unlocked = unlocked_total / total_users if total_users else 0.0
            average_rate = (
                average_unlocked / len(catalog) * 100 if catalog else 0.0
            )
            top_pigs = sorted(
                pig_stats,
                key=lambda item: (-item["draws"], -item["collectors"], item["id"]),
            )[:10]

            trend = [
                {
                    "date": str(row["draw_date"]),
                    "users": int(row["users"]),
                    "draws": int(row["draws"]),
                    "new_unlocks": int(row["new_unlocks"]),
                }
                for row in connection.execute(
                    "SELECT draw_date, COUNT(DISTINCT user_id) AS users, "
                    "COUNT(*) AS draws, COALESCE(SUM(was_new_unlock), 0) AS new_unlocks "
                    "FROM daily_draws WHERE draw_date BETWEEN ? AND ? "
                    "GROUP BY draw_date ORDER BY draw_date",
                    (str(start_date), str(end_date)),
                ).fetchall()
            ]
            observability = self._analytics_observability(connection)

        observability["query_elapsed_ms"] = round(
            (time.monotonic() - started) * 1000, 3
        )
        return {
            "total_users": total_users,
            "total_draws": total_draws,
            "average_unlocked": average_unlocked,
            "average_unlock_rate": average_rate,
            "trend": trend,
            "top_pigs": top_pigs,
            "observability": observability,
        }

'''
sqlite = replace_once(
    sqlite,
    "    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:\n",
    analytics_methods
    + "    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:\n",
    "sqlite analytics methods",
)

rebuild_method = '''    def rebuild_projections(
        self, *, reason: str = "manual"
    ) -> dict[str, Any]:
        reason_text = str(reason or "manual")[:80]
        with self.transaction() as connection:
            authority = self._write_authority(connection)
            if authority.startswith("sql-primary-"):
                self._repair_compatibility_documents_tx(connection)
                self._set_write_authority(connection)
                action = "repaired-compatibility-documents-from-sql"
            else:
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
                action = "rebuilt-normalized-projections-from-documents"
            repaired_at = str(int(time.time()))
            metadata = {
                "last_rebuild_at": repaired_at,
                "last_repair_at": repaired_at,
                "last_repair_action": action,
                "last_repair_reason": reason_text,
            }
            for key, value in metadata.items():
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
            result = self._projection_health(connection)
            if not result["projection_ok"]:
                raise RuntimeError(
                    "projection repair did not reconcile all storage layers"
                )
        return {"ok": True, "action": action, "reason": reason_text, **result}
'''
sqlite = replace_class_method(sqlite, "SQLiteStorage", "rebuild_projections", rebuild_method)

health_method = '''    def health(self) -> dict[str, Any]:
        observability = {
            "analytics_source": "normalized-sql",
            "write_authority": "",
            "last_repair_action": "",
            "last_repair_reason": "",
            "last_repair_at": 0,
        }
        try:
            verification = self.verify(deep=False)
            with self._lock, self._connection() as connection:
                observability = self._analytics_observability(connection)
        except Exception as exc:
            self._last_error = str(exc)
            verification = {
                "ok": False,
                "integrity": "error",
                "foreign_key_errors": 0,
                "schema_version": 0,
                "documents": 0,
                "daily_draws": 0,
                "users": 0,
            }
        return {
            "backend": self.backend_name,
            "transactional_batch": True,
            "wal": True,
            "last_write_at": self._last_write_at,
            "last_error": self._last_error,
            "database_size": self.database_path.stat().st_size
            if self.database_path.exists()
            else 0,
            **observability,
            **verification,
        }
'''
sqlite = replace_class_method(sqlite, "SQLiteStorage", "health", health_method)
sqlite_path.write_text(sqlite, encoding="utf-8")


# Distinguish startup auto repair from manual repair.
manager_path = ROOT / "storage" / "manager.py"
manager = manager_path.read_text(encoding="utf-8")
manager = replace_once(
    manager,
    "                candidate.rebuild_projections()\n",
    "                candidate.rebuild_projections(reason=\"startup-auto\")\n",
    "startup repair reason",
)
manager = replace_once(
    manager,
    "            result = target.rebuild_projections()\n",
    "            result = target.rebuild_projections(reason=\"manual\")\n",
    "manual repair reason",
)
manager_path.write_text(manager, encoding="utf-8")


# Route dashboard overview through SQL when the backend supports it.
main_path = ROOT / "main.py"
main = main_path.read_text(encoding="utf-8")
main = main.replace("AstrBot-RollPig/2.13.1", "AstrBot-RollPig/2.14.0", 1)
tree = ast.parse(main)
plugin = next(
    node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
)
overview_node = next(
    node
    for node in plugin.body
    if isinstance(node, ast.FunctionDef) and node.name == "_build_overview_data"
)
lines = main.splitlines(keepends=True)
overview = "".join(lines[overview_node.lineno - 1 : overview_node.end_lineno])
marker = '            catalog_ids = {str(pig.get("id")) for pig in self.pig_list}\n'
sql_branch = '''            if getattr(self.storage, "supports_dashboard_analytics", False):
                start_date = (today - datetime.timedelta(days=13)).isoformat()
                end_date = today.isoformat()
                stored = self.storage.get_dashboard_overview(
                    start_date=start_date,
                    end_date=end_date,
                    catalog_ids=tuple(sorted(catalog_ids)),
                ) or {}
                trend_rows = {
                    str(item.get("date") or ""): item
                    for item in stored.get("trend", [])
                    if isinstance(item, dict)
                }
                trend = []
                for offset in range(13, -1, -1):
                    day = today - datetime.timedelta(days=offset)
                    item = trend_rows.get(day.isoformat(), {})
                    trend.append(
                        {
                            "date": f"{day.month}/{day.day}",
                            "users": int(item.get("users", 0)),
                            "draws": int(item.get("draws", 0)),
                            "new_unlocks": int(item.get("new_unlocks", 0)),
                        }
                    )
                names = {
                    str(pig.get("id")): str(pig.get("name") or pig.get("id"))
                    for pig in self.pig_list
                }
                top_pigs = [
                    {
                        "id": str(item.get("id") or ""),
                        "name": names.get(
                            str(item.get("id") or ""),
                            str(item.get("id") or ""),
                        ),
                        "draws": int(item.get("draws", 0)),
                        "collectors": int(item.get("collectors", 0)),
                    }
                    for item in stored.get("top_pigs", [])
                    if str(item.get("id") or "") in names
                ]
                today_item = trend_rows.get(end_date, {})
                return {
                    "metrics": {
                        "total_users": int(stored.get("total_users", 0)),
                        "total_draws": int(stored.get("total_draws", 0)),
                        "catalog_count": len(catalog_ids),
                        "today_users": int(today_item.get("users", 0)),
                        "average_unlocked": round(
                            float(stored.get("average_unlocked", 0)), 2
                        ),
                        "average_unlock_rate": round(
                            float(stored.get("average_unlock_rate", 0)), 2
                        ),
                    },
                    "trend": trend,
                    "top_pigs": top_pigs,
                    "analytics": stored.get("observability", {}),
                }
'''
overview = replace_once(overview, marker, marker + sql_branch, "main SQL overview branch")
main = (
    "".join(lines[: overview_node.lineno - 1])
    + overview.rstrip()
    + "\n\n"
    + "".join(lines[overview_node.end_lineno :])
)
main_path.write_text(main, encoding="utf-8")


# Expose analytics source and last repair in the storage status panel.
page_path = ROOT / "pages" / "pig-manager" / "index.html"
page = page_path.read_text(encoding="utf-8")
status_pattern = re.compile(
    r"function renderStorageStatus\(d\)\{.*?\}\nasync function loadStorageStatus",
    re.DOTALL,
)
status_replacement = '''function formatStorageRepair(h){if(!h.last_repair_action)return'尚无修复记录';const reason=h.last_repair_reason?` · ${h.last_repair_reason}`:'';const when=Number(h.last_repair_at||0)?` · ${new Date(Number(h.last_repair_at)*1000).toLocaleString()}`:'';return`${h.last_repair_action}${reason}${when}`}
function renderStorageStatus(d){storageSnapshot=d;const h=d.health||{},sqlite=d.active_backend==='sqlite',ok=Boolean(h.ok),mode=d.configured_mode||'auto',sqlAnalytics=h.analytics_source==='normalized-sql',repair=formatStorageRepair(h);$('storageStatus').innerHTML=`<span class="pill ${sqlite?'ok':''}">当前 ${esc(d.active_backend||'json')}</span><span class="pill">配置 ${esc(mode)}</span><span class="pill ${ok?'ok':'warn'}">${d.database_exists?(ok?'数据库完整':'数据库需检查'):'尚未建库'}</span>${h.schema_version?`<span class="pill">Schema ${h.schema_version}</span>`:''}${sqlAnalytics?'<span class="pill ok">统计 SQL</span>':'<span class="pill">统计 JSON</span>'}${h.documents!==undefined?`<span class="pill">文档 ${h.documents}</span>`:''}${h.users!==undefined?`<span class="pill">用户 ${h.users}</span>`:''}${h.last_repair_action?`<span class="pill">最近修复 ${esc(h.last_repair_reason||'manual')}</span>`:''}`;$('storageMigrateBtn').disabled=sqlite||mode==='json';$('storageRollbackBtn').disabled=!sqlite;$('storageVerifyBtn').disabled=!d.database_exists;$('storageRebuildBtn').disabled=!d.database_exists;if(d.last_error)setStorageFeedback(`后端已安全降级：${d.last_error}`);else if(sqlite)setStorageFeedback(`SQLite 正在使用 WAL 与事务；统计来源：${sqlAnalytics?'规范化 SQL':'兼容快照'}；最近修复：${repair}；最近 JSON 备份：${d.latest_backup||'无'}。`);else if(mode==='json')setStorageFeedback('配置已强制使用 JSON；需要改为 auto 后才能从面板迁移。');else setStorageFeedback('当前继续使用 JSON；迁移会先备份、临时建库、哈希对账并通过完整性检查后才切换。')}
async function loadStorageStatus'''
page, replacements = status_pattern.subn(status_replacement, page, count=1)
if replacements != 1:
    raise RuntimeError(f"storage status UI: expected one match, found {replacements}")
page_path.write_text(page, encoding="utf-8")


# Version and changelog.
metadata_path = ROOT / "metadata.yaml"
metadata = metadata_path.read_text(encoding="utf-8")
metadata = replace_once(
    metadata, 'version: "2.13.1"', 'version: "2.14.0"', "metadata version"
)
metadata_path.write_text(metadata, encoding="utf-8")

changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
entry = '''# 更新
## v2.14.0 (2026-08-04)
### SQL 原生统计与存储可观测性
- 管理面板的总用户、累计抽取、平均解锁、近 14 日趋势与热门小猪改为直接聚合规范化 SQL 表，不再遍历整份 `pig_history` 运行快照。
- schema 5 新增日期／小猪与图鉴反向查询索引，改善大数据量下的趋势和收藏统计性能。
- 存储状态面板显示统计来源、schema、写入权威以及最近一次自动／手动修复的动作、原因和时间。
- 保留 JSON 后端的原有统计回退路径；SQLite 不可用或主动回滚后，管理面板仍可正常工作。
- 增加十万用户与三十万每日记录的 SQL 聚合压力测试及索引、修复元数据回归测试。

'''
changelog = replace_once(changelog, "# 更新\n", entry, "changelog v2.14")
changelog_path.write_text(changelog, encoding="utf-8")


# Functional, observability and scale tests.
test_path = ROOT / "tests" / "test_dashboard_sql_analytics.py"
test_path.write_text(
    '''from __future__ import annotations

import time

from storage import SQLiteStorage, StorageManager


def _pig(pig_id: str) -> dict:
    return {
        "id": pig_id,
        "name": pig_id,
        "description": "测试",
        "analysis": "测试",
    }


def test_sql_dashboard_overview_aggregates_normalized_tables(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.create_daily_draw(
        draw_date="2026-08-01", user_id="u1", pig=_pig("pig-a")
    )
    storage.create_daily_draw(
        draw_date="2026-08-02", user_id="u1", pig=_pig("pig-a")
    )
    storage.create_daily_draw(
        draw_date="2026-08-02", user_id="u2", pig=_pig("pig-b")
    )

    overview = storage.get_dashboard_overview(
        start_date="2026-08-01",
        end_date="2026-08-14",
        catalog_ids=("pig-a", "pig-b"),
    )
    assert overview["total_users"] == 2
    assert overview["total_draws"] == 3
    assert overview["average_unlocked"] == 1
    assert overview["average_unlock_rate"] == 50
    trend = {item["date"]: item for item in overview["trend"]}
    assert trend["2026-08-01"] == {
        "date": "2026-08-01",
        "users": 1,
        "draws": 1,
        "new_unlocks": 1,
    }
    assert trend["2026-08-02"] == {
        "date": "2026-08-02",
        "users": 2,
        "draws": 2,
        "new_unlocks": 1,
    }
    assert overview["top_pigs"][:2] == [
        {"id": "pig-a", "draws": 2, "collectors": 1},
        {"id": "pig-b", "draws": 1, "collectors": 1},
    ]
    assert overview["observability"]["analytics_source"] == "normalized-sql"
    assert overview["observability"]["schema_version"] == 5


def test_dashboard_indexes_and_repair_observability(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.rebuild_projections(reason="startup-auto")
    health = storage.health()
    assert health["analytics_source"] == "normalized-sql"
    assert health["last_repair_reason"] == "startup-auto"
    assert health["last_repair_action"]
    assert health["last_repair_at"] > 0
    with storage._connection() as connection:
        indexes = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
    assert {
        "idx_daily_draws_date_pig",
        "idx_user_pigs_pig_user",
        "idx_user_pigs_first_unlocked",
    } <= indexes


def test_sql_dashboard_analytics_scales_to_hundred_thousand_users(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    with storage.transaction() as connection:
        connection.execute(
            """
            WITH RECURSIVE seq(x) AS (
                SELECT 0 UNION ALL SELECT x + 1 FROM seq WHERE x < 99999
            )
            INSERT INTO identities(
                identity_key, namespace, identity_type, raw_id, legacy_id, created_at
            )
            SELECT printf('u%06d', x), 'load', 'user', printf('%d', x),
                   printf('%d', x), 1 FROM seq
            """
        )
        connection.execute(
            """
            INSERT INTO user_stats(
                user_id, total_draws, active_days, duplicate_streak, payload_json
            )
            SELECT identity_key, 3, 3, 2, '{}'
            FROM identities WHERE namespace = 'load'
            """
        )
        connection.execute(
            """
            INSERT INTO user_pigs(
                user_id, pig_id, first_unlocked, last_drawn, draw_count
            )
            SELECT identity_key,
                   printf('pig-%02d', CAST(raw_id AS INTEGER) % 50),
                   '2026-08-01', '2026-08-03', 3
            FROM identities WHERE namespace = 'load'
            """
        )
        connection.execute(
            """
            WITH RECURSIVE seq(x) AS (
                SELECT 0 UNION ALL SELECT x + 1 FROM seq WHERE x < 299999
            )
            INSERT INTO daily_draws(
                draw_date, user_id, pig_id, original_pig_id,
                group_ids_json, created_at, was_new_unlock
            )
            SELECT date('2026-08-01', printf('+%d day', x % 3)),
                   printf('u%06d', x % 100000),
                   printf('pig-%02d', (x % 100000) % 50),
                   '', '[]', 1, CASE WHEN x % 3 = 0 THEN 1 ELSE 0 END
            FROM seq
            """
        )

    started = time.monotonic()
    overview = storage.get_dashboard_overview(
        start_date="2026-08-01",
        end_date="2026-08-14",
        catalog_ids=tuple(f"pig-{index:02d}" for index in range(50)),
    )
    elapsed = time.monotonic() - started
    assert overview["total_users"] == 100_000
    assert overview["total_draws"] == 300_000
    assert sum(item["draws"] for item in overview["trend"]) == 300_000
    assert elapsed < 8
''',
    encoding="utf-8",
)

# Existing schema expectations now target v5.
for path in ROOT.joinpath("tests").glob("test_*.py"):
    if path == test_path:
        continue
    source = path.read_text(encoding="utf-8")
    source = source.replace("assert version == 4", "assert version == 5")
    path.write_text(source, encoding="utf-8")

regression_path = ROOT / "tests" / "test_source_regressions.py"
regression = regression_path.read_text(encoding="utf-8")
regression += '''


def test_v214_dashboard_uses_sql_analytics_and_exposes_repair_status():
    overview = ast.get_source_segment(SOURCE, _method("_build_overview_data")) or ""
    storage_source = (ROOT / "storage" / "sqlite_storage.py").read_text(
        encoding="utf-8"
    )
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "supports_dashboard_analytics" in overview
    assert "get_dashboard_overview" in overview
    assert "COUNT(DISTINCT user_id)" in storage_source
    assert "idx_daily_draws_date_pig" in storage_source
    assert "last_repair_reason" in storage_source
    assert "统计 SQL" in page
    assert "最近修复" in page
'''
regression_path.write_text(regression, encoding="utf-8")

# Validate all edited Python before CI installs dependencies.
for path in (
    base_path,
    sqlite_path,
    manager_path,
    main_path,
    test_path,
    regression_path,
):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

print("v2.14.0 dashboard analytics patch applied")
