from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.5"
PAGE = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(encoding="utf-8")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.scripts: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "script":
            self.scripts.append(values)


def test_admin_page_stays_lightweight_and_keeps_all_internal_views():
    assert len(PAGE.encode("utf-8")) < 300_000
    assert "rollpig-inline-assets:start" not in PAGE
    assert "data-rollpig-analytics-ui" not in PAGE
    parser = PageParser()
    parser.feed(PAGE)
    for element_id in (
        "view-overview",
        "view-catalog",
        "refreshBtn",
        "storageStatus",
        "updateStatus",
        "pigGrid",
    ):
        assert element_id in parser.ids


def test_external_enhancement_loader_cannot_block_the_main_module():
    loader = f'<script src="./ui-feedback.js?v={VERSION}"></script>'
    assert loader in PAGE
    assert PAGE.index(loader) < PAGE.index('<script type="module">')
    assert "const bridge=window.AstrBotPluginPage" in PAGE
    assert "loadOverview" in PAGE
    assert "loadPigs" in PAGE


def test_loader_versions_maintenance_assets():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
    for asset in (
        "enterprise-theme.css",
        "analytics-theme.css",
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert asset in LOADER


def test_main_module_is_extractable_for_node_syntax_validation():
    match = re.search(r'<script type="module">(.*?)</script>', PAGE, re.S)
    assert match and match.group(1).strip()
