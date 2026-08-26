from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_asset_provenance.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path, *, wrong_hash: bool = False, committed: bool = True) -> Path:
    source = root / "resource"
    image_root = source / "image"
    image_root.mkdir(parents=True)
    image = image_root / "test-pig.png"
    Image.new("RGBA", (8, 8), (255, 120, 160, 255)).save(image)
    replacement_sha = "0" * 64 if wrong_hash else _sha256(image)
    (source / "asset_provenance.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "publication_state": "approved",
                "assets": {
                    "test-pig": {
                        "distribution_mode": "public",
                        "asset_role": "derived-rework",
                        "rights_basis": "derived-from-mit-upstream",
                        "source_repo": "example/upstream",
                        "source_path": "resource/image/test-pig.png",
                        "source_sha256": "1" * 64,
                        "replacement_sha256": replacement_sha,
                        "license": "MIT",
                        "attribution": ["Example Author"],
                        "redistribution_allowed": True,
                        "binary_committed": committed,
                    }
                },
                "withheld": {
                    "unknown-pig": {
                        "rights_basis": "unknown",
                        "redistribution_allowed": False,
                        "reason": "No redistribution evidence.",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return source


def _run(source: Path, output: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(CHECKER), "--source", str(source)]
    if output is not None:
        command += ["--output", str(output)]
    return subprocess.run(command, capture_output=True, text=True)


def test_asset_provenance_accepts_exact_replacement_hash_and_publishes(tmp_path):
    source = _fixture(tmp_path)
    output = tmp_path / "dist" / "asset_provenance.json"
    result = _run(source, output)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["approved_asset_count"] == 1
    assert summary["withheld_asset_count"] == 1
    published = json.loads(output.read_text(encoding="utf-8"))
    assert published["assets"]["test-pig"]["redistribution_allowed"] is True
    assert published["withheld"]["unknown-pig"]["redistribution_allowed"] is False


def test_asset_provenance_rejects_replacement_hash_mismatch(tmp_path):
    source = _fixture(tmp_path, wrong_hash=True)
    result = _run(source)
    assert result.returncode != 0
    assert "bundled image SHA-256 不符" in result.stderr


def test_asset_provenance_rejects_uncommitted_binary(tmp_path):
    source = _fixture(tmp_path, committed=False)
    result = _run(source)
    assert result.returncode != 0
    assert "replacement binary 尚未標記為 committed" in result.stderr
