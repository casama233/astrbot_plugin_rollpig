from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


sqlite_path = ROOT / "storage" / "sqlite_storage.py"
sqlite = sqlite_path.read_text(encoding="utf-8")
connect_anchor = '''        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        return connection

    def _initialize(self) -> None:
'''
connect_replacement = '''        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
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
'''
sqlite = replace_once(
    sqlite, connect_anchor, connect_replacement, "connection context manager"
)
lock_count = sqlite.count("with self._lock, self._connect() as connection:")
plain_count = sqlite.count("with self._connect() as connection:")
if lock_count < 4 or plain_count < 2:
    raise RuntimeError(
        f"unexpected connection anchors: lock={lock_count}, plain={plain_count}"
    )
sqlite = sqlite.replace(
    "with self._lock, self._connect() as connection:",
    "with self._lock, self._connection() as connection:",
)
sqlite = sqlite.replace(
    "with self._connect() as connection:",
    "with self._connection() as connection:",
)
batch_anchor = '''        unmanaged = {
            Path(path): value
            for path, value in updates.items()
            if not self._is_managed(Path(path))
        }
        with self._lock:
'''
batch_replacement = '''        unmanaged = {
            Path(path): value
            for path, value in updates.items()
            if not self._is_managed(Path(path))
        }
        if managed and unmanaged:
            raise ValueError(
                "同一批次不能混合 SQLite 关键文档与普通 JSON 缓存"
            )
        with self._lock:
'''
sqlite = replace_once(
    sqlite, batch_anchor, batch_replacement, "mixed batch rejection"
)
sqlite_path.write_text(sqlite, encoding="utf-8", newline="\n")

manager_path = ROOT / "storage" / "manager.py"
manager = manager_path.read_text(encoding="utf-8")
migrate_anchor = '''    def migrate_to_sqlite(self) -> dict[str, Any]:
        with self._lock:
            if isinstance(self.backend, SQLiteStorage):
'''
migrate_replacement = '''    def migrate_to_sqlite(self) -> dict[str, Any]:
        with self._lock:
            if self.mode == "json":
                raise StorageMigrationError(
                    "配置已强制使用 JSON；请先将 storage_backend 改为 auto"
                )
            if isinstance(self.backend, SQLiteStorage):
'''
manager = replace_once(
    manager, migrate_anchor, migrate_replacement, "json mode enforcement"
)
manager_path.write_text(manager, encoding="utf-8", newline="\n")

tests_path = ROOT / "tests" / "test_sqlite_storage.py"
tests = tests_path.read_text(encoding="utf-8")
tests = replace_once(
    tests,
    "import json\nimport time\nimport zipfile\n",
    "import json\nimport sqlite3\nimport time\nimport zipfile\n",
    "sqlite3 test import",
)
tests += '''


def test_connection_context_rolls_back_and_closes(tmp_path, monkeypatch):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    connection = storage._connect()
    monkeypatch.setattr(storage, "_connect", lambda: connection)
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
'''
tests_path.write_text(tests, encoding="utf-8", newline="\n")

Path(__file__).unlink()
