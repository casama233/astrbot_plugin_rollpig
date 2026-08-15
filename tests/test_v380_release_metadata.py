from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v380_release_notes_remain_available_as_history():
    notes = ROOT / ".github" / "release-v3.8.0.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "v3.8.0" in text
    assert "201 / 201" in text
    assert "/添柴" in text
    assert "Wiki" in text
