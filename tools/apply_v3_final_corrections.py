from __future__ import annotations

import re
import textwrap
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing replacement in {path}: {old[:120]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_primary_manager() -> None:
    replace_once(
        "storage/primary_manager.py",
        "str(key): self._clone(value) for key, value in documents.items()",
        "str(key): SQLitePrimaryStorage._clone(value) "
        "for key, value in documents.items()",
    )


def patch_primary_storage() -> None:
    path = Path("storage/sqlite_primary.py")
    text = path.read_text(encoding="utf-8")

    strict_checks = '''            "stats_total_draw_mismatches": (
                "SELECT COUNT(*) FROM user_stats WHERE total_draws != COALESCE(("
                "SELECT SUM(user_pigs.draw_count) FROM user_pigs "
                "WHERE user_pigs.user_id = user_stats.user_id), 0)"
            ),
            "stats_active_day_mismatches": (
                "SELECT COUNT(*) FROM user_stats WHERE active_days != ("
                "SELECT COUNT(*) FROM daily_draws "
                "WHERE daily_draws.user_id = user_stats.user_id)"
            ),
'''
    if strict_checks not in text:
        raise SystemExit("strict aggregate checks not found")
    text = text.replace(strict_checks, "", 1)

    destructive_rebuild = '''            user_ids = [
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
    missing_only_rebuild = '''            user_ids = [
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
    if destructive_rebuild not in text:
        raise SystemExit("destructive aggregate rebuild block not found")
    path.write_text(
        text.replace(destructive_rebuild, missing_only_rebuild, 1),
        encoding="utf-8",
    )


def replace_test(text: str, name: str, body: str) -> str:
    pattern = rf"def {re.escape(name)}\(.*?(?=\n\ndef test_|\Z)"
    replacement = textwrap.dedent(body).strip()
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"test not found: {name}")
    return updated


def patch_tests() -> None:
    path = Path("tests/test_sqlite_v3_primary.py")
    text = path.read_text(encoding="utf-8")
    text = replace_test(
        text,
        "test_v3_refuses_promotion_when_normalized_tables_are_inconsistent",
        '''
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
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES "
                    "('write_authority', 'sql-primary-v2.15') "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                )

            manager = StorageManager(tmp_path, mode="auto")
            assert manager.backend.backend_name == "json"
            assert "inconsistent normalized tables" in manager._last_error
            connection = sqlite3.connect(tmp_path / "rollpig.db")
            try:
                assert connection.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                ).fetchone()[0] == 5
                assert connection.execute(
                    "SELECT COUNT(*) FROM documents"
                ).fetchone()[0] == 1
                assert connection.execute(
                    "SELECT COUNT(*) FROM user_pigs"
                ).fetchone()[0] == 1
            finally:
                connection.close()
        ''',
    )
    text = replace_test(
        text,
        "test_v3_verify_and_rebuild_reconcile_user_stat_totals",
        '''
        def test_v3_rebuild_restores_missing_user_stats(tmp_path):
            storage = StorageManager(tmp_path, mode="auto").backend
            storage.create_daily_draw(
                draw_date="2026-08-04",
                user_id="v2|qq|user|1",
                pig={"id": "pig-a", "name": "A"},
            )
            with storage.transaction() as connection:
                connection.execute(
                    "DELETE FROM user_stats WHERE user_id = 'v2|qq|user|1'"
                )
            verification = storage.verify()
            assert verification["ok"] is False
            assert "missing_user_stats" in verification["projection_mismatches"]

            repaired = storage.rebuild_projections(reason="test-missing-stats")
            assert repaired["ok"] is True
            assert storage.verify()["ok"] is True
            collection = storage.get_user_collection(("v2|qq|user|1",))
            assert collection["total_draws"] == 1
            assert collection["active_days"] == 1
        ''',
    )
    path.write_text(text.rstrip() + "\n", encoding="utf-8")

    contract = Path("tests/test_v215_release_contract.py")
    contract_text = contract.read_text(encoding="utf-8")
    contract_text = contract_text.replace(
        'assert \'version: "2.15.0"\' in metadata',
        'assert \'version: "3.0.0"\' in metadata',
        1,
    ).replace(
        "assert 'AstrBot-RollPig/2.15.0' in main",
        "assert 'AstrBot-RollPig/3.0.0' in main",
        1,
    )
    contract.write_text(contract_text, encoding="utf-8")


if __name__ == "__main__":
    patch_primary_manager()
    patch_primary_storage()
    patch_tests()
