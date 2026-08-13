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


def test_resource_source_builder_emits_v1_manifest_and_matching_hashes(tmp_path):
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
            "2026.08.14.1",
            "--generated-at",
            "2026-08-14T00:00:00+00:00",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert summary["pig_count"] == 1
    assert manifest["schema_version"] == 1
    assert manifest["client"] == "astrbot_plugin_rollpig_plus"
    assert manifest["resource_version"] == "2026.08.14.1"
    assert manifest["pig_count"] == 1
    for entry in [manifest["pig_json"], *manifest["images"]]:
        path = output / entry["path"]
        assert path.stat().st_size == entry["size"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    health = json.loads((output / "health.json").read_text(encoding="utf-8"))
    assert health["status"] == "ok"
    assert health["protocol_version"] == 1


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
