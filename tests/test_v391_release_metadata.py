from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_v391_metadata_declares_current_stable_version():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    assert re.search(r'^version:\s*"3\.9\.1"\s*$', metadata, re.MULTILINE)


def test_v391_release_notes_cover_maintenance_fixes():
    notes = ROOT / ".github" / "release-v3.9.1.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "v3.9.1" in text
    assert "#131" in text
    assert "#132" in text
    assert "簡體中文" in text
    assert "sparkline" in text
    assert "CHANGELOG.md" in text


def test_v391_changelog_history_is_retained_with_unreleased_section():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v3.9.1 (2026-08-17)" in changelog
    assert "## v3.9.0" in changelog
    assert "## v3.8.1" in changelog
    assert "## v3.7.0" in changelog
    head = changelog.split("## v3.9.1", 1)[0]
    assert "## 未發佈" in head
    # Post-release PRs must be allowed to accumulate real unreleased entries.
    # The maintenance contract separately rejects a PR that fails to add one.
    assert head.strip() != "# 更新\n\n## 未發佈\n\n- 暫無。"
