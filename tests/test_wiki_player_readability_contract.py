from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


PLAYER_ENTRY_PAGES = {
    "homepage": DOCS / "index.md",
    "quick-start": DOCS / "getting-started" / "index.md",
    "gameplay-map": DOCS / "gameplay" / "index.md",
}

# Entry pages should route readers to precise pages instead of duplicating whole
# rulebooks. These ceilings are intentionally generous enough for useful UI copy.
MAX_CHARACTERS = {
    "homepage": 7000,
    "quick-start": 5000,
    "gameplay-map": 6000,
}

PLAYER_JARGON = (
    "Gameplay Event",
    "domain write",
    "lazy migration",
    "fail-closed",
    "authority",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_player_entry_pages_stay_short_and_progressive():
    for name, path in PLAYER_ENTRY_PAGES.items():
        text = _text(path)
        assert len(text) <= MAX_CHARACTERS[name], (
            f"{path} grew to {len(text)} characters; move precise rules to the "
            "linked gameplay/technical page instead of expanding the entry page"
        )


def test_player_entry_pages_do_not_leak_backend_jargon():
    for path in PLAYER_ENTRY_PAGES.values():
        text = _text(path)
        for term in PLAYER_JARGON:
            assert term not in text, f"{path} should explain {term!r} in player language"


def test_quick_start_keeps_the_minimum_three_command_path():
    text = _text(PLAYER_ENTRY_PAGES["quick-start"])
    for command in ("/今日小豬", "/我的豬圈", "/豬豬幫助"):
        assert command in text


def test_troubleshooting_uses_canonical_firewood_and_documents_at_view_gate():
    text = _text(DOCS / "troubleshooting" / "index.md")
    assert "at_view_pig = true" in text
    assert "## `/添柴`" in text
    assert "## `/添煤`" not in text
    assert "/添煤" in text  # compatibility alias remains searchable
