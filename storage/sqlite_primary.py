from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .sqlite_storage import SQLiteStorage as LegacySQLiteStorage


class SQLitePrimaryStorage(LegacySQLiteStorage):
    """SQLite v3 single-authority runtime storage.

    Normalized tables are the only runtime authority. Compatibility JSON
    documents are reconstructed in memory only for export, rollback and
    disaster recovery; hot domain writes never rebuild or persist them.
    """

    supports_lazy_compatibility_export = True
    schema_version = 6

    RUNTIME_DOCUMENT_KEYS = (
        "pig_history.json",
        "roast_state.json",
        "ai_roast_copies.json",
        "local_overrides.json",
        "deleted_pigs.json",
        "rollpig_today.json",
    )

    def _initialize(self) -> None:
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

    @staticmethod
    def _set_write_authority(connection: sqlite3.Connection) -> None:
        connection.execute(
            "INSERT INTO projection_meta(key, value) VALUES "
            "('write_authority', 'sql-primary-v3.0') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )
        connection.execute(
            "INSERT INTO projection_meta(key, value) VALUES "
            "('compatibility_mode', 'on-demand') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )

    @classmethod
    def _mark_primary_write_tx(cls, connection: sqlite3.Connection) -> None:
        cls._set_write_authority(connection)
        connection.execute(
            "INSERT INTO projection_meta(key, value) VALUES "
            "('last_domain_write_at', CAST(unixepoch() AS TEXT)) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )

    @staticmethod
    def _merge_today_into_history(
        history_value: Any, today_value: Any
    ) -> dict[str, Any]:
        history = (
            json.loads(json.dumps(history_value, ensure_ascii=False))
            if isinstance(history_value, dict)
            else {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}}
        )
        today = today_value if isinstance(today_value, dict) else {}
        draw_date = str(today.get("date") or "")
        records = today.get("records") if isinstance(today.get("records"), dict) else {}
        if not draw_date or not records:
            return history
        users = history.setdefault("users", {})
        daily = history.setdefault("daily", {})
        snapshots = history.setdefault("pig_snapshots", {})
        day = daily.setdefault(
            draw_date,
            {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
        )
        day_users = day.setdefault("users", [])
        day_records = day.setdefault("records", {})
        for raw_user_id, raw_pig in records.items():
            if not isinstance(raw_pig, dict):
                continue
            user_id = str(raw_user_id)
            pig = dict(raw_pig)
            pig_id = str(pig.get("id") or "").strip()
            if not pig_id:
                continue
            snapshots[pig_id] = pig
            if user_id in day_records:
                continue
            user = users.setdefault(
                user_id,
                {"total_draws": 0, "active_days": 0, "duplicate_streak": 0, "pigs": {}},
            )
            pigs = user.setdefault("pigs", {})
            unlocked = pig_id not in pigs
            record = pigs.setdefault(
                pig_id,
                {
                    "first_unlocked": draw_date,
                    "last_drawn": draw_date,
                    "count": 0,
                },
            )
            record["last_drawn"] = draw_date
            record["count"] = int(record.get("count", 0) or 0) + 1
            user["total_draws"] = int(user.get("total_draws", 0) or 0) + 1
            user["active_days"] = int(user.get("active_days", 0) or 0) + 1
            user["duplicate_streak"] = 0 if unlocked else int(
                user.get("duplicate_streak", 0) or 0
            ) + 1
            day_users.append(user_id)
            day_records[user_id] = pig_id
            day["draws"] = int(day.get("draws", 0) or 0) + 1
            if unlocked:
                day["new_unlocks"] = int(day.get("new_unlocks", 0) or 0) + 1
        day["users"] = list(dict.fromkeys(str(item) for item in day_users))
        return history

    def import_legacy_documents(self, documents: dict[str, Any]) -> dict[str, Any]:
        """Import a JSON-era snapshot once, then discard compatibility rows."""
        source = {str(key): self._clone(value) for key, value in documents.items()}
        source["pig_history.json"] = self._merge_today_into_history(
            source.get("pig_history.json"), source.get("rollpig_today.json")
        )
        order = (
            "pig_history.json",
            "roast_state.json",
            "ai_roast_copies.json",
            "local_overrides.json",
            "deleted_pigs.json",
        )
        with self.transaction() as connection:
            self._clear_projections(connection)
            for key in order:
                if key in source:
                    self._refresh_projection(connection, key, source[key])
            connection.execute("DELETE FROM documents")
            self._set_write_authority(connection)
            now = str(int(time.time()))
            for key, value in {
                "legacy_import_at": now,
                "compatibility_mode": "on-demand",
            }.items():
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
        verification = self.verify()
        if not verification.get("ok"):
            raise RuntimeError("legacy JSON import did not pass normalized verification")
        return verification

    def load_json(self, path: Path, default: Any) -> Any:
        path = Path(path)
        if not self._is_managed(path):
            return self.fallback.load_json(path, default)
        key = self._relative_key(path)
        with self._lock, self._connection() as connection:
            if key == "pig_history.json":
                value = self._history_document_from_sql(connection)
            elif key == "roast_state.json":
                value = self._roast_document_from_sql(connection)
            elif key == "ai_roast_copies.json":
                value = self._ai_document_from_sql(connection)
            elif key == "local_overrides.json":
                value = self._catalog_documents_from_sql(connection)[0]
            elif key == "deleted_pigs.json":
                value = self._catalog_documents_from_sql(connection)[1]
            elif key == "rollpig_today.json":
                value = self._today_document_from_sql(connection)
            else:
                value = default
        return self._clone(value)

    def save_json_batch(self, updates: dict[Path, Any]) -> None:
        if not updates:
            return
        managed = [Path(path) for path in updates if self._is_managed(Path(path))]
        unmanaged = {
            Path(path): value
            for path, value in updates.items()
            if not self._is_managed(Path(path))
        }
        if managed and unmanaged:
            raise ValueError("同一批次不能混合 SQLite 关键状态与普通 JSON 缓存")
        if managed:
            names = ", ".join(sorted(self._relative_key(path) for path in managed))
            raise RuntimeError(
                "SQLite v3 关键状态禁止整份 JSON 写回；请使用领域事务 API：" + names
            )
        self.fallback.save_json_batch(unmanaged)

    @staticmethod
    def _selected_ai_copies_tx(
        connection: sqlite3.Connection, pig_id: str
    ) -> dict[str, str]:
        return {
            str(row["generated_date"]): str(row["content"])
            for row in connection.execute(
                "SELECT generated_date, content FROM ai_roast_copies "
                "WHERE pig_id = ? ORDER BY generated_date",
                (str(pig_id),),
            ).fetchall()
        }

    def claim_legacy_identity(
        self,
        *,
        namespaced: str,
        legacy: str,
        kind: str,
        accepted_claims: tuple[str, ...] = (),
    ) -> dict[str, Any]:
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
                self._mark_primary_write_tx(connection)
            return {
                "claimed": claimed,
                "changed": changed,
                "storage_key": legacy if claimed else namespaced,
            }

    def remember_identity_alias(
        self,
        *,
        namespace: str,
        canonical_id: str,
        username: str,
    ) -> dict[str, Any]:
        namespace = str(namespace)
        canonical_id = str(canonical_id)
        username = str(username).lstrip("@")
        alias_key = username.lower()
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT alias_key, canonical_id, username FROM identity_aliases "
                "WHERE namespace = ? AND (alias_key = ? OR canonical_id = ?)",
                (namespace, alias_key, canonical_id),
            ).fetchall()
            changed = not any(
                str(row["alias_key"]) == alias_key
                and str(row["canonical_id"]) == canonical_id
                and str(row["username"]) == username
                for row in rows
            ) or len(rows) != 1
            if changed:
                connection.execute(
                    "DELETE FROM identity_aliases "
                    "WHERE namespace = ? AND (alias_key = ? OR canonical_id = ?)",
                    (namespace, alias_key, canonical_id),
                )
                connection.execute(
                    "INSERT INTO identity_aliases(namespace, alias_key, canonical_id, username) "
                    "VALUES (?, ?, ?, ?)",
                    (namespace, alias_key, canonical_id, username),
                )
                self._mark_primary_write_tx(connection)
            return {"changed": changed}

    def consume_roast_cooldown(
        self,
        *,
        group_id: str,
        actor_id: str,
        now: float,
        cooldown_seconds: int,
    ) -> dict[str, Any]:
        group_id = str(group_id)
        actor_id = str(actor_id)
        cooldown_key = f"{group_id}:{actor_id}"
        now = float(now)
        cooldown_seconds = max(1, int(cooldown_seconds))
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT last_used_at FROM roast_cooldowns WHERE cooldown_key = ?",
                (cooldown_key,),
            ).fetchone()
            if row:
                remaining = int(float(row["last_used_at"]) + cooldown_seconds - now)
                if remaining > 0:
                    return {"remaining": remaining, "claimed": False}
            self._remember_identity(connection, actor_id)
            connection.execute(
                "INSERT INTO roast_cooldowns(cooldown_key, group_id, actor_id, last_used_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(cooldown_key) DO UPDATE SET "
                "group_id = excluded.group_id, actor_id = excluded.actor_id, "
                "last_used_at = excluded.last_used_at",
                (cooldown_key, group_id, actor_id, now),
            )
            self._mark_primary_write_tx(connection)
            return {"remaining": 0, "claimed": True}

    def increment_roast_count(
        self,
        *,
        draw_date: str,
        group_id: str,
        user_id: str,
        cutoff_date: str,
    ) -> dict[str, Any]:
        draw_date = str(draw_date)
        group_id = str(group_id)
        user_id = str(user_id)
        with self.transaction() as connection:
            self._remember_identity(connection, user_id)
            connection.execute(
                "INSERT INTO daily_roast_counts(draw_date, group_id, user_id, roast_count) "
                "VALUES (?, ?, ?, 1) ON CONFLICT(draw_date, group_id, user_id) "
                "DO UPDATE SET roast_count = daily_roast_counts.roast_count + 1",
                (draw_date, group_id, user_id),
            )
            total = int(
                connection.execute(
                    "SELECT roast_count FROM daily_roast_counts "
                    "WHERE draw_date = ? AND group_id = ? AND user_id = ?",
                    (draw_date, group_id, user_id),
                ).fetchone()[0]
            )
            connection.execute(
                "DELETE FROM daily_roast_counts WHERE draw_date < ?",
                (str(cutoff_date),),
            )
            self._mark_primary_write_tx(connection)
            return {"count": total}

    def consume_daily_backdoor(
        self,
        *,
        draw_date: str,
        actor_id: str,
        cutoff_date: str,
    ) -> dict[str, Any]:
        draw_date = str(draw_date)
        actor_id = str(actor_id)
        backdoor_key = f"{draw_date}:{actor_id}"
        with self.transaction() as connection:
            self._remember_identity(connection, actor_id)
            cursor = connection.execute(
                "INSERT OR IGNORE INTO daily_backdoors(" 
                "backdoor_key, draw_date, actor_id, used) VALUES (?, ?, ?, 1)",
                (backdoor_key, draw_date, actor_id),
            )
            if cursor.rowcount == 0:
                return {"consumed": False}
            connection.execute(
                "DELETE FROM daily_backdoors WHERE draw_date < ?",
                (str(cutoff_date),),
            )
            self._mark_primary_write_tx(connection)
            return {"consumed": True}

    def get_ai_roast_copies(
        self,
        *,
        pig_id: str,
        cutoff_date: str,
        through_date: str,
    ) -> dict[str, Any]:
        pig_id = str(pig_id)
        with self.transaction() as connection:
            self._prune_ai_rows(connection, cutoff_date, through_date)
            copies = self._selected_ai_copies_tx(connection, pig_id)
            self._mark_primary_write_tx(connection)
            return {"copies": copies}

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
                copies = self._selected_ai_copies_tx(connection, pig_id)
                self._mark_primary_write_tx(connection)
                return {
                    "claimed": False,
                    "status": "ready",
                    "content": str(cached["content"]),
                    "copies": copies,
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
            copies = self._selected_ai_copies_tx(connection, pig_id)
            self._mark_primary_write_tx(connection)
            return {
                "claimed": cursor.rowcount == 1,
                "status": str(row["status"]),
                "owner": str(row["owner_token"]),
                "copies": copies,
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
        pig_id = str(pig_id).strip()
        generated_date = str(generated_date)
        owner_token = str(owner_token).strip()
        text = str(content or "").strip()
        with self.transaction() as connection:
            self._prune_ai_rows(connection, cutoff_date, through_date)
            attempt = connection.execute(
                "SELECT owner_token FROM ai_roast_generation_attempts "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            if not attempt or str(attempt["owner_token"]) != owner_token:
                raise ValueError("AI 文案生成权已失效")
            if text:
                connection.execute(
                    "INSERT OR IGNORE INTO ai_roast_copies(pig_id, generated_date, content) "
                    "VALUES (?, ?, ?)",
                    (pig_id, generated_date, text),
                )
                connection.execute(
                    "UPDATE ai_roast_generation_attempts SET status = 'ready', completed_at = ? "
                    "WHERE pig_id = ? AND generated_date = ? AND owner_token = ?",
                    (float(completed_at), pig_id, generated_date, owner_token),
                )
            else:
                connection.execute(
                    "UPDATE ai_roast_generation_attempts SET status = 'failed', completed_at = ? "
                    "WHERE pig_id = ? AND generated_date = ? AND owner_token = ?",
                    (float(completed_at), pig_id, generated_date, owner_token),
                )
            stored = connection.execute(
                "SELECT content FROM ai_roast_copies "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            copies = self._selected_ai_copies_tx(connection, pig_id)
            self._mark_primary_write_tx(connection)
            return {
                "status": "ready" if stored else "failed",
                "content": str(stored["content"]) if stored else "",
                "copies": copies,
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
        pig_id = str(pig_id).strip()
        generated_date = str(generated_date)
        content = str(content).strip()
        if not pig_id or not generated_date or not content:
            raise ValueError("AI 文案缓存参数无效")
        with self.transaction() as connection:
            self._prune_ai_rows(connection, cutoff_date, through_date)
            cursor = connection.execute(
                "INSERT OR IGNORE INTO ai_roast_copies(pig_id, generated_date, content) "
                "VALUES (?, ?, ?)",
                (pig_id, generated_date, content),
            )
            connection.execute(
                "INSERT INTO ai_roast_generation_attempts(" 
                "pig_id, generated_date, status, owner_token, attempted_at, completed_at) "
                "VALUES (?, ?, 'ready', '', ?, ?) ON CONFLICT(pig_id, generated_date) "
                "DO UPDATE SET status = 'ready', completed_at = excluded.completed_at",
                (pig_id, generated_date, time.time(), time.time()),
            )
            stored = connection.execute(
                "SELECT content FROM ai_roast_copies "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            copies = self._selected_ai_copies_tx(connection, pig_id)
            self._mark_primary_write_tx(connection)
            return {
                "created": cursor.rowcount == 1,
                "content": str(stored["content"]),
                "copies": copies,
            }

    def upsert_catalog_override(
        self, *, record: dict[str, Any]
    ) -> dict[str, Any]:
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
            self._mark_primary_write_tx(connection)
            return {"overrides": overrides, "tombstones": tombstones}

    def delete_catalog_entry(self, *, pig_id: str) -> dict[str, Any]:
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
            self._mark_primary_write_tx(connection)
            return {"overrides": overrides, "tombstones": tombstones}

    @staticmethod
    def _valid_pig(value: Any) -> bool:
        return isinstance(value, dict) and bool(str(value.get("id") or "").strip())

    def create_daily_draw(
        self,
        *,
        draw_date: str,
        user_id: str,
        user_candidates: tuple[str, ...] = (),
        pig: dict[str, Any] | None = None,
        group_id: str = "",
        penalty_should_fail: bool = False,
    ) -> dict[str, Any]:
        draw_date = str(draw_date)
        canonical_id = str(user_id)
        candidates = self._ordered_candidates(canonical_id, user_candidates)
        now = int(time.time())
        with self.transaction() as connection:
            existing = None
            for candidate in candidates:
                existing = connection.execute(
                    "SELECT user_id, pig_id FROM daily_draws "
                    "WHERE draw_date = ? AND user_id = ?",
                    (draw_date, candidate),
                ).fetchone()
                if existing:
                    break
            if existing:
                actual_id = str(existing["user_id"])
                pig_id = str(existing["pig_id"])
                if group_id:
                    connection.execute(
                        "INSERT OR IGNORE INTO daily_draw_groups VALUES (?, ?, ?)",
                        (draw_date, actual_id, str(group_id)),
                    )
                    groups = [
                        str(row[0])
                        for row in connection.execute(
                            "SELECT group_id FROM daily_draw_groups "
                            "WHERE draw_date = ? AND user_id = ? ORDER BY group_id",
                            (draw_date, actual_id),
                        ).fetchall()
                    ]
                    connection.execute(
                        "UPDATE daily_draws SET group_ids_json = ? "
                        "WHERE draw_date = ? AND user_id = ?",
                        (json.dumps(groups, ensure_ascii=False), draw_date, actual_id),
                    )
                    self._mark_primary_write_tx(connection)
                snapshot = connection.execute(
                    "SELECT payload_json FROM pig_snapshots WHERE pig_id = ?",
                    (pig_id,),
                ).fetchone()
                pig_payload = (
                    self._decode(str(snapshot["payload_json"]))
                    if snapshot
                    else {"id": pig_id}
                )
                return {
                    "status": "existing",
                    "created": False,
                    "user_id": actual_id,
                    "pig_id": pig_id,
                    "pig": pig_payload,
                }

            penalty_row = None
            for candidate in candidates:
                penalty_row = connection.execute(
                    "SELECT user_id, due_date, failed FROM eaten_penalties "
                    "WHERE user_id = ?",
                    (candidate,),
                ).fetchone()
                if penalty_row:
                    break
            if penalty_row:
                penalty_user = str(penalty_row["user_id"])
                due_date = str(penalty_row["due_date"])
                failed = bool(penalty_row["failed"])
                if due_date < draw_date:
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )
                    self._mark_primary_write_tx(connection)
                elif due_date == draw_date and failed:
                    return {"status": "penalty-blocked", "created": False}
                elif due_date == draw_date and penalty_should_fail:
                    payload = {"due_date": draw_date, "failed": True}
                    connection.execute(
                        "UPDATE eaten_penalties SET failed = 1, payload_json = ? "
                        "WHERE user_id = ?",
                        (json.dumps(payload, ensure_ascii=False, sort_keys=True), penalty_user),
                    )
                    self._mark_primary_write_tx(connection)
                    return {"status": "penalty-blocked", "created": False}
                elif due_date == draw_date and self._valid_pig(pig):
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )

            if not self._valid_pig(pig):
                return {"status": "needs-pig", "created": False}

            pig_payload = self._clone(pig)
            pig_id = str(pig_payload["id"])
            self._remember_identity(connection, canonical_id)
            unlocked = connection.execute(
                "SELECT 1 FROM user_pigs WHERE user_id = ? AND pig_id = ?",
                (canonical_id, pig_id),
            ).fetchone() is None
            stats = connection.execute(
                "SELECT total_draws, active_days, duplicate_streak, payload_json "
                "FROM user_stats WHERE user_id = ?",
                (canonical_id,),
            ).fetchone()
            total_draws = int(stats["total_draws"]) if stats else 0
            active_days = int(stats["active_days"]) if stats else 0
            duplicate_streak = int(stats["duplicate_streak"]) if stats else 0
            try:
                user_payload = json.loads(str(stats["payload_json"] or "{}")) if stats else {}
            except (TypeError, ValueError, json.JSONDecodeError):
                user_payload = {}
            user_payload = user_payload if isinstance(user_payload, dict) else {}
            user_payload.pop("pigs", None)
            user_payload.update(
                {
                    "total_draws": total_draws + 1,
                    "active_days": active_days + 1,
                    "duplicate_streak": 0 if unlocked else duplicate_streak + 1,
                }
            )
            connection.execute(
                "INSERT INTO daily_draws(" 
                "draw_date, user_id, pig_id, original_pig_id, group_ids_json, "
                "created_at, was_new_unlock) VALUES (?, ?, ?, '', ?, ?, ?)",
                (
                    draw_date,
                    canonical_id,
                    pig_id,
                    json.dumps([str(group_id)] if group_id else [], ensure_ascii=False),
                    now,
                    int(unlocked),
                ),
            )
            if group_id:
                connection.execute(
                    "INSERT INTO daily_draw_groups VALUES (?, ?, ?)",
                    (draw_date, canonical_id, str(group_id)),
                )
            connection.execute(
                "INSERT INTO user_pigs(user_id, pig_id, first_unlocked, last_drawn, draw_count) "
                "VALUES (?, ?, ?, ?, 1) ON CONFLICT(user_id, pig_id) DO UPDATE SET "
                "last_drawn = excluded.last_drawn, draw_count = user_pigs.draw_count + 1",
                (canonical_id, pig_id, draw_date, draw_date),
            )
            connection.execute(
                "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES (?, ?) "
                "ON CONFLICT(pig_id) DO UPDATE SET payload_json = excluded.payload_json",
                (pig_id, json.dumps(pig_payload, ensure_ascii=False, sort_keys=True)),
            )
            connection.execute(
                "INSERT INTO user_stats(" 
                "user_id, total_draws, active_days, duplicate_streak, payload_json) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
                "total_draws = excluded.total_draws, active_days = excluded.active_days, "
                "duplicate_streak = excluded.duplicate_streak, payload_json = excluded.payload_json",
                (
                    canonical_id,
                    total_draws + 1,
                    active_days + 1,
                    0 if unlocked else duplicate_streak + 1,
                    json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            self._mark_primary_write_tx(connection)
            return {
                "status": "created",
                "created": True,
                "user_id": canonical_id,
                "pig_id": pig_id,
                "pig": pig_payload,
                "was_new_unlock": unlocked,
            }

    def replace_daily_pig_with_eaten(
        self,
        *,
        draw_date: str,
        due_date: str,
        cutoff_date: str,
        user_id: str,
        user_candidates: tuple[str, ...] = (),
        group_id: str,
        actor_id: str,
        outcome: str,
        eaten_pig: dict[str, Any],
    ) -> dict[str, Any]:
        draw_date = str(draw_date)
        candidates = self._ordered_candidates(str(user_id), user_candidates)
        now = int(time.time())
        with self.transaction() as connection:
            row = None
            for candidate in candidates:
                row = connection.execute(
                    "SELECT user_id, pig_id, original_pig_id FROM daily_draws "
                    "WHERE draw_date = ? AND user_id = ?",
                    (draw_date, candidate),
                ).fetchone()
                if row:
                    break
            if not row:
                return {"status": "missing"}
            actual_id = str(row["user_id"])
            current_pig_id = str(row["pig_id"])
            if current_pig_id == "eaten":
                return {"status": "already-eaten", "user_id": actual_id}
            original_id = str(row["original_pig_id"] or current_pig_id)
            eaten_payload = self._clone(eaten_pig)
            eaten_payload["id"] = "eaten"
            connection.execute(
                "UPDATE daily_draws SET pig_id = 'eaten', original_pig_id = ? "
                "WHERE draw_date = ? AND user_id = ?",
                (original_id, draw_date, actual_id),
            )
            connection.execute(
                "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES ('eaten', ?) "
                "ON CONFLICT(pig_id) DO UPDATE SET payload_json = excluded.payload_json",
                (json.dumps(eaten_payload, ensure_ascii=False, sort_keys=True),),
            )
            self._remember_identity(connection, actual_id)
            self._remember_identity(connection, str(actor_id))
            penalty_payload = {"due_date": str(due_date), "failed": False}
            connection.execute(
                "INSERT INTO eaten_penalties(user_id, due_date, failed, payload_json) "
                "VALUES (?, ?, 0, ?) ON CONFLICT(user_id) DO UPDATE SET "
                "due_date = excluded.due_date, failed = 0, payload_json = excluded.payload_json",
                (
                    actual_id,
                    str(due_date),
                    json.dumps(penalty_payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            event_key = self._event_key(draw_date, group_id, actual_id)
            event_payload = {
                "actor_id": str(actor_id),
                "outcome": str(outcome),
                "at": now,
            }
            connection.execute(
                "INSERT INTO eaten_events(" 
                "event_key, event_date, group_id, user_id, actor_id, outcome, created_at, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(event_key) DO UPDATE SET "
                "actor_id = excluded.actor_id, outcome = excluded.outcome, "
                "created_at = excluded.created_at, payload_json = excluded.payload_json",
                (
                    event_key,
                    draw_date,
                    str(group_id),
                    actual_id,
                    str(actor_id),
                    str(outcome),
                    now,
                    json.dumps(event_payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            connection.execute(
                "DELETE FROM eaten_events WHERE event_date < ?", (str(cutoff_date),)
            )
            connection.execute(
                "DELETE FROM eaten_penalties WHERE due_date < ?", (draw_date,)
            )
            self._mark_primary_write_tx(connection)
            return {
                "status": "updated",
                "user_id": actual_id,
                "previous_pig_id": current_pig_id,
                "original_pig_id": original_id,
                "pig": eaten_payload,
            }

    @staticmethod
    def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
        tables = (
            "user_stats",
            "user_pigs",
            "daily_draws",
            "daily_draw_groups",
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
        )
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }

    def _normalized_health(self, connection: sqlite3.Connection) -> dict[str, Any]:
        counts = self._table_counts(connection)
        checks = {
            "compatibility_documents": "SELECT COUNT(*) FROM documents",
            "missing_user_stats": (
                "SELECT COUNT(*) FROM (SELECT user_id FROM user_pigs UNION "
                "SELECT user_id FROM daily_draws) source LEFT JOIN user_stats "
                "ON user_stats.user_id = source.user_id WHERE user_stats.user_id IS NULL"
            ),
            "missing_pig_snapshots": (
                "SELECT COUNT(*) FROM daily_draws LEFT JOIN pig_snapshots "
                "ON pig_snapshots.pig_id = daily_draws.pig_id "
                "WHERE pig_snapshots.pig_id IS NULL"
            ),
            "new_unlock_mismatches": (
                "SELECT COUNT(*) FROM daily_draws WHERE was_new_unlock != CASE WHEN EXISTS ("
                "SELECT 1 FROM user_pigs WHERE user_pigs.user_id = daily_draws.user_id "
                "AND user_pigs.pig_id = COALESCE(NULLIF(daily_draws.original_pig_id, ''), "
                "daily_draws.pig_id) AND user_pigs.first_unlocked = daily_draws.draw_date"
                ") THEN 1 ELSE 0 END"
            ),
            "invalid_user_pig_counts": "SELECT COUNT(*) FROM user_pigs WHERE draw_count <= 0",
            "invalid_roast_counts": (
                "SELECT COUNT(*) FROM daily_roast_counts WHERE roast_count <= 0"
            ),
        }
        actual = {
            name: int(connection.execute(query).fetchone()[0])
            for name, query in checks.items()
        }
        mismatches = {
            name: {"expected": 0, "actual": value}
            for name, value in actual.items()
            if value
        }
        return {
            "projection_ok": not mismatches,
            "projection_mismatches": mismatches,
            "projection_expected": counts,
            "projection_actual": counts,
            "projection_authority": self._write_authority(connection),
            "projection_decode_errors": {},
            "compatibility_mode": "on-demand",
            "compatibility_documents": actual["compatibility_documents"],
        }

    def rebuild_projections(self, *, reason: str = "manual") -> dict[str, Any]:
        reason_text = str(reason or "manual")[:80]
        with self.transaction() as connection:
            user_ids = [
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
            missing_pigs = [
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT daily_draws.pig_id FROM daily_draws "
                    "LEFT JOIN pig_snapshots ON pig_snapshots.pig_id = daily_draws.pig_id "
                    "WHERE pig_snapshots.pig_id IS NULL"
                ).fetchall()
            ]
            for pig_id in missing_pigs:
                connection.execute(
                    "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES (?, ?)",
                    (pig_id, json.dumps({"id": pig_id}, ensure_ascii=False)),
                )
            connection.execute(
                "UPDATE daily_draws SET was_new_unlock = CASE WHEN EXISTS ("
                "SELECT 1 FROM user_pigs WHERE user_pigs.user_id = daily_draws.user_id "
                "AND user_pigs.pig_id = COALESCE(NULLIF(daily_draws.original_pig_id, ''), "
                "daily_draws.pig_id) AND user_pigs.first_unlocked = daily_draws.draw_date"
                ") THEN 1 ELSE 0 END"
            )
            rows = connection.execute(
                "SELECT draw_date, user_id FROM daily_draws"
            ).fetchall()
            for row in rows:
                groups = [
                    str(item[0])
                    for item in connection.execute(
                        "SELECT group_id FROM daily_draw_groups "
                        "WHERE draw_date = ? AND user_id = ? ORDER BY group_id",
                        (str(row["draw_date"]), str(row["user_id"])),
                    ).fetchall()
                ]
                connection.execute(
                    "UPDATE daily_draws SET group_ids_json = ? "
                    "WHERE draw_date = ? AND user_id = ?",
                    (
                        json.dumps(groups, ensure_ascii=False),
                        str(row["draw_date"]),
                        str(row["user_id"]),
                    ),
                )
            connection.execute("DELETE FROM documents")
            self._set_write_authority(connection)
            repaired_at = str(int(time.time()))
            action = "repaired-normalized-derived-state"
            for key, value in {
                "last_rebuild_at": repaired_at,
                "last_repair_at": repaired_at,
                "last_repair_action": action,
                "last_repair_reason": reason_text,
            }.items():
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
            result = self._normalized_health(connection)
            if not result["projection_ok"]:
                raise RuntimeError("normalized repair did not reconcile derived state")
        return {"ok": True, "action": action, "reason": reason_text, **result}

    def export_documents(self) -> dict[str, Any]:
        """Generate legacy JSON documents in memory without persisting them."""
        with self._lock, self._connection() as connection:
            return self._compatibility_documents_from_sql(connection)

    def document_hashes(self) -> dict[str, str]:
        return {
            key: hashlib.sha256(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            for key, value in self.export_documents().items()
        }

    def verify(self, *, deep: bool = True) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            foreign_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
            schema_row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()
            documents = int(
                connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            )
            daily_draws = int(
                connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0]
            )
            users = int(
                connection.execute("SELECT COUNT(*) FROM user_stats").fetchone()[0]
            )
            projection = (
                self._normalized_health(connection)
                if deep
                else {
                    "projection_ok": None,
                    "projection_mismatches": {},
                    "projection_expected": {},
                    "projection_actual": {},
                    "projection_authority": self._write_authority(connection),
                    "projection_decode_errors": {},
                    "compatibility_mode": "on-demand",
                    "compatibility_documents": documents,
                }
            )
        return {
            "ok": (
                integrity == "ok"
                and not foreign_rows
                and projection["projection_ok"] is not False
                and documents == 0
            ),
            "integrity": integrity,
            "foreign_key_errors": len(foreign_rows),
            "schema_version": int(schema_row[0] if schema_row else 0),
            "documents": documents,
            "daily_draws": daily_draws,
            "users": users,
            "deep_verified": deep,
            **projection,
        }

    def health(self) -> dict[str, Any]:
        try:
            verification = self.verify(deep=False)
            with self._lock, self._connection() as connection:
                observability = self._analytics_observability(connection)
                row = connection.execute(
                    "SELECT value FROM projection_meta WHERE key = 'last_domain_write_at'"
                ).fetchone()
                last_write_at = int(row[0]) if row and str(row[0]).isdigit() else 0
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
            observability = {
                "analytics_source": "normalized-sql",
                "write_authority": "sql-primary-v3.0",
                "last_repair_action": "",
                "last_repair_reason": "",
                "last_repair_at": 0,
            }
            last_write_at = 0
        return {
            "backend": self.backend_name,
            "transactional_batch": True,
            "wal": True,
            "runtime_authority": "normalized-sql",
            "compatibility_mode": "on-demand",
            "last_write_at": last_write_at,
            "last_error": self._last_error,
            "database_size": self.database_path.stat().st_size
            if self.database_path.exists()
            else 0,
            **observability,
            **verification,
        }
