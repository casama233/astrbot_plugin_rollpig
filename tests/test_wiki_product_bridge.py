from __future__ import annotations

from pathlib import Path

from wiki_links import (
    WIKI_ADMIN_UI_HELP_URL,
    WIKI_ADMIN_URL,
    WIKI_BASE_URL,
    WIKI_CREATOR_URL,
    WIKI_HOME_URL,
    WIKI_PLAYER_URL,
    WIKI_RESOURCE_SYNC_HELP_URL,
    WIKI_TROUBLESHOOTING_URL,
)


ROOT = Path(__file__).resolve().parents[1]


def test_public_wiki_routes_share_one_canonical_base():
    assert WIKI_BASE_URL == "https://casama233.github.io/astrbot_plugin_rollpig/"
    assert WIKI_HOME_URL == WIKI_BASE_URL
    assert WIKI_PLAYER_URL == f"{WIKI_BASE_URL}gameplay/"
    assert WIKI_ADMIN_URL == f"{WIKI_BASE_URL}CONFIGURATION/"
    assert WIKI_CREATOR_URL == f"{WIKI_BASE_URL}creators/"
    assert WIKI_TROUBLESHOOTING_URL == f"{WIKI_BASE_URL}troubleshooting/"
    assert WIKI_RESOURCE_SYNC_HELP_URL.endswith(
        "/troubleshooting/admin/#resource-sync"
    )
    assert WIKI_ADMIN_UI_HELP_URL.endswith("/troubleshooting/admin/#admin-ui")


def test_mkdocs_and_admin_ui_use_the_same_wiki_origin():
    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages" / "pig-manager" / "ui-bootstrap.js").read_text(
        encoding="utf-8"
    )

    assert f"site_url: {WIKI_BASE_URL}" in mkdocs
    assert f"const WIKI_BASE_URL = '{WIKI_BASE_URL}';" in bootstrap
    for label in ("玩家 Wiki", "管理员手册", "投稿指南"):
        assert label in bootstrap
    for anchor in ("#resource-sync", "#admin-ui"):
        assert anchor in bootstrap


def test_admin_troubleshooting_page_exposes_stable_deep_link_anchors():
    source = (ROOT / "docs" / "troubleshooting" / "admin.md").read_text(
        encoding="utf-8"
    )
    assert "{: #resource-sync }" in source
    assert "{: #admin-ui }" in source


def test_dynamic_help_links_to_wiki_and_invalidates_old_cached_card():
    feature = (ROOT / "help_feature.py").read_text(encoding="utf-8")
    renderer = (ROOT / "renderers" / "help.py").read_text(encoding="utf-8")

    assert "HELP_RENDER_CACHE_VERSION = 3" in feature
    assert "WIKI_HOME_URL" in feature
    assert "WIKI_TROUBLESHOOTING_URL" in feature
    assert "WIKI_HOME_URL" in renderer
    assert "完整玩法 · 管理 · 投稿 · 排障" in renderer
