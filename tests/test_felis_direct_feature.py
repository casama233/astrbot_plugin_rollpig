from __future__ import annotations

import json
import hashlib
import io
import asyncio
from pathlib import Path

import pytest

from felis_direct_feature import (
    FELIS_DIRECT_IDS,
    FELIS_DIRECT_MANIFEST_URL,
    FelisDirectFeature,
)
from services.resource_read_service import ResourceReadService
from PIL import Image


def _feature(tmp_path: Path):
    feature = object.__new__(FelisDirectFeature)
    feature.config = {}
    feature.plugin_data_dir = tmp_path
    feature.IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "gif")
    feature._init_felis_direct()
    return feature


def _write_complete_cache(feature, active: Path | None = None):
    active = active or feature.felis_direct_active_dir
    images = active / "images"
    images.mkdir(parents=True)
    records = [
        {"id": pig_id, "name": pig_id, "description": "d", "analysis": "a"}
        for pig_id in sorted(FELIS_DIRECT_IDS)
    ]
    image = io.BytesIO()
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(image, "PNG")
    image_bytes = image.getvalue()
    (active / "pig.json").write_text(json.dumps(records), encoding="utf-8")
    (active / "manifest.json").write_text(
        json.dumps({
            "resource_version": "test",
            "images": [
                {"id": item["id"], "filename": f"{item['id']}.png", "size": len(image_bytes), "sha256": hashlib.sha256(image_bytes).hexdigest()}
                for item in records
            ],
        }),
        encoding="utf-8",
    )
    for item in records:
        (images / f"{item['id']}.png").write_bytes(image_bytes)
    return records, image_bytes


def test_allowlist_is_exactly_34_and_url_is_official(tmp_path):
    assert len(FELIS_DIRECT_IDS) == 34
    feature = _feature(tmp_path)
    feature._felis_direct_validate_url(FELIS_DIRECT_MANIFEST_URL)
    with pytest.raises(ValueError):
        feature._felis_direct_validate_url(
            FELIS_DIRECT_MANIFEST_URL.replace(
                "raw.githubusercontent.com", "raw.githubusercontent.com:444"
            )
        )


def test_cache_requires_all_allowlisted_records_and_images(tmp_path):
    feature = _feature(tmp_path)
    records, _ = _write_complete_cache(feature)
    assert len(feature._felis_direct_cached_pigs()) == 34
    (feature.felis_direct_active_dir / "pig.json").write_text(
        json.dumps(records + [records[0]]), encoding="utf-8"
    )
    assert feature._felis_direct_cached_pigs() == []
    (feature.felis_direct_active_dir / "pig.json").write_text(
        json.dumps(records), encoding="utf-8"
    )
    (feature.felis_direct_active_dir / "images" / "awakened-pig.png").unlink()
    assert feature._felis_direct_cached_pigs() == []


def test_interrupted_activation_recovers_previous_complete_cache(tmp_path):
    feature = _feature(tmp_path)
    previous = feature.felis_direct_root / "previous"
    _write_complete_cache(feature, previous)
    feature.felis_direct_active_dir.mkdir()
    (feature.felis_direct_active_dir / "broken").write_text("broken", encoding="utf-8")
    assert feature._recover_felis_direct_cache() is True
    assert len(feature._felis_direct_cached_pigs()) == 34
    assert not previous.exists()


def test_status_exposes_direct_source_and_license(tmp_path):
    feature = _feature(tmp_path)
    status = feature._felis_direct_status()
    assert status["source"] == "felis-upstream-direct"
    assert status["allowlisted_ids"] == 34
    assert "RESOURCES-LICENSE.md" in status["license_url"]


def test_resource_read_uses_felis_overlay_after_cloud(tmp_path):
    custom = tmp_path / "custom"
    cloud = tmp_path / "cloud"
    overlay = tmp_path / "felis"
    bundled = tmp_path / "bundled"
    for directory in (custom, cloud, overlay, bundled):
        directory.mkdir()
    direct = overlay / "awakened-pig.png"
    direct.write_bytes(b"cached")
    result = ResourceReadService().find_image(
        "awakened-pig",
        custom_image_dir=custom,
        cloud_image_dir=cloud,
        overlay_image_dir=overlay,
        bundled_image_dir=bundled,
    )
    assert result == direct
    bundled_image = bundled / "awakened-pig.png"
    bundled_image.write_bytes(b"bundled")
    assert ResourceReadService().find_image(
        "awakened-pig",
        custom_image_dir=custom,
        cloud_image_dir=cloud,
        overlay_image_dir=None,
        bundled_image_dir=bundled,
    ) == bundled_image
    legacy_source = (Path(__file__).parents[1] / "legacy_main.py").read_text(
        encoding="utf-8"
    )
    assert "if self.felis_direct_enabled\n                else None" in legacy_source


def test_async_sync_writes_only_34_and_preserves_cache_on_bad_hash(tmp_path):
    feature = _feature(tmp_path)
    image = io.BytesIO()
    Image.new("RGBA", (2, 2), (0, 128, 255, 255)).save(image, "PNG")
    image_bytes = image.getvalue()
    records = [
        {"id": pig_id, "name": pig_id, "description": "d", "analysis": "a"}
        for pig_id in sorted(FELIS_DIRECT_IDS)
    ]
    manifest = {
        "schema_version": 1,
        "resource_version": "test-1",
        "pig_json": {"path": "pig.json", "size": len(json.dumps(records).encode()), "sha256": hashlib.sha256(json.dumps(records).encode()).hexdigest()},
        "images": [
            {"id": item["id"], "filename": f"{item['id']}.png", "path": f"images/{item['id']}.png", "size": len(image_bytes), "sha256": hashlib.sha256(image_bytes).hexdigest()}
            for item in records
        ],
    }
    pig_raw = json.dumps(records).encode()
    payloads = {feature.felis_direct_manifest_url: json.dumps(manifest).encode(), feature.felis_direct_manifest_url.rsplit("/", 1)[0] + "/pig.json": pig_raw}
    payloads.update({feature.felis_direct_manifest_url.rsplit("/", 1)[0] + f"/images/{item['id']}.png": image_bytes for item in records})

    async def download(url, _max):
        return payloads[url]

    feature._download_limited = lambda _client, url, max_size: download(url, max_size)
    client_options = {}
    def new_client(**kwargs):
        client_options.update(kwargs)
        return _FakeClient()
    feature._new_http_client = new_client
    feature._resource_request_headers = lambda: {}
    feature.resource_read_service = type("Reader", (), {"clear_cache": lambda self: None})()
    feature._reload_catalog_layers = lambda: setattr(feature, "reloaded", True)
    result = asyncio.run(feature.sync_felis_direct_resources(force=True))
    assert result["updated"] is True
    assert len(feature._felis_direct_cached_pigs()) == 34
    assert feature.reloaded is True
    assert client_options["follow_redirects"] is False
    old = (feature.felis_direct_active_dir / "images" / "awakened-pig.png").read_bytes()
    payloads[feature.felis_direct_manifest_url.rsplit("/", 1)[0] + "/images/awakened-pig.png"] = b"bad"
    stale = asyncio.run(feature.sync_felis_direct_resources(force=True))
    assert stale["stale"] is True
    assert (feature.felis_direct_active_dir / "images" / "awakened-pig.png").read_bytes() == old
    payloads[feature.felis_direct_manifest_url.rsplit("/", 1)[0] + "/images/awakened-pig.png"] = image_bytes
    duplicate_raw = json.dumps(records + [records[0]]).encode()
    manifest["resource_version"] = "test-duplicate"
    manifest["pig_json"] = {
        "path": "pig.json",
        "size": len(duplicate_raw),
        "sha256": hashlib.sha256(duplicate_raw).hexdigest(),
    }
    payloads[feature.felis_direct_manifest_url] = json.dumps(manifest).encode()
    payloads[feature.felis_direct_manifest_url.rsplit("/", 1)[0] + "/pig.json"] = duplicate_raw
    duplicate = asyncio.run(feature.sync_felis_direct_resources(force=True))
    assert duplicate["stale"] is True
    assert len(feature._felis_direct_cached_pigs()) == 34


class _FakeClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False
