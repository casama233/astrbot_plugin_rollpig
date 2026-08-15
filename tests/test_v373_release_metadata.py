from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v373_release_notes_remain_available_as_history():
    notes = ROOT / ".github" / "release-v3.7.3.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "v3.7.3" in text
    assert "今日小豬" in text
