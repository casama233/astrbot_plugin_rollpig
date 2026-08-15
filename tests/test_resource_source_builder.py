from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_resource_source.py"


def _fixture(root: Path, *, with_image: bool = True) -> Path:
    source = root / "resource"
    (source / "image").mkdir(parents=True)
    (source / "pig.json").write_text(
        json.dumps(
            [
                {
                    "id": "test-pig",
                    "name": "測試豬",
                    "description": "測試來源",
                    "analysis": "只供資源建構器回歸測試。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if with_image:
        Image.new("RGBA", (8, 8), (255, 120, 160, 255)).save(
            source / "image" / "test-pig.png"
        )
    return source


def _add_ex_variants(source: Path, *, include_image: bool = True) -> None:
    (source / "pig_ex_variants.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pigs": {
                    "test-pig": {
                        "2": {
                            "description": "EX2 描述",
                            "image": "test-pig-ex2.png",
                        },
                        "4": {"analysis": "EX4 文案"},
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if include_image:
        (source / "ex_variants").mkdir()
        Image.new("RGBA", (8, 8), (80, 160, 255, 255)).save(
            source / "ex_variants" / "test-pig-ex2.png"
        )


def _run_builder(source: Path, output: Path, version: str) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--source",
            str(source),
            "--output",
            str(output),
            "--version",
            version,
            "--generated-at",
            "2026-08-14T00:00:00+00:00",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_resource_source_builder_emits_v1_manifest_and_full_ex_baseline(tmp_path):
    source = _fixture(tmp_path)
    output = tmp_path / "release"
    summary = _run_builder(source, output, "2026.08.14.1")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert summary["pig_count"] == 1
    assert summary["ex_variant_pig_count"] == 1
    assert manifest["schema_version"] == 1
    assert manifest["client"] == "astrbot_plugin_rollpig_plus"
    assert manifest["resource_version"] == "2026.08.14.1"
    assert manifest["pig_count"] == 1
    assert manifest["ex_variant_pig_count"] == 1
    assert manifest["ex_variants"]["path"] == "pig_ex_variants.json"
    for entry in [
        manifest["pig_json"],
        *manifest["images"],
        manifest["ex_variants"],
    ]:
        path = output / entry["path"]
        assert path.stat().st_size == entry["size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

    variants = json.loads(
        (output / "pig_ex_variants.json").read_text(encoding="utf-8")
    )
    levels = variants["pigs"]["test-pig"]
    assert set(levels) == {"1", "2", "3", "4", "5"}
    assert len({levels[str(level)]["description"] for level in range(1, 6)}) == 5
    assert len({levels[str(level)]["analysis"] for level in range(1, 6)}) == 5

    health = json.loads((output / "health.json").read_text(encoding="utf-8"))
    assert health["status"] == "ok"
    assert health["protocol_version"] == 1
    assert health["ex_variant_pig_count"] == 1
    assert health["ex_variant_image_count"] == 0


def test_resource_source_builder_materializes_sparse_override_inheritance(tmp_path):
    source = _fixture(tmp_path)
    _add_ex_variants(source)
    output = tmp_path / "release"
    _run_builder(source, output, "2026.08.14.ex1")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["ex_variants"]["path"] == "pig_ex_variants.json"
    assert manifest["ex_variant_pig_count"] == manifest["pig_count"] == 1
    assert [item["filename"] for item in manifest["variant_images"]] == [
        "test-pig-ex2.png"
    ]
    entries = [manifest["ex_variants"], *manifest["variant_images"]]
    for entry in entries:
        path = output / entry["path"]
        assert path.stat().st_size == entry["size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

    variants = json.loads(
        (output / "pig_ex_variants.json").read_text(encoding="utf-8")
    )
    levels = variants["pigs"]["test-pig"]
    assert levels["1"]["description"] != "EX2 描述"
    assert levels["2"]["description"] == "EX2 描述"
    assert levels["3"]["description"] == "EX2 描述"
    assert levels["2"]["image"] == "test-pig-ex2.png"
    assert levels["5"]["image"] == "test-pig-ex2.png"
    assert levels["4"]["analysis"] == "EX4 文案"
    assert levels["5"]["analysis"] == "EX4 文案"
    health = json.loads((output / "health.json").read_text(encoding="utf-8"))
    assert health["ex_variant_pig_count"] == 1
    assert health["ex_variant_image_count"] == 1


def test_resource_source_builder_rejects_missing_ex_variant_image(tmp_path):
    source = _fixture(tmp_path)
    _add_ex_variants(source, include_image=False)
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--source",
            str(source),
            "--output",
            str(tmp_path / "release"),
            "--version",
            "broken-ex",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "缺少 resource/ex_variants" in result.stderr


def test_resource_source_builder_rejects_catalog_without_matching_image(tmp_path):
    source = _fixture(tmp_path, with_image=False)
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--source",
            str(source),
            "--output",
            str(tmp_path / "release"),
            "--version",
            "broken",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "缺少圖片" in result.stderr


def test_resource_source_builder_default_timestamp_is_python310_compatible(tmp_path):
    source = _fixture(tmp_path)
    output = tmp_path / "release"
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--source",
            str(source),
            "--output",
            str(output),
            "--version",
            "2026.08.14.2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert result.returncode == 0
    assert manifest["generated_at"].endswith("+00:00")
    assert "dt.UTC" not in BUILDER.read_text(encoding="utf-8")
