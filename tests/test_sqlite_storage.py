from __future__ import annotations

import json
import sqlite3
import time
import zipfile
from pathlib import Path

import pytest

from storage import JSONStorage, SQLiteStorage, StorageManager, StorageMigrationError


def _documents(root: Path) -> dict[str, object]:
    history = {
        "version": 1,
        "users": {
            "v2|qq|user|10001": {
                "total_draws": 2,
                "active_days": 2,
                "duplicate_streak": 1,
                "pigs": {
                    "pink-pig": {
                        "first_unlocked": "2026-08-01",
                        "last_drawn": "2026-08-02",
                        "count": 2,
                    }
                },
            }
        },
        "daily": {
            "2026-08-02": {
                "draws": 1,
                "new_unlocks": 0,
                "users": ["v2|qq|user|10001"],
                "records": {"v2|qq|user|10001": "eaten"},
                "eaten_originals": {"v2|qq|user|10001": "pink-pig"},
                "groups": {"v2|qq|group|20001": ["v2|qq|user|10001"]},
            }
        },
        "pig_snapshots": {
            "pink-pig": {
                "id": "pink-pig",
                "name": "粉红猪",
                "description": "粉粉嫩嫩",
                "analysis": "测试快照",
            }
        },
        "identity_aliases": {},
    }
    roast = {
        "version": 1,
        "cooldowns": {
            "v2|qq|group|20001:v2|qq|user|10001": 123.5,
        },
        "daily_backdoors": {"2026-08-02:v2|qq|user|10001": True},
        "daily_roast_counts": {
            json.dumps(
                ["2026-08-02", "v2|qq|group|20001", "v2|qq|user|10001"],
                ensure_ascii=False,
            ): 3
        },
        "eaten_penalties": {
            "v2|qq|user|10001": {"due_date": "2026-08-03", "failed": False}
        },
        "eaten_events": {
            json.dumps(
                ["2026-08-02", "v2|qq|group|20001", "v2|qq|user|10001"],
                ensure_ascii=False,
            ): {
                "actor_id": "v2|qq|user|10002",
                "outcome": "eat_success",
                "at": 1785720000,
            }
        },
    }
    values: dict[str, object] = {
        "rollpig_today.json": {
            "date": "2026-08-02",
            "records": {
                "v2|qq|user|10001": {
                    "id": "eaten",
                    "name": "吃掉了",
                    "description": "你来晚了",
                    "analysis": "盘子空空如也",
                }
            },
        },
        "pig_history.json": history,
        "roast_state.json": roast,
        "ai_roast_copies.json": {
            "version": 1,
            "copies": {"pink-pig": {"2026-08-02": "今天也很适合上桌。"}},
        },
        "pig_catalog.json": [],
        "local_overrides.json": [
            {
                "id": "local-pig",
                "name": "本地猪",
                "description": "本地限定",
                "analysis": "不会被云端覆盖。",
            }
        ],
        "deleted_pigs.json": ["old-pig"],
    }
    for relative, value in values.items():
        (root / relative).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return values


def test_sqlite_storage_projects_real_v28_shapes(tmp_path):
    values = _documents(tmp_path)
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    storage.save_json_batch(
        {tmp_path / relative: value for relative, value in values.items()}
    )
    health = storage.health()
    assert health["ok"] is True
    assert health["documents"] == len(values)
    assert health["users"] == 1
    assert health["daily_draws"] == 1

    with storage._connect() as connection:
        draw = connection.execute(
            "SELECT pig_id, original_pig_id, group_ids_json FROM daily_draws"
        ).fetchone()
        penalty = connection.execute(
            "SELECT due_date, failed FROM eaten_penalties"
        ).fetchone()
        roast_count = connection.execute(
            "SELECT roast_count FROM daily_roast_counts"
        ).fetchone()
        copy = connection.execute(
            "SELECT content FROM ai_roast_copies"
        ).fetchone()
    assert draw["pig_id"] == "eaten"
    assert draw["original_pig_id"] == "pink-pig"
    assert "v2|qq|group|20001" in draw["group_ids_json"]
    assert tuple(penalty) == ("2026-08-03", 0)
    assert roast_count["roast_count"] == 3
    assert copy["content"] == "今天也很适合上桌。"


def test_manager_migration_is_idempotent_and_auto_selects_sqlite(tmp_path):
    values = _documents(tmp_path)
    manager = StorageManager(tmp_path, mode="auto")
    assert manager.backend.backend_name == "json"
    first = manager.migrate_to_sqlite()
    assert first["status"] == "migrated"
    assert first["documents"] == len(values)
    assert manager.backend.backend_name == "sqlite"
    second = manager.migrate_to_sqlite()
    assert second["status"] == "already-sqlite"

    restarted = StorageManager(tmp_path, mode="auto")
    assert restarted.backend.backend_name == "sqlite"
    assert restarted.verify()["ok"] is True
    assert restarted.backend.load_json(tmp_path / "pig_history.json", {}) == values[
        "pig_history.json"
    ]


def test_migration_rejects_malformed_json_without_switching(tmp_path):
    _documents(tmp_path)
    (tmp_path / "pig_history.json").write_text("{broken", encoding="utf-8")
    manager = StorageManager(tmp_path, mode="auto")
    with pytest.raises(StorageMigrationError, match="pig_history.json"):
        manager.migrate_to_sqlite()
    assert manager.backend.backend_name == "json"
    assert not (tmp_path / "rollpig.db").exists()
    assert (tmp_path / "pig_history.json").read_text(encoding="utf-8") == "{broken"


def test_migration_failure_keeps_json_and_removes_temporary_database(
    tmp_path, monkeypatch
):
    _documents(tmp_path)
    manager = StorageManager(tmp_path, mode="auto")
    real_replace = __import__("os").replace

    def fail_database_replace(source, target):
        if Path(target).name == "rollpig.db":
            raise OSError("simulated final replace failure")
        return real_replace(source, target)

    monkeypatch.setattr("storage.manager.os.replace", fail_database_replace)
    with pytest.raises(StorageMigrationError, match="simulated"):
        manager.migrate_to_sqlite()
    assert manager.backend.backend_name == "json"
    assert not (tmp_path / "rollpig.db").exists()
    assert not list(tmp_path.glob(".rollpig.db.migrating-*.tmp"))
    assert json.loads((tmp_path / "pig_history.json").read_text(encoding="utf-8"))[
        "users"
    ]


def test_export_and_rollback_preserve_latest_sqlite_documents(tmp_path):
    _documents(tmp_path)
    manager = StorageManager(tmp_path, mode="auto")
    manager.migrate_to_sqlite()
    changed = manager.backend.load_json(tmp_path / "pig_history.json", {})
    changed["users"]["v2|qq|user|10001"]["total_draws"] = 9
    manager.backend.save_json(tmp_path / "pig_history.json", changed)

    exported = manager.export_json_backup()
    archive = tmp_path / "storage_exports" / exported["filename"]
    assert archive.exists()
    with zipfile.ZipFile(archive) as bundle:
        archived_history = json.loads(bundle.read("pig_history.json"))
        assert archived_history["users"]["v2|qq|user|10001"]["total_draws"] == 9
        assert "manifest.json" in bundle.namelist()

    result = manager.rollback_to_json()
    assert result["status"] == "rolled-back"
    assert manager.backend.backend_name == "json"
    restored = json.loads((tmp_path / "pig_history.json").read_text(encoding="utf-8"))
    assert restored["users"]["v2|qq|user|10001"]["total_draws"] == 9
    assert not (tmp_path / "rollpig.db").exists()
    assert list(tmp_path.glob("rollpig.db.disabled-*"))


def test_json_mode_never_activates_existing_sqlite(tmp_path):
    _documents(tmp_path)
    auto = StorageManager(tmp_path, mode="auto")
    auto.migrate_to_sqlite()
    forced_json = StorageManager(tmp_path, mode="json")
    assert forced_json.backend.backend_name == "json"


def test_projection_smoke_for_one_hundred_thousand_users(tmp_path):
    users = {
        f"v2|qq|user|{index}": {
            "total_draws": 1,
            "active_days": 1,
            "duplicate_streak": 0,
            "pigs": {},
        }
        for index in range(100_000)
    }
    history = {
        "version": 1,
        "users": users,
        "daily": {},
        "pig_snapshots": {},
    }
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    started = time.monotonic()
    storage.save_json(tmp_path / "pig_history.json", history)
    elapsed = time.monotonic() - started
    assert storage.health()["users"] == 100_000
    assert elapsed < 45


def test_unmanaged_cache_files_stay_on_json_fallback(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
        fallback=JSONStorage(),
    )
    cache = tmp_path / "pighub_images.json"
    storage.save_json(cache, {"images": [1]})
    assert json.loads(cache.read_text(encoding="utf-8")) == {"images": [1]}
    assert "pighub_images.json" not in storage.export_documents()



def test_connection_context_rolls_back_and_closes(tmp_path, monkeypatch):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    connection = storage._connect()
    with monkeypatch.context() as scoped:
        scoped.setattr(storage, "_connect", lambda: connection)
        with pytest.raises(RuntimeError, match="abort"):
            with storage._connection() as active:
                active.execute("BEGIN IMMEDIATE")
                active.execute(
                    "INSERT INTO documents(key, payload, payload_sha256, updated_at) "
                    "VALUES ('partial.json', '{}', 'x', 1)"
                )
                raise RuntimeError("abort")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    with storage._connection() as active:
        assert active.execute(
            "SELECT COUNT(*) FROM documents WHERE key = 'partial.json'"
        ).fetchone()[0] == 0


def test_forced_json_mode_rejects_server_side_migration(tmp_path):
    _documents(tmp_path)
    manager = StorageManager(tmp_path, mode="json")
    with pytest.raises(StorageMigrationError, match="强制使用 JSON"):
        manager.migrate_to_sqlite()
    assert manager.backend.backend_name == "json"
    assert not (tmp_path / "rollpig.db").exists()


def test_mixed_sqlite_and_fallback_batch_is_rejected_atomically(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    history = tmp_path / "pig_history.json"
    cache = tmp_path / "pighub_images.json"
    with pytest.raises(ValueError, match="不能混合"):
        storage.save_json_batch({history: {"users": {}}, cache: {"images": []}})
    assert "pig_history.json" not in storage.export_documents()
    assert not cache.exists()



def test_projection_tables_enforce_identity_foreign_keys(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    expected = {
        "daily_draws",
        "user_pigs",
        "user_stats",
        "eaten_penalties",
        "eaten_events",
        "roast_cooldowns",
        "daily_roast_counts",
        "daily_backdoors",
    }
    with storage._connection() as connection:
        constrained = {
            table
            for table in expected
            if any(
                row[2] == "identities"
                for row in connection.execute(
                    f"PRAGMA foreign_key_list({table})"
                ).fetchall()
            )
        }
        assert constrained == expected
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO user_stats("
                "user_id, total_draws, active_days, duplicate_streak, payload_json"
                ") VALUES ('missing-identity', 0, 0, 0, '{}')"
            )
