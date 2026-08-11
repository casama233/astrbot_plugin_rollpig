from pathlib import Path

import pytest

from updater import PluginUpdateManager, UpdateError


def _asset(name: str) -> dict[str, str]:
    return {
        "name": name,
        "browser_download_url": f"https://github.com/casama233/astrbot_plugin_rollpig/releases/download/v3.2.0/{name}",
    }


def _release(tag: str, asset_name: str, *, draft: bool = False, prerelease: bool = False):
    return {
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/casama233/astrbot_plugin_rollpig/releases/tag/{tag}",
        "assets": [_asset(asset_name)],
    }


def test_plus_channel_ignores_legacy_bridge_even_when_github_latest_points_to_it():
    releases = [
        _release("v3.1.4", "astrbot_plugin_rollpig-v3.1.4.zip"),
        _release("v3.2.0", "astrbot_plugin_rollpig_plus-v3.2.0.zip"),
    ]
    selected = PluginUpdateManager._select_release_payload(releases)
    assert selected["tag_name"] == "v3.2.0"


def test_plus_channel_selects_highest_stable_plus_release():
    releases = [
        _release("v3.2.0", "astrbot_plugin_rollpig_plus-v3.2.0.zip"),
        _release("v3.3.0", "astrbot_plugin_rollpig_plus-v3.3.0.zip", prerelease=True),
        _release("v3.2.2", "astrbot_plugin_rollpig_plus-v3.2.2.zip"),
        _release("v3.2.1", "astrbot_plugin_rollpig_plus-v3.2.1.zip", draft=True),
    ]
    selected = PluginUpdateManager._select_release_payload(releases)
    assert selected["tag_name"] == "v3.2.2"


def test_plus_channel_rejects_wrong_asset_identity_or_version():
    releases = [
        _release("v3.2.1", "astrbot_plugin_rollpig-v3.2.1.zip"),
        _release("v3.2.0", "astrbot_plugin_rollpig_plus-v9.9.9.zip"),
    ]
    with pytest.raises(UpdateError, match="RollPig Plus"):
        PluginUpdateManager._select_release_payload(releases)


def test_release_api_is_list_channel_not_global_latest():
    source = Path("updater.py").read_text(encoding="utf-8")
    assert "releases?per_page=30" in source
    assert "/releases/latest" not in source
