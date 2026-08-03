from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .base import StorageBackend
from .json_storage import JSONStorage


class SQLiteStorage(StorageBackend):
    """SQLite-backed logical JSON documents with normalized read projections.

    v2.11 makes normalized tables authoritative for daily draws and eat events.
    Compatibility documents remain transactionally synchronized only for export,
    rollback and older code paths; these hot writes no longer rebuild whole tables.
    """

    backend_name = "sqlite"
    supports_domain_reads = True
    supports_domain_writes = True
    schema_version = 2

    def __init__(
        self,
        database_path: Path,
        data_root: Path,
        managed_paths: set[str],
        *,
        fallback: JSONStorage | None = None,
        lock: threading.RLock | None = None,
        busy_timeout_ms: int = 5000,
    ):
        self.database_path = Path(database_path)
        self.data_root = Path(data_root).resolve()
        self.managed_paths = {Path(item).as_posix() for item in managed_paths}
        self.fallback = fallback or JSONStorage(lock=lock)
        self._lock = lock or threading.RLock()
        self.busy_timeout_ms = min(30000, max(1000, int(busy_timeout_ms)))
        self._last_error = ""
        self._last_write_at = 0
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _clone(value: Any) -> Any:
        return copy.deepcopy(value)

    def _relative_key(self, path: Path) -> str:
        resolved = Path(path).resolve()
        try:
            return resolved.relative_to(self.data_root).as_posix()
        except ValueError:
            return ""

    def _is_managed(self, path: Path) -> bool:
        return self._relative_key(path) in self.managed_paths

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.busy_timeout_ms / 1000,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Yield one configured connection and always roll back/close it."""
        connection = self._connect()
        try:
            yield connection
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS identities (
                    identity_key TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    identity_type TEXT NOT NULL,
                    raw_id TEXT NOT NULL,
                    legacy_id TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS daily_draws (
                    draw_date TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
                    pig_id TEXT NOT NULL,
                    original_pig_id TEXT NOT NULL DEFAULT '',
                    group_ids_json TEXT NOT NULL DEFAULT '[]',
                    created_at INTEGER NOT NULL DEFAULT 0,
                    was_new_unlock INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (draw_date, user_id)
                );
                CREATE TABLE IF NOT EXISTS user_pigs (
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
                    pig_id TEXT NOT NULL,
                    first_unlocked TEXT NOT NULL,
                    last_drawn TEXT NOT NULL,
                    draw_count INTEGER NOT NULL,
                    PRIMARY KEY (user_id, pig_id)
                );
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY REFERENCES identities(identity_key),
                    total_draws INTEGER NOT NULL,
                    active_days INTEGER NOT NULL,
                    duplicate_streak INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pig_snapshots (
                    pig_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS eaten_penalties (
                    user_id TEXT PRIMARY KEY REFERENCES identities(identity_key),
                    due_date TEXT NOT NULL,
                    failed INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS eaten_events (
                    event_key TEXT PRIMARY KEY,
                    event_date TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
                    actor_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS roast_cooldowns (
                    cooldown_key TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),
                    last_used_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS daily_roast_counts (
                    draw_date TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
                    roast_count INTEGER NOT NULL,
                    PRIMARY KEY (draw_date, group_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS daily_backdoors (
                    backdoor_key TEXT PRIMARY KEY,
                    draw_date TEXT NOT NULL,
                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),
                    used INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_roast_copies (
                    pig_id TEXT NOT NULL,
                    generated_date TEXT NOT NULL,
                    content TEXT NOT NULL,
                    PRIMARY KEY (pig_id, generated_date)
                );
                CREATE TABLE IF NOT EXISTS catalog_overrides (
                    pig_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS catalog_tombstones (
                    pig_id TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS projection_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_daily_draws_date
                    ON daily_draws(draw_date);
                CREATE INDEX IF NOT EXISTS idx_eaten_events_date_group
                    ON eaten_events(event_date, group_id);
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            try:
                identity_columns = {
                    str(row[1]) for row in connection.execute("PRAGMA table_info(identities)")
                }
                if "legacy_id" not in identity_columns:
                    connection.execute(
                        "ALTER TABLE identities ADD COLUMN legacy_id TEXT NOT NULL DEFAULT ''"
                    )
                if "created_at" not in identity_columns:
                    connection.execute(
                        "ALTER TABLE identities ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0"
                    )
                draw_columns = {
                    str(row[1]) for row in connection.execute("PRAGMA table_info(daily_draws)")
                }
                if "created_at" not in draw_columns:
                    connection.execute(
                        "ALTER TABLE daily_draws ADD COLUMN created_at INTEGER NOT NULL DEFAULT 0"
                    )
                if "was_new_unlock" not in draw_columns:
                    connection.execute(
                        "ALTER TABLE daily_draws ADD COLUMN was_new_unlock INTEGER NOT NULL DEFAULT 0"
                    )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_draw_groups (
                        draw_date TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        PRIMARY KEY (draw_date, user_id, group_id),
                        FOREIGN KEY (draw_date, user_id)
                            REFERENCES daily_draws(draw_date, user_id)
                            ON DELETE CASCADE
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_identities_namespace_raw "
                    "ON identities(namespace, raw_id)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_daily_draw_groups_group_date "
                    "ON daily_draw_groups(group_id, draw_date)"
                )
                connection.execute(
                    "UPDATE identities SET legacy_id = raw_id WHERE legacy_id = ''"
                )
                connection.execute(
                    "UPDATE identities SET created_at = unixepoch() WHERE created_at = 0"
                )
                migrated = {
                    int(row[0])
                    for row in connection.execute(
                        "SELECT version FROM schema_migrations"
                    ).fetchall()
                }
                if 2 not in migrated:
                    rows = connection.execute(
                        "SELECT draw_date, user_id, group_ids_json FROM daily_draws"
                    ).fetchall()
                    for row in rows:
                        try:
                            groups = json.loads(str(row["group_ids_json"] or "[]"))
                        except (TypeError, ValueError, json.JSONDecodeError):
                            groups = []
                        for group_id in groups if isinstance(groups, list) else []:
                            connection.execute(
                                "INSERT OR IGNORE INTO daily_draw_groups VALUES (?, ?, ?)",
                                (str(row["draw_date"]), str(row["user_id"]), str(group_id)),
                            )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (1, unixepoch())"
                )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (2, unixepoch())"
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Open one real BEGIN IMMEDIATE transaction and always close it."""
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    @staticmethod
    def _encode(value: Any) -> tuple[str, str]:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _decode(payload: str) -> Any:
        return json.loads(payload)

    def load_json(self, path: Path, default: Any) -> Any:
        path = Path(path)
        if not self._is_managed(path):
            return self.fallback.load_json(path, default)
        key = self._relative_key(path)
        with self._lock:
            try:
                with self._connection() as connection:
                    row = connection.execute(
                        "SELECT payload FROM documents WHERE key = ?", (key,)
                    ).fetchone()
                if row:
                    return self._decode(str(row["payload"]))
                value = self.fallback.load_json(path, default)
                self.save_json(path, value)
                return self._clone(value)
            except Exception as exc:
                self._last_error = f"{key}: {exc}"
                raise

    def save_json(self, path: Path, data: Any) -> None:
        self.save_json_batch({Path(path): data})

    def save_json_batch(self, updates: dict[Path, Any]) -> None:
        if not updates:
            return
        managed = {
            Path(path): value
            for path, value in updates.items()
            if self._is_managed(Path(path))
        }
        unmanaged = {
            Path(path): value
            for path, value in updates.items()
            if not self._is_managed(Path(path))
        }
        if managed and unmanaged:
            raise ValueError(
                "同一批次不能混合 SQLite 关键文档与普通 JSON 缓存"
            )
        with self._lock:
            try:
                if managed:
                    with self._connection() as connection:
                        connection.execute("BEGIN IMMEDIATE")
                        now = int(time.time())
                        for path, value in managed.items():
                            key = self._relative_key(path)
                            payload, digest = self._encode(value)
                            connection.execute(
                                """
                                INSERT INTO documents(key, payload, payload_sha256, updated_at)
                                VALUES (?, ?, ?, ?)
                                ON CONFLICT(key) DO UPDATE SET
                                    payload = excluded.payload,
                                    payload_sha256 = excluded.payload_sha256,
                                    updated_at = excluded.updated_at
                                """,
                                (key, payload, digest, now),
                            )
                            self._refresh_projection(connection, key, value)
                        connection.execute("COMMIT")
                if unmanaged:
                    self.fallback.save_json_batch(unmanaged)
                self._last_write_at = int(time.time())
                self._last_error = ""
            except Exception as exc:
                self._last_error = str(exc)
                raise

    @staticmethod
    def _identity_parts(identity_key: str) -> tuple[str, str, str]:
        value = str(identity_key or "")
        parts = value.split("|", 3)
        if len(parts) == 4 and parts[0] == "v2":
            return parts[1], parts[2], parts[3]
        return "legacy", "user", value

    def _remember_identity(self, connection: sqlite3.Connection, identity_key: str) -> None:
        key = str(identity_key or "").strip()
        if not key:
            return
        namespace, identity_type, raw_id = self._identity_parts(key)
        connection.execute(
            """
            INSERT INTO identities(
                identity_key, namespace, identity_type, raw_id, legacy_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(identity_key) DO UPDATE SET
                namespace = excluded.namespace,
                identity_type = excluded.identity_type,
                raw_id = excluded.raw_id,
                legacy_id = excluded.legacy_id
            """,
            (key, namespace, identity_type, raw_id, raw_id, int(time.time())),
        )

    def _refresh_projection(
        self, connection: sqlite3.Connection, key: str, value: Any
    ) -> None:
        if key == "pig_history.json":
            self._project_history(connection, value)
        elif key == "roast_state.json":
            self._project_roast_state(connection, value)
        elif key == "ai_roast_copies.json":
            self._project_ai_copies(connection, value)
        elif key == "local_overrides.json":
            self._project_catalog_overrides(connection, value)
        elif key == "deleted_pigs.json":
            self._project_tombstones(connection, value)

    def _project_history(self, connection: sqlite3.Connection, value: Any) -> None:
        connection.execute("DELETE FROM daily_draw_groups")
        connection.execute("DELETE FROM daily_draws")
        connection.execute("DELETE FROM user_pigs")
        connection.execute("DELETE FROM user_stats")
        connection.execute("DELETE FROM pig_snapshots")
        history = value if isinstance(value, dict) else {}
        users = history.get("users") if isinstance(history.get("users"), dict) else {}
        for user_id, raw_user in users.items():
            if not isinstance(raw_user, dict):
                continue
            user_key = str(user_id)
            self._remember_identity(connection, user_key)
            connection.execute(
                """
                INSERT INTO user_stats(
                    user_id, total_draws, active_days, duplicate_streak, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_key,
                    int(raw_user.get("total_draws", 0) or 0),
                    int(raw_user.get("active_days", 0) or 0),
                    int(raw_user.get("duplicate_streak", 0) or 0),
                    json.dumps(raw_user, ensure_ascii=False, sort_keys=True),
                ),
            )
            pigs = raw_user.get("pigs") if isinstance(raw_user.get("pigs"), dict) else {}
            for pig_id, raw_pig in pigs.items():
                if not isinstance(raw_pig, dict):
                    continue
                connection.execute(
                    """
                    INSERT INTO user_pigs(
                        user_id, pig_id, first_unlocked, last_drawn, draw_count
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_key,
                        str(pig_id),
                        str(raw_pig.get("first_unlocked") or ""),
                        str(raw_pig.get("last_drawn") or ""),
                        int(raw_pig.get("count", 0) or 0),
                    ),
                )

        daily = history.get("daily") if isinstance(history.get("daily"), dict) else {}
        for draw_date, raw_day in daily.items():
            if not isinstance(raw_day, dict):
                continue
            records = raw_day.get("records") if isinstance(raw_day.get("records"), dict) else {}
            originals = raw_day.get("eaten_originals") if isinstance(raw_day.get("eaten_originals"), dict) else {}
            groups = raw_day.get("groups") if isinstance(raw_day.get("groups"), dict) else {}
            memberships: dict[str, list[str]] = {}
            for group_id, members in groups.items():
                if not isinstance(members, list):
                    continue
                for member in members:
                    memberships.setdefault(str(member), []).append(str(group_id))
            for user_id, pig_id in records.items():
                user_key = str(user_id)
                self._remember_identity(connection, user_key)
                group_ids = sorted(set(memberships.get(user_key, [])))
                connection.execute(
                    """
                    INSERT INTO daily_draws(
                        draw_date, user_id, pig_id, original_pig_id, group_ids_json,
                        created_at, was_new_unlock
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(draw_date),
                        user_key,
                        str(pig_id or ""),
                        str(originals.get(user_id) or ""),
                        json.dumps(group_ids, ensure_ascii=False),
                        int(time.time()),
                        0,
                    ),
                )
                for group_id in group_ids:
                    connection.execute(
                        "INSERT INTO daily_draw_groups VALUES (?, ?, ?)",
                        (str(draw_date), user_key, group_id),
                    )

        snapshots = history.get("pig_snapshots") if isinstance(history.get("pig_snapshots"), dict) else {}
        for pig_id, snapshot in snapshots.items():
            if isinstance(snapshot, dict):
                connection.execute(
                    "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES (?, ?)",
                    (str(pig_id), json.dumps(snapshot, ensure_ascii=False, sort_keys=True)),
                )

    def _project_roast_state(self, connection: sqlite3.Connection, value: Any) -> None:
        for table in (
            "eaten_penalties",
            "eaten_events",
            "roast_cooldowns",
            "daily_roast_counts",
            "daily_backdoors",
        ):
            connection.execute(f"DELETE FROM {table}")
        state = value if isinstance(value, dict) else {}

        cooldowns = state.get("cooldowns") if isinstance(state.get("cooldowns"), dict) else {}
        for cooldown_key, used_at in cooldowns.items():
            group_id, separator, actor_id = str(cooldown_key).rpartition(":")
            if not separator:
                group_id, actor_id = "", str(cooldown_key)
            self._remember_identity(connection, actor_id)
            connection.execute(
                "INSERT INTO roast_cooldowns VALUES (?, ?, ?, ?)",
                (str(cooldown_key), group_id, actor_id, float(used_at or 0)),
            )

        counts = state.get("daily_roast_counts") if isinstance(state.get("daily_roast_counts"), dict) else {}
        for raw_key, count in counts.items():
            try:
                parsed = json.loads(str(raw_key))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(parsed, list) or len(parsed) != 3:
                continue
            draw_date, group_id, user_id = map(str, parsed)
            self._remember_identity(connection, user_id)
            connection.execute(
                "INSERT INTO daily_roast_counts VALUES (?, ?, ?, ?)",
                (draw_date, group_id, user_id, int(count or 0)),
            )

        penalties = state.get("eaten_penalties") if isinstance(state.get("eaten_penalties"), dict) else {}
        for user_id, entry in penalties.items():
            if not isinstance(entry, dict):
                continue
            user_key = str(user_id)
            self._remember_identity(connection, user_key)
            connection.execute(
                "INSERT INTO eaten_penalties VALUES (?, ?, ?, ?)",
                (
                    user_key,
                    str(entry.get("due_date") or ""),
                    int(bool(entry.get("failed"))),
                    json.dumps(entry, ensure_ascii=False, sort_keys=True),
                ),
            )

        events = state.get("eaten_events") if isinstance(state.get("eaten_events"), dict) else {}
        for event_key, entry in events.items():
            if not isinstance(entry, dict):
                continue
            try:
                parsed = json.loads(str(event_key))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(parsed, list) or len(parsed) != 3:
                continue
            event_date, group_id, user_id = map(str, parsed)
            actor_id = str(entry.get("actor_id") or "")
            self._remember_identity(connection, user_id)
            self._remember_identity(connection, actor_id)
            connection.execute(
                "INSERT INTO eaten_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(event_key),
                    event_date,
                    group_id,
                    user_id,
                    actor_id,
                    str(entry.get("outcome") or ""),
                    int(entry.get("at", 0) or 0),
                    json.dumps(entry, ensure_ascii=False, sort_keys=True),
                ),
            )

        backdoors = state.get("daily_backdoors") if isinstance(state.get("daily_backdoors"), dict) else {}
        for backdoor_key, used in backdoors.items():
            draw_date, separator, actor_id = str(backdoor_key).partition(":")
            if not separator or not actor_id:
                continue
            self._remember_identity(connection, actor_id)
            connection.execute(
                "INSERT INTO daily_backdoors VALUES (?, ?, ?, ?)",
                (str(backdoor_key), draw_date, actor_id, int(bool(used))),
            )

    @staticmethod
    def _project_ai_copies(connection: sqlite3.Connection, value: Any) -> None:
        connection.execute("DELETE FROM ai_roast_copies")
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

    @staticmethod
    def _project_catalog_overrides(connection: sqlite3.Connection, value: Any) -> None:
        connection.execute("DELETE FROM catalog_overrides")
        for item in value if isinstance(value, list) else []:
            if isinstance(item, dict) and str(item.get("id") or ""):
                connection.execute(
                    "INSERT INTO catalog_overrides VALUES (?, ?)",
                    (
                        str(item["id"]),
                        json.dumps(item, ensure_ascii=False, sort_keys=True),
                    ),
                )

    @staticmethod
    def _project_tombstones(connection: sqlite3.Connection, value: Any) -> None:
        connection.execute("DELETE FROM catalog_tombstones")
        for pig_id in value if isinstance(value, list) else []:
            if str(pig_id):
                connection.execute(
                    "INSERT INTO catalog_tombstones VALUES (?)", (str(pig_id),)
                )

    @staticmethod
    def _candidate_tuple(user_candidates: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(str(item) for item in user_candidates if str(item))

    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:
        candidates = self._candidate_tuple(user_candidates)
        if not candidates:
            return None
        with self._lock, self._connection() as connection:
            for user_id in candidates:
                stats = connection.execute(
                    "SELECT total_draws, active_days, duplicate_streak "
                    "FROM user_stats WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if not stats:
                    continue
                pigs = connection.execute(
                    "SELECT pig_id, first_unlocked, last_drawn, draw_count "
                    "FROM user_pigs WHERE user_id = ? ORDER BY pig_id",
                    (user_id,),
                ).fetchall()
                return {
                    "total_draws": int(stats["total_draws"]),
                    "active_days": int(stats["active_days"]),
                    "duplicate_streak": int(stats["duplicate_streak"]),
                    "pigs": {
                        str(row["pig_id"]): {
                            "first_unlocked": str(row["first_unlocked"]),
                            "last_drawn": str(row["last_drawn"]),
                            "count": int(row["draw_count"]),
                        }
                        for row in pigs
                    },
                }
        return None

    def get_daily_draw(
        self, draw_date: str, user_candidates: tuple[str, ...]
    ) -> dict[str, Any] | None:
        candidates = self._candidate_tuple(user_candidates)
        with self._lock, self._connection() as connection:
            for user_id in candidates:
                row = connection.execute(
                    "SELECT user_id, pig_id, original_pig_id FROM daily_draws "
                    "WHERE draw_date = ? AND user_id = ?",
                    (str(draw_date), user_id),
                ).fetchone()
                if row:
                    return {
                        "user_id": str(row["user_id"]),
                        "pig_id": str(row["pig_id"]),
                        "original_pig_id": str(row["original_pig_id"]),
                    }
        return None

    def get_group_members(self, draw_date: str, group_id: str) -> list[str] | None:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT user_id FROM daily_draw_groups "
                "WHERE draw_date = ? AND group_id = ? ORDER BY user_id",
                (str(draw_date), str(group_id)),
            ).fetchall()
        return [str(row["user_id"]) for row in rows]

    def get_eaten_victims(self, event_date: str, group_id: str) -> list[str] | None:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT DISTINCT user_id FROM eaten_events "
                "WHERE event_date = ? AND group_id = ? ORDER BY user_id",
                (str(event_date), str(group_id)),
            ).fetchall()
        return [str(row["user_id"]) for row in rows]

    def _read_document_tx(
        self, connection: sqlite3.Connection, key: str, default: Any
    ) -> Any:
        row = connection.execute(
            "SELECT payload FROM documents WHERE key = ?", (str(key),)
        ).fetchone()
        return self._decode(str(row["payload"])) if row else self._clone(default)

    def _write_document_tx(
        self,
        connection: sqlite3.Connection,
        key: str,
        value: Any,
        *,
        updated_at: int | None = None,
    ) -> None:
        payload, digest = self._encode(value)
        connection.execute(
            """
            INSERT INTO documents(key, payload, payload_sha256, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                payload = excluded.payload,
                payload_sha256 = excluded.payload_sha256,
                updated_at = excluded.updated_at
            """,
            (str(key), payload, digest, int(updated_at or time.time())),
        )

    @staticmethod
    def _ordered_candidates(
        user_id: str, user_candidates: tuple[str, ...]
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item
                for item in (str(user_id), *(str(x) for x in user_candidates))
                if item
            )
        )

    @staticmethod
    def _event_key(event_date: str, group_id: str, user_id: str) -> str:
        return json.dumps(
            [str(event_date), str(group_id), str(user_id)], ensure_ascii=False
        )

    @staticmethod
    def _valid_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

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
        """Create one daily draw with SQL uniqueness and synchronized export docs.

        A probe call with ``pig=None`` returns an existing draw, consumes/blocks a
        due penalty, or returns ``needs-pig``. The caller can then choose a pig and
        retry; a competing process that wins between the two calls is returned as
        ``existing`` instead of creating a second result.
        """
        draw_date = str(draw_date)
        canonical_id = str(user_id)
        candidates = self._ordered_candidates(canonical_id, user_candidates)
        now = int(time.time())
        history_default = {
            "version": 1,
            "users": {},
            "daily": {},
            "pig_snapshots": {},
        }
        roast_default = {
            "version": 1,
            "cooldowns": {},
            "daily_backdoors": {},
            "daily_roast_counts": {},
            "eaten_penalties": {},
            "eaten_events": {},
        }
        today_default = {"date": draw_date, "records": {}}

        with self.transaction() as connection:
            history = self._valid_dict(
                self._read_document_tx(connection, "pig_history.json", history_default)
            )
            roast = self._valid_dict(
                self._read_document_tx(connection, "roast_state.json", roast_default)
            )
            today_doc = self._valid_dict(
                self._read_document_tx(connection, "rollpig_today.json", today_default)
            )

            existing = None
            for candidate in candidates:
                existing = connection.execute(
                    "SELECT user_id, pig_id, original_pig_id FROM daily_draws "
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
                    daily = history.setdefault("daily", {})
                    if not isinstance(daily, dict):
                        daily = {}
                        history["daily"] = daily
                    day = daily.setdefault(
                        draw_date,
                        {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
                    )
                    day_groups = day.setdefault("groups", {})
                    members = day_groups.setdefault(str(group_id), [])
                    if actual_id not in members:
                        members.append(actual_id)
                snapshot = connection.execute(
                    "SELECT payload_json FROM pig_snapshots WHERE pig_id = ?",
                    (pig_id,),
                ).fetchone()
                pig_payload = (
                    self._decode(str(snapshot["payload_json"]))
                    if snapshot
                    else {"id": pig_id}
                )
                if today_doc.get("date") != draw_date:
                    today_doc = {"date": draw_date, "records": {}}
                today_doc.setdefault("records", {})[actual_id] = pig_payload
                self._write_document_tx(
                    connection, "pig_history.json", history, updated_at=now
                )
                self._write_document_tx(
                    connection, "rollpig_today.json", today_doc, updated_at=now
                )
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES "
                    "('write_authority', 'sql-primary-v2.11') "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                )
                return {
                    "status": "existing",
                    "created": False,
                    "user_id": actual_id,
                    "pig_id": pig_id,
                    "pig": pig_payload,
                    "history": history,
                    "roast_state": roast,
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
            penalties_doc = roast.get("eaten_penalties")
            if not isinstance(penalties_doc, dict):
                penalties_doc = {}
                roast["eaten_penalties"] = penalties_doc
            roast_changed = False
            if penalty_row:
                penalty_user = str(penalty_row["user_id"])
                due_date = str(penalty_row["due_date"])
                failed = bool(penalty_row["failed"])
                if due_date < draw_date:
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )
                    penalties_doc.pop(penalty_user, None)
                    roast_changed = True
                elif due_date == draw_date and failed:
                    return {
                        "status": "penalty-blocked",
                        "created": False,
                        "history": history,
                        "roast_state": roast,
                    }
                elif due_date == draw_date and penalty_should_fail:
                    payload = {"due_date": draw_date, "failed": True}
                    connection.execute(
                        "UPDATE eaten_penalties SET failed = 1, payload_json = ? "
                        "WHERE user_id = ?",
                        (json.dumps(payload, ensure_ascii=False, sort_keys=True), penalty_user),
                    )
                    penalties_doc[penalty_user] = payload
                    self._write_document_tx(
                        connection, "roast_state.json", roast, updated_at=now
                    )
                    connection.execute(
                        "INSERT INTO projection_meta(key, value) VALUES "
                        "('write_authority', 'sql-primary-v2.11') "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                    )
                    return {
                        "status": "penalty-blocked",
                        "created": False,
                        "history": history,
                        "roast_state": roast,
                    }
                elif due_date == draw_date:
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )
                    penalties_doc.pop(penalty_user, None)
                    roast_changed = True

            if not isinstance(pig, dict) or not str(pig.get("id") or "").strip():
                if roast_changed:
                    self._write_document_tx(
                        connection, "roast_state.json", roast, updated_at=now
                    )
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES "
                    "('write_authority', 'sql-primary-v2.11') "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                )
                return {
                    "status": "needs-pig",
                    "created": False,
                    "history": history,
                    "roast_state": roast,
                }

            pig_payload = self._clone(pig)
            pig_id = str(pig_payload["id"])
            self._remember_identity(connection, canonical_id)
            unlocked = (
                connection.execute(
                    "SELECT 1 FROM user_pigs WHERE user_id = ? AND pig_id = ?",
                    (canonical_id, pig_id),
                ).fetchone()
                is None
            )
            stats = connection.execute(
                "SELECT total_draws, active_days, duplicate_streak "
                "FROM user_stats WHERE user_id = ?",
                (canonical_id,),
            ).fetchone()
            total_draws = int(stats["total_draws"]) if stats else 0
            active_days = int(stats["active_days"]) if stats else 0
            duplicate_streak = int(stats["duplicate_streak"]) if stats else 0

            connection.execute(
                """
                INSERT INTO daily_draws(
                    draw_date, user_id, pig_id, original_pig_id, group_ids_json,
                    created_at, was_new_unlock
                ) VALUES (?, ?, ?, '', ?, ?, ?)
                """,
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
                """
                INSERT INTO user_pigs(
                    user_id, pig_id, first_unlocked, last_drawn, draw_count
                ) VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id, pig_id) DO UPDATE SET
                    last_drawn = excluded.last_drawn,
                    draw_count = user_pigs.draw_count + 1
                """,
                (canonical_id, pig_id, draw_date, draw_date),
            )
            connection.execute(
                "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES (?, ?) "
                "ON CONFLICT(pig_id) DO UPDATE SET payload_json = excluded.payload_json",
                (
                    pig_id,
                    json.dumps(pig_payload, ensure_ascii=False, sort_keys=True),
                ),
            )

            users = history.get("users")
            if not isinstance(users, dict):
                users = {}
                history["users"] = users
            user_doc = users.setdefault(
                canonical_id, {"total_draws": 0, "active_days": 0, "pigs": {}}
            )
            pigs_doc = user_doc.get("pigs")
            if not isinstance(pigs_doc, dict):
                pigs_doc = {}
                user_doc["pigs"] = pigs_doc
            record_doc = pigs_doc.setdefault(
                pig_id,
                {
                    "first_unlocked": draw_date,
                    "last_drawn": draw_date,
                    "count": 0,
                },
            )
            record_doc["last_drawn"] = draw_date
            record_doc["count"] = int(record_doc.get("count", 0)) + 1
            user_doc["total_draws"] = total_draws + 1
            user_doc["active_days"] = active_days + 1
            user_doc["duplicate_streak"] = 0 if unlocked else duplicate_streak + 1

            daily = history.get("daily")
            if not isinstance(daily, dict):
                daily = {}
                history["daily"] = daily
            day = daily.setdefault(
                draw_date,
                {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
            )
            day.setdefault("users", []).append(canonical_id)
            day.setdefault("records", {})[canonical_id] = pig_id
            day["draws"] = int(day.get("draws", 0)) + 1
            if unlocked:
                day["new_unlocks"] = int(day.get("new_unlocks", 0)) + 1
            if group_id:
                members = day.setdefault("groups", {}).setdefault(str(group_id), [])
                if canonical_id not in members:
                    members.append(canonical_id)
            history.setdefault("pig_snapshots", {})[pig_id] = pig_payload

            connection.execute(
                """
                INSERT INTO user_stats(
                    user_id, total_draws, active_days, duplicate_streak, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_draws = excluded.total_draws,
                    active_days = excluded.active_days,
                    duplicate_streak = excluded.duplicate_streak,
                    payload_json = excluded.payload_json
                """,
                (
                    canonical_id,
                    total_draws + 1,
                    active_days + 1,
                    0 if unlocked else duplicate_streak + 1,
                    json.dumps(user_doc, ensure_ascii=False, sort_keys=True),
                ),
            )
            if today_doc.get("date") != draw_date:
                today_doc = {"date": draw_date, "records": {}}
            today_doc.setdefault("records", {})[canonical_id] = pig_payload

            self._write_document_tx(
                connection, "pig_history.json", history, updated_at=now
            )
            self._write_document_tx(
                connection, "rollpig_today.json", today_doc, updated_at=now
            )
            if roast_changed:
                self._write_document_tx(
                    connection, "roast_state.json", roast, updated_at=now
                )
            connection.execute(
                "INSERT INTO projection_meta(key, value) VALUES "
                "('write_authority', 'sql-primary-v2.11') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )
            return {
                "status": "created",
                "created": True,
                "user_id": canonical_id,
                "pig_id": pig_id,
                "pig": pig_payload,
                "was_new_unlock": unlocked,
                "history": history,
                "roast_state": roast,
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
        """Atomically replace a draw, create its penalty and record the event."""
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
                """
                INSERT INTO eaten_penalties(user_id, due_date, failed, payload_json)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    due_date = excluded.due_date,
                    failed = 0,
                    payload_json = excluded.payload_json
                """,
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
                """
                INSERT INTO eaten_events(
                    event_key, event_date, group_id, user_id, actor_id,
                    outcome, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_key) DO UPDATE SET
                    actor_id = excluded.actor_id,
                    outcome = excluded.outcome,
                    created_at = excluded.created_at,
                    payload_json = excluded.payload_json
                """,
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

            history = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "pig_history.json",
                    {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}},
                )
            )
            roast = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "roast_state.json",
                    {
                        "version": 1,
                        "cooldowns": {},
                        "daily_backdoors": {},
                        "daily_roast_counts": {},
                        "eaten_penalties": {},
                        "eaten_events": {},
                    },
                )
            )
            today_doc = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "rollpig_today.json",
                    {"date": draw_date, "records": {}},
                )
            )
            if today_doc.get("date") != draw_date:
                today_doc = {"date": draw_date, "records": {}}
            today_doc.setdefault("records", {})[actual_id] = eaten_payload

            daily = history.setdefault("daily", {})
            day = daily.setdefault(
                draw_date,
                {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
            )
            day.setdefault("records", {})[actual_id] = "eaten"
            day.setdefault("eaten_originals", {}).setdefault(actual_id, original_id)
            history.setdefault("pig_snapshots", {})["eaten"] = eaten_payload

            penalties_doc = roast.get("eaten_penalties")
            if not isinstance(penalties_doc, dict):
                penalties_doc = {}
                roast["eaten_penalties"] = penalties_doc
            penalties_doc[actual_id] = penalty_payload
            roast["eaten_penalties"] = {
                key: value
                for key, value in penalties_doc.items()
                if isinstance(value, dict)
                and str(value.get("due_date") or "") >= draw_date
            }
            events_doc = roast.get("eaten_events")
            if not isinstance(events_doc, dict):
                events_doc = {}
                roast["eaten_events"] = events_doc
            events_doc[event_key] = event_payload
            roast["eaten_events"] = {
                key: value
                for key, value in events_doc.items()
                if isinstance(value, dict)
                and (
                    (lambda parsed: isinstance(parsed, list) and len(parsed) == 3 and str(parsed[0]) >= str(cutoff_date))(
                        json.loads(key)
                    )
                    if isinstance(key, str)
                    else False
                )
            }

            self._write_document_tx(
                connection, "pig_history.json", history, updated_at=now
            )
            self._write_document_tx(
                connection, "roast_state.json", roast, updated_at=now
            )
            self._write_document_tx(
                connection, "rollpig_today.json", today_doc, updated_at=now
            )
            connection.execute(
                "INSERT INTO projection_meta(key, value) VALUES "
                "('write_authority', 'sql-primary-v2.11') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )
            return {
                "status": "updated",
                "user_id": actual_id,
                "previous_pig_id": current_pig_id,
                "original_pig_id": original_id,
                "history": history,
                "roast_state": roast,
            }

    @staticmethod
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
        ai_count = sum(
            sum(1 for content in value.values() if str(content or "").strip())
            for value in copies.values()
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
        documents = {
            str(row["key"]): self._decode(str(row["payload"])) for row in rows
        }
        expected = self._expected_projection_counts(documents)
        actual = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in expected
        }
        mismatches = {
            table: {"expected": expected[table], "actual": actual[table]}
            for table in expected
            if expected[table] != actual[table]
        }
        return {
            "projection_ok": not mismatches,
            "projection_mismatches": mismatches,
            "projection_expected": expected,
            "projection_actual": actual,
        }

    @staticmethod
    def _clear_projections(connection: sqlite3.Connection) -> None:
        for table in (
            "daily_draw_groups",
            "daily_draws",
            "user_pigs",
            "user_stats",
            "pig_snapshots",
            "eaten_penalties",
            "eaten_events",
            "roast_cooldowns",
            "daily_roast_counts",
            "daily_backdoors",
            "ai_roast_copies",
            "catalog_overrides",
            "catalog_tombstones",
            "identities",
        ):
            connection.execute(f"DELETE FROM {table}")

    def rebuild_projections(self) -> dict[str, Any]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT key, payload FROM documents ORDER BY key"
            ).fetchall()
            documents = {
                str(row["key"]): self._decode(str(row["payload"])) for row in rows
            }
            self._clear_projections(connection)
            for key, value in documents.items():
                self._refresh_projection(connection, key, value)
            connection.execute(
                "INSERT INTO projection_meta(key, value) VALUES ('last_rebuild_at', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(int(time.time())),),
            )
            result = self._projection_health(connection)
            if not result["projection_ok"]:
                raise RuntimeError("projection rebuild did not reconcile all tables")
        return {"ok": True, **result}

    def export_documents(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT key, payload FROM documents ORDER BY key"
            ).fetchall()
        return {str(row["key"]): self._decode(str(row["payload"])) for row in rows}

    def document_hashes(self) -> dict[str, str]:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT key, payload_sha256 FROM documents ORDER BY key"
            ).fetchall()
        return {str(row["key"]): str(row["payload_sha256"]) for row in rows}

    def checkpoint(self) -> None:
        with self._lock, self._connection() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

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
                self._projection_health(connection)
                if deep
                else {
                    "projection_ok": None,
                    "projection_mismatches": {},
                    "projection_expected": {},
                    "projection_actual": {},
                }
            )
        return {
            "ok": (
                integrity == "ok"
                and not foreign_rows
                and projection["projection_ok"] is not False
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
            **verification,
        }
