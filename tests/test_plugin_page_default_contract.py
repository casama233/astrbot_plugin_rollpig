from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES_ROOT = ROOT / "pages"


def _discovered_page_names() -> list[str]:
    # AstrBot discovers first-level page directories sorted by lowercase name,
    # then its sidebar opens pages[0] as the plugin's default Page.
    return sorted(
        (
            item.name
            for item in PAGES_ROOT.iterdir()
            if item.is_dir() and (item / "index.html").is_file()
        ),
        key=str.lower,
    )


def test_pig_manager_stays_the_default_astrbot_plugin_page():
    pages = _discovered_page_names()
    assert pages == [
        "pig-manager",
        "pig-manager-ex",
        "pig-manager-ex-public-source",
    ]
    assert pages[0] == "pig-manager"


def test_plugin_page_i18n_tracks_the_stable_page_names():
    for locale in ("zh-CN", "zh-TW"):
        payload = json.loads(
            (ROOT / ".astrbot-plugin" / "i18n" / f"{locale}.json").read_text(
                encoding="utf-8"
            )
        )
        pages = payload["pages"]
        assert set(pages) == {
            "pig-manager",
            "pig-manager-ex",
            "pig-manager-ex-public-source",
        }
        assert "管理" in pages["pig-manager"]["title"]
        assert pages["pig-manager-ex"]["title"].startswith("EX ")
