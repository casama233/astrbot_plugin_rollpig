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
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:80]!r}")
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


# ---------------------------------------------------------------------------
# Storage contract
# ---------------------------------------------------------------------------
replace_once(
    "storage/base.py",
    '    supports_domain_reads = False\n    supports_domain_writes = False\n',
    '    supports_domain_reads = False\n    supports_domain_writes = False\n'
    '    supports_runtime_snapshot = False\n',
)
replace_once(
    "storage/base.py",
    '    def delete_catalog_entry(self, **kwargs: Any) -> dict[str, Any]:\n'
    '        raise NotImplementedError\n\n'
    '    # Transitional domain read API.',
    '    def delete_catalog_entry(self, **kwargs: Any) -> dict[str, Any]:\n'
    '        raise NotImplementedError\n\n'
    '    def claim_ai_roast_generation(self, **kwargs: Any) -> dict[str, Any]:\n'
    '        raise NotImplementedError\n\n'
    '    def complete_ai_roast_generation(self, **kwargs: Any) -> dict[str, Any]:\n'
    '        raise NotImplementedError\n\n'
    '    def load_runtime_snapshot(self) -> dict[str, Any]:\n'
    '        raise NotImplementedError\n\n'
    '    # Transitional domain read API.',
)


# ---------------------------------------------------------------------------
# SQLite schema, normalized runtime snapshot and generation claims
# ---------------------------------------------------------------------------
replace_once(
    "storage/sqlite_storage.py",
    '    v2.12 makes normalized tables authoritative for daily draws and eat events.\n',
    '    v2.13 makes normalized tables authoritative for runtime startup snapshots.\n',
)
replace_once(
    "storage/sqlite_storage.py",
    '    supports_domain_writes = True\n    schema_version = 2\n',
    '    supports_domain_writes = True\n    supports_runtime_snapshot = True\n    schema_version = 3\n',
)
replace_once(
    "storage/sqlite_storage.py",
    '''                CREATE TABLE IF NOT EXISTS ai_roast_copies (\n                    pig_id TEXT NOT NULL,\n                    generated_date TEXT NOT NULL,\n                    content TEXT NOT NULL,\n                    PRIMARY KEY (pig_id, generated_date)\n                );\n                CREATE TABLE IF NOT EXISTS catalog_overrides (''',
    '''                CREATE TABLE IF NOT EXISTS ai_roast_copies (\n                    pig_id TEXT NOT NULL,\n                    generated_date TEXT NOT NULL,\n                    content TEXT NOT NULL,\n                    PRIMARY KEY (pig_id, generated_date)\n                );\n                CREATE TABLE IF NOT EXISTS ai_roast_generation_attempts (\n                    pig_id TEXT NOT NULL,\n                    generated_date TEXT NOT NULL,\n                    status TEXT NOT NULL,\n                    owner_token TEXT NOT NULL DEFAULT '',\n                    attempted_at REAL NOT NULL,\n                    completed_at REAL NOT NULL DEFAULT 0,\n                    PRIMARY KEY (pig_id, generated_date),\n                    CHECK (status IN ('generating', 'ready', 'failed'))\n                );\n                CREATE TABLE IF NOT EXISTS identity_claims (\n                    claim_kind TEXT NOT NULL,\n                    legacy_id TEXT NOT NULL,\n                    namespaced_id TEXT NOT NULL,\n                    PRIMARY KEY (claim_kind, legacy_id)\n                );\n                CREATE TABLE IF NOT EXISTS identity_aliases (\n                    namespace TEXT NOT NULL,\n                    alias_key TEXT NOT NULL,\n                    canonical_id TEXT NOT NULL,\n                    username TEXT NOT NULL,\n                    PRIMARY KEY (namespace, alias_key),\n                    UNIQUE (namespace, canonical_id)\n                );\n                CREATE TABLE IF NOT EXISTS catalog_overrides (''',
)
replace_once(
    "storage/sqlite_storage.py",
    '''                connection.execute(\n                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (1, unixepoch())"\n                )\n                connection.execute(\n                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (2, unixepoch())"\n                )\n                connection.execute("COMMIT")''',
    '''                connection.execute(\n                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (1, unixepoch())"\n                )\n                connection.execute(\n                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (2, unixepoch())"\n                )\n                if 3 not in migrated:\n                    history_row = connection.execute(\n                        "SELECT payload FROM documents WHERE key = 'pig_history.json'"\n                    ).fetchone()\n                    try:\n                        history = (\n                            json.loads(str(history_row["payload"])) if history_row else {}\n                        )\n                    except (TypeError, ValueError, json.JSONDecodeError):\n                        history = {}\n                    claims_root = (\n                        history.get("identity_claims", {})\n                        if isinstance(history, dict)\n                        else {}\n                    )\n                    for claim_kind, claims in (\n                        claims_root.items() if isinstance(claims_root, dict) else []\n                    ):\n                        for legacy_id, namespaced_id in (\n                            claims.items() if isinstance(claims, dict) else []\n                        ):\n                            if str(legacy_id) and str(namespaced_id):\n                                connection.execute(\n                                    "INSERT OR REPLACE INTO identity_claims VALUES (?, ?, ?)",\n                                    (str(claim_kind), str(legacy_id), str(namespaced_id)),\n                                )\n                    aliases_root = (\n                        history.get("identity_aliases", {})\n                        if isinstance(history, dict)\n                        else {}\n                    )\n                    for namespace, bucket in (\n                        aliases_root.items() if isinstance(aliases_root, dict) else []\n                    ):\n                        by_alias = (\n                            bucket.get("by_alias", {})\n                            if isinstance(bucket, dict)\n                            else {}\n                        )\n                        by_user = (\n                            bucket.get("by_user", {})\n                            if isinstance(bucket, dict)\n                            else {}\n                        )\n                        for alias_key, canonical_id in (\n                            by_alias.items() if isinstance(by_alias, dict) else []\n                        ):\n                            username = (\n                                str(by_user.get(str(canonical_id)) or alias_key)\n                                if isinstance(by_user, dict)\n                                else str(alias_key)\n                            )\n                            if str(alias_key) and str(canonical_id):\n                                connection.execute(\n                                    "INSERT OR REPLACE INTO identity_aliases "\n                                    "(namespace, alias_key, canonical_id, username) "\n                                    "VALUES (?, ?, ?, ?)",\n                                    (\n                                        str(namespace),\n                                        str(alias_key).lower(),\n                                        str(canonical_id),\n                                        username.lstrip("@"),\n                                    ),\n                                )\n                    ai_row = connection.execute(\n                        "SELECT payload FROM documents WHERE key = 'ai_roast_copies.json'"\n                    ).fetchone()\n                    try:\n                        ai_document = json.loads(str(ai_row["payload"])) if ai_row else {}\n                    except (TypeError, ValueError, json.JSONDecodeError):\n                        ai_document = {}\n                    attempts_root = (\n                        ai_document.get("attempts", {})\n                        if isinstance(ai_document, dict)\n                        else {}\n                    )\n                    for pig_id, attempts in (\n                        attempts_root.items() if isinstance(attempts_root, dict) else []\n                    ):\n                        for generated_date, status in (\n                            attempts.items() if isinstance(attempts, dict) else []\n                        ):\n                            status_text = str(status)\n                            if status_text not in {"generating", "ready", "failed"}:\n                                continue\n                            connection.execute(\n                                "INSERT OR IGNORE INTO ai_roast_generation_attempts "\n                                "(pig_id, generated_date, status, owner_token, attempted_at, completed_at) "\n                                "VALUES (?, ?, ?, '', 0, 0)",\n                                (str(pig_id), str(generated_date), status_text),\n                            )\n                    connection.execute(\n                        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) "\n                        "VALUES (3, unixepoch())"\n                    )\n                connection.execute("COMMIT")''',
)
replace_once(
    "storage/sqlite_storage.py",
    '        return {"version": 1, "copies": {}}\n',
    '        return {"version": 2, "copies": {}, "attempts": {}}\n',
)
content = read("storage/sqlite_storage.py").replace("sql-primary-v2.12", "sql-primary-v2.13")
write("storage/sqlite_storage.py", content)

snapshot_methods = r'''    def _history_document_from_sql(
        self, connection: sqlite3.Connection
    ) -> dict[str, Any]:
        history: dict[str, Any] = {
            "version": 1,
            "users": {},
            "daily": {},
            "pig_snapshots": {},
            "identity_claims": {},
            "identity_aliases": {},
        }
        users = history["users"]
        for row in connection.execute(
            "SELECT user_id, total_draws, active_days, duplicate_streak, payload_json "
            "FROM user_stats ORDER BY user_id"
        ).fetchall():
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            user = payload if isinstance(payload, dict) else {}
            user["total_draws"] = int(row["total_draws"])
            user["active_days"] = int(row["active_days"])
            user["duplicate_streak"] = int(row["duplicate_streak"])
            user["pigs"] = {}
            users[str(row["user_id"])] = user
        for row in connection.execute(
            "SELECT user_id, pig_id, first_unlocked, last_drawn, draw_count "
            "FROM user_pigs ORDER BY user_id, pig_id"
        ).fetchall():
            user_id = str(row["user_id"])
            user = users.setdefault(
                user_id,
                {
                    "total_draws": 0,
                    "active_days": 0,
                    "duplicate_streak": 0,
                    "pigs": {},
                },
            )
            user.setdefault("pigs", {})[str(row["pig_id"])] = {
                "first_unlocked": str(row["first_unlocked"]),
                "last_drawn": str(row["last_drawn"]),
                "count": int(row["draw_count"]),
            }
        daily = history["daily"]
        for row in connection.execute(
            "SELECT draw_date, user_id, pig_id, original_pig_id, was_new_unlock "
            "FROM daily_draws ORDER BY draw_date, user_id"
        ).fetchall():
            draw_date = str(row["draw_date"])
            user_id = str(row["user_id"])
            day = daily.setdefault(
                draw_date,
                {
                    "draws": 0,
                    "new_unlocks": 0,
                    "users": [],
                    "records": {},
                    "eaten_originals": {},
                    "groups": {},
                },
            )
            day["draws"] = int(day.get("draws", 0)) + 1
            day["new_unlocks"] = int(day.get("new_unlocks", 0)) + int(
                row["was_new_unlock"]
            )
            day["users"].append(user_id)
            day["records"][user_id] = str(row["pig_id"])
            original = str(row["original_pig_id"] or "")
            if original:
                day["eaten_originals"][user_id] = original
        for row in connection.execute(
            "SELECT draw_date, user_id, group_id FROM daily_draw_groups "
            "ORDER BY draw_date, group_id, user_id"
        ).fetchall():
            day = daily.setdefault(
                str(row["draw_date"]),
                {
                    "draws": 0,
                    "new_unlocks": 0,
                    "users": [],
                    "records": {},
                    "eaten_originals": {},
                    "groups": {},
                },
            )
            members = day["groups"].setdefault(str(row["group_id"]), [])
            user_id = str(row["user_id"])
            if user_id not in members:
                members.append(user_id)
        for day in daily.values():
            day["users"] = list(dict.fromkeys(str(item) for item in day["users"]))
            if not day["eaten_originals"]:
                day.pop("eaten_originals", None)
        for row in connection.execute(
            "SELECT pig_id, payload_json FROM pig_snapshots ORDER BY pig_id"
        ).fetchall():
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                history["pig_snapshots"][str(row["pig_id"])] = payload
        for row in connection.execute(
            "SELECT claim_kind, legacy_id, namespaced_id FROM identity_claims "
            "ORDER BY claim_kind, legacy_id"
        ).fetchall():
            history["identity_claims"].setdefault(str(row["claim_kind"]), {})[
                str(row["legacy_id"])
            ] = str(row["namespaced_id"])
        for row in connection.execute(
            "SELECT namespace, alias_key, canonical_id, username FROM identity_aliases "
            "ORDER BY namespace, alias_key"
        ).fetchall():
            bucket = history["identity_aliases"].setdefault(
                str(row["namespace"]), {"by_alias": {}, "by_user": {}}
            )
            bucket["by_alias"][str(row["alias_key"])] = str(row["canonical_id"])
            bucket["by_user"][str(row["canonical_id"])] = str(row["username"])
        return history

    def _roast_document_from_sql(
        self, connection: sqlite3.Connection
    ) -> dict[str, Any]:
        roast = self._roast_document_default()
        roast["cooldowns"] = {
            str(row["cooldown_key"]): float(row["last_used_at"])
            for row in connection.execute(
                "SELECT cooldown_key, last_used_at FROM roast_cooldowns "
                "ORDER BY cooldown_key"
            ).fetchall()
        }
        roast["daily_roast_counts"] = {
            self._event_key(
                str(row["draw_date"]), str(row["group_id"]), str(row["user_id"])
            ): int(row["roast_count"])
            for row in connection.execute(
                "SELECT draw_date, group_id, user_id, roast_count "
                "FROM daily_roast_counts ORDER BY draw_date, group_id, user_id"
            ).fetchall()
            if int(row["roast_count"]) > 0
        }
        roast["daily_backdoors"] = {
            str(row["backdoor_key"]): True
            for row in connection.execute(
                "SELECT backdoor_key FROM daily_backdoors WHERE used = 1 "
                "ORDER BY draw_date, actor_id"
            ).fetchall()
        }
        penalties: dict[str, Any] = {}
        for row in connection.execute(
            "SELECT user_id, due_date, failed, payload_json FROM eaten_penalties "
            "ORDER BY user_id"
        ).fetchall():
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            entry = payload if isinstance(payload, dict) else {}
            entry["due_date"] = str(row["due_date"])
            entry["failed"] = bool(row["failed"])
            penalties[str(row["user_id"])] = entry
        roast["eaten_penalties"] = penalties
        events: dict[str, Any] = {}
        for row in connection.execute(
            "SELECT event_key, actor_id, outcome, created_at, payload_json "
            "FROM eaten_events ORDER BY event_date, group_id, user_id"
        ).fetchall():
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            entry = payload if isinstance(payload, dict) else {}
            entry["actor_id"] = str(row["actor_id"])
            entry["outcome"] = str(row["outcome"])
            entry["at"] = int(row["created_at"])
            events[str(row["event_key"])] = entry
        roast["eaten_events"] = events
        return roast

    def _catalog_documents_from_sql(
        self, connection: sqlite3.Connection
    ) -> tuple[list[dict[str, Any]], list[str]]:
        overrides: list[dict[str, Any]] = []
        for row in connection.execute(
            "SELECT pig_id, payload_json FROM catalog_overrides ORDER BY rowid"
        ).fetchall():
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and str(payload.get("id") or row["pig_id"]):
                payload["id"] = str(payload.get("id") or row["pig_id"])
                overrides.append(payload)
        tombstones = [
            str(row["pig_id"])
            for row in connection.execute(
                "SELECT pig_id FROM catalog_tombstones ORDER BY pig_id"
            ).fetchall()
        ]
        return overrides, tombstones

    def load_runtime_snapshot(self) -> dict[str, Any]:
        """Rebuild detached runtime state from normalized SQL tables only."""
        with self._lock, self._connection() as connection:
            history = self._history_document_from_sql(connection)
            roast = self._roast_document_from_sql(connection)
            ai = self._ai_document_from_sql(connection)
            overrides, tombstones = self._catalog_documents_from_sql(connection)
        return {
            "source": "normalized-sql-v3",
            "history": history,
            "roast_state": roast,
            "ai_roast_copies": ai,
            "catalog_overrides": overrides,
            "catalog_tombstones": tombstones,
        }

'''
content = read("storage/sqlite_storage.py")
marker = "    def claim_legacy_identity(\n"
if content.count(marker) != 1:
    raise RuntimeError("claim_legacy_identity marker mismatch")
write("storage/sqlite_storage.py", content.replace(marker, snapshot_methods + marker, 1))

claim_and_alias = r'''    def claim_legacy_identity(
        self,
        *,
        namespaced: str,
        legacy: str,
        kind: str,
        accepted_claims: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Atomically claim one ambiguous legacy key in normalized SQL."""
        namespaced = str(namespaced)
        legacy = str(legacy)
        kind = str(kind)
        accepted = {str(item) for item in accepted_claims if str(item)}
        accepted.add(namespaced)
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT namespaced_id FROM identity_claims "
                "WHERE claim_kind = ? AND legacy_id = ?",
                (kind, legacy),
            ).fetchone()
            claimed_by = str(row["namespaced_id"] if row else "")
            claimed = not claimed_by or claimed_by in accepted
            changed = claimed and claimed_by != namespaced
            if changed:
                connection.execute(
                    "INSERT INTO identity_claims(claim_kind, legacy_id, namespaced_id) "
                    "VALUES (?, ?, ?) ON CONFLICT(claim_kind, legacy_id) DO UPDATE SET "
                    "namespaced_id = excluded.namespaced_id",
                    (kind, legacy, namespaced),
                )
                history = self._history_document_from_sql(connection)
                self._write_document_tx(connection, "pig_history.json", history)
            else:
                history = self._history_document_from_sql(connection)
            self._set_write_authority(connection)
            return {
                "claimed": claimed,
                "storage_key": legacy if claimed else namespaced,
                "history": history,
            }

    def remember_identity_alias(
        self,
        *,
        namespace: str,
        canonical_id: str,
        username: str,
    ) -> dict[str, Any]:
        """Merge one username alias through normalized SQL uniqueness."""
        namespace = str(namespace)
        canonical_id = str(canonical_id)
        username = str(username).lstrip("@")
        alias_key = username.lower()
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT canonical_id, username FROM identity_aliases "
                "WHERE namespace = ? AND alias_key = ?",
                (namespace, alias_key),
            ).fetchone()
            changed = not (
                row
                and str(row["canonical_id"]) == canonical_id
                and str(row["username"]) == username
            )
            if changed:
                connection.execute(
                    "DELETE FROM identity_aliases "
                    "WHERE namespace = ? AND (alias_key = ? OR canonical_id = ?)",
                    (namespace, alias_key, canonical_id),
                )
                connection.execute(
                    "INSERT INTO identity_aliases(" 
                    "namespace, alias_key, canonical_id, username) VALUES (?, ?, ?, ?)",
                    (namespace, alias_key, canonical_id, username),
                )
                history = self._history_document_from_sql(connection)
                self._write_document_tx(connection, "pig_history.json", history)
            else:
                history = self._history_document_from_sql(connection)
            self._set_write_authority(connection)
            return {"changed": changed, "history": history}

'''
replace_region(
    "storage/sqlite_storage.py",
    "    def claim_legacy_identity(\n",
    "    @staticmethod\n    def _roast_document_default",
    claim_and_alias,
)

ai_methods = r'''    def _ai_document_from_sql(
        self, connection: sqlite3.Connection
    ) -> dict[str, Any]:
        document = self._ai_document_default()
        copies: dict[str, dict[str, str]] = {}
        for row in connection.execute(
            "SELECT pig_id, generated_date, content FROM ai_roast_copies "
            "ORDER BY pig_id, generated_date"
        ).fetchall():
            copies.setdefault(str(row["pig_id"]), {})[
                str(row["generated_date"])
            ] = str(row["content"])
        attempts: dict[str, dict[str, str]] = {}
        for row in connection.execute(
            "SELECT pig_id, generated_date, status FROM ai_roast_generation_attempts "
            "ORDER BY pig_id, generated_date"
        ).fetchall():
            attempts.setdefault(str(row["pig_id"]), {})[
                str(row["generated_date"])
            ] = str(row["status"])
        document["copies"] = copies
        document["attempts"] = attempts
        return document

    @staticmethod
    def _selected_ai_copies(document: dict[str, Any], pig_id: str) -> dict[str, str]:
        copies = document.get("copies", {})
        selected = copies.get(str(pig_id), {}) if isinstance(copies, dict) else {}
        return dict(selected) if isinstance(selected, dict) else {}

    @staticmethod
    def _prune_ai_rows(
        connection: sqlite3.Connection, cutoff_date: str, through_date: str
    ) -> None:
        bounds = (str(cutoff_date), str(through_date))
        connection.execute(
            "DELETE FROM ai_roast_copies "
            "WHERE generated_date < ? OR generated_date > ?",
            bounds,
        )
        connection.execute(
            "DELETE FROM ai_roast_generation_attempts "
            "WHERE generated_date < ? OR generated_date > ?",
            bounds,
        )

    def get_ai_roast_copies(
        self,
        *,
        pig_id: str,
        cutoff_date: str,
        through_date: str,
    ) -> dict[str, Any]:
        """Read the rolling seven-day cache from normalized SQL."""
        pig_id = str(pig_id)
        with self.transaction() as connection:
            self._prune_ai_rows(connection, cutoff_date, through_date)
            document = self._ai_document_from_sql(connection)
            self._write_document_tx(connection, "ai_roast_copies.json", document)
            self._set_write_authority(connection)
            return {
                "copies": self._selected_ai_copies(document, pig_id),
                "ai_roast_copies": document,
            }

    def claim_ai_roast_generation(
        self,
        *,
        pig_id: str,
        generated_date: str,
        owner_token: str,
        attempted_at: float,
        cutoff_date: str,
        through_date: str,
    ) -> dict[str, Any]:
        """Grant the one model-call opportunity for one pig and date."""
        pig_id = str(pig_id).strip()
        generated_date = str(generated_date)
        owner_token = str(owner_token).strip()
        if not pig_id or not generated_date or not owner_token:
            raise ValueError("AI 文案生成权参数无效")
        with self.transaction() as connection:
            self._prune_ai_rows(connection, cutoff_date, through_date)
            cached = connection.execute(
                "SELECT content FROM ai_roast_copies "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            if cached:
                document = self._ai_document_from_sql(connection)
                self._write_document_tx(connection, "ai_roast_copies.json", document)
                self._set_write_authority(connection)
                return {
                    "claimed": False,
                    "status": "ready",
                    "content": str(cached["content"]),
                    "copies": self._selected_ai_copies(document, pig_id),
                    "ai_roast_copies": document,
                }
            cursor = connection.execute(
                "INSERT OR IGNORE INTO ai_roast_generation_attempts(" 
                "pig_id, generated_date, status, owner_token, attempted_at, completed_at) "
                "VALUES (?, ?, 'generating', ?, ?, 0)",
                (pig_id, generated_date, owner_token, float(attempted_at)),
            )
            row = connection.execute(
                "SELECT status, owner_token FROM ai_roast_generation_attempts "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            document = self._ai_document_from_sql(connection)
            self._write_document_tx(connection, "ai_roast_copies.json", document)
            self._set_write_authority(connection)
            return {
                "claimed": cursor.rowcount == 1,
                "status": str(row["status"]),
                "owner": str(row["owner_token"]),
                "copies": self._selected_ai_copies(document, pig_id),
                "ai_roast_copies": document,
            }

    def complete_ai_roast_generation(
        self,
        *,
        pig_id: str,
        generated_date: str,
        owner_token: str,
        content: str,
        completed_at: float,
        cutoff_date: str,
        through_date: str,
    ) -> dict[str, Any]:
        """Finish the unique daily attempt as ready or failed."""
        pig_id = str(pig_id).strip()
        generated_date = str(generated_date)
        owner_token = str(owner_token).strip()
        text = str(content or "").strip()
        with self.transaction() as connection:
            self._prune_ai_rows(connection, cutoff_date, through_date)
            attempt = connection.execute(
                "SELECT status, owner_token FROM ai_roast_generation_attempts "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            if not attempt or str(attempt["owner_token"]) != owner_token:
                raise ValueError("AI 文案生成权已失效")
            if text:
                connection.execute(
                    "INSERT OR IGNORE INTO ai_roast_copies(" 
                    "pig_id, generated_date, content) VALUES (?, ?, ?)",
                    (pig_id, generated_date, text),
                )
                connection.execute(
                    "UPDATE ai_roast_generation_attempts SET "
                    "status = 'ready', completed_at = ? "
                    "WHERE pig_id = ? AND generated_date = ? AND owner_token = ?",
                    (float(completed_at), pig_id, generated_date, owner_token),
                )
            else:
                connection.execute(
                    "UPDATE ai_roast_generation_attempts SET "
                    "status = 'failed', completed_at = ? "
                    "WHERE pig_id = ? AND generated_date = ? AND owner_token = ?",
                    (float(completed_at), pig_id, generated_date, owner_token),
                )
            stored = connection.execute(
                "SELECT content FROM ai_roast_copies "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            document = self._ai_document_from_sql(connection)
            self._write_document_tx(connection, "ai_roast_copies.json", document)
            self._set_write_authority(connection)
            return {
                "status": "ready" if stored else "failed",
                "content": str(stored["content"]) if stored else "",
                "copies": self._selected_ai_copies(document, pig_id),
                "ai_roast_copies": document,
            }

    def store_ai_roast_copy(
        self,
        *,
        pig_id: str,
        generated_date: str,
        content: str,
        cutoff_date: str,
        through_date: str,
    ) -> dict[str, Any]:
        """Compatibility writer; direct callers mark the attempt ready."""
        pig_id = str(pig_id)
        generated_date = str(generated_date)
        content = str(content).strip()
        if not pig_id or not generated_date or not content:
            raise ValueError("AI 文案缓存参数无效")
        with self.transaction() as connection:
            self._prune_ai_rows(connection, cutoff_date, through_date)
            cursor = connection.execute(
                "INSERT OR IGNORE INTO ai_roast_copies(" 
                "pig_id, generated_date, content) VALUES (?, ?, ?)",
                (pig_id, generated_date, content),
            )
            connection.execute(
                "INSERT INTO ai_roast_generation_attempts(" 
                "pig_id, generated_date, status, owner_token, attempted_at, completed_at) "
                "VALUES (?, ?, 'ready', '', ?, ?) "
                "ON CONFLICT(pig_id, generated_date) DO UPDATE SET "
                "status = 'ready', completed_at = excluded.completed_at",
                (pig_id, generated_date, time.time(), time.time()),
            )
            stored = connection.execute(
                "SELECT content FROM ai_roast_copies "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            document = self._ai_document_from_sql(connection)
            self._write_document_tx(connection, "ai_roast_copies.json", document)
            self._set_write_authority(connection)
            return {
                "created": cursor.rowcount == 1,
                "content": str(stored["content"]),
                "copies": self._selected_ai_copies(document, pig_id),
                "ai_roast_copies": document,
            }

'''
replace_region(
    "storage/sqlite_storage.py",
    "    def _ai_document_from_sql(\n",
    "    def upsert_catalog_override(\n",
    ai_methods,
)


# ---------------------------------------------------------------------------
# Runtime startup and exact AI-copy semantics in main
# ---------------------------------------------------------------------------
content = read("main.py").replace("AstrBot-RollPig/2.12.0", "AstrBot-RollPig/2.13.0")
write("main.py", content)
replace_once(
    "main.py",
    '        self.storage = self.storage_manager.backend\n        self.draw_service = DrawService(\n',
    '        self.storage = self.storage_manager.backend\n'
    '        self._runtime_snapshot = (\n'
    '            self.storage.load_runtime_snapshot()\n'
    '            if getattr(self.storage, "supports_runtime_snapshot", False)\n'
    '            else {}\n'
    '        )\n'
    '        self.draw_service = DrawService(\n',
)
replace_once(
    "main.py",
    '''        # 初始化数据\n        bundled_pigs = self.load_json(self.piginfo_path, [])\n        self._bundled_pigs = self._validate_pig_records(bundled_pigs)\n        self._migrate_catalog_layers()\n        self._reload_catalog_layers()\n        self._load_pighub_cache()\n        if not self.pig_list:\n            logger.error("小猪信息为空或不存在，请检查资源文件！")\n        self.today_path = self.plugin_data_dir / "rollpig_today.json"\n        self.history = self.load_json(\n            self.history_path,\n            {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}},\n        )\n        self.roast_state = self.load_json(\n            self.roast_state_path,\n            {\n                "version": 1,\n                "cooldowns": {},\n                "daily_backdoors": {},\n                "daily_roast_counts": {},\n                "eaten_penalties": {},\n                "eaten_events": {},\n            },\n        )\n        self.ai_roast_copies = self.load_json(\n            self.ai_roast_copies_path,\n            {"version": 1, "copies": {}},\n        )\n        self._migrate_today_to_history()\n''',
    '''        # 初始化数据；SQLite 运行态直接由规范化表重建，不读取兼容文档。\n        bundled_pigs = self.load_json(self.piginfo_path, [])\n        self._bundled_pigs = self._validate_pig_records(bundled_pigs)\n        if not getattr(self.storage, "supports_runtime_snapshot", False):\n            self._migrate_catalog_layers()\n        self._reload_catalog_layers()\n        self._load_pighub_cache()\n        if not self.pig_list:\n            logger.error("小猪信息为空或不存在，请检查资源文件！")\n        self.today_path = self.plugin_data_dir / "rollpig_today.json"\n        history_default = {\n            "version": 1, "users": {}, "daily": {}, "pig_snapshots": {}\n        }\n        roast_default = {\n            "version": 1,\n            "cooldowns": {},\n            "daily_backdoors": {},\n            "daily_roast_counts": {},\n            "eaten_penalties": {},\n            "eaten_events": {},\n        }\n        ai_default = {"version": 2, "copies": {}, "attempts": {}}\n        self.history = self._runtime_document(\n            "history", self.history_path, history_default\n        )\n        self.roast_state = self._runtime_document(\n            "roast_state", self.roast_state_path, roast_default\n        )\n        self.ai_roast_copies = self._runtime_document(\n            "ai_roast_copies", self.ai_roast_copies_path, ai_default\n        )\n        if not getattr(self.storage, "supports_runtime_snapshot", False):\n            self._migrate_today_to_history()\n''',
)
replace_once(
    "main.py",
    '    def save_json_batch(self, updates: dict[Path, object]) -> None:\n'
    '        self.storage.save_json_batch(updates)\n\n'
    '    def _validate_pig_records',
    '    def save_json_batch(self, updates: dict[Path, object]) -> None:\n'
    '        self.storage.save_json_batch(updates)\n\n'
    '    def _runtime_document(self, key: str, path: Path, default):\n'
    '        value = self._runtime_snapshot.get(key)\n'
    '        return value if value is not None else self.load_json(path, default)\n\n'
    '    def _refresh_runtime_snapshot(self) -> None:\n'
    '        if getattr(self.storage, "supports_runtime_snapshot", False):\n'
    '            self._runtime_snapshot = self.storage.load_runtime_snapshot()\n\n'
    '    def _validate_pig_records',
)
replace_once(
    "main.py",
    '        try:\n            overrides = self._validate_pig_records(\n                self.load_json(self.local_overrides_path, [])\n            )\n',
    '        try:\n            overrides = self._validate_pig_records(\n                self._runtime_document(\n                    "catalog_overrides", self.local_overrides_path, []\n                )\n            )\n',
)
replace_once(
    "main.py",
    '        raw_tombstones = self.load_json(self.tombstones_path, [])\n',
    '        raw_tombstones = self._runtime_document(\n'
    '            "catalog_tombstones", self.tombstones_path, []\n'
    '        )\n',
)
replace_once(
    "main.py",
    '            "local_overrides": len(self.load_json(self.local_overrides_path, [])),\n'
    '            "deleted_count": len(self.load_json(self.tombstones_path, [])),\n',
    '            "local_overrides": len(\n'
    '                self._runtime_document(\n'
    '                    "catalog_overrides", self.local_overrides_path, []\n'
    '                )\n'
    '            ),\n'
    '            "deleted_count": len(\n'
    '                self._runtime_document(\n'
    '                    "catalog_tombstones", self.tombstones_path, []\n'
    '                )\n'
    '            ),\n',
)

recent_and_get = r'''    def _recent_ai_roast_copies(self, pig_id: str) -> tuple[dict[str, str], bool]:
        """返回指定小猪近七天文案，并清理缓存和生成尝试。"""
        today = self._today()
        cutoff = (today - datetime.timedelta(days=6)).isoformat()
        today_text = today.isoformat()
        copies_root = self.ai_roast_copies.get("copies")
        changed = not isinstance(copies_root, dict)
        if not isinstance(copies_root, dict):
            copies_root = {}
            self.ai_roast_copies["copies"] = copies_root
        for item_id, stored in list(copies_root.items()):
            valid = (
                {
                    str(day): str(copy).strip()
                    for day, copy in stored.items()
                    if cutoff <= str(day) <= today_text and str(copy).strip()
                }
                if isinstance(stored, dict)
                else {}
            )
            if valid:
                if stored != valid:
                    copies_root[item_id] = valid
                    changed = True
            else:
                copies_root.pop(item_id, None)
                changed = True
        attempts_root = self.ai_roast_copies.get("attempts")
        if not isinstance(attempts_root, dict):
            attempts_root = {}
            self.ai_roast_copies["attempts"] = attempts_root
            changed = True
        for item_id, stored in list(attempts_root.items()):
            valid = (
                {
                    str(day): str(status)
                    for day, status in stored.items()
                    if cutoff <= str(day) <= today_text
                    and str(status) in {"generating", "ready", "failed"}
                }
                if isinstance(stored, dict)
                else {}
            )
            if valid:
                if stored != valid:
                    attempts_root[item_id] = valid
                    changed = True
            else:
                attempts_root.pop(item_id, None)
                changed = True
        selected = copies_root.get(pig_id, {})
        return (selected if isinstance(selected, dict) else {}), changed

    def _save_ai_roast_copies(self) -> None:
        self.save_json(self.ai_roast_copies_path, self.ai_roast_copies)

    async def _get_ai_roast_copy(
        self, event: AstrMessageEvent, pig: dict
    ) -> str | None:
        """每天每只猪只调用一次模型；后续随机复用滚动七日文案。"""
        if not self.enable_ai_roast_copy:
            return None
        pig_id = str(pig.get("id") or "").strip()
        if not pig_id:
            return await self._generate_ai_roast_copy(event, pig)
        today_value = self._today()
        today = today_value.isoformat()
        cutoff = (today_value - datetime.timedelta(days=6)).isoformat()
        async with self._ai_roast_lock(pig_id):
            if getattr(self.storage, "supports_domain_writes", False):
                owner_token = uuid.uuid4().hex
                claimed = await asyncio.to_thread(
                    self.storage.claim_ai_roast_generation,
                    pig_id=pig_id,
                    generated_date=today,
                    owner_token=owner_token,
                    attempted_at=time.time(),
                    cutoff_date=cutoff,
                    through_date=today,
                )
                document = claimed.get("ai_roast_copies")
                if isinstance(document, dict):
                    self.ai_roast_copies = document
                recent = claimed.get("copies")
                recent = recent if isinstance(recent, dict) else {}
                if str(claimed.get("status")) == "ready" and today in recent:
                    return random.choice(list(recent.values()))
                if not claimed.get("claimed"):
                    return random.choice(list(recent.values())) if recent else None
                generated = await self._generate_ai_roast_copy(event, pig)
                completed = await asyncio.to_thread(
                    self.storage.complete_ai_roast_generation,
                    pig_id=pig_id,
                    generated_date=today,
                    owner_token=owner_token,
                    content=generated or "",
                    completed_at=time.time(),
                    cutoff_date=cutoff,
                    through_date=today,
                )
                document = completed.get("ai_roast_copies")
                if isinstance(document, dict):
                    self.ai_roast_copies = document
                if generated and str(completed.get("status")) == "ready":
                    return str(completed.get("content") or generated)
                recent = completed.get("copies")
                recent = recent if isinstance(recent, dict) else {}
                return random.choice(list(recent.values())) if recent else None

            with self._data_lock:
                recent, changed = self._recent_ai_roast_copies(pig_id)
                attempts_root = self.ai_roast_copies.setdefault("attempts", {})
                attempts = attempts_root.setdefault(pig_id, {})
                if today in recent:
                    if changed:
                        self._save_ai_roast_copies()
                    return random.choice(list(recent.values()))
                if today in attempts:
                    if changed:
                        self._save_ai_roast_copies()
                    return random.choice(list(recent.values())) if recent else None
                attempts[today] = "generating"
                self._save_ai_roast_copies()
            generated = await self._generate_ai_roast_copy(event, pig)
            with self._data_lock:
                recent, _ = self._recent_ai_roast_copies(pig_id)
                attempts = self.ai_roast_copies.setdefault("attempts", {}).setdefault(
                    pig_id, {}
                )
                if generated:
                    recent[today] = generated
                    self.ai_roast_copies.setdefault("copies", {})[pig_id] = recent
                    attempts[today] = "ready"
                else:
                    attempts[today] = "failed"
                self._save_ai_roast_copies()
            if generated:
                return generated
            return random.choice(list(recent.values())) if recent else None

'''
replace_region(
    "main.py",
    "    def _recent_ai_roast_copies(",
    "    async def _generate_ai_roast_copy(",
    recent_and_get,
)

# Preserve the runtime catalog snapshot after SQL mutations.
replace_once(
    "main.py",
    '                    self.storage.upsert_catalog_override(record=dict(record))\n',
    '                    result = self.storage.upsert_catalog_override(record=dict(record))\n'
    '                    self._runtime_snapshot["catalog_overrides"] = result.get(\n'
    '                        "overrides", []\n'
    '                    )\n'
    '                    self._runtime_snapshot["catalog_tombstones"] = result.get(\n'
    '                        "tombstones", []\n'
    '                    )\n',
)
replace_once(
    "main.py",
    '                    self.storage.delete_catalog_entry(pig_id=str(pig_id))\n',
    '                    result = self.storage.delete_catalog_entry(pig_id=str(pig_id))\n'
    '                    self._runtime_snapshot["catalog_overrides"] = result.get(\n'
    '                        "overrides", []\n'
    '                    )\n'
    '                    self._runtime_snapshot["catalog_tombstones"] = result.get(\n'
    '                        "tombstones", []\n'
    '                    )\n',
)


# ---------------------------------------------------------------------------
# Version metadata and changelog
# ---------------------------------------------------------------------------
replace_once("metadata.yaml", 'version: "2.12.0"', 'version: "2.13.0"')
replace_once(
    "CHANGELOG.md",
    "# 更新\n",
    "# 更新\n"
    "## v2.13.0 (2026-08-04)\n"
    "### 每日 AI 生成权与 SQL 启动快照\n"
    "- 新增 `ai_roast_generation_attempts`，以 `(pig_id, generated_date)` 唯一键保证所有 AstrBot 实例每天每只猪最多实际调用一次模型；生成失败也会记录，当天不重复消耗 Token。\n"
    "- 当天首次成功生成直接使用新文案；同一天后续烧烤从该猪今天及此前六天的有效文案中随机选择，滚动窗口共七个自然日。\n"
    "- SQLite 启动时由规范化表重建用户图鉴、每日记录、烤猪状态、AI 缓存、身份映射及本地图鉴层，不再把兼容文档作为运行时启动来源。\n"
    "- `identity_claims` 与 `identity_aliases` 改为 SQL 主写；兼容 JSON 继续事务同步，仅用于导出、回滚和旧版灾难恢复。\n\n",
)


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------
tests = read("tests/test_sqlite_storage.py")
tests += r'''


def test_v213_ai_generation_attempt_is_cross_connection_once_per_day(tmp_path):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    one = first.claim_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner-a",
        attempted_at=1.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    two = second.claim_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner-b",
        attempted_at=2.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    assert one["claimed"] is True
    assert two["claimed"] is False
    assert two["status"] == "generating"
    completed = first.complete_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner-a",
        content="当天第一份",
        completed_at=3.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    assert completed["status"] == "ready"
    cached = second.claim_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner-c",
        attempted_at=4.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    assert cached["claimed"] is False
    assert cached["status"] == "ready"
    assert cached["copies"] == {"2026-08-04": "当天第一份"}


def test_v213_failed_ai_attempt_cannot_generate_again_that_day(tmp_path):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    first.claim_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner-a",
        attempted_at=1.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    failed = first.complete_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner-a",
        content="",
        completed_at=2.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    assert failed["status"] == "failed"
    retry = second.claim_ai_roast_generation(
        pig_id="pig-a",
        generated_date="2026-08-04",
        owner_token="owner-b",
        attempted_at=3.0,
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    assert retry["claimed"] is False
    assert retry["status"] == "failed"


def test_v213_runtime_snapshot_comes_from_normalized_tables(tmp_path):
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
        content="SQL 文案",
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    storage.upsert_catalog_override(
        record={
            "id": "local-pig",
            "name": "本地猪",
            "description": "本地限定",
            "analysis": "SQL 图鉴",
        }
    )
    with storage.transaction() as connection:
        for key, payload in {
            "pig_history.json": '{"version":1,"users":{},"daily":{},"pig_snapshots":{}}',
            "roast_state.json": '{"version":1}',
            "ai_roast_copies.json": '{"version":2,"copies":{},"attempts":{}}',
            "local_overrides.json": '[]',
            "deleted_pigs.json": '[]',
        }.items():
            connection.execute(
                "UPDATE documents SET payload = ?, payload_sha256 = 'broken' WHERE key = ?",
                (payload, key),
            )
    snapshot = storage.load_runtime_snapshot()
    assert snapshot["source"] == "normalized-sql-v3"
    assert snapshot["history"]["daily"]["2026-08-04"]["records"][
        "v2|qq|user|1"
    ] == "pig-a"
    roast_key = json.dumps(
        ["2026-08-04", "v2|qq|group|9", "v2|qq|user|1"],
        ensure_ascii=False,
    )
    assert snapshot["roast_state"]["daily_roast_counts"][roast_key] == 1
    assert snapshot["ai_roast_copies"]["copies"]["pig-a"]["2026-08-04"] == "SQL 文案"
    assert snapshot["catalog_overrides"][0]["id"] == "local-pig"


def test_v213_identity_claims_and_aliases_are_sql_primary(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    claimed = storage.claim_legacy_identity(
        namespaced="v2|qq|user|123",
        legacy="123",
        kind="users",
    )
    assert claimed["claimed"] is True
    alias = storage.remember_identity_alias(
        namespace="telegram@bot",
        canonical_id="v2|telegram@bot|user|123",
        username="PigFriend",
    )
    assert alias["changed"] is True
    with storage.transaction() as connection:
        connection.execute(
            "UPDATE documents SET payload = '{\"version\":1}' "
            "WHERE key = 'pig_history.json'"
        )
    history = storage.load_runtime_snapshot()["history"]
    assert history["identity_claims"]["users"]["123"] == "v2|qq|user|123"
    bucket = history["identity_aliases"]["telegram@bot"]
    assert bucket["by_alias"]["pigfriend"] == "v2|telegram@bot|user|123"
    assert bucket["by_user"]["v2|telegram@bot|user|123"] == "PigFriend"
'''
write("tests/test_sqlite_storage.py", tests)

source_tests = read("tests/test_source_regressions.py")
source_tests += r'''


def test_v213_runtime_uses_sql_snapshot_and_unique_ai_generation_claim():
    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""
    ai = ast.get_source_segment(SOURCE, _method("_get_ai_roast_copy")) or ""
    assert "self.storage.load_runtime_snapshot()" in init
    assert "self._runtime_document" in init
    assert "claim_ai_roast_generation" in ai
    assert "complete_ai_roast_generation" in ai
    assert "uuid.uuid4().hex" in ai
    assert "random.choice(list(recent.values()))" in ai
'''
write("tests/test_source_regressions.py", source_tests)

print("v2.13 applicator completed")
