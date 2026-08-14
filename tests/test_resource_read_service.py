from __future__ import annotations

from pathlib import Path

from services.resource_read_service import ResourceReadService


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def test_local_override_wins_before_ex_variant_and_base_layers(tmp_path: Path):
    local = _touch(tmp_path / "local" / "pig.png")
    variant = _touch(tmp_path / "variant" / "pig-ex2.png")
    _touch(tmp_path / "cloud" / "pig.png")
    _touch(tmp_path / "bundled" / "pig.png")

    result = ResourceReadService().find_image(
        "pig",
        custom_image_dir=tmp_path / "local",
        cloud_image_dir=tmp_path / "cloud",
        bundled_image_dir=tmp_path / "bundled",
        ex_level=2,
        variant_resolver=lambda _pig_id, _level: variant,
    )

    assert result == local


def test_ex_variant_wins_over_cloud_and_bundled_when_no_local_override(tmp_path: Path):
    variant = _touch(tmp_path / "variant" / "pig-ex2.png")
    _touch(tmp_path / "cloud" / "pig.png")
    _touch(tmp_path / "bundled" / "pig.png")

    result = ResourceReadService().find_image(
        "pig",
        custom_image_dir=tmp_path / "local",
        cloud_image_dir=tmp_path / "cloud",
        bundled_image_dir=tmp_path / "bundled",
        ex_level=2,
        variant_resolver=lambda _pig_id, _level: variant,
    )

    assert result == variant


def test_cloud_base_wins_over_bundled_base(tmp_path: Path):
    cloud = _touch(tmp_path / "cloud" / "pig.webp")
    _touch(tmp_path / "bundled" / "pig.png")

    result = ResourceReadService().find_image(
        "pig",
        custom_image_dir=tmp_path / "local",
        cloud_image_dir=tmp_path / "cloud",
        bundled_image_dir=tmp_path / "bundled",
    )

    assert result == cloud


def test_bundled_fallback_and_missing_image(tmp_path: Path):
    bundled = _touch(tmp_path / "bundled" / "pig.jpg")
    service = ResourceReadService()

    assert service.find_image(
        "pig",
        custom_image_dir=tmp_path / "local",
        cloud_image_dir=tmp_path / "cloud",
        bundled_image_dir=tmp_path / "bundled",
    ) == bundled
    assert service.find_image(
        "missing",
        custom_image_dir=tmp_path / "local",
        cloud_image_dir=tmp_path / "cloud",
        bundled_image_dir=tmp_path / "bundled",
    ) is None
