import asyncio
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

from storage import JSONStorage
from updater import PluginUpdateManager, UpdateError


def _manager(tmp_path: Path) -> PluginUpdateManager:
    plugin = tmp_path / "plugin"
    data = tmp_path / "data"
    (plugin / "resource").mkdir(parents=True)
    data.mkdir()
    (plugin / "metadata.yaml").write_text(
        'name: "astrbot_plugin_rollpig"\n'
        'version: "2.7.0"\n'
        'repo: "https://github.com/casama233/astrbot_plugin_rollpig"\n',
        encoding="utf-8",
    )
    (plugin / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    (plugin / "resource" / "pig.json").write_text("[]\n", encoding="utf-8")
    return PluginUpdateManager(plugin, data)


def _release_zip(version: str = "2.8.0", extra: dict[str, bytes] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        root = f"casama233-astrbot_plugin_rollpig-{version}/"
        archive.writestr(root + "main.py", "VALUE = 2\n")
        archive.writestr(
            root + "metadata.yaml",
            'name: "astrbot_plugin_rollpig"\n'
            f'version: "{version}"\n'
            'repo: "https://github.com/casama233/astrbot_plugin_rollpig"\n',
        )
        archive.writestr(root + "resource/pig.json", "[]\n")
        for name, content in (extra or {}).items():
            archive.writestr(root + name, content)
    return buffer.getvalue()


def test_json_storage_preserves_default_and_recovers_backup(tmp_path):
    path = tmp_path / "state.json"
    storage = JSONStorage()
    default = {"items": []}
    loaded = storage.load_json(path, default)
    loaded["items"].append("local")
    assert default == {"items": []}

    storage.save_json(path, {"ok": 1})
    storage.save_json(path, {"ok": 2})
    path.write_text("{broken", encoding="utf-8")
    assert storage.load_json(path, {}) == {"ok": 1}
    assert list(tmp_path.glob("state.json.corrupt-*"))


def test_json_storage_batch_rolls_back_new_and_existing_files(tmp_path, monkeypatch):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    storage = JSONStorage()
    storage.save_json(first, {"before": True})

    real_replace = os.replace
    calls = 0

    def fail_second(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated replacement failure")
        return real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError):
        storage.save_json_batch({first: {"after": True}, second: {"new": True}})

    assert json.loads(first.read_text(encoding="utf-8")) == {"before": True}
    assert not second.exists()


def test_updater_accepts_only_stable_semver_and_parses_checksum(tmp_path):
    manager = _manager(tmp_path)
    assert manager._version_tuple("v2.8.0") > manager._version_tuple("2.7.9")
    with pytest.raises(UpdateError):
        manager._normalise_version("2.8.0-rc.1")

    digest = "a" * 64
    assert manager._parse_checksum(f"{digest}  rollpig.zip\n", "rollpig.zip") == digest
    assert manager._parse_checksum(f"{digest}\n", "rollpig.zip") == digest


def test_updater_rejects_zip_slip(tmp_path):
    manager = _manager(tmp_path)
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("root/main.py", "VALUE = 2\n")
        archive.writestr("root/../../escape.py", "bad = True\n")
    staging = tmp_path / "staging"
    staging.mkdir()
    with pytest.raises(UpdateError, match="路径穿越"):
        manager._safe_extract(archive_path, staging)
    assert not (tmp_path / "escape.py").exists()


def test_updater_stages_valid_official_release(tmp_path):
    manager = _manager(tmp_path)
    raw = _release_zip(extra={"updater.py": b"VALUE = 3\n"})
    result = manager._stage_validate_and_apply(
        raw,
        {
            "current_version": "2.7.0",
            "latest_version": "2.8.0",
            "checksum_available": True,
        },
        hashlib.sha256(raw).hexdigest(),
    )
    assert result["to_version"] == "2.8.0"
    assert result["restart_required"] is True
    assert (manager.plugin_dir / "main.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    assert (manager.data_dir / "update_state.json").exists()
    assert list((manager.data_dir / "update_backups").iterdir())


def test_unsigned_release_requires_explicit_confirmation(tmp_path, monkeypatch):
    manager = _manager(tmp_path)

    async def fake_check():
        manager._pending = {"download_url": "https://github.com/example.zip"}
        return {
            "current_version": "2.7.0",
            "latest_version": "2.8.0",
            "update_available": True,
            "checksum_available": False,
            "expected_sha256": "",
        }

    monkeypatch.setattr(manager, "_check_unlocked", fake_check)
    with pytest.raises(UpdateError, match="二次确认"):
        asyncio.run(manager.apply_update(confirm_unsigned=False))



def test_updater_ignores_unrelated_release_zip_assets(tmp_path):
    manager = _manager(tmp_path)
    assets = [
        {"name": "website-assets.zip", "browser_download_url": "https://example.invalid/a"},
        {"name": "astrbot_plugin_rollpig-v2.8.0.zip", "browser_download_url": "https://example.invalid/b"},
    ]
    assert manager._select_archive_asset(assets)["name"] == "astrbot_plugin_rollpig-v2.8.0.zip"
    assert manager._select_archive_asset(assets[:1]) is None


def test_updater_status_does_not_expose_backup_path(tmp_path):
    manager = _manager(tmp_path)
    manager._last_result = {
        "status": "installed-restart-required",
        "backup_dir": "/private/server/path",
        "restart_required": True,
    }
    status = manager.status()
    assert "backup_dir" not in status["last_result"]
    assert status["last_result"]["restart_required"] is True


def test_state_write_failure_is_reported_as_warning_after_valid_install(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    raw = _release_zip()

    def fail_state(_state):
        raise OSError("disk metadata write failure")

    monkeypatch.setattr(manager, "_write_state", fail_state)
    result = manager._stage_validate_and_apply(
        raw,
        {
            "current_version": "2.7.0",
            "latest_version": "2.8.0",
            "checksum_available": True,
        },
        hashlib.sha256(raw).hexdigest(),
    )

    assert result["status"] == "installed-restart-required"
    assert result["restart_required"] is True
    assert result["warnings"]
    assert "backup_dir" not in result
    assert (manager.plugin_dir / "main.py").read_text(encoding="utf-8") == "VALUE = 2\n"
