from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ACTION_REF = re.compile(
    r"(?m)^\s*uses:\s*actions/[A-Za-z0-9_.-]+@([^\s#]+)"
)


def read_workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_all_official_actions_use_full_commit_revisions() -> None:
    revisions = [
        revision
        for path in WORKFLOWS.glob("*.yml")
        for revision in ACTION_REF.findall(path.read_text(encoding="utf-8"))
    ]
    assert revisions
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in revisions)


def test_release_follows_successful_main_ci_only() -> None:
    source = read_workflow("release.yml")
    assert "workflow_run:" in source
    assert "conclusion == 'success'" in source
    assert "head_branch == 'main'" in source
    assert "head_repository.full_name == github.repository" in source
    assert "\n  push:\n" not in source


def test_release_uses_the_tested_revision() -> None:
    source = read_workflow("release.yml")
    assert "github.event.workflow_run.head_sha" in source
    assert "needs.gate.outputs.tested_sha" in source
    assert "git rev-parse origin/main" in source
    assert "TESTED_SHA" in source
    assert "grep -Fxq metadata.yaml" in source


def test_ci_pins_python_and_node_versions() -> None:
    source = read_workflow("ci.yml")
    assert 'python-version: "3.12"' in source
    assert 'node-version: "22"' in source
