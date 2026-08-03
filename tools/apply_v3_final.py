from __future__ import annotations

import re
import textwrap
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing replacement in {path}: {old[:100]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_test(text: str, name: str, body: str) -> str:
    pattern = rf"def {re.escape(name)}\(.*?(?=\n\ndef test_|\Z)"
    replacement = textwrap.dedent(body).strip()
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"could not replace test {name}")
    return updated


def patch_manager() -> None:
    path = Path("storage/primary_manager.py")
    text = path.read_text(encoding="utf-8")
    old = '''    MANAGED_PATHS = {
        "rollpig_today.json",
        "pig_history.json",
        "roast_state.json",
        "ai_roast_copies.json",
        "local_overrides.json",
        "deleted_pigs.json",
    }
    LEGACY_IMPORT_PATHS = MANAGED_PATHS | {"pig_catalog.json"}
'''
    new = '''    # Preserve the public v2 path set for integrations that instantiate the
    # legacy SQLiteStorage directly. v3 itself stores only runtime authority
    # documents; the cloud catalog remains an ordinary replaceable JSON cache.
    MANAGED_PATHS = {
        "rollpig_today.json",
        "pig_history.json",
        "roast_state.json",
        "ai_roast_copies.json",
        "pig_catalog.json",
        "local_overrides.json",
        "deleted_pigs.json",
    }
    RUNTIME_MANAGED_PATHS = MANAGED_PATHS - {"pig_catalog.json"}
    LEGACY_IMPORT_PATHS = MANAGED_PATHS
'''
    if old not in text:
        raise SystemExit("primary manager path constants already changed or missing")
    text = text.replace(old, new, 1)
    text = text.replace(
        "            self.MANAGED_PATHS,\n            fallback=self.json_storage,",
        "            self.RUNTIME_MANAGED_PATHS,\n            fallback=self.json_storage,",
        1,
    )
    text = text.replace(
        '''        status["compatibility_exports_on_demand"] = isinstance(
            self.backend, SQLitePrimaryStorage
        )
        return status
''',
        '''        status["compatibility_exports_on_demand"] = isinstance(
            self.backend, SQLitePrimaryStorage
        )
        status["managed_documents"] = sorted(self.RUNTIME_MANAGED_PATHS)
        status["json_cache_documents"] = ["pig_catalog.json"]
        return status
''',
        1,
    )
    path.write_text(text, encoding="utf-8")


def patch_existing_tests() -> None:
    path = Path("tests/test_sqlite_storage.py")
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "from storage import JSONStorage, SQLiteStorage, StorageManager, StorageMigrationError",
        "from storage import (\n"
        "    JSONStorage,\n"
        "    SQLitePrimaryStorage,\n"
        "    SQLiteStorage,\n"
        "    StorageManager,\n"
        "    StorageMigrationError,\n"
        ")",
        1,
    )
    text = replace_test(
        text,
        "test_manager_migration_is_idempotent_and_auto_selects_sqlite",
        '''
        def test_manager_migration_is_idempotent_and_auto_selects_sqlite(tmp_path):
            values = _documents(tmp_path)
            manager = StorageManager(tmp_path, mode="auto")
            assert isinstance(manager.backend, SQLitePrimaryStorage)
            assert manager._last_action["status"] == "auto-migrated"
            assert manager._last_action["documents"] == len(values)
            assert manager.verify()["ok"] is True
            assert manager.verify()["schema_version"] == 6
            with manager.backend._connection() as connection:
                assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
            second = manager.migrate_to_sqlite()
            assert second["status"] == "already-sqlite"

            restarted = StorageManager(tmp_path, mode="auto")
            assert isinstance(restarted.backend, SQLitePrimaryStorage)
            history = restarted.backend.load_json(tmp_path / "pig_history.json", {})
            assert history["users"]["v2|qq|user|10001"]["total_draws"] == 2
            assert history["daily"]["2026-08-02"]["records"][
                "v2|qq|user|10001"
            ] == "eaten"
            assert list((tmp_path / "storage_backups").glob("*-json"))
        ''',
    )
    text = replace_test(
        text,
        "test_migration_failure_keeps_json_and_removes_temporary_database",
        '''
        def test_migration_failure_keeps_json_and_removes_temporary_database(
            tmp_path, monkeypatch
        ):
            _documents(tmp_path)
            real_replace = __import__("os").replace

            def fail_database_replace(source, target):
                if Path(target).name == "rollpig.db":
                    raise OSError("simulated final replace failure")
                return real_replace(source, target)

            monkeypatch.setattr("storage.manager.os.replace", fail_database_replace)
            manager = StorageManager(tmp_path, mode="auto")
            assert manager.backend.backend_name == "json"
            assert "simulated" in manager._last_error
            with pytest.raises(StorageMigrationError, match="simulated"):
                manager.migrate_to_sqlite()
            assert not (tmp_path / "rollpig.db").exists()
            assert not list(tmp_path.glob(".rollpig.db.migrating-*.tmp"))
            assert json.loads((tmp_path / "pig_history.json").read_text(encoding="utf-8"))[
                "users"
            ]
        ''',
    )
    text = replace_test(
        text,
        "test_export_and_rollback_preserve_latest_sqlite_documents",
        '''
        def test_export_and_rollback_preserve_latest_sqlite_documents(tmp_path):
            _documents(tmp_path)
            manager = StorageManager(tmp_path, mode="auto")
            result = manager.backend.create_daily_draw(
                draw_date="2026-08-04",
                user_id="v2|qq|user|10001",
                pig={"id": "blue-pig", "name": "蓝猪"},
                group_id="v2|qq|group|20001",
            )
            assert result["created"] is True

            exported = manager.export_json_backup()
            assert exported["generated_on_demand"] is True
            archive = tmp_path / "storage_exports" / exported["filename"]
            assert archive.exists()
            with zipfile.ZipFile(archive) as bundle:
                archived_history = json.loads(bundle.read("pig_history.json"))
                assert archived_history["users"]["v2|qq|user|10001"]["total_draws"] == 3
                assert archived_history["daily"]["2026-08-04"]["records"][
                    "v2|qq|user|10001"
                ] == "blue-pig"
                assert "manifest.json" in bundle.namelist()
            with manager.backend._connection() as connection:
                assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0

            rollback = manager.rollback_to_json()
            assert rollback["status"] == "rolled-back"
            assert manager.backend.backend_name == "json"
            restored = json.loads((tmp_path / "pig_history.json").read_text(encoding="utf-8"))
            assert restored["users"]["v2|qq|user|10001"]["total_draws"] == 3
            assert restored["daily"]["2026-08-04"]["records"][
                "v2|qq|user|10001"
            ] == "blue-pig"
            assert not (tmp_path / "rollpig.db").exists()
            assert list(tmp_path.glob("rollpig.db.disabled-*"))
        ''',
    )
    text = replace_test(
        text,
        "test_v213_sql_primary_rebuild_repairs_documents_without_overwriting_sql",
        '''
        def test_v3_promotion_discards_stale_documents_without_overwriting_sql(tmp_path):
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
                content="SQL 保留文案",
                cutoff_date="2026-07-29",
                through_date="2026-08-04",
            )
            with storage.transaction() as connection:
                connection.execute(
                    "UPDATE documents SET payload = 'not-json', payload_sha256 = 'broken' "
                    "WHERE key = 'pig_history.json'"
                )
                connection.execute(
                    "UPDATE documents SET payload = '{\"version\":1}', "
                    "payload_sha256 = 'broken' WHERE key = 'roast_state.json'"
                )

            manager = StorageManager(tmp_path, mode="auto")
            assert isinstance(manager.backend, SQLitePrimaryStorage)
            verification = manager.backend.verify()
            assert verification["ok"] is True
            assert verification["schema_version"] == 6
            assert verification["documents"] == 0
            assert verification["projection_authority"] == "sql-primary-v3.0"
            snapshot = manager.backend.load_runtime_snapshot()
            assert snapshot["history"]["daily"]["2026-08-04"]["records"][
                "v2|qq|user|1"
            ] == "pig-a"
            roast_key = json.dumps(
                ["2026-08-04", "v2|qq|group|9", "v2|qq|user|1"],
                ensure_ascii=False,
            )
            assert snapshot["roast_state"]["daily_roast_counts"][roast_key] == 1
            assert snapshot["ai_roast_copies"]["copies"]["pig-a"][
                "2026-08-04"
            ] == "SQL 保留文案"
            documents = manager.backend.export_documents()
            assert documents["pig_history.json"]["daily"]["2026-08-04"]["records"][
                "v2|qq|user|1"
            ] == "pig-a"
        ''',
    )
    path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")


def write_v3_tests() -> None:
    Path("tests/test_sqlite_v3_primary.py").write_text(
        '''from __future__ import annotations

import multiprocessing
import sqlite3
from pathlib import Path

import pytest

from storage import SQLitePrimaryStorage, StorageManager


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
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    patch_manager()
    patch_existing_tests()
    write_v3_tests()
