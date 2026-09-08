from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from storage import SQLitePrimaryStorage, StorageManager, StorageMigrationError


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


@pytest.mark.parametrize("legacy_json", [False, True])
def test_rejected_database_never_activates_old_or_empty_json(tmp_path, legacy_json):
    broken = b"not-a-sqlite-database"
    (tmp_path / "rollpig.db").write_bytes(broken)
    (tmp_path / "rollpig.db-wal").write_bytes(b"rejected-wal")
    (tmp_path / "rollpig.db-shm").write_bytes(b"rejected-shm")
    if legacy_json:
        _write_minimal_json_history(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}

    with pytest.raises(StorageMigrationError, match="SQLite 需要恢复"):
        StorageManager(tmp_path, mode="auto")

    assert (tmp_path / "rollpig.db").read_bytes() == broken
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*.json")} == before
    assert not list(tmp_path.glob("rollpig.db.rejected-*"))
    # Original sidecars may be touched by SQLite during open. Preflight copies
    # remain available even though no manager or plugin instance is returned.
    assert any(p.read_bytes() == b"rejected-wal" for p in tmp_path.glob(".rollpig.db.preflight-*-wal"))
    assert any(p.read_bytes() == b"rejected-shm" for p in tmp_path.glob(".rollpig.db.preflight-*-shm"))


@pytest.mark.parametrize("mode", ["auto", "sqlite", "json"])
def test_sql_authority_marker_blocks_missing_database_bootstrap(tmp_path, mode):
    _write_minimal_json_history(tmp_path)
    marker = tmp_path / "storage_state.json"
    marker.write_text('{"active_backend": "sqlite"}', encoding="utf-8")
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}

    with pytest.raises(StorageMigrationError, match="SQLite 需要恢复"):
        StorageManager(tmp_path, mode=mode)

    assert not (tmp_path / "rollpig.db").exists()
    assert {p.name: p.read_bytes() for p in tmp_path.glob("*.json")} == before


@pytest.mark.parametrize("suffix", ["-wal", "-shm"])
def test_orphan_sidecar_is_not_a_fresh_installation(tmp_path, suffix):
    sidecar = tmp_path / f"rollpig.db{suffix}"
    sidecar.write_bytes(b"unreconciled")
    with pytest.raises(StorageMigrationError, match="SQLite 需要恢复"):
        StorageManager(tmp_path, mode="auto")
    assert not (tmp_path / "rollpig.db").exists()
    assert sidecar.read_bytes() == b"unreconciled"
    assert not list(tmp_path.glob("*.json"))


@pytest.mark.parametrize("content", ["not-json", "[]", "{}"])
def test_unverifiable_authority_marker_is_preserved(tmp_path, content):
    marker = tmp_path / "storage_state.json"
    marker.write_text(content, encoding="utf-8")
    with pytest.raises(StorageMigrationError, match="SQLite 需要恢复"):
        StorageManager(tmp_path, mode="auto")
    assert marker.read_text(encoding="utf-8") == content
    assert not (tmp_path / "rollpig.db").exists()


def test_json_configuration_cannot_bypass_existing_sql_authority(tmp_path):
    manager = StorageManager(tmp_path, mode="auto")
    manager.backend.create_daily_draw(
        draw_date="2026-08-04", user_id="user-1", pig={"id": "pig-a", "name": "A"}
    )
    with pytest.raises(StorageMigrationError, match="SQLite 需要恢复"):
        StorageManager(tmp_path, mode="json")
    assert not (tmp_path / "pig_history.json").exists()
    assert StorageManager(tmp_path, mode="auto").backend.get_user_collection(("user-1",))["total_draws"] == 1


def test_json_native_installation_still_works(tmp_path):
    _write_minimal_json_history(tmp_path)
    manager = StorageManager(tmp_path, mode="json")
    assert manager.backend.backend_name == "json"
    assert not (tmp_path / "rollpig.db").exists()


def test_uncommitted_first_migration_failure_retains_original_json(tmp_path, monkeypatch):
    _write_minimal_json_history(tmp_path)
    history = tmp_path / "pig_history.json"
    before = history.read_bytes()

    def fail_new_sqlite(self, path=None):
        raise OSError("simulated storage unavailable before promotion")

    monkeypatch.setattr(StorageManager, "_new_sqlite", fail_new_sqlite)
    manager = StorageManager(tmp_path, mode="auto")
    assert manager.backend.backend_name == "json"
    assert history.read_bytes() == before
    assert not (tmp_path / "rollpig.db").exists()


def test_broken_legacy_json_is_not_overwritten_with_empty_defaults(tmp_path):
    history = tmp_path / "pig_history.json"
    history.write_bytes(b"broken-json")
    with pytest.raises(StorageMigrationError, match="迁移前无法读取"):
        StorageManager(tmp_path, mode="auto")
    assert history.read_bytes() == b"broken-json"
    assert not (tmp_path / "rollpig.db").exists()


def test_retry_migration_cannot_replace_a_failed_live_sqlite(tmp_path, monkeypatch):
    manager = StorageManager(tmp_path, mode="auto")
    _write_minimal_json_history(tmp_path)
    original_backend = manager.backend
    monkeypatch.setattr(original_backend, "verify", lambda: {"ok": False})
    with pytest.raises(StorageMigrationError, match="SQLite 需要恢复"):
        manager.migrate_to_sqlite()
    assert manager.backend is original_backend
    assert not list(tmp_path.glob("rollpig.db.rejected-*"))


def test_repaired_database_can_load_again(tmp_path):
    manager = StorageManager(tmp_path, mode="auto")
    manager.backend.create_daily_draw(
        draw_date="2026-08-04", user_id="user-1", pig={"id": "pig-a", "name": "A"}
    )
    manager.backend.checkpoint()
    database = tmp_path / "rollpig.db"
    healthy = database.read_bytes()
    database.write_bytes(b"broken")
    with pytest.raises(StorageMigrationError, match="SQLite 需要恢复"):
        StorageManager(tmp_path, mode="auto")
    database.write_bytes(healthy)
    recovered = StorageManager(tmp_path, mode="auto")
    assert isinstance(recovered.backend, SQLitePrimaryStorage)
    assert recovered.backend.get_user_collection(("user-1",))["total_draws"] == 1


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

    # Completed, reconciled rollback is still a legitimate JSON authority.
    restarted = StorageManager(tmp_path, mode="json")
    assert restarted.backend.backend_name == "json"
    history = restarted.backend.load_json(tmp_path / "pig_history.json", {})
    assert history["daily"]["2026-08-04"]["records"]["v2|qq|user|9"] == "pig-z"
