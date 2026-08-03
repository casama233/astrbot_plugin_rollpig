from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:100]!r}")
    write(path, content.replace(old, new, 1))


def replace_region(path: str, start: str, end: str, replacement: str) -> None:
    content = read(path)
    left = content.find(start)
    if left < 0:
        raise RuntimeError(f"{path}: start marker not found: {start!r}")
    right = content.find(end, left)
    if right < 0:
        raise RuntimeError(f"{path}: end marker not found: {end!r}")
    write(path, content[:left] + replacement + content[right:])


PATH = "storage/sqlite_storage.py"

# Legacy/import projection rebuilds must include the schema-v3 normalized tables.
replace_once(
    PATH,
    '        connection.execute("DELETE FROM pig_snapshots")\n'
    '        history = value if isinstance(value, dict) else {}\n',
    '        connection.execute("DELETE FROM pig_snapshots")\n'
    '        connection.execute("DELETE FROM identity_claims")\n'
    '        connection.execute("DELETE FROM identity_aliases")\n'
    '        history = value if isinstance(value, dict) else {}\n',
)
replace_once(
    PATH,
    '''                connection.execute(\n                    "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES (?, ?)",\n                    (str(pig_id), json.dumps(snapshot, ensure_ascii=False, sort_keys=True)),\n                )\n\n    def _project_roast_state''',
    '''                connection.execute(\n                    "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES (?, ?)",\n                    (str(pig_id), json.dumps(snapshot, ensure_ascii=False, sort_keys=True)),\n                )\n\n        claims_root = (\n            history.get("identity_claims")\n            if isinstance(history.get("identity_claims"), dict)\n            else {}\n        )\n        for claim_kind, claims in claims_root.items():\n            for legacy_id, namespaced_id in (\n                claims.items() if isinstance(claims, dict) else []\n            ):\n                if str(legacy_id) and str(namespaced_id):\n                    connection.execute(\n                        "INSERT OR REPLACE INTO identity_claims VALUES (?, ?, ?)",\n                        (str(claim_kind), str(legacy_id), str(namespaced_id)),\n                    )\n\n        aliases_root = (\n            history.get("identity_aliases")\n            if isinstance(history.get("identity_aliases"), dict)\n            else {}\n        )\n        for namespace, bucket in aliases_root.items():\n            by_alias = (\n                bucket.get("by_alias", {}) if isinstance(bucket, dict) else {}\n            )\n            by_user = bucket.get("by_user", {}) if isinstance(bucket, dict) else {}\n            for alias_key, canonical_id in (\n                by_alias.items() if isinstance(by_alias, dict) else []\n            ):\n                alias_text = str(alias_key).lower()\n                canonical_text = str(canonical_id)\n                username = (\n                    str(by_user.get(canonical_text) or alias_key).lstrip("@")\n                    if isinstance(by_user, dict)\n                    else str(alias_key).lstrip("@")\n                )\n                if alias_text and canonical_text:\n                    connection.execute(\n                        "INSERT OR REPLACE INTO identity_aliases("\n                        "namespace, alias_key, canonical_id, username) "\n                        "VALUES (?, ?, ?, ?)",\n                        (str(namespace), alias_text, canonical_text, username),\n                    )\n\n    def _project_roast_state''',
)

project_ai = r'''    @staticmethod
    def _project_ai_copies(connection: sqlite3.Connection, value: Any) -> None:
        connection.execute("DELETE FROM ai_roast_copies")
        connection.execute("DELETE FROM ai_roast_generation_attempts")
        root = value if isinstance(value, dict) else {}
        copies = root.get("copies") if isinstance(root.get("copies"), dict) else {}
        for pig_id, by_date in copies.items():
            if not isinstance(by_date, dict):
                continue
            for generated_date, content in by_date.items():
                text = str(content or "").strip()
                if text:
                    connection.execute(
                        "INSERT INTO ai_roast_copies VALUES (?, ?, ?)",
                        (str(pig_id), str(generated_date), text),
                    )
        attempts = (
            root.get("attempts") if isinstance(root.get("attempts"), dict) else {}
        )
        for pig_id, by_date in attempts.items():
            if not isinstance(by_date, dict):
                continue
            for generated_date, status in by_date.items():
                status_text = str(status)
                if status_text not in {"generating", "ready", "failed"}:
                    continue
                connection.execute(
                    "INSERT OR REPLACE INTO ai_roast_generation_attempts("
                    "pig_id, generated_date, status, owner_token, attempted_at, completed_at) "
                    "VALUES (?, ?, ?, '', 0, 0)",
                    (str(pig_id), str(generated_date), status_text),
                )

'''
replace_region(
    PATH,
    "    @staticmethod\n    def _project_ai_copies(",
    "    @staticmethod\n    def _project_catalog_overrides(",
    project_ai,
)

# Build all compatibility documents from normalized SQL. These are secondary
# export/rollback snapshots, never the authority after sql-primary activation.
helpers = r'''    def _today_document_from_sql(
        self, connection: sqlite3.Connection, preferred_date: str = ""
    ) -> dict[str, Any]:
        selected_date = str(preferred_date or "")
        if not selected_date:
            row = connection.execute("SELECT MAX(draw_date) FROM daily_draws").fetchone()
            selected_date = str(row[0] or "") if row else ""
        records: dict[str, Any] = {}
        if selected_date:
            rows = connection.execute(
                "SELECT user_id, pig_id FROM daily_draws "
                "WHERE draw_date = ? ORDER BY user_id",
                (selected_date,),
            ).fetchall()
            for row in rows:
                pig_id = str(row["pig_id"])
                snapshot = connection.execute(
                    "SELECT payload_json FROM pig_snapshots WHERE pig_id = ?",
                    (pig_id,),
                ).fetchone()
                if snapshot:
                    try:
                        payload = json.loads(str(snapshot["payload_json"]))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        payload = {"id": pig_id}
                else:
                    payload = {"id": pig_id}
                records[str(row["user_id"])] = (
                    payload if isinstance(payload, dict) else {"id": pig_id}
                )
        return {"date": selected_date, "records": records}

    def _compatibility_documents_from_sql(
        self, connection: sqlite3.Connection
    ) -> dict[str, Any]:
        overrides, tombstones = self._catalog_documents_from_sql(connection)
        return {
            "pig_history.json": self._history_document_from_sql(connection),
            "roast_state.json": self._roast_document_from_sql(connection),
            "ai_roast_copies.json": self._ai_document_from_sql(connection),
            "local_overrides.json": overrides,
            "deleted_pigs.json": tombstones,
            "rollpig_today.json": self._today_document_from_sql(connection),
        }

    def _repair_compatibility_documents_tx(
        self, connection: sqlite3.Connection
    ) -> dict[str, Any]:
        documents = self._compatibility_documents_from_sql(connection)
        now = int(time.time())
        for key, value in documents.items():
            self._write_document_tx(connection, key, value, updated_at=now)
        return documents

    @staticmethod
    def _write_authority(connection: sqlite3.Connection) -> str:
        row = connection.execute(
            "SELECT value FROM projection_meta WHERE key = 'write_authority'"
        ).fetchone()
        return str(row[0] or "") if row else ""

'''
replace_once(
    PATH,
    '        return overrides, tombstones\n\n    def load_runtime_snapshot',
    '        return overrides, tombstones\n\n' + helpers + '    def load_runtime_snapshot',
)

# SQL-domain writes must derive secondary documents from the normalized rows.
replace_once(
    PATH,
    '''            roast = self._valid_dict(\n                self._read_document_tx(\n                    connection, "roast_state.json", self._roast_document_default()\n                )\n            )\n            cooldowns = roast.get("cooldowns")\n            if not isinstance(cooldowns, dict):\n                cooldowns = {}\n                roast["cooldowns"] = cooldowns\n            cooldowns[cooldown_key] = now\n''',
    '''            roast = self._roast_document_from_sql(connection)\n''',
)
replace_once(
    PATH,
    '''            rows = connection.execute(\n                "SELECT draw_date, group_id, user_id, roast_count "\n                "FROM daily_roast_counts ORDER BY draw_date, group_id, user_id"\n            ).fetchall()\n            roast = self._valid_dict(\n                self._read_document_tx(\n                    connection, "roast_state.json", self._roast_document_default()\n                )\n            )\n            roast["daily_roast_counts"] = {\n                self._event_key(\n                    str(row["draw_date"]),\n                    str(row["group_id"]),\n                    str(row["user_id"]),\n                ): int(row["roast_count"])\n                for row in rows\n                if int(row["roast_count"]) > 0\n            }\n''',
    '''            roast = self._roast_document_from_sql(connection)\n''',
)
replace_once(
    PATH,
    '''            rows = connection.execute(\n                "SELECT backdoor_key FROM daily_backdoors "\n                "WHERE used = 1 ORDER BY draw_date, actor_id"\n            ).fetchall()\n            roast = self._valid_dict(\n                self._read_document_tx(\n                    connection, "roast_state.json", self._roast_document_default()\n                )\n            )\n            roast["daily_backdoors"] = {\n                str(row["backdoor_key"]): True for row in rows\n            }\n''',
    '''            roast = self._roast_document_from_sql(connection)\n''',
)

catalog_methods = r'''    def upsert_catalog_override(
        self, *, record: dict[str, Any]
    ) -> dict[str, Any]:
        """Upsert one local catalog record and clear its tombstone atomically."""
        payload = self._clone(record)
        pig_id = str(payload.get("id") or "").strip()
        if not pig_id:
            raise ValueError("小猪 ID 无效")
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO catalog_overrides(pig_id, payload_json) VALUES (?, ?) "
                "ON CONFLICT(pig_id) DO UPDATE SET payload_json = excluded.payload_json",
                (pig_id, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )
            connection.execute(
                "DELETE FROM catalog_tombstones WHERE pig_id = ?", (pig_id,)
            )
            overrides, tombstones = self._catalog_documents_from_sql(connection)
            self._write_document_tx(connection, "local_overrides.json", overrides)
            self._write_document_tx(connection, "deleted_pigs.json", tombstones)
            self._set_write_authority(connection)
            return {"overrides": overrides, "tombstones": tombstones}

    def delete_catalog_entry(self, *, pig_id: str) -> dict[str, Any]:
        """Remove a local override and add one tombstone atomically."""
        pig_id = str(pig_id).strip()
        if not pig_id:
            raise ValueError("小猪 ID 无效")
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM catalog_overrides WHERE pig_id = ?", (pig_id,)
            )
            connection.execute(
                "INSERT OR IGNORE INTO catalog_tombstones(pig_id) VALUES (?)",
                (pig_id,),
            )
            overrides, tombstones = self._catalog_documents_from_sql(connection)
            self._write_document_tx(connection, "local_overrides.json", overrides)
            self._write_document_tx(connection, "deleted_pigs.json", tombstones)
            self._set_write_authority(connection)
            return {"overrides": overrides, "tombstones": tombstones}

'''
replace_region(
    PATH,
    "    def upsert_catalog_override(\n",
    "    def create_daily_draw(\n",
    catalog_methods,
)

replace_once(
    PATH,
    '''        history_default = {\n            "version": 1,\n            "users": {},\n            "daily": {},\n            "pig_snapshots": {},\n        }\n        roast_default = {\n            "version": 1,\n            "cooldowns": {},\n            "daily_backdoors": {},\n            "daily_roast_counts": {},\n            "eaten_penalties": {},\n            "eaten_events": {},\n        }\n        today_default = {"date": draw_date, "records": {}}\n\n        with self.transaction() as connection:\n            history = self._valid_dict(\n                self._read_document_tx(connection, "pig_history.json", history_default)\n            )\n            roast = self._valid_dict(\n                self._read_document_tx(connection, "roast_state.json", roast_default)\n            )\n            today_doc = self._valid_dict(\n                self._read_document_tx(connection, "rollpig_today.json", today_default)\n            )\n''',
    '''        with self.transaction() as connection:\n            history = self._history_document_from_sql(connection)\n            roast = self._roast_document_from_sql(connection)\n            today_doc = self._today_document_from_sql(connection, draw_date)\n''',
)
replace_once(
    PATH,
    '''            history = self._valid_dict(\n                self._read_document_tx(\n                    connection,\n                    "pig_history.json",\n                    {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}},\n                )\n            )\n            roast = self._valid_dict(\n                self._read_document_tx(\n                    connection,\n                    "roast_state.json",\n                    {\n                        "version": 1,\n                        "cooldowns": {},\n                        "daily_backdoors": {},\n                        "daily_roast_counts": {},\n                        "eaten_penalties": {},\n                        "eaten_events": {},\n                    },\n                )\n            )\n            today_doc = self._valid_dict(\n                self._read_document_tx(\n                    connection,\n                    "rollpig_today.json",\n                    {"date": draw_date, "records": {}},\n                )\n            )\n''',
    '''            history = self._history_document_from_sql(connection)\n            roast = self._roast_document_from_sql(connection)\n            today_doc = self._today_document_from_sql(connection, draw_date)\n''',
)

# Directional verification/rebuild: sql-primary repairs secondary documents from
# SQL. Only pre-SQL/import databases may rebuild projections from documents.
health_region = r'''    @staticmethod
    def _expected_projection_counts(documents: dict[str, Any]) -> dict[str, int]:
        history = documents.get("pig_history.json")
        history = history if isinstance(history, dict) else {}
        users = history.get("users") if isinstance(history.get("users"), dict) else {}
        daily = history.get("daily") if isinstance(history.get("daily"), dict) else {}
        snapshots = (
            history.get("pig_snapshots")
            if isinstance(history.get("pig_snapshots"), dict)
            else {}
        )
        valid_users = {
            str(user_id): value
            for user_id, value in users.items()
            if isinstance(value, dict)
        }
        user_pigs = sum(
            sum(
                1
                for value in raw_user.get("pigs", {}).values()
                if isinstance(value, dict)
            )
            for raw_user in valid_users.values()
            if isinstance(raw_user.get("pigs"), dict)
        )
        daily_draws = 0
        daily_groups = 0
        for day in daily.values():
            if not isinstance(day, dict):
                continue
            records = day.get("records") if isinstance(day.get("records"), dict) else {}
            groups = day.get("groups") if isinstance(day.get("groups"), dict) else {}
            daily_draws += len(records)
            membership: dict[str, set[str]] = {}
            for group_id, members in groups.items():
                if not isinstance(members, list):
                    continue
                for user_id in members:
                    membership.setdefault(str(user_id), set()).add(str(group_id))
            daily_groups += sum(
                len(membership.get(str(user_id), set())) for user_id in records
            )

        claims_root = (
            history.get("identity_claims")
            if isinstance(history.get("identity_claims"), dict)
            else {}
        )
        identity_claims = sum(
            sum(1 for legacy, target in claims.items() if str(legacy) and str(target))
            for claims in claims_root.values()
            if isinstance(claims, dict)
        )
        aliases_root = (
            history.get("identity_aliases")
            if isinstance(history.get("identity_aliases"), dict)
            else {}
        )
        identity_aliases = 0
        for bucket in aliases_root.values():
            by_alias = bucket.get("by_alias", {}) if isinstance(bucket, dict) else {}
            alias_to_user: dict[str, str] = {}
            user_to_alias: dict[str, str] = {}
            for alias, canonical in (
                by_alias.items() if isinstance(by_alias, dict) else []
            ):
                alias_key = str(alias).lower()
                user_id = str(canonical)
                if not alias_key or not user_id:
                    continue
                previous_user = alias_to_user.get(alias_key)
                if previous_user:
                    user_to_alias.pop(previous_user, None)
                previous_alias = user_to_alias.get(user_id)
                if previous_alias:
                    alias_to_user.pop(previous_alias, None)
                alias_to_user[alias_key] = user_id
                user_to_alias[user_id] = alias_key
            identity_aliases += len(alias_to_user)

        roast = documents.get("roast_state.json")
        roast = roast if isinstance(roast, dict) else {}
        counts = roast.get("daily_roast_counts")
        valid_roast_counts = 0
        for raw_key in counts if isinstance(counts, dict) else {}:
            try:
                parsed = json.loads(str(raw_key))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            valid_roast_counts += int(isinstance(parsed, list) and len(parsed) == 3)
        events = roast.get("eaten_events")
        valid_events = 0
        for raw_key, entry in events.items() if isinstance(events, dict) else ():
            if not isinstance(entry, dict):
                continue
            try:
                parsed = json.loads(str(raw_key))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            valid_events += int(isinstance(parsed, list) and len(parsed) == 3)
        backdoors = roast.get("daily_backdoors")
        valid_backdoors = sum(
            1
            for raw_key in backdoors if isinstance(backdoors, dict)
            if ":" in str(raw_key) and str(raw_key).partition(":")[2]
        )

        ai = documents.get("ai_roast_copies.json")
        ai = ai if isinstance(ai, dict) else {}
        copies = ai.get("copies") if isinstance(ai.get("copies"), dict) else {}
        attempts = ai.get("attempts") if isinstance(ai.get("attempts"), dict) else {}
        ai_count = sum(
            sum(1 for content in value.values() if str(content or "").strip())
            for value in copies.values()
            if isinstance(value, dict)
        )
        attempt_count = sum(
            sum(
                1
                for status in value.values()
                if str(status) in {"generating", "ready", "failed"}
            )
            for value in attempts.values()
            if isinstance(value, dict)
        )
        overrides = documents.get("local_overrides.json")
        tombstones = documents.get("deleted_pigs.json")
        penalties = roast.get("eaten_penalties")
        cooldowns = roast.get("cooldowns")
        return {
            "user_stats": len(valid_users),
            "user_pigs": user_pigs,
            "daily_draws": daily_draws,
            "daily_draw_groups": daily_groups,
            "pig_snapshots": sum(
                1 for value in snapshots.values() if isinstance(value, dict)
            ),
            "identity_claims": identity_claims,
            "identity_aliases": identity_aliases,
            "eaten_penalties": sum(
                1 for value in penalties.values() if isinstance(value, dict)
            )
            if isinstance(penalties, dict)
            else 0,
            "eaten_events": valid_events,
            "roast_cooldowns": len(cooldowns) if isinstance(cooldowns, dict) else 0,
            "daily_roast_counts": valid_roast_counts,
            "daily_backdoors": valid_backdoors,
            "ai_roast_copies": ai_count,
            "ai_roast_generation_attempts": attempt_count,
            "catalog_overrides": sum(
                1
                for value in overrides
                if isinstance(value, dict) and str(value.get("id") or "")
            )
            if isinstance(overrides, list)
            else 0,
            "catalog_tombstones": sum(1 for value in tombstones if str(value))
            if isinstance(tombstones, list)
            else 0,
        }

    def _projection_health(self, connection: sqlite3.Connection) -> dict[str, Any]:
        rows = connection.execute("SELECT key, payload FROM documents").fetchall()
        documents: dict[str, Any] = {}
        decode_errors: dict[str, str] = {}
        for row in rows:
            key = str(row["key"])
            try:
                documents[key] = self._decode(str(row["payload"]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                decode_errors[key] = str(exc)
        authority = self._write_authority(connection)
        document_mismatches: dict[str, Any] = {}
        if authority.startswith("sql-primary-"):
            authoritative = self._compatibility_documents_from_sql(connection)
            for key, expected_value in authoritative.items():
                actual_value = documents.get(key)
                if key in decode_errors or actual_value != expected_value:
                    document_mismatches[f"document:{key}"] = {
                        "expected": "normalized-sql",
                        "actual": "invalid-or-stale",
                    }
            expected = self._expected_projection_counts(authoritative)
        else:
            expected = self._expected_projection_counts(documents)
        actual = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in expected
        }
        table_mismatches = {
            table: {"expected": expected[table], "actual": actual[table]}
            for table in expected
            if expected[table] != actual[table]
        }
        mismatches = {**table_mismatches, **document_mismatches}
        for key, message in decode_errors.items():
            if not authority.startswith("sql-primary-") or key not in {
                item.removeprefix("document:") for item in document_mismatches
            }:
                mismatches[f"document:{key}"] = {
                    "expected": "valid-json",
                    "actual": message,
                }
        return {
            "projection_ok": not mismatches,
            "projection_mismatches": mismatches,
            "projection_expected": expected,
            "projection_actual": actual,
            "projection_authority": authority or "compatibility-documents",
            "projection_decode_errors": decode_errors,
        }

    @staticmethod
    def _clear_projections(connection: sqlite3.Connection) -> None:
        for table in (
            "daily_draw_groups",
            "daily_draws",
            "user_pigs",
            "user_stats",
            "pig_snapshots",
            "identity_claims",
            "identity_aliases",
            "eaten_penalties",
            "eaten_events",
            "roast_cooldowns",
            "daily_roast_counts",
            "daily_backdoors",
            "ai_roast_copies",
            "ai_roast_generation_attempts",
            "catalog_overrides",
            "catalog_tombstones",
            "identities",
        ):
            connection.execute(f"DELETE FROM {table}")

    def rebuild_projections(self) -> dict[str, Any]:
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
            connection.execute(
                "INSERT INTO projection_meta(key, value) VALUES ('last_rebuild_at', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(int(time.time())),),
            )
            result = self._projection_health(connection)
            if not result["projection_ok"]:
                raise RuntimeError("projection repair did not reconcile all storage layers")
        return {"ok": True, "action": action, **result}

    def export_documents(self) -> dict[str, Any]:
        with self.transaction() as connection:
            if self._write_authority(connection).startswith("sql-primary-"):
                self._repair_compatibility_documents_tx(connection)
                self._set_write_authority(connection)
            rows = connection.execute(
                "SELECT key, payload FROM documents ORDER BY key"
            ).fetchall()
        return {str(row["key"]): self._decode(str(row["payload"])) for row in rows}

'''
replace_region(
    PATH,
    "    @staticmethod\n    def _expected_projection_counts(",
    "    def document_hashes(\n",
    health_region,
)

# Document the repair direction.
replace_once(
    "CHANGELOG.md",
    "- `identity_claims` 与 `identity_aliases` 改为 SQL 主写；兼容 JSON 继续事务同步，仅用于导出、回滚和旧版灾难恢复。\n",
    "- `identity_claims` 与 `identity_aliases` 改为 SQL 主写；兼容 JSON 继续事务同步，仅用于导出、回滚和旧版灾难恢复。\n"
    "- SQLite 主写数据库检测到兼容文档损坏或过期时，只会由规范化 SQL 反向修复文档；不会再用旧文档覆盖正确数据库。\n",
)

# Regressions for SQL authority, stale-document isolation and directional repair.
tests_path = "tests/test_sqlite_storage.py"
tests = read(tests_path)
tests += r'''


def test_v213_sql_primary_rebuild_repairs_documents_without_overwriting_sql(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    storage.increment_roast_count(
        draw_date="2026-08-04",
        group_id="v2|qq|group|9",
        user_id="v2|qq|user|1",
        cutoff_date="2026-07-27",
    )
    storage.store_ai_roast_copy(
        pig_id="pig-a",
        generated_date="2026-08-04",
        content="SQL 保留文案",
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    with storage.transaction() as connection:
        connection.execute(
            "UPDATE documents SET payload = 'not-json', payload_sha256 = 'broken' "
            "WHERE key = 'pig_history.json'"
        )
        connection.execute(
            "UPDATE documents SET payload = '{\"version\":1}', payload_sha256 = 'broken' "
            "WHERE key = 'roast_state.json'"
        )
        connection.execute(
            "UPDATE documents SET payload = '{\"version\":2,\"copies\":{},\"attempts\":{}}', "
            "payload_sha256 = 'broken' WHERE key = 'ai_roast_copies.json'"
        )
    manager = StorageManager(tmp_path, mode="auto")
    assert isinstance(manager.backend, SQLiteStorage)
    assert manager._last_action == {"status": "auto-rebuilt-projections"}
    snapshot = manager.backend.load_runtime_snapshot()
    assert snapshot["history"]["daily"]["2026-08-04"]["records"][
        "v2|qq|user|1"
    ] == "pig-a"
    roast_key = json.dumps(
        ["2026-08-04", "v2|qq|group|9", "v2|qq|user|1"],
        ensure_ascii=False,
    )
    assert snapshot["roast_state"]["daily_roast_counts"][roast_key] == 1
    assert snapshot["ai_roast_copies"]["copies"]["pig-a"]["2026-08-04"] == "SQL 保留文案"
    documents = manager.backend.export_documents()
    assert documents["pig_history.json"]["daily"]["2026-08-04"]["records"][
        "v2|qq|user|1"
    ] == "pig-a"
    assert documents["ai_roast_copies.json"]["copies"]["pig-a"][
        "2026-08-04"
    ] == "SQL 保留文案"


def test_v213_domain_draw_write_ignores_stale_compatibility_documents(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
    )
    with storage.transaction() as connection:
        connection.execute(
            "UPDATE documents SET payload = ? WHERE key = 'pig_history.json'",
            ('{"version":1,"users":{},"daily":{},"pig_snapshots":{}}',),
        )
        connection.execute(
            "UPDATE documents SET payload = ? WHERE key = 'roast_state.json'",
            ('{"version":1,"cooldowns":{},"daily_backdoors":{},"daily_roast_counts":{},"eaten_penalties":{},"eaten_events":{}}',),
        )
        connection.execute(
            "UPDATE documents SET payload = ? WHERE key = 'rollpig_today.json'",
            ('{"date":"","records":{}}',),
        )
    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|2",
        pig={"id": "pig-b", "name": "B"},
    )
    day = result["history"]["daily"]["2026-08-04"]
    assert day["draws"] == 2
    assert day["records"] == {
        "v2|qq|user|1": "pig-a",
        "v2|qq|user|2": "pig-b",
    }
    with storage._connection() as connection:
        stored = json.loads(
            connection.execute(
                "SELECT payload FROM documents WHERE key = 'pig_history.json'"
            ).fetchone()[0]
        )
    assert stored["daily"]["2026-08-04"]["draws"] == 2


def test_v213_projection_health_covers_schema3_tables(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.claim_legacy_identity(
        namespaced="v2|qq|user|1", legacy="1", kind="users"
    )
    storage.remember_identity_alias(
        namespace="telegram@bot",
        canonical_id="v2|telegram@bot|user|1",
        username="PigOne",
    )
    storage.claim_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner",
        attempted_at=1.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    verification = storage.verify()
    assert verification["projection_ok"] is True
    assert verification["projection_actual"]["identity_claims"] == 1
    assert verification["projection_actual"]["identity_aliases"] == 1
    assert verification["projection_actual"]["ai_roast_generation_attempts"] == 1
'''
write(tests_path, tests)

source_path = "tests/test_source_regressions.py"
source = read(source_path)
source += r'''


def test_v213_sql_authority_repairs_documents_in_the_safe_direction():
    storage_source = (ROOT / "storage" / "sqlite_storage.py").read_text(
        encoding="utf-8"
    )
    assert 'authority.startswith("sql-primary-")' in storage_source
    assert "_repair_compatibility_documents_tx" in storage_source
    assert 'action = "repaired-compatibility-documents-from-sql"' in storage_source
    assert "history = self._history_document_from_sql(connection)" in storage_source
    assert "roast = self._roast_document_from_sql(connection)" in storage_source
    assert "today_doc = self._today_document_from_sql(connection, draw_date)" in storage_source
'''
write(source_path, source)

print("v2.13 SQL-authority hardening applied")
