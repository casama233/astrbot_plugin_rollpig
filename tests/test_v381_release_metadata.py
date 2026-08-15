from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_v381_metadata_declares_current_stable_version():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    assert re.search(r'^version:\s*"3\.8\.1"\s*$', metadata, re.MULTILINE)


def test_v381_release_notes_are_present():
    notes = ROOT / ".github" / "release-v3.8.1.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "v3.8.1" in text
    assert "ex-manager" in text
    assert "pig-manager" in text
    assert "overlay" in text
    assert "#119" in text
