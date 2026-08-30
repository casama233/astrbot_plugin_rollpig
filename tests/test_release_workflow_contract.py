from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
RELEASE = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")


def _action_refs(text: str) -> list[str]:
    return re.findall(r"(?m)^\s*uses:\s*[^\s@]+@([^\s#]+)", text)


def test_official_actions_are_pinned_to_full_commit_shas():
    refs = _action_refs(CI) + _action_refs(RELEASE)
    assert refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs), refs


def test_ci_declares_deterministic_python_and_node_toolchains():
    assert "python-version: \"3.12\"" in CI
    assert "node-version: \"20\"" in CI
    assert "cache-dependency-path: requirements.txt" in CI
    assert "cache-dependency-path: package-lock.json" in CI


def test_release_is_driven_only_by_successful_main_push_ci():
    assert "workflow_run:" in RELEASE
    assert "- CI" in RELEASE
    assert "github.event.workflow_run.conclusion" in RELEASE
    assert "github.event.workflow_run.event" in RELEASE
    assert "github.event.workflow_run.head_branch" in RELEASE
    assert "== 'success'" in RELEASE
    assert "== 'push'" in RELEASE
    assert "== 'main'" in RELEASE
    assert "paths:\n      - metadata.yaml" not in RELEASE


def test_release_checks_out_and_publishes_the_tested_sha():
    assert "github.event.workflow_run.head_sha" in RELEASE
    assert "checked_out_sha=\"$(git rev-parse HEAD)\"" in RELEASE
    assert "refs/remotes/origin/main" in RELEASE
    assert "Skipping stale tested revision" in RELEASE
    assert "--target \"$TESTED_SHA\"" in RELEASE


def test_existing_stable_release_is_a_noop():
    assert "already exists; no release mutation is required" in RELEASE
    assert "gh release edit" not in RELEASE
