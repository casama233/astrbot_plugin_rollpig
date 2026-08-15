from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_v372_metadata_declares_current_stable_version():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    assert re.search(r'^version:\s*"3\.7\.2"\s*$', metadata, re.MULTILINE)


def test_v372_release_notes_are_present():
    notes = ROOT / ".github" / "release-v3.7.2.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "v3.7.2" in text
    assert "今日小豬" in text
