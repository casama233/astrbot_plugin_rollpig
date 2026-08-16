from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v390_release_notes_remain_available_as_history():
    notes = ROOT / ".github" / "release-v3.9.0.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")
    assert "v3.9.0" in text
    assert "EX 1–5" in text
    assert "#127" in text
    assert "#128" in text
    assert "#124" in text
    assert "Wiki" in text
