from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v381_release_notes_remain_available_as_history():
    notes = ROOT / ".github" / "release-v3.8.1.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "v3.8.1" in text
    assert "ex-manager" in text
    assert "pig-manager" in text
    assert "overlay" in text
    assert "#119" in text
