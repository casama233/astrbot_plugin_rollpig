from __future__ import annotations

import os
from pathlib import Path

from services.resource_read_service import ResourceReadService


def test_repeated_base_lookup_reuses_directory_probe_cache(tmp_path, monkeypatch):
    custom = tmp_path / "custom"
    cloud = tmp_path / "cloud"
    bundled = tmp_path / "bundled"
    for directory in (custom, cloud, bundled):
        directory.mkdir()
    bundled_path = bundled / "pig.png"
    bundled_path.write_bytes(b"bundled")

    service = ResourceReadService()
    service.clear_cache()
    original_exists = Path.exists
    probe_calls = 0
    watched = {custom, cloud, bundled}

    def tracked_exists(path: Path):
        nonlocal probe_calls
        if path.parent in watched:
            probe_calls += 1
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", tracked_exists)
    kwargs = {
        "custom_image_dir": custom,
        "cloud_image_dir": cloud,
        "bundled_image_dir": bundled,
    }

    first = service.find_image("pig", **kwargs)
    first_probe_calls = probe_calls
    second = service.find_image("pig", **kwargs)

    assert first == bundled_path
    assert second == bundled_path
    assert first_probe_calls > 0
    assert probe_calls == first_probe_calls


def test_directory_change_invalidates_cached_miss_and_preserves_precedence(tmp_path):
    custom = tmp_path / "custom"
    cloud = tmp_path / "cloud"
    bundled = tmp_path / "bundled"
    for directory in (custom, cloud, bundled):
        directory.mkdir()
    bundled_path = bundled / "pig.png"
    bundled_path.write_bytes(b"bundled")

    service = ResourceReadService()
    service.clear_cache()
    kwargs = {
        "custom_image_dir": custom,
        "cloud_image_dir": cloud,
        "bundled_image_dir": bundled,
    }
    assert service.find_image("pig", **kwargs) == bundled_path

    custom_path = custom / "pig.webp"
    custom_path.write_bytes(b"custom")
    stat = custom.stat()
    os.utime(custom, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert service.find_image("pig", **kwargs) == custom_path


def test_variant_resolver_remains_live_between_cached_base_lookups(tmp_path):
    custom = tmp_path / "custom"
    cloud = tmp_path / "cloud"
    bundled = tmp_path / "bundled"
    variants = tmp_path / "variants"
    for directory in (custom, cloud, bundled, variants):
        directory.mkdir()
    cloud_path = cloud / "pig.png"
    variant_path = variants / "pig-ex1.png"
    cloud_path.write_bytes(b"cloud")
    variant_path.write_bytes(b"variant")

    service = ResourceReadService()
    service.clear_cache()
    resolver_calls = 0

    def resolver(pig_id: str, ex_level: int):
        nonlocal resolver_calls
        resolver_calls += 1
        assert pig_id == "pig"
        assert ex_level == 1
        return variant_path

    kwargs = {
        "custom_image_dir": custom,
        "cloud_image_dir": cloud,
        "bundled_image_dir": bundled,
        "ex_level": 1,
        "variant_resolver": resolver,
    }

    assert service.find_image("pig", **kwargs) == variant_path
    assert service.find_image("pig", **kwargs) == variant_path
    assert resolver_calls == 2
