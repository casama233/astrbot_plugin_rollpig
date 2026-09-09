from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from storage import SQLitePrimaryStorage, SQLiteStorage, StorageManager, StorageMigrationError


@pytest.mark.parametrize('mode', ['auto', 'sqlite'])
@pytest.mark.parametrize('marker', [False, True])
@pytest.mark.parametrize('content', [b'', b'SQLite format 3\x00', b'not-a-database'])
def test_existing_empty_or_truncated_database_is_never_initialized(tmp_path, monkeypatch, mode, marker, content):
    database = tmp_path / 'rollpig.db'
    database.write_bytes(content)
    if marker:
        (tmp_path / 'storage_state.json').write_text(json.dumps({'active_backend': 'sqlite'}))
    history = tmp_path / 'pig_history.json'
    history.write_text('{"users":{"stale":{}}}')
    before = {path.name: path.read_bytes() for path in tmp_path.glob('*.json')}

    def forbidden(*args, **kwargs):
        pytest.fail('existing database preflight must happen before backend initialization')

    monkeypatch.setattr(StorageManager, '_new_sqlite', forbidden)
    with pytest.raises(StorageMigrationError, match='SQLite 需要恢复'):
        StorageManager(tmp_path, mode=mode)
    assert database.read_bytes() == content
    assert {path.name: path.read_bytes() for path in tmp_path.glob('*.json')} == before


@pytest.mark.parametrize('kind', ['empty-schema', 'unrelated'])
def test_valid_sqlite_file_without_rollpig_schema_is_not_bootstrapped(tmp_path, monkeypatch, kind):
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as connection:
        if kind == 'empty-schema':
            connection.execute('VACUUM')
        else:
            connection.execute('CREATE TABLE unrelated(value TEXT)')
            connection.commit()
    before = database.read_bytes()
    monkeypatch.setattr(StorageManager, '_new_sqlite', lambda *args: pytest.fail('must preflight first'))
    with pytest.raises(StorageMigrationError, match='核心表'):
        StorageManager(tmp_path)
    assert database.read_bytes() == before


@pytest.mark.parametrize('table', ['schema_migrations', 'documents', 'identities', 'daily_draws', 'user_pigs'])
def test_missing_core_table_is_not_recreated_before_validation(tmp_path, table):
    manager = StorageManager(tmp_path)
    manager.backend.checkpoint()
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as connection:
        connection.execute('PRAGMA journal_mode=DELETE')
        connection.execute(f'DROP TABLE {table}')
        connection.commit()
    before = database.read_bytes()
    with pytest.raises(StorageMigrationError, match='核心表'):
        StorageManager(tmp_path)
    assert database.read_bytes() == before


@pytest.mark.parametrize('version', [None, 0, 999])
def test_unverified_schema_version_does_not_trigger_migrations(tmp_path, version):
    manager = StorageManager(tmp_path)
    manager.backend.checkpoint()
    with closing(sqlite3.connect(tmp_path / 'rollpig.db')) as connection:
        connection.execute('DELETE FROM schema_migrations')
        if version is not None:
            connection.execute('INSERT INTO schema_migrations VALUES (?, 1)', (version,))
        connection.commit()
    with pytest.raises(StorageMigrationError, match='schema'):
        StorageManager(tmp_path)


def test_healthy_empty_database_and_new_install_remain_supported(tmp_path):
    first = StorageManager(tmp_path)
    assert isinstance(first.backend, SQLitePrimaryStorage)
    assert first.verify()['ok'] is True
    restarted = StorageManager(tmp_path)
    assert isinstance(restarted.backend, SQLitePrimaryStorage)
    assert restarted.verify()['ok'] is True


def test_valid_v2_database_still_upgrades(tmp_path):
    old = SQLiteStorage(tmp_path / 'rollpig.db', tmp_path, StorageManager.MANAGED_PATHS)
    old.save_json(tmp_path / 'pig_history.json', {'version': 1, 'users': {}, 'daily': {}, 'pig_snapshots': {}})
    old.checkpoint()
    manager = StorageManager(tmp_path)
    assert isinstance(manager.backend, SQLitePrimaryStorage)
    assert manager.verify()['schema_version'] == 6
    assert manager.verify()['ok'] is True


def test_preflight_reads_wal_schema_and_latest_committed_collection(tmp_path):
    manager = StorageManager(tmp_path)
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as keeper:
        keeper.execute('PRAGMA journal_mode=WAL')
        keeper.execute('PRAGMA wal_autocheckpoint=0')
        keeper.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()
        manager.backend.create_daily_draw(draw_date='2026-09-09', user_id='user-wal', pig={'id': 'pig-a', 'name': 'A'})
        assert Path(f'{database}-wal').stat().st_size > 0
        restarted = StorageManager(tmp_path)
        assert restarted.backend.get_user_collection(('user-wal',))['total_draws'] == 1
        assert restarted.verify()['ok'] is True


def test_readonly_preflight_uses_schema_from_wal_not_immutable_database(tmp_path):
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('PRAGMA wal_autocheckpoint=0')
        for name in ('documents', 'identities', 'daily_draws', 'user_pigs'):
            writer.execute(f'CREATE TABLE {name}(value TEXT)')
        writer.execute('CREATE TABLE schema_migrations(version INTEGER, applied_at INTEGER)')
        writer.execute('INSERT INTO schema_migrations VALUES (1, 1)')
        writer.commit()
        probe = StorageManager.__new__(StorageManager)
        probe.database_path = database
        probe.busy_timeout_ms = 1000
        before = database.read_bytes()
        probe._preflight_existing_sqlite()
        assert database.read_bytes() == before
        assert Path(f'{database}-wal').stat().st_size > 0


def test_empty_database_preserves_orphan_sidecar_evidence(tmp_path):
    database = tmp_path / 'rollpig.db'
    database.write_bytes(b'')
    for suffix in ('-wal', '-shm'):
        Path(f'{database}{suffix}').write_bytes(('evidence' + suffix).encode())
    with pytest.raises(StorageMigrationError, match='SQLite 需要恢复'):
        StorageManager(tmp_path)
    assert database.read_bytes() == b''
    for suffix in ('-wal', '-shm'):
        expected = ('evidence' + suffix).encode()
        assert Path(f'{database}{suffix}').read_bytes() == expected
        assert any(path.read_bytes() == expected for path in tmp_path.glob('.rollpig.db.preflight-*' + suffix))
