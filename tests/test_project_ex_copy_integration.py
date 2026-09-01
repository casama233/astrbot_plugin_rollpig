from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_resource_source.py"


def test_runtime_layers_bundled_copy_before_felis_copy():
    source = (ROOT / "ex_variant_feature.py").read_text(encoding="utf-8")
    assert "from .bundled_ex_copy import load_bundled_ex_copy" in source
    assert "bundled_copy = self._read_bundled_ex_copy(" in source
    assert "felis_copy = self._read_felis_direct_ex_copy(" in source
    assert source.index("variants.update(bundled_copy)") < source.index(
        "variants.update(felis_copy)"
    )
    assert "project_copy.update(felis_copy)" in source


def test_resource_source_builder_materializes_project_owned_handwritten_copy(tmp_path: Path):
    resource = tmp_path / "resource"
    (resource / "image").mkdir(parents=True)
    (resource / "pig.json").write_text(
        json.dumps(
            [
                {
                    "id": "test-pig",
                    "name": "测试猪",
                    "description": "基础描述",
                    "analysis": "基础文案",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    Image.new("RGBA", (8, 8), (255, 120, 160, 255)).save(
        resource / "image" / "test-pig.png"
    )
    (resource / "bundled_ex_copy.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provenance": {
                    "scope": "bundled-lineage-text-only",
                    "source_basis": "test fixture",
                    "quarantined_ex_used": False,
                },
                "pigs": {
                    "test-pig": {
                        "levels": {
                            str(level): {
                                "description": f"手写 EX{level}",
                                "analysis": f"这是第 {level} 级独立手写文案。",
                            }
                            for level in range(1, 6)
                        }
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output = tmp_path / "release"
    subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--source",
            str(resource),
            "--output",
            str(output),
            "--version",
            "handwritten-test",
            "--generated-at",
            "2026-08-28T00:00:00+00:00",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(
        (output / "pig_ex_variants.json").read_text(encoding="utf-8")
    )
    levels = payload["pigs"]["test-pig"]
    assert [levels[str(level)]["description"] for level in range(1, 6)] == [
        f"手写 EX{level}" for level in range(1, 6)
    ]
    assert all("image" not in levels[str(level)] for level in range(1, 6))


def test_historical_quarantined_authored_paths_remain_absent():
    assert not (ROOT / "resource" / "pig_ex_variants.json").exists()
    assert not (ROOT / "resource" / "ex_curated").exists()
    assert (ROOT / "resource" / "bundled_ex_copy.json").is_file()
