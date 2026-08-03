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
            INSERT INTO daily_draws VALUES ('2026-08-04', 'v2|qq|user|1', 'pig', '', '["g1"]');
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


def test_projection_verification_ignores_unprojectable_legacy_garbage(tmp_path):
    values = _documents(tmp_path)
    roast = values["roast_state.json"]
    roast["daily_roast_counts"]["broken"] = 1
    roast["eaten_events"]["broken"] = {"actor_id": "x"}
    roast["daily_backdoors"]["broken"] = True
    values["ai_roast_copies.json"]["copies"]["pink-pig"]["bad"] = ""
    values["local_overrides.json"].append({})
    values["deleted_pigs.json"].append("")
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.save_json_batch(
        {tmp_path / key: value for key, value in values.items()}
    )
    assert storage.verify()["projection_ok"] is True


def test_dashboard_health_avoids_deep_document_projection_scan(
    tmp_path, monkeypatch
):
    values = _documents(tmp_path)
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.save_json_batch(
        {tmp_path / key: value for key, value in values.items()}
    )
    monkeypatch.setattr(
        storage,
        "_projection_health",
        lambda connection: (_ for _ in ()).throw(AssertionError("deep scan")),
    )
    health = storage.health()
    assert health["ok"] is True
    assert health["deep_verified"] is False



def _empty_sql_documents(tmp_path: Path) -> tuple[SQLiteStorage, dict[str, object]]:
    values: dict[str, object] = {
        "rollpig_today.json": {"date": "", "records": {}},
        "pig_history.json": {
            "version": 1,
            "users": {},
            "daily": {},
            "pig_snapshots": {},
        },
        "roast_state.json": {
            "version": 1,
            "cooldowns": {},
            "daily_backdoors": {},
            "daily_roast_counts": {},
            "eaten_penalties": {},
            "eaten_events": {},
        },
        "ai_roast_copies.json": {"version": 1, "copies": {}},
        "pig_catalog.json": [],
        "local_overrides.json": [],
        "deleted_pigs.json": [],
    }
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.save_json_batch(
        {tmp_path / name: value for name, value in values.items()}
    )
    return storage, values


def test_sql_primary_daily_draw_does_not_rebuild_history_projection(
    tmp_path, monkeypatch
):
    storage, _ = _empty_sql_documents(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("direct write must not rebuild history projection")

    monkeypatch.setattr(storage, "_project_history", forbidden)
    probe = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        user_candidates=("1",),
        pig=None,
        group_id="v2|qq|group|9",
        penalty_should_fail=False,
    )
    assert probe["status"] == "needs-pig"
    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        user_candidates=("1",),
        pig={"id": "pink-pig", "name": "粉红猪"},
        group_id="v2|qq|group|9",
        penalty_should_fail=False,
    )
    assert result["status"] == "created"
    assert storage.verify(deep=True)["projection_ok"] is True


def test_sql_primary_daily_draw_is_cross_connection_idempotent(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )

    def draw(storage, pig_id):
        return storage.create_daily_draw(
            draw_date="2026-08-04",
            user_id="v2|qq|user|1",
            user_candidates=("1",),
            pig={"id": pig_id, "name": pig_id},
            group_id="v2|qq|group|9",
            penalty_should_fail=False,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: draw(*args),
                ((first, "pig-a"), (second, "pig-b")),
            )
        )
    assert sorted(result["status"] for result in results) == ["created", "existing"]
    with first._connection() as connection:
        rows = connection.execute(
            "SELECT pig_id FROM daily_draws WHERE draw_date = '2026-08-04'"
        ).fetchall()
        stats = connection.execute(
            "SELECT total_draws FROM user_stats WHERE user_id = 'v2|qq|user|1'"
        ).fetchone()
    assert len(rows) == 1
    assert stats[0] == 1


def test_sql_primary_penalty_and_draw_share_transaction(tmp_path):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_penalties"] = {
        "v2|qq|user|1": {"due_date": "2026-08-04", "failed": False}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)
    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        penalty_should_fail=True,
    )
    assert result["status"] == "penalty-blocked"
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 0
        assert connection.execute(
            "SELECT failed FROM eaten_penalties WHERE user_id = 'v2|qq|user|1'"
        ).fetchone()[0] == 1


def test_sql_primary_eat_rolls_back_all_tables_and_documents(tmp_path, monkeypatch):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    original_writer = storage._write_document_tx

    def fail_on_roast(connection, key, value, **kwargs):
        if key == "roast_state.json":
            raise RuntimeError("fault injection")
        return original_writer(connection, key, value, **kwargs)

    monkeypatch.setattr(storage, "_write_document_tx", fail_on_roast)
    with pytest.raises(RuntimeError, match="fault injection"):
        storage.replace_daily_pig_with_eaten(
            draw_date="2026-08-04",
            due_date="2026-08-05",
            cutoff_date="2026-08-02",
            user_id="v2|qq|user|1",
            group_id="v2|qq|group|9",
            actor_id="v2|qq|user|2",
            outcome="eat_success",
            eaten_pig={"id": "eaten", "name": "吃掉了"},
        )
    with storage._connection() as connection:
        draw = connection.execute("SELECT pig_id FROM daily_draws").fetchone()[0]
        penalties = connection.execute("SELECT COUNT(*) FROM eaten_penalties").fetchone()[0]
        events = connection.execute("SELECT COUNT(*) FROM eaten_events").fetchone()[0]
    assert draw == "pig-a"
    assert penalties == 0
    assert events == 0
    docs = storage.export_documents()
    assert docs["pig_history.json"]["daily"]["2026-08-04"]["records"]["v2|qq|user|1"] == "pig-a"


def test_sql_primary_eat_updates_draw_penalty_event_and_export_docs(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    result = storage.replace_daily_pig_with_eaten(
        draw_date="2026-08-04",
        due_date="2026-08-05",
        cutoff_date="2026-08-02",
        user_id="v2|qq|user|1",
        group_id="v2|qq|group|9",
        actor_id="v2|qq|user|2",
        outcome="eat_success",
        eaten_pig={"id": "eaten", "name": "吃掉了"},
    )
    assert result["status"] == "updated"
    with storage._connection() as connection:
        draw = connection.execute(
            "SELECT pig_id, original_pig_id FROM daily_draws"
        ).fetchone()
        penalty = connection.execute(
            "SELECT due_date, failed FROM eaten_penalties"
        ).fetchone()
        event = connection.execute(
            "SELECT outcome, user_id FROM eaten_events"
        ).fetchone()
    assert tuple(draw) == ("eaten", "pig-a")
    assert tuple(penalty) == ("2026-08-05", 0)
    assert tuple(event) == ("eat_success", "v2|qq|user|1")
    assert storage.verify(deep=True)["projection_ok"] is True



def test_sql_primary_metadata_merges_do_not_rebuild_or_erase_draws(
    tmp_path, monkeypatch
):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    first.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|telegram@one|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|telegram@one|group|9",
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("metadata merge must not rebuild projections")

    monkeypatch.setattr(second, "_project_history", forbidden)
    claim = second.claim_legacy_identity(
        namespaced="v2|telegram@one|user|1",
        legacy="1",
        kind="users",
        accepted_claims=("v2|telegram@one|user|1", "v2|telegram|user|1", "1"),
    )
    alias = second.remember_identity_alias(
        namespace="telegram@one",
        canonical_id="v2|telegram@one|user|1",
        username="ExampleUser",
    )
    assert claim["storage_key"] == "1"
    assert alias["changed"] is True
    with first._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM user_stats").fetchone()[0] == 1
    history = first.export_documents()["pig_history.json"]
    assert history["identity_claims"]["users"]["1"] == "v2|telegram@one|user|1"
    assert history["identity_aliases"]["telegram@one"]["by_alias"]["exampleuser"] == "v2|telegram@one|user|1"


def test_sql_primary_legacy_claim_is_atomic_across_platforms(tmp_path):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    one = first.claim_legacy_identity(
        namespaced="v2|qq@one|user|1",
        legacy="1",
        kind="users",
        accepted_claims=("v2|qq@one|user|1", "1"),
    )
    two = second.claim_legacy_identity(
        namespaced="v2|discord@one|user|1",
        legacy="1",
        kind="users",
        accepted_claims=("v2|discord@one|user|1", "1"),
    )
    assert one["storage_key"] == "1"
    assert two["storage_key"] == "v2|discord@one|user|1"


def test_sql_primary_eat_drops_malformed_legacy_event_keys(tmp_path):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_events"] = {
        "not-json": {"actor_id": "broken", "outcome": "legacy", "at": 1}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    result = storage.replace_daily_pig_with_eaten(
        draw_date="2026-08-04",
        due_date="2026-08-05",
        cutoff_date="2026-08-02",
        user_id="v2|qq|user|1",
        group_id="v2|qq|group|9",
        actor_id="v2|qq|user|2",
        outcome="eat_success",
        eaten_pig={"id": "eaten", "name": "吃掉了"},
    )
    assert result["status"] == "updated"
    assert "not-json" not in storage.export_documents()["roast_state.json"]["eaten_events"]



def test_sql_primary_successful_penalty_is_not_consumed_by_probe(tmp_path):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_penalties"] = {
        "v2|qq|user|1": {"due_date": "2026-08-04", "failed": False}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)

    probe = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig=None,
        penalty_should_fail=False,
    )
    assert probe["status"] == "needs-pig"
    with storage._connection() as connection:
        penalty = connection.execute(
            "SELECT due_date, failed FROM eaten_penalties "
            "WHERE user_id = 'v2|qq|user|1'"
        ).fetchone()
        assert tuple(penalty) == ("2026-08-04", 0)

    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        penalty_should_fail=False,
    )
    assert result["status"] == "created"
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM eaten_penalties").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 1


def test_sql_primary_successful_penalty_rolls_back_with_failed_draw(
    tmp_path, monkeypatch
):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_penalties"] = {
        "v2|qq|user|1": {"due_date": "2026-08-04", "failed": False}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)
    original_writer = storage._write_document_tx

    def fail_on_history(connection, key, value, **kwargs):
        if key == "pig_history.json":
            raise RuntimeError("draw fault injection")
        return original_writer(connection, key, value, **kwargs)

    monkeypatch.setattr(storage, "_write_document_tx", fail_on_history)
    with pytest.raises(RuntimeError, match="draw fault injection"):
        storage.create_daily_draw(
            draw_date="2026-08-04",
            user_id="v2|qq|user|1",
            pig={"id": "pig-a", "name": "A"},
            penalty_should_fail=False,
        )
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 0
        penalty = connection.execute(
            "SELECT due_date, failed FROM eaten_penalties "
            "WHERE user_id = 'v2|qq|user|1'"
        ).fetchone()
        assert tuple(penalty) == ("2026-08-04", 0)
    documents = storage.export_documents()
    assert documents["roast_state.json"]["eaten_penalties"]["v2|qq|user|1"] == {
        "due_date": "2026-08-04",
        "failed": False,
    }
