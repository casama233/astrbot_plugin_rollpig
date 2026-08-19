import asyncio

import pytest

from resource_failover_feature import ResourceFailoverMixin


class _BaseHarness:
    OFFICIAL_RESOURCE_MANIFEST_URL = (
        "https://curryudon.top/astrbot-rollpig/v1/manifest.json"
    )
    RESOURCE_CLIENT_ID = "astrbot_plugin_rollpig_plus"

    def __init__(self):
        self.resource_manifest_url = self.OFFICIAL_RESOURCE_MANIFEST_URL
        self.resource_vercel_mirror_url = (
            "https://rollpig-public-source-mirror.vercel.app/v1/manifest.json"
        )
        self.resource_github_fallback_enabled = True
        self.resource_github_mirror_url = (
            "https://raw.githubusercontent.com/casama233/rollpig-public-source-mirror/"
            "main/public/v1/manifest.json"
        )
        self._state = {"resource_version": "2026.08.19.2", "synced_at": 1}
        self.resource_state_path = object()
        self.calls = []
        self.last_sync_error = ""

    def _cloud_state(self):
        return dict(self._state)

    def save_json(self, path, data):
        assert path is self.resource_state_path
        self._state = dict(data)

    def _save_sync_status(self, error=""):
        self.last_sync_error = str(error or "")

    def _sync_status(self):
        return {"enabled": True}

    async def sync_cloud_resources(self, force=False):
        self.calls.append((self.resource_manifest_url, bool(force)))
        self._state = {
            "resource_version": "2026.08.19.3",
            "synced_at": 2,
        }
        return {"updated": True, "version": "2026.08.19.3"}


class _Harness(ResourceFailoverMixin, _BaseHarness):
    def __init__(self):
        _BaseHarness.__init__(self)



def test_official_source_chain_keeps_primary_vercel_github_order():
    plugin = _Harness()
    assert [name for name, _ in plugin._official_resource_sources()] == [
        "primary",
        "vercel",
        "github",
    ]



def test_custom_manifest_does_not_fall_back_to_public_sources():
    plugin = _Harness()
    plugin.resource_manifest_url = "https://private.example/resources/manifest.json"
    assert plugin._official_resource_sources() == [
        ("custom", "https://private.example/resources/manifest.json")
    ]



def test_numeric_official_versions_refuse_downgrade():
    plugin = _Harness()
    assert plugin._fallback_would_downgrade("2026.08.19.1") is True
    assert plugin._fallback_would_downgrade("2026.08.19.2") is False
    assert plugin._fallback_would_downgrade("2026.08.19.3") is False



def test_failover_uses_vercel_after_primary_probe_failure_and_restores_configured_url(monkeypatch):
    plugin = _Harness()

    async def probe(url):
        if url == plugin.OFFICIAL_RESOURCE_MANIFEST_URL:
            raise OSError("primary unavailable")
        return "2026.08.19.3"

    monkeypatch.setattr(plugin, "_probe_official_resource_manifest", probe)
    result = asyncio.run(plugin.sync_cloud_resources())

    assert result["source"] == "vercel"
    assert plugin.calls == [(plugin.resource_vercel_mirror_url, False)]
    assert plugin.resource_manifest_url == plugin.OFFICIAL_RESOURCE_MANIFEST_URL
    assert plugin._state["source_name"] == "vercel"
    assert plugin._state["source_url"] == plugin.resource_vercel_mirror_url



def test_failover_skips_stale_vercel_and_uses_github(monkeypatch):
    plugin = _Harness()

    async def probe(url):
        if url == plugin.OFFICIAL_RESOURCE_MANIFEST_URL:
            raise OSError("primary unavailable")
        if url == plugin.resource_vercel_mirror_url:
            return "2026.08.19.1"
        return "2026.08.19.3"

    monkeypatch.setattr(plugin, "_probe_official_resource_manifest", probe)
    result = asyncio.run(plugin.sync_cloud_resources())

    assert result["source"] == "github"
    assert plugin.calls == [(plugin.resource_github_mirror_url, False)]
    assert plugin.resource_manifest_url == plugin.OFFICIAL_RESOURCE_MANIFEST_URL



def test_all_official_sources_fail_without_destroying_configured_source(monkeypatch):
    plugin = _Harness()

    async def probe(_url):
        raise OSError("offline")

    monkeypatch.setattr(plugin, "_probe_official_resource_manifest", probe)
    with pytest.raises(ValueError, match="公共猪源全部不可用"):
        asyncio.run(plugin.sync_cloud_resources())

    assert plugin.resource_manifest_url == plugin.OFFICIAL_RESOURCE_MANIFEST_URL
    assert "primary" in plugin.last_sync_error
    assert "vercel" in plugin.last_sync_error
    assert "github" in plugin.last_sync_error



def test_sync_status_exposes_last_successful_remote_origin():
    plugin = _Harness()
    plugin._state.update(
        {
            "source_name": "vercel",
            "source_url": plugin.resource_vercel_mirror_url,
        }
    )
    payload = plugin._sync_status()
    assert payload["active_remote_source"] == "vercel"
    assert payload["active_remote_url"] == plugin.resource_vercel_mirror_url
    assert [item["name"] for item in payload["source_chain"]] == [
        "primary",
        "vercel",
        "github",
    ]



def test_fresh_install_uses_short_jitter_before_first_sync(monkeypatch):
    plugin = _Harness()
    plugin._state = {}
    calls = []

    def randint(low, high):
        calls.append((low, high))
        return 7

    monkeypatch.setattr("resource_failover_feature.random.randint", randint)
    assert plugin._initial_resource_sync_delay_seconds(damaged_cache=False) == 7
    assert calls == [(3, 10)]



def test_existing_cache_keeps_broader_startup_jitter(monkeypatch):
    plugin = _Harness()
    calls = []

    def randint(low, high):
        calls.append((low, high))
        return 60

    monkeypatch.setattr("resource_failover_feature.random.randint", randint)
    assert plugin._initial_resource_sync_delay_seconds(damaged_cache=False) == 60
    assert calls == [(30, 120)]



def test_damaged_cache_repair_stays_immediate_without_random_jitter(monkeypatch):
    plugin = _Harness()

    def unexpected_randint(_low, _high):
        raise AssertionError("damaged cache repair must not wait for random jitter")

    monkeypatch.setattr("resource_failover_feature.random.randint", unexpected_randint)
    assert plugin._initial_resource_sync_delay_seconds(damaged_cache=True) == 5
