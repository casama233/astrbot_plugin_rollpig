from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from storage import SQLitePrimaryStorage, StorageManager


def _write_minimal_json_history(root: Path) -> None:
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
    (root / "pig_history.json").write_text(
        json.dumps(history, ensure_ascii=False), encoding="utf-8"
    )


def test_manual_retry_preserves_rejected_database_before_replacement(tmp_path):
    broken = b"not-a-sqlite-database"
    (tmp_path / "rollpig.db").write_bytes(broken)
    (tmp_path / "rollpig.db-wal").write_bytes(b"rejected-wal")
    (tmp_path / "rollpig.db-shm").write_bytes(b"rejected-shm")
    _write_minimal_json_history(tmp_path)

    manager = StorageManager(tmp_path, mode="auto")
    assert manager.backend.backend_name == "json"
    result = manager.migrate_to_sqlite()

    assert result["status"] == "migrated"
    assert isinstance(manager.backend, SQLitePrimaryStorage)
    preserved_name = result["replaced_database"]
    assert preserved_name.startswith("rollpig.db.rejected-")
    assert (tmp_path / preserved_name).read_bytes() == broken
    assert Path(f"{tmp_path / preserved_name}-wal").read_bytes() == b"rejected-wal"
    assert Path(f"{tmp_path / preserved_name}-shm").read_bytes() == b"rejected-shm"
    assert manager.verify()["ok"] is True


def test_rollback_disabled_database_contains_latest_checkpointed_draw(tmp_path):
    manager = StorageManager(tmp_path, mode="auto")
    storage = manager.backend
    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|9",
        pig={"id": "pig-z", "name": "Z"},
        group_id="v2|qq|group|7",
    )
    assert result["created"] is True

    rollback = manager.rollback_to_json()
    disabled = tmp_path / rollback["disabled_database"]
    assert disabled.exists()

    connection = sqlite3.connect(disabled)
    try:
        row = connection.execute(
            "SELECT pig_id FROM daily_draws "
            "WHERE draw_date = ? AND user_id = ?",
            ("2026-08-04", "v2|qq|user|9"),
        ).fetchone()
        assert row == ("pig-z",)
    finally:
        connection.close()
