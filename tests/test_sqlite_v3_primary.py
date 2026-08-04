from __future__ import annotations

import multiprocessing
import sqlite3
from pathlib import Path

import pytest

from storage import (
    JSONStorage,
    SQLitePrimaryStorage,
    SQLiteStorage,
    StorageManager,
)


def _managed() -> set[str]:
    return set(StorageManager.RUNTIME_MANAGED_PATHS)


def _worker_draw(root: str, output) -> None:
    storage = SQLitePrimaryStorage(
        Path(root) / "rollpig.db",
        Path(root),
        _managed(),
    )
    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|42",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    output.put(result["status"])


def test_v3_empty_auto_install_creates_sqlite(tmp_path):
    manager = StorageManager(tmp_path, mode="auto")
    assert isinstance(manager.backend, SQLitePrimaryStorage)
    verification = manager.verify()
    assert verification["ok"] is True
    assert verification["schema_version"] == 6
    assert verification["documents"] == 0
    health = manager.backend.health()
    assert health["runtime_authority"] == "normalized-sql"
    assert health["compatibility_mode"] == "on-demand"
    assert health["write_authority"] == "sql-primary-v3.0"


def test_v3_hot_domain_writes_never_persist_compatibility_documents(tmp_path):
    storage = StorageManager(tmp_path, mode="auto").backend
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
        cutoff_date="2026-07-28",
    )
    storage.remember_identity_alias(
        namespace="telegram@bot",
        canonical_id="v2|telegram@bot|user|1",
        username="PigOne",
    )
    storage.store_ai_roast_copy(
        pig_id="pig-a",
        generated_date="2026-08-04",
        content="只在 SQL",
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    storage.upsert_catalog_override(record={"id": "local", "name": "Local"})
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    exported = storage.export_documents()
    assert exported["pig_history.json"]["daily"]["2026-08-04"]["records"][
        "v2|qq|user|1"
    ] == "pig-a"
    assert exported["ai_roast_copies.json"]["copies"]["pig-a"][
        "2026-08-04"
    ] == "只在 SQL"
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0


def test_v3_rejects_full_runtime_snapshot_writes(tmp_path):
    storage = StorageManager(tmp_path, mode="auto").backend
    with pytest.raises(RuntimeError, match="禁止整份 JSON 写回"):
        storage.save_json(tmp_path / "pig_history.json", {"version": 1})
    assert storage.verify()["documents"] == 0


def test_v3_failed_domain_transaction_rolls_back_all_normalized_rows(
    tmp_path, monkeypatch
):
    storage = StorageManager(tmp_path, mode="auto").backend

    def fail_before_commit(connection):
        raise RuntimeError("simulated crash before commit")

    monkeypatch.setattr(storage, "_mark_primary_write_tx", fail_before_commit)
    with pytest.raises(RuntimeError, match="simulated crash"):
        storage.create_daily_draw(
            draw_date="2026-08-04",
            user_id="v2|qq|user|1",
            pig={"id": "pig-a", "name": "A"},
        )
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM user_pigs").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM user_stats").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0


def test_v3_daily_draw_is_unique_across_processes(tmp_path):
    StorageManager(tmp_path, mode="auto")
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    processes = [
        context.Process(target=_worker_draw, args=(str(tmp_path), output))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    statuses = [output.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    assert sorted(statuses) == ["created", "existing"]
    connection = sqlite3.connect(tmp_path / "rollpig.db")
    try:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM user_pigs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
    finally:
        connection.close()


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
