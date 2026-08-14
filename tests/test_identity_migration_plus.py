import json
import sqlite3
from pathlib import Path

import pytest

from identity_migration import (
    IdentityMigrationError,
    migrate_legacy_config,
    migrate_legacy_data,
    validate_runtime_namespace,
)
from storage import StorageManager


def _write_marker(root: Path) -> None:
    (root / ".rollpig-enhanced-origin.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_repository": "casama233/astrbot_plugin_rollpig",
                "source_plugin_name": "astrbot_plugin_rollpig",
                "bridge_version": "3.1.4",
                "migration_target": "casama233/astrbot_plugin_rollpig_plus",
            }
        ),
        encoding="utf-8",
    )


def test_valid_bridge_json_is_copied_verified_and_source_is_retained(tmp_path: Path):
    old = tmp_path / "astrbot_plugin_rollpig"
    new = tmp_path / "astrbot_plugin_rollpig_plus"
    old.mkdir()
    new.mkdir()
    _write_marker(old)
    history = {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}}
    roast = {"version": 1, "cooldowns": {}}
    (old / "pig_history.json").write_text(json.dumps(history), encoding="utf-8")
    (old / "roast_state.json").write_text(json.dumps(roast), encoding="utf-8")
    (old / "images").mkdir()
    (old / "images" / "custom.png").write_bytes(b"custom-image")

    result = migrate_legacy_data(new)

    assert result["status"] == "migrated"
    assert result["source_retained"] is True
    assert (old / "pig_history.json").is_file()
    assert (new / "images" / "custom.png").read_bytes() == b"custom-image"
    state = json.loads((new / "identity_migration_state.json").read_text(encoding="utf-8"))
    assert state["status"] == "verified-copy"
    assert state["source_retained"] is True
    assert state["qualification"] == "bridge-marker"
    assert state["verification"]["ok"] is True


def test_original_style_legacy_data_is_not_auto_migrated(tmp_path: Path):
    old = tmp_path / "astrbot_plugin_rollpig"
    new = tmp_path / "astrbot_plugin_rollpig_plus"
    old.mkdir()
    new.mkdir()
    (old / "rollpig_today.json").write_text(
        '{"date":"2026-08-11","records":{}}', encoding="utf-8"
    )

    result = migrate_legacy_data(new)

    assert result["status"] == "legacy-source-ambiguous"
    assert list(new.iterdir()) == []
    assert (old / "rollpig_today.json").is_file()


def test_corrupt_qualified_sqlite_aborts_without_committing_destination(tmp_path: Path):
    old = tmp_path / "astrbot_plugin_rollpig"
    new = tmp_path / "astrbot_plugin_rollpig_plus"
    old.mkdir()
    new.mkdir()
    _write_marker(old)
    (old / "rollpig.db").write_bytes(b"not-a-sqlite-database")

    with pytest.raises(IdentityMigrationError):
        migrate_legacy_data(new)

    assert list(new.iterdir()) == []
    assert (old / "rollpig.db").read_bytes() == b"not-a-sqlite-database"


def test_sqlite_wal_snapshot_is_migrated_through_backup_api(tmp_path: Path):
    old = tmp_path / "astrbot_plugin_rollpig"
    new = tmp_path / "astrbot_plugin_rollpig_plus"
    old.mkdir()
    new.mkdir()
    manager = StorageManager(old, mode="auto")
    assert manager.verify()["ok"] is True
    database = old / "rollpig.db"
    writer = sqlite3.connect(database)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute(
            "INSERT INTO projection_meta(key, value) VALUES ('migration_wal_probe', 'present') "
            "ON CONFLICT(key) DO UPDATE SET value='present'"
        )
        writer.commit()
        result = migrate_legacy_data(new)
    finally:
        writer.close()

    assert result["status"] == "migrated"
    check = sqlite3.connect(new / "rollpig.db")
    try:
        row = check.execute(
            "SELECT value FROM projection_meta WHERE key='migration_wal_probe'"
        ).fetchone()
    finally:
        check.close()
    assert row == ("present",)
    assert (old / "rollpig.db").is_file()


class FakeConfig(dict):
    def __init__(self, path: Path):
        super().__init__({"timezone": "local", "enable_roast": True, "new_only": 7})
        self.config_path = str(path)
        self.first_deploy = True
        self.saved = False

    def save_config(self):
        self.saved = True
        Path(self.config_path).write_text(json.dumps(self), encoding="utf-8")


def test_config_migration_copies_only_current_schema_keys(tmp_path: Path):
    new_path = tmp_path / "astrbot_plugin_rollpig_plus_config.json"
    old_path = tmp_path / "astrbot_plugin_rollpig_config.json"
    old_path.write_text(
        json.dumps(
            {
                "timezone": "Asia/Hong_Kong",
                "enable_roast": False,
                "removed_key": 99,
            }
        ),
        encoding="utf-8",
    )
    config = FakeConfig(new_path)

    result = migrate_legacy_config(config)

    assert result["status"] == "migrated"
    assert config["timezone"] == "Asia/Hong_Kong"
    assert config["enable_roast"] is False
    assert config["new_only"] == 7
    assert "removed_key" not in config
    assert config.saved is True


def test_runtime_namespace_rejects_manual_clone_into_legacy_directory(tmp_path: Path):
    legacy_dir = tmp_path / "astrbot_plugin_rollpig"
    legacy_dir.mkdir()
    config = FakeConfig(tmp_path / "astrbot_plugin_rollpig_plus_config.json")
    with pytest.raises(IdentityMigrationError):
        validate_runtime_namespace(legacy_dir, config)


def test_phase2_metadata_and_updater_use_new_identity():
    metadata = Path("metadata.yaml").read_text(encoding="utf-8")
    assert 'name: "astrbot_plugin_rollpig_plus"' in metadata
    assert 'author: "casama233"' in metadata
    assert 'version: "3.6.4"' in metadata
    updater = Path("updater.py").read_text(encoding="utf-8")
    assert 'name.group(1) != "astrbot_plugin_rollpig_plus"' in updater
    assert 'author.group(1).strip() != "casama233"' in updater
    assert "禁止直接覆盖安装 3.2.0+" not in updater
