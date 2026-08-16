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


def test_v391_changelog_is_current_and_unreleased_is_clean():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v3.9.1 (2026-08-17)" in changelog
    assert "## v3.9.0" in changelog
    assert "## v3.8.1" in changelog
    assert "## v3.7.0" in changelog
    head = changelog.split("## v3.9.1", 1)[0]
    assert "## 未發佈" in head
    assert "- 暫無。" in head
