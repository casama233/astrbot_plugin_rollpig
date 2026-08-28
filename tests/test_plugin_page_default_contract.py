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


def test_pig_manager_is_the_only_astrbot_plugin_page():
    pages = _discovered_page_names()
    assert pages == ["pig-manager"]


def test_plugin_page_i18n_tracks_the_stable_page_names():
    for locale in ("zh-CN", "zh-TW"):
        payload = json.loads(
            (ROOT / ".astrbot-plugin" / "i18n" / f"{locale}.json").read_text(
                encoding="utf-8"
            )
        )
        pages = payload["pages"]
        assert set(pages) == {"pig-manager"}
        assert "管理" in pages["pig-manager"]["title"]


def test_retired_admin_surfaces_are_absent_from_the_release_tree():
    retired = (
        ROOT / "pig_studio_admin.py",
        ROOT / "pig_studio_feature.py",
        PAGES_ROOT / "pig-manager" / "studio-integration.js",
        PAGES_ROOT / "pig-manager-ex" / "index.html",
        PAGES_ROOT / "pig-manager-ex-public-source" / "index.html",
    )
    assert all(not path.exists() for path in retired)

    main = (ROOT / "main.py").read_text(encoding="utf-8")
    page = (PAGES_ROOT / "pig-manager" / "index.html").read_text(encoding="utf-8")
    bootstrap = (PAGES_ROOT / "pig-manager" / "ui-bootstrap.js").read_text(
        encoding="utf-8"
    )
    assert "PigStudioMixin" not in main
    assert "PigStudioAdminMixin" not in main
    assert "studio-integration.js" not in page
    assert "studio-integration.js" not in bootstrap
