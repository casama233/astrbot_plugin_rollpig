from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def replace_method(source: str, name: str, replacement: str, *, async_def: bool = False) -> str:
    prefix = "async def" if async_def else "def"
    pattern = re.compile(
        rf"^    {prefix} {re.escape(name)}\(.*?(?=^    (?:@|async def |def ))",
        re.MULTILINE | re.DOTALL,
    )
    updated, count = pattern.subn(replacement.rstrip() + "\n\n", source, count=1)
    if count != 1:
        raise RuntimeError(f"method {name}: expected one match, found {count}")
    return updated


# ---------------------------------------------------------------------------
# Business services
# ---------------------------------------------------------------------------
write(
    "services/__init__.py",
    '''from .draw_service import DrawService
from .roast_service import RoastService

__all__ = ["DrawService", "RoastService"]
''',
)

write(
    "services/draw_service.py",
    '''from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DrawService:
    """Pure daily-draw selection policy, independent from persistence and AstrBot."""

    enable_new_pig_pity: bool = True
    pity_step_percent: int = 15

    def choose(
        self,
        pigs: Sequence[Mapping[str, Any]],
        collection: Mapping[str, Any] | None,
        *,
        rng: Any = random,
    ) -> dict[str, Any]:
        if not pigs:
            raise ValueError("pig catalog is empty")
        chosen = dict(rng.choice(pigs))
        if not self.enable_new_pig_pity:
            return chosen
        user = collection if isinstance(collection, Mapping) else {}
        unlocked_raw = user.get("pigs")
        unlocked = set(unlocked_raw) if isinstance(unlocked_raw, Mapping) else set()
        unseen = [pig for pig in pigs if str(pig.get("id") or "") not in unlocked]
        chosen_id = str(chosen.get("id") or "")
        if not unseen or chosen_id not in unlocked:
            return chosen
        streak = max(0, int(user.get("duplicate_streak", 0) or 0))
        chance = min(0.80, streak * max(0, self.pity_step_percent) / 100)
        return dict(rng.choice(unseen)) if rng.random() < chance else chosen
''',
)

write(
    "services/roast_service.py",
    '''from __future__ import annotations

from typing import Any, Mapping

try:
    from ..rollpig_core import special_pig_state
except ImportError:  # pragma: no cover - direct module loading compatibility
    from rollpig_core import special_pig_state


class RoastService:
    """Eligibility and copy rules for roast/eat actions."""

    @staticmethod
    def _name(pig: Mapping[str, Any] | None) -> str:
        value = pig or {}
        return str(value.get("name") or value.get("id") or "特殊形态").strip()

    def roast_block_reason(
        self, pig: Mapping[str, Any] | None, *, subject: str = "target"
    ) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        actor = subject == "actor"
        if state == "missing":
            return "你今天还没有抽取小猪。" if actor else "对方今天还没有抽取小猪。"
        name = self._name(pig)
        if state == "human":
            if actor:
                return "你今天是「人类」：只能围观，不能参与猪圈料理。"
            return "对方今天是「人类」：猪圈劳动合同不支持把人送上烤架。"
        if state == "eaten":
            if actor:
                return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
            return "对方今天是「吃掉了」：盘子都空了，不能继续参与烧烤流程。"
        if actor:
            return f"你今天是「{name}」：已经上桌了，不能再次参与烧烤。"
        return f"对方今天是「{name}」：已经是熟食，不能再上一次烤架。"

    def eat_actor_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        if state == "missing":
            return "你今天还没有抽取小猪，不能发动吃群友。"
        name = self._name(pig)
        if state == "human":
            return "你今天是「人类」：猪圈菜单不允许人类发动吃群友。"
        if state == "eaten":
            return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
        return f"你今天是「{name}」：已经上桌了，暂时不能去吃群友。"

    def eat_target_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state in {"normal", "cooked"}:
            return None
        if state == "missing":
            return "对方今天还没有抽取小猪。"
        if state == "human":
            return "对方今天是「人类」：吃人不在猪圈菜单里。"
        return "对方今天已经是「吃掉了」：盘子空了，不能再吃一次。"

    def eat_success_message(self, pig: Mapping[str, Any]) -> str:
        name = self._name(pig)
        action = (
            "开袋即食成功"
            if special_pig_state(dict(pig)) == "cooked"
            else "吃群友成功"
        )
        return f" 🍴 {action}，「{name}」被吃掉了；明天抽猪可能失败。"
''',
)

# ---------------------------------------------------------------------------
# Storage contract
# ---------------------------------------------------------------------------
base = read("storage/base.py")
base = replace_once(
    base,
    '    backend_name = "unknown"\n',
    '    backend_name = "unknown"\n    supports_domain_reads = False\n',
    "base capabilities",
)
base = replace_once(
    base,
    '    def health(self) -> dict[str, Any]:\n        """Return a small dashboard-safe backend status snapshot."""\n',
    '''    def health(self) -> dict[str, Any]:
        """Return a small dashboard-safe backend status snapshot."""

    # Transitional domain read API. JSONStorage keeps using the in-memory
    # compatibility documents; SQLite overrides these methods with indexed SQL.
    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:
        return None

    def get_daily_draw(
        self, draw_date: str, user_candidates: tuple[str, ...]
    ) -> dict[str, Any] | None:
        return None

    def get_group_members(self, draw_date: str, group_id: str) -> list[str] | None:
        return None

    def get_eaten_victims(self, event_date: str, group_id: str) -> list[str] | None:
        return None
''',
    "base domain API",
)
write("storage/base.py", base)

# ---------------------------------------------------------------------------
# SQLite schema v2, real transaction context and indexed read paths
# ---------------------------------------------------------------------------
sqlite = read("storage/sqlite_storage.py")
sqlite = replace_once(sqlite, '    backend_name = "sqlite"\n    schema_version = 1\n', '    backend_name = "sqlite"\n    supports_domain_reads = True\n    schema_version = 2\n', "sqlite capabilities")

initialize = '''    def _initialize(self) -> None:
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
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS daily_draw_groups (
                        draw_date TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        PRIMARY KEY (draw_date, user_id, group_id),
                        FOREIGN KEY (draw_date, user_id)
                            REFERENCES daily_draws(draw_date, user_id)
                            ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_identities_namespace_raw
                        ON identities(namespace, raw_id);
                    CREATE INDEX IF NOT EXISTS idx_daily_draw_groups_group_date
                        ON daily_draw_groups(group_id, draw_date);
                    """
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
'''
sqlite = replace_method(sqlite, "_initialize", initialize)

transaction = '''    @contextmanager
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
'''
# replace_method cannot include the decorator in its match; replace the complete old block.
sqlite = replace_once(
    sqlite,
    '''    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            yield
''',
    transaction,
    "sqlite transaction",
)

remember_identity = '''    def _remember_identity(self, connection: sqlite3.Connection, identity_key: str) -> None:
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
'''
sqlite = replace_method(sqlite, "_remember_identity", remember_identity)

sqlite = replace_once(
    sqlite,
    '''        connection.execute("DELETE FROM daily_draws")
        connection.execute("DELETE FROM user_pigs")
''',
    '''        connection.execute("DELETE FROM daily_draw_groups")
        connection.execute("DELETE FROM daily_draws")
        connection.execute("DELETE FROM user_pigs")
''',
    "projection delete order",
)

old_draw_insert = '''                connection.execute(
                    """
                    INSERT INTO daily_draws(
                        draw_date, user_id, pig_id, original_pig_id, group_ids_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(draw_date),
                        user_key,
                        str(pig_id or ""),
                        str(originals.get(user_id) or ""),
                        json.dumps(sorted(set(memberships.get(user_key, []))), ensure_ascii=False),
                    ),
                )
'''
new_draw_insert = '''                group_ids = sorted(set(memberships.get(user_key, [])))
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
'''
sqlite = replace_once(sqlite, old_draw_insert, new_draw_insert, "daily group projection")

query_methods = '''    @staticmethod
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
        user_pigs = sum(
            len(value.get("pigs", {}))
            for value in users.values()
            if isinstance(value, dict) and isinstance(value.get("pigs"), dict)
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
            daily_groups += sum(len(membership.get(str(user_id), set())) for user_id in records)

        roast = documents.get("roast_state.json")
        roast = roast if isinstance(roast, dict) else {}
        ai = documents.get("ai_roast_copies.json")
        ai = ai if isinstance(ai, dict) else {}
        copies = ai.get("copies") if isinstance(ai.get("copies"), dict) else {}
        ai_count = sum(len(value) for value in copies.values() if isinstance(value, dict))
        overrides = documents.get("local_overrides.json")
        tombstones = documents.get("deleted_pigs.json")
        return {
            "user_stats": sum(1 for value in users.values() if isinstance(value, dict)),
            "user_pigs": user_pigs,
            "daily_draws": daily_draws,
            "daily_draw_groups": daily_groups,
            "pig_snapshots": sum(1 for value in snapshots.values() if isinstance(value, dict)),
            "eaten_penalties": len(roast.get("eaten_penalties", {}))
            if isinstance(roast.get("eaten_penalties"), dict)
            else 0,
            "eaten_events": len(roast.get("eaten_events", {}))
            if isinstance(roast.get("eaten_events"), dict)
            else 0,
            "roast_cooldowns": len(roast.get("cooldowns", {}))
            if isinstance(roast.get("cooldowns"), dict)
            else 0,
            "daily_roast_counts": len(roast.get("daily_roast_counts", {}))
            if isinstance(roast.get("daily_roast_counts"), dict)
            else 0,
            "daily_backdoors": len(roast.get("daily_backdoors", {}))
            if isinstance(roast.get("daily_backdoors"), dict)
            else 0,
            "ai_roast_copies": ai_count,
            "catalog_overrides": sum(1 for value in overrides if isinstance(value, dict))
            if isinstance(overrides, list)
            else 0,
            "catalog_tombstones": len(tombstones) if isinstance(tombstones, list) else 0,
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

'''
sqlite = replace_once(
    sqlite,
    '    def export_documents(self) -> dict[str, Any]:\n',
    query_methods + '    def export_documents(self) -> dict[str, Any]:\n',
    "sqlite query methods",
)

verify = '''    def verify(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            foreign_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
            schema_row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()
            documents = int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
            daily_draws = int(connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0])
            users = int(connection.execute("SELECT COUNT(*) FROM user_stats").fetchone()[0])
            projection = self._projection_health(connection)
        return {
            "ok": integrity == "ok" and not foreign_rows and projection["projection_ok"],
            "integrity": integrity,
            "foreign_key_errors": len(foreign_rows),
            "schema_version": int(schema_row[0] if schema_row else 0),
            "documents": documents,
            "daily_draws": daily_draws,
            "users": users,
            **projection,
        }
'''
sqlite = replace_method(sqlite, "verify", verify)
write("storage/sqlite_storage.py", sqlite)

# ---------------------------------------------------------------------------
# Manager: auto repair projections and dashboard rebuild action
# ---------------------------------------------------------------------------
manager = read("storage/manager.py")
old_select = '''            verification = candidate.verify()
            if not verification.get("ok"):
                raise StorageMigrationError(
                    f"SQLite 完整性检查失败：{verification.get('integrity')}"
                )
            self.backend = candidate
'''
new_select = '''            verification = candidate.verify()
            if (
                verification.get("integrity") == "ok"
                and int(verification.get("foreign_key_errors", 0) or 0) == 0
                and verification.get("projection_ok") is False
            ):
                candidate.rebuild_projections()
                verification = candidate.verify()
                self._last_action = {"status": "auto-rebuilt-projections"}
            if not verification.get("ok"):
                raise StorageMigrationError(
                    f"SQLite 完整性或投影检查失败：{verification.get('integrity')}"
                )
            self.backend = candidate
'''
manager = replace_once(manager, old_select, new_select, "manager auto rebuild")
manager = replace_once(
    manager,
    '    def status(self) -> dict[str, Any]:\n',
    '''    def rebuild_projections(self) -> dict[str, Any]:
        with self._lock:
            if not self.database_path.exists():
                raise StorageMigrationError("尚未建立 SQLite 数据库")
            target = self._new_sqlite()
            result = target.rebuild_projections()
            verification = target.verify()
            if not verification.get("ok"):
                raise StorageMigrationError("投影重建后仍未通过一致性验证")
            if isinstance(self.backend, SQLiteStorage):
                self.backend = target
            action = {
                "status": "projections-rebuilt",
                "backend": self.backend.backend_name,
                "verification": verification,
            }
            self._last_error = ""
            self._last_action = action
            return action

    def status(self) -> dict[str, Any]:
''',
    "manager rebuild",
)
write("storage/manager.py", manager)

# ---------------------------------------------------------------------------
# Main plugin delegates business policy and indexed reads
# ---------------------------------------------------------------------------
main = read("main.py")
main = replace_once(
    main,
    '''try:
    from .rollpig_core import special_pig_state
    from .storage import StorageManager, StorageMigrationError
    from .updater import PluginUpdateManager, UpdateError
except ImportError:  # pragma: no cover - direct module loading compatibility
    from rollpig_core import special_pig_state
    from storage import StorageManager, StorageMigrationError
    from updater import PluginUpdateManager, UpdateError
''',
    '''try:
    from .services import DrawService, RoastService
    from .storage import StorageManager, StorageMigrationError
    from .updater import PluginUpdateManager, UpdateError
except ImportError:  # pragma: no cover - direct module loading compatibility
    from services import DrawService, RoastService
    from storage import StorageManager, StorageMigrationError
    from updater import PluginUpdateManager, UpdateError
''',
    "main service imports",
)
main = main.replace("AstrBot-RollPig/2.9.2", "AstrBot-RollPig/2.10.0")
main = replace_once(
    main,
    '''        self.storage = self.storage_manager.backend
        self._storage_admin_lock = asyncio.Lock()
''',
    '''        self.storage = self.storage_manager.backend
        self.draw_service = DrawService(
            enable_new_pig_pity=self.enable_new_pig_pity,
            pity_step_percent=self.pity_step_percent,
        )
        self.roast_service = RoastService()
        self._storage_admin_lock = asyncio.Lock()
''',
    "service initialization",
)

choose = '''    def _choose_daily_pig(self, user_id: str) -> dict:
        """Delegate pure pity/selection policy to DrawService."""
        return self.draw_service.choose(
            self.pig_list,
            self._get_user_collection(user_id),
        )
'''
main = replace_method(main, "_choose_daily_pig", choose)

collection = '''    def _get_user_collection(self, user_id: str) -> dict:
        candidates = tuple(self._user_read_candidates(str(user_id)))
        if getattr(self.storage, "supports_domain_reads", False):
            stored = self.storage.get_user_collection(candidates)
            return stored or {}
        users = self.history.get("users", {})
        for candidate in candidates:
            user = users.get(candidate, {})
            if isinstance(user, dict) and user:
                return user
        return {}
'''
main = replace_method(main, "_get_user_collection", collection)

daily = '''    def _get_daily_pig(self, user_id: str, date_value: datetime.date) -> dict | None:
        candidates = tuple(self._user_read_candidates(str(user_id)))
        if getattr(self.storage, "supports_domain_reads", False):
            stored = self.storage.get_daily_draw(date_value.isoformat(), candidates)
            pig_id = str((stored or {}).get("pig_id") or "")
            if not pig_id:
                return None
            return self._find_catalog_pig(pig_id) or self.history.get(
                "pig_snapshots", {}
            ).get(pig_id)
        day = self.history.get("daily", {}).get(date_value.isoformat(), {})
        records = day.get("records", {})
        pig_id = ""
        for candidate in candidates:
            pig_id = str(records.get(candidate, ""))
            if pig_id:
                break
        if not pig_id:
            return None
        return self._find_catalog_pig(pig_id) or self.history.get(
            "pig_snapshots", {}
        ).get(pig_id)
'''
main = replace_method(main, "_get_daily_pig", daily)

weekly = '''    def _get_weekly_pig(self, user_id: str, date_value: datetime.date) -> tuple[dict | None, bool]:
        """Read weekly display data, preserving the original pig after eating."""
        user_key = str(user_id)
        candidates = tuple(self._user_read_candidates(user_key))
        if getattr(self.storage, "supports_domain_reads", False):
            stored = self.storage.get_daily_draw(date_value.isoformat(), candidates)
            if not stored:
                return None, False
            pig_id = str(stored.get("pig_id") or "")
            original_id = str(stored.get("original_pig_id") or "")
            if pig_id == "eaten" and original_id:
                original = self._find_catalog_pig(original_id) or self.history.get(
                    "pig_snapshots", {}
                ).get(original_id)
                if original:
                    return original, True
            pig = self._find_catalog_pig(pig_id) or self.history.get(
                "pig_snapshots", {}
            ).get(pig_id)
            return pig, False
        day = self.history.get("daily", {}).get(date_value.isoformat(), {})
        records = day.get("records", {})
        originals = day.get("eaten_originals", {})
        pig_id = ""
        original_id = ""
        for candidate in candidates:
            if not pig_id:
                pig_id = str(records.get(candidate, ""))
            if not original_id:
                original_id = str(originals.get(candidate, ""))
        if pig_id == "eaten" and original_id:
            original = self._find_catalog_pig(original_id) or self.history.get(
                "pig_snapshots", {}
            ).get(original_id)
            if original:
                return original, True
        return self._get_daily_pig(user_key, date_value), False
'''
main = replace_method(main, "_get_weekly_pig", weekly)

main = replace_method(
    main,
    "_roast_block_reason",
    '''    def _roast_block_reason(
        self, pig: dict | None, *, subject: str = "target"
    ) -> str | None:
        return self.roast_service.roast_block_reason(pig, subject=subject)
''',
)
main = replace_method(
    main,
    "_eat_actor_block_reason",
    '''    def _eat_actor_block_reason(self, pig: dict | None) -> str | None:
        return self.roast_service.eat_actor_block_reason(pig)
''',
)
main = replace_method(
    main,
    "_eat_target_block_reason",
    '''    def _eat_target_block_reason(self, pig: dict | None) -> str | None:
        return self.roast_service.eat_target_block_reason(pig)
''',
)
main = replace_method(
    main,
    "_eat_success_message",
    '''    def _eat_success_message(self, pig: dict) -> str:
        return self.roast_service.eat_success_message(pig)
''',
)

victims_and_members = '''    def _daily_eaten_victims(self, group_id: str, draw_date: str) -> list[str]:
        """Read daily eaten victims from SQL when available."""
        if getattr(self.storage, "supports_domain_reads", False):
            stored = self.storage.get_eaten_victims(draw_date, group_id)
            return stored or []
        events = self.roast_state.get("eaten_events", {})
        if not isinstance(events, dict):
            return []
        victims: list[str] = []
        for key in events:
            try:
                date_value, event_group, user_id = json.loads(key)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if str(date_value) == draw_date and str(event_group) == group_id:
                user_id = str(user_id)
                if user_id not in victims:
                    victims.append(user_id)
        return victims

    def _daily_group_members(self, group_id: str, draw_date: str) -> list[str]:
        if getattr(self.storage, "supports_domain_reads", False):
            stored = self.storage.get_group_members(draw_date, group_id)
            return stored or []
        day = self.history.get("daily", {}).get(draw_date, {})
        members = day.get("groups", {}).get(group_id, [])
        return [str(value) for value in members] if isinstance(members, list) else []
'''
main = replace_method(main, "_daily_eaten_victims", victims_and_members)

main = replace_once(
    main,
    '''        day = self.history.get("daily", {}).get(today.isoformat(), {})
        members = day.get("groups", {}).get(group_id, [])
''',
    '''        members = self._daily_group_members(group_id, today.isoformat())
''',
    "random roast SQL members",
)
main = replace_once(
    main,
    '''        day = self.history.get("daily", {}).get(self._today().isoformat(), {})
        members = day.get("groups", {}).get(group_id, [])
''',
    '''        members = self._daily_group_members(group_id, self._today().isoformat())
''',
    "random eat SQL members",
)
main = replace_once(
    main,
    '''        day = self.history.get("daily", {}).get(today, {})
        members = day.get("groups", {}).get(group_id, [])
        victims = self._daily_eaten_victims(group_id, today)
''',
    '''        members = self._daily_group_members(group_id, today)
        victims = self._daily_eaten_victims(group_id, today)
''',
    "daily report SQL members",
)

# Register and expose projection rebuild.
registration_anchor = '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/storage/export",
            self.page_storage_export,
            ["POST"],
            "导出今日小猪 JSON 备份",
        )
'''
main = replace_once(
    main,
    registration_anchor,
    '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/storage/rebuild",
            self.page_storage_rebuild,
            ["POST"],
            "重建今日小猪 SQLite 投影索引",
        )
''' + registration_anchor,
    "storage rebuild registration",
)

rebuild_endpoint = '''    async def page_storage_rebuild(self):
        """管理面板：由兼容文档事务性重建全部 SQL 投影。"""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not bool(payload.get("confirm")):
                return self._jsonify({"status": "error", "message": "需要明确确认重建"})
            async with self._storage_admin_lock:
                data = await asyncio.to_thread(self.storage_manager.rebuild_projections)
                self.storage = self.storage_manager.backend
            logger.warning("SQLite 投影已从兼容文档完整重建")
            return self._jsonify({"status": "ok", "data": data})
        except StorageMigrationError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.exception("重建 SQLite 投影失败")
            return self._jsonify({"status": "error", "message": f"重建失败：{exc}"})

'''
main = replace_once(
    main,
    '    async def page_storage_export(self):\n',
    rebuild_endpoint + '    async def page_storage_export(self):\n',
    "storage rebuild endpoint",
)
write("main.py", main)

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
page = read("pages/pig-manager/index.html")
page = replace_once(
    page,
    '<div class="update-actions"><button class="btn ghost" id="storageVerifyBtn">验证</button><button class="btn ghost" id="storageExportBtn">导出 JSON</button><button class="btn" id="storageMigrateBtn">迁移 SQLite</button><button class="btn danger" id="storageRollbackBtn" disabled>回滚 JSON</button></div>',
    '<div class="update-actions"><button class="btn ghost" id="storageVerifyBtn">验证</button><button class="btn ghost" id="storageRebuildBtn">重建索引</button><button class="btn ghost" id="storageExportBtn">导出 JSON</button><button class="btn" id="storageMigrateBtn">迁移 SQLite</button><button class="btn danger" id="storageRollbackBtn" disabled>回滚 JSON</button></div>',
    "panel rebuild button",
)
page = replace_once(
    page,
    "$('storageVerifyBtn').disabled=!d.database_exists;",
    "$('storageVerifyBtn').disabled=!d.database_exists;$('storageRebuildBtn').disabled=!d.database_exists;",
    "panel rebuild disabled",
)
page = replace_once(
    page,
    'async function exportStorage(){',
    '''async function rebuildStorage(){if(!window.confirm('确定由 SQLite 内保存的兼容文档完整重建查询索引吗？该操作不会修改抽取结果，但期间会暂时锁定数据库写入。'))return;busy(true);setStorageFeedback('正在事务性清空并重建 SQL 投影…');try{const d=await post('storage/rebuild',{confirm:true});toast('SQLite 索引已重建');await loadStorageStatus()}catch(e){setStorageFeedback(`重建失败：${e.message}`);toast(e.message)}finally{busy(false)}}
async function exportStorage(){''',
    "panel rebuild function",
)
page = replace_once(
    page,
    "$('storageMigrateBtn').onclick=migrateStorage;$('storageVerifyBtn').onclick=verifyStorage;$('storageExportBtn').onclick=exportStorage;",
    "$('storageMigrateBtn').onclick=migrateStorage;$('storageVerifyBtn').onclick=verifyStorage;$('storageRebuildBtn').onclick=rebuildStorage;$('storageExportBtn').onclick=exportStorage;",
    "panel rebuild binding",
)
write("pages/pig-manager/index.html", page)

# ---------------------------------------------------------------------------
# Version/docs/CI
# ---------------------------------------------------------------------------
metadata = read("metadata.yaml").replace('version: "2.9.2"', 'version: "2.10.0"')
write("metadata.yaml", metadata)
updater = read("updater.py").replace("Safe-Updater/2.9.2", "Safe-Updater/2.10.0")
write("updater.py", updater)

changelog = read("CHANGELOG.md")
changelog = replace_once(
    changelog,
    "# 更新\n",
    '''# 更新
## v2.10.0 (2026-08-04)
### SQLite 查询路径与投影修复
- 新增 schema migration v2：身份补充 legacy/创建时间索引，群成员关系拆为 `daily_draw_groups`，避免继续查询 `group_ids_json`。
- SQLite 的用户图鉴、每日结果、群成员和被吃名单改为直接 SQL 查询；JSON 后端仍保留原有兼容读取。
- 修复 `transaction()` 只有 Python 锁而没有数据库事务的问题，现在使用独立连接与 `BEGIN IMMEDIATE`，异常必定回滚并关闭连接。
- 数据库验证新增文档与投影逐表计数对账；启动时可自动重建仅投影损坏的数据库，管理面板也新增手动“重建索引”。
- 抽取保底与烤／吃特殊形态规则移入 `services/`，继续缩小 `main.py` 的业务职责。
- 本版仍保留兼容文档作为写入权威层；直接 SQL 写入与 SQLite 默认启用留到 v3.0，避免在未完成增量事务前贸然切换。

''',
    "changelog",
)
write("CHANGELOG.md", changelog)

readme = read("README.md")
readme = replace_once(
    readme,
    "v2.9 的完整 JSON 文档仍是兼容权威层，`daily_draws`、`user_pigs`、`user_stats`、被吃事件、冷却、AI 文案和图鉴覆盖等表作为同事务投影；后续版本会逐步把高频查询迁移为直接 SQL。",
    "v2.10 起，SQLite 模式下的用户图鉴、每日结果、群成员与被吃名单已经直接查询索引表，并提供投影对账、自动修复和手动重建。兼容文档目前仍是写入权威层；v3.0 才会把每日抽取与吃群友改成增量 SQL 事务，并在验证完成后将 SQLite 设为默认。",
    "readme storage status",
)
write("README.md", readme)

ci = read(".github/workflows/ci.yml")
ci = ci.replace("updater.py storage", "updater.py storage services")
write(".github/workflows/ci.yml", ci)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
write(
    "tests/test_services.py",
    '''from services import DrawService, RoastService


class FakeRng:
    def __init__(self, choices, roll):
        self.choices = list(choices)
        self.roll = roll

    def choice(self, values):
        wanted = self.choices.pop(0)
        return next(value for value in values if value["id"] == wanted)

    def random(self):
        return self.roll


def test_draw_service_applies_duplicate_pity_without_storage_dependency():
    pigs = [{"id": "seen"}, {"id": "new"}]
    service = DrawService(enable_new_pig_pity=True, pity_step_percent=20)
    chosen = service.choose(
        pigs,
        {"duplicate_streak": 4, "pigs": {"seen": {}}},
        rng=FakeRng(["seen", "new"], 0.1),
    )
    assert chosen["id"] == "new"


def test_roast_service_keeps_actor_and_target_rules_separate():
    service = RoastService()
    pork = {"id": "mc_porkchop", "name": "猪排"}
    machine = {"id": "mechanical-pig", "name": "机械猪"}
    assert service.eat_actor_block_reason(pork).startswith("你今天是")
    assert service.eat_target_block_reason(pork) is None
    assert service.eat_target_block_reason(machine) is None
    assert "开袋即食成功" in service.eat_success_message(pork)
''',
)

sqlite_tests = read("tests/test_sqlite_storage.py")
sqlite_tests += '''


def test_schema_v2_migrates_identity_columns_and_group_index(tmp_path):
    database = tmp_path / "rollpig.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL);
            INSERT INTO schema_migrations VALUES (1, 1);
            CREATE TABLE identities(
                identity_key TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                identity_type TEXT NOT NULL,
                raw_id TEXT NOT NULL
            );
            CREATE TABLE daily_draws(
                draw_date TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES identities(identity_key),
                pig_id TEXT NOT NULL,
                original_pig_id TEXT NOT NULL DEFAULT '',
                group_ids_json TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(draw_date, user_id)
            );
            INSERT INTO identities VALUES ('v2|qq|user|1', 'qq', 'user', '1');
            INSERT INTO daily_draws VALUES ('2026-08-04', 'v2|qq|user|1', 'pig', '', '[\"g1\"]');
            """
        )
    storage = SQLiteStorage(database, tmp_path, StorageManager.MANAGED_PATHS)
    with storage._connection() as connection:
        identity_columns = {row[1] for row in connection.execute("PRAGMA table_info(identities)")}
        draw_columns = {row[1] for row in connection.execute("PRAGMA table_info(daily_draws)")}
        groups = connection.execute("SELECT group_id FROM daily_draw_groups").fetchall()
        version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
    assert {"legacy_id", "created_at"} <= identity_columns
    assert {"created_at", "was_new_unlock"} <= draw_columns
    assert [row[0] for row in groups] == ["g1"]
    assert version == 2


def test_real_transaction_commits_and_rolls_back(tmp_path):
    storage = SQLiteStorage(tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS)
    with storage.transaction() as connection:
        storage._remember_identity(connection, "v2|qq|user|ok")
    with storage._connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM identities WHERE identity_key = 'v2|qq|user|ok'"
        ).fetchone()[0] == 1
    with pytest.raises(RuntimeError):
        with storage.transaction() as connection:
            storage._remember_identity(connection, "v2|qq|user|rollback")
            raise RuntimeError("abort")
    with storage._connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM identities WHERE identity_key = 'v2|qq|user|rollback'"
        ).fetchone()[0] == 0


def test_indexed_domain_reads_and_projection_rebuild(tmp_path):
    values = _documents(tmp_path)
    storage = SQLiteStorage(tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS)
    storage.save_json_batch({tmp_path / key: value for key, value in values.items()})
    collection = storage.get_user_collection(("v2|qq|user|10001",))
    draw = storage.get_daily_draw("2026-08-02", ("v2|qq|user|10001",))
    members = storage.get_group_members("2026-08-02", "v2|qq|group|20001")
    victims = storage.get_eaten_victims("2026-08-02", "v2|qq|group|20001")
    assert collection["pigs"]["pink-pig"]["count"] == 2
    assert draw["original_pig_id"] == "pink-pig"
    assert members == ["v2|qq|user|10001"]
    assert victims == ["v2|qq|user|10001"]

    with storage._connection() as connection:
        connection.execute("DELETE FROM user_pigs")
    broken = storage.verify()
    assert broken["ok"] is False
    assert "user_pigs" in broken["projection_mismatches"]
    rebuilt = storage.rebuild_projections()
    assert rebuilt["ok"] is True
    assert storage.verify()["projection_ok"] is True


def test_sql_collection_query_is_not_linear_in_all_users(tmp_path):
    users = {
        f"v2|qq|user|{index}": {
            "total_draws": 1,
            "active_days": 1,
            "duplicate_streak": 0,
            "pigs": {"pig": {"first_unlocked": "2026-01-01", "last_drawn": "2026-01-01", "count": 1}},
        }
        for index in range(25_000)
    }
    history = {"version": 1, "users": users, "daily": {}, "pig_snapshots": {}}
    storage = SQLiteStorage(tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS)
    storage.save_json(tmp_path / "pig_history.json", history)
    started = time.monotonic()
    result = storage.get_user_collection(("v2|qq|user|24999",))
    elapsed = time.monotonic() - started
    assert result["total_draws"] == 1
    assert elapsed < 2
'''
write("tests/test_sqlite_storage.py", sqlite_tests)

source_tests = read("tests/test_source_regressions.py")
source_tests += '''


def test_main_uses_services_and_indexed_sql_read_boundaries():
    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""
    choose = ast.get_source_segment(SOURCE, _method("_choose_daily_pig")) or ""
    collection = ast.get_source_segment(SOURCE, _method("_get_user_collection")) or ""
    daily = ast.get_source_segment(SOURCE, _method("_get_daily_pig")) or ""
    members = ast.get_source_segment(SOURCE, _method("_daily_group_members")) or ""
    victims = ast.get_source_segment(SOURCE, _method("_daily_eaten_victims")) or ""
    assert "self.draw_service = DrawService" in init
    assert "self.roast_service = RoastService" in init
    assert "self.draw_service.choose" in choose
    assert "self.storage.get_user_collection" in collection
    assert "self.storage.get_daily_draw" in daily
    assert "self.storage.get_group_members" in members
    assert "self.storage.get_eaten_victims" in victims


def test_storage_rebuild_api_keeps_csrf_and_confirmation():
    method = ast.get_source_segment(SOURCE, _method("page_storage_rebuild")) or ""
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    assert "_is_authorized_write_request" in method
    assert 'payload.get("confirm")' in method
    assert "storage/rebuild" in page
    assert "storageRebuildBtn" in page
'''
write("tests/test_source_regressions.py", source_tests)

print("v2.10.0 patch applied")
