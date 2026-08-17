import asyncio
from pathlib import Path

import pytest

from updater import PluginUpdateManager, UpdateError


def _manager(tmp_path: Path) -> PluginUpdateManager:
    plugin = tmp_path / "plugin"
    data = tmp_path / "data"
    plugin.mkdir()
    data.mkdir()
    (plugin / "metadata.yaml").write_text(
        'name: "astrbot_plugin_rollpig_plus"\nversion: "3.11.2"\n',
        encoding="utf-8",
    )
    return PluginUpdateManager(plugin, data)


def _release(version: str = "3.11.3") -> dict:
    archive = f"astrbot_plugin_rollpig_plus-v{version}.zip"
    base = "https://github.com/casama233/astrbot_plugin_rollpig"
    return {
        "draft": False,
        "prerelease": False,
        "tag_name": f"v{version}",
        "html_url": f"{base}/releases/tag/v{version}",
        "assets": [
            {
                "name": archive,
                "browser_download_url": f"{base}/releases/download/v{version}/{archive}",
            }
        ],
    }


def test_updater_uses_latest_endpoint_when_release_list_would_be_empty(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    calls = []

    async def fake_json(url):
        calls.append(("json", url))
        return _release()

    async def fake_list(url):
        calls.append(("list", url))
        return []

    monkeypatch.setattr(manager, "_request_json", fake_json)
    monkeypatch.setattr(manager, "_request_json_list", fake_list)

    payload = asyncio.run(manager._fetch_stable_release_payload())
    assert payload["tag_name"] == "v3.11.3"
    assert calls == [("json", manager.LATEST_RELEASE_API)]


def test_updater_falls_back_to_release_list_when_latest_is_not_verifiable(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    calls = []

    async def fake_json(url):
        calls.append(("json", url))
        return {"tag_name": "v3.11.3", "draft": False, "prerelease": False, "assets": []}

    async def fake_list(url):
        calls.append(("list", url))
        return [_release("3.11.2")]

    monkeypatch.setattr(manager, "_request_json", fake_json)
    monkeypatch.setattr(manager, "_request_json_list", fake_list)

    payload = asyncio.run(manager._fetch_stable_release_payload())
    assert payload["tag_name"] == "v3.11.2"
    assert calls == [
        ("json", manager.LATEST_RELEASE_API),
        ("list", manager.RELEASES_API),
    ]


def test_updater_reports_both_release_channels_when_neither_is_usable(tmp_path, monkeypatch):
    manager = _manager(tmp_path)

    async def fake_json(_url):
        return {"tag_name": "v3.11.3", "draft": False, "prerelease": False, "assets": []}

    async def fake_list(_url):
        return []

    monkeypatch.setattr(manager, "_request_json", fake_json)
    monkeypatch.setattr(manager, "_request_json_list", fake_list)

    with pytest.raises(UpdateError, match="latest=.*list="):
        asyncio.run(manager._fetch_stable_release_payload())


def test_latest_release_endpoint_is_the_primary_channel():
    assert PluginUpdateManager.LATEST_RELEASE_API.endswith("/releases/latest")
    assert PluginUpdateManager.RELEASES_API.endswith("/releases?per_page=30")
