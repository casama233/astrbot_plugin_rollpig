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


def _fixture(
    root: Path,
    *,
    wrong_hash: bool = False,
    image_suffix: str = ".png",
    catalog_id: str = "test-pig",
) -> Path:
    source = root / "resource"
    image_root = source / "image"
    image_root.mkdir(parents=True)
    image = image_root / f"test-pig{image_suffix}"
    Image.new("RGBA", (8, 8), (255, 120, 160, 255)).save(image, format="PNG")
    replacement_sha = "0" * 64 if wrong_hash else _sha256(image)
    (source / "pig.json").write_text(
        json.dumps(
            [
                {
                    "id": catalog_id,
                    "name": "Test Pig",
                    "description": "Test description",
                    "analysis": "Test analysis",
                }
            ]
        ),
        encoding="utf-8",
    )
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


def _manifest(root: Path, filenames: list[str]) -> Path:
    path = root / "manifest.json"
    path.write_text(
        json.dumps({"images": [{"filename": name} for name in filenames]}),
        encoding="utf-8",
    )
    return path


def _run(
    source: Path,
    output: Path | None = None,
    artifact_manifest: Path | None = None,
    git_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(CHECKER), "--source", str(source)]
    if output is not None:
        command += ["--output", str(output)]
    if artifact_manifest is not None:
        command += ["--artifact-manifest", str(artifact_manifest)]
    if git_root is not None:
        command += ["--git-root", str(git_root)]
    return subprocess.run(command, capture_output=True, text=True)


def _init_git_repo(root: Path, *, include_image: bool = True) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    paths = ["resource/pig.json", "resource/asset_provenance.json"]
    if include_image:
        paths.append("resource/image/test-pig.png")
    subprocess.run(["git", "add", "--", *paths], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-q",
            "-m",
            "fixture",
        ],
        cwd=root,
        check=True,
    )


def test_asset_provenance_accepts_exact_replacement_hash_and_publishes(tmp_path):
    source = _fixture(tmp_path)
    output = tmp_path / "dist" / "asset_provenance.json"
    manifest = _manifest(tmp_path, ["test-pig.png"])
    _init_git_repo(tmp_path)
    result = _run(source, output, manifest, tmp_path)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["approved_asset_count"] == 1
    assert summary["withheld_asset_count"] == 1
    published = json.loads(output.read_text(encoding="utf-8"))
    assert published["assets"]["test-pig"]["redistribution_allowed"] is True
    assert "binary_committed" not in published["assets"]["test-pig"]
    assert published["withheld"]["unknown-pig"]["redistribution_allowed"] is False


def test_asset_provenance_rejects_replacement_hash_mismatch(tmp_path):
    source = _fixture(tmp_path, wrong_hash=True)
    result = _run(source)
    assert result.returncode != 0
    assert "bundled image SHA-256 不符" in result.stderr


def test_asset_provenance_rejects_untracked_binary(tmp_path):
    source = _fixture(tmp_path)
    _init_git_repo(tmp_path, include_image=False)
    result = _run(source, git_root=tmp_path)
    assert result.returncode != 0
    assert "approved replacement image 未被 Git 追蹤" in result.stderr


def test_asset_provenance_accepts_mixed_case_image_extension(tmp_path):
    source = _fixture(tmp_path, image_suffix=".PnG")
    result = _run(source)
    assert result.returncode == 0, result.stderr


def test_asset_provenance_rejects_approved_id_outside_catalog(tmp_path):
    source = _fixture(tmp_path, catalog_id="different-pig")
    result = _run(source)
    assert result.returncode != 0
    assert "approved provenance ID 不在 pig.json" in result.stderr


def test_asset_provenance_rejects_approved_image_missing_from_artifact(tmp_path):
    source = _fixture(tmp_path)
    manifest = _manifest(tmp_path, [])
    result = _run(source, artifact_manifest=manifest)
    assert result.returncode != 0
    assert "approved provenance 圖片未出現在生成 artifact" in result.stderr
