from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MKDOCS = ROOT / "mkdocs.yml"


def test_wiki_is_dark_only_without_palette_toggle():
    source = MKDOCS.read_text(encoding="utf-8")

    assert "palette:\n    scheme: slate" in source
    assert "prefers-color-scheme: light" not in source
    assert "prefers-color-scheme: dark" not in source
    assert "scheme: default" not in source
    assert "toggle:" not in source
    assert "material/weather-night" not in source
    assert "material/weather-sunny" not in source
