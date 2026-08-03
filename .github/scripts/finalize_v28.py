from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


updater_path = ROOT / "updater.py"
updater = updater_path.read_text(encoding="utf-8")

updater = replace_once(
    updater,
    '''    def status(self) -> dict[str, Any]:
        current = self.current_version()
        pending = dict(self._pending or {})
        pending.pop("checksum_url", None)
        pending.pop("download_url", None)
        return {
            "current_version": current,
            "backend": "official-github-release",
            "official_repository": self.OFFICIAL_REPOSITORY,
            "busy": self._lock.locked(),
            "last_check_at": self._last_check_at,
            "last_error": self._last_error,
            "pending": pending or None,
            "last_result": self._last_result,
        }
''',
    '''    def status(self) -> dict[str, Any]:
        current = self.current_version()
        pending = dict(self._pending or {})
        pending.pop("checksum_url", None)
        pending.pop("download_url", None)
        last_result = dict(self._last_result or {})
        last_result.pop("backup_dir", None)
        return {
            "current_version": current,
            "backend": "official-github-release",
            "official_repository": self.OFFICIAL_REPOSITORY,
            "busy": self._lock.locked(),
            "last_check_at": self._last_check_at,
            "last_error": self._last_error,
            "pending": pending or None,
            "last_result": last_result or None,
        }
''',
    "sanitize status",
)

updater = replace_once(
    updater,
    '''    @staticmethod
    def _select_archive_asset(assets: list[Any]) -> dict[str, Any] | None:
        candidates = [
            item
            for item in assets
            if isinstance(item, dict)
            and str(item.get("name") or "").lower().endswith(".zip")
        ]
''',
    '''    @staticmethod
    def _select_archive_asset(assets: list[Any]) -> dict[str, Any] | None:
        candidates = [
            item
            for item in assets
            if isinstance(item, dict)
            and str(item.get("name") or "").lower().endswith(".zip")
            and "rollpig" in str(item.get("name") or "").lower()
        ]
''',
    "restrict archive assets",
)

updater = replace_once(
    updater,
    '''        checksum_url = self._select_checksum_url(assets, archive_name)
        expected_sha256 = ""
        if checksum_url:
''',
    '''        checksum_url = self._select_checksum_url(assets, archive_name)
        expected_sha256 = ""
        if checksum_url:
            expected_checksum_prefix = (
                f"https://github.com/{self.OFFICIAL_REPOSITORY}/releases/download/"
            )
            if not checksum_url.startswith(expected_checksum_prefix):
                raise UpdateError("Release 校验文件地址不属于官方仓库")
''',
    "validate checksum asset origin",
)

updater = replace_once(
    updater,
    '''        self._write_state(state)
        self._prune_backups()
        self._log(
            "info",
            f"今日小猪已安全更新到 {release['latest_version']}，等待 AstrBot 重启加载",
        )
        return state
''',
    '''        warnings: list[str] = []
        try:
            self._write_state(state)
        except OSError as exc:
            warning = f"代码已更新，但状态记录写入失败：{type(exc).__name__}"
            warnings.append(warning)
            self._log("warning", warning)
        try:
            self._prune_backups()
        except OSError as exc:
            warning = f"代码已更新，但旧备份清理失败：{type(exc).__name__}"
            warnings.append(warning)
            self._log("warning", warning)
        self._log(
            "info",
            f"今日小猪已安全更新到 {release['latest_version']}，等待 AstrBot 重启加载",
        )
        public_state = dict(state)
        public_state.pop("backup_dir", None)
        if warnings:
            public_state["warnings"] = warnings
        return public_state
''',
    "make post-install bookkeeping non-fatal",
)

updater_path.write_text(updater, encoding="utf-8", newline="\n")


tests_path = ROOT / "tests" / "test_storage_and_updater.py"
tests = tests_path.read_text(encoding="utf-8")
tests += r'''


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
'''
tests_path.write_text(tests, encoding="utf-8", newline="\n")

Path(__file__).unlink()
