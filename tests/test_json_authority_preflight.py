"""Explicit JSON configuration is not permission to reset broken authority."""
from __future__ import annotations

import json
import re

import pytest

from storage import JSONStorage, StorageManager, StorageMigrationError


@pytest.mark.parametrize("has_marker", [False, True])
@pytest.mark.parametrize("filename", sorted(StorageManager.LEGACY_IMPORT_PATHS))
def test_explicit_json_preflight_preserves_broken_document(
    tmp_path, has_marker, filename, monkeypatch
):
    if has_marker:
        (tmp_path / "storage_state.json").write_text(
            json.dumps({"active_backend": "json"}), encoding="utf-8"
        )
    broken = tmp_path / filename
    broken.write_bytes(b"{broken-source")
    before = {path.name: path.read_bytes() for path in tmp_path.glob("*.json")}

    def forbid_repair(*args, **kwargs):
        pytest.fail("authority preflight must not call the repair-capable loader")

    monkeypatch.setattr(JSONStorage, "load_json", forbid_repair)
    with pytest.raises(StorageMigrationError, match=re.escape(filename)):
        StorageManager(tmp_path, mode="json")

    assert {path.name: path.read_bytes() for path in tmp_path.glob("*.json")} == before
    assert not list(tmp_path.glob("*.corrupt-*"))
    assert not (tmp_path / "rollpig.db").exists()


@pytest.mark.parametrize("mode", ["auto", "sqlite", "json"])
def test_unreadable_utf8_source_is_preserved(tmp_path, mode):
    path = tmp_path / "pig_history.json"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(StorageMigrationError, match=r"pig_history\.json"):
        StorageManager(tmp_path, mode=mode)
    assert path.read_bytes() == b"\xff\xfe"
    assert not list(tmp_path.glob("*.corrupt-*"))
    assert not (tmp_path / "rollpig.db").exists()


def test_json_preflight_rejects_unreadable_file_without_writing(tmp_path, monkeypatch):
    from pathlib import Path

    history = tmp_path / "pig_history.json"
    history.write_text('{"users": {}}', encoding="utf-8")
    original = Path.read_text

    def permission_error(path, *args, **kwargs):
        if path == history:
            raise PermissionError("synthetic unreadable authority")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", permission_error)
    with pytest.raises(StorageMigrationError, match="synthetic unreadable"):
        StorageManager(tmp_path, mode="json")
    assert history.read_bytes() == b'{"users": {}}'
    assert not list(tmp_path.glob("*.corrupt-*"))


def test_valid_json_native_source_is_unchanged(tmp_path):
    history = tmp_path / "pig_history.json"
    history.write_text('{"version": 1, "users": {}}', encoding="utf-8")
    original = history.read_bytes()
    manager = StorageManager(tmp_path, mode="json")
    assert manager.backend.backend_name == "json"
    assert history.read_bytes() == original
    assert not (tmp_path / "rollpig.db").exists()


def test_empty_json_native_installation_is_still_supported(tmp_path):
    manager = StorageManager(tmp_path, mode="json")
    assert manager.backend.backend_name == "json"
    assert not (tmp_path / "rollpig.db").exists()
