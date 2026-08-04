from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.5"
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "pages/pig-manager/ui-feedback.js").read_text(encoding="utf-8")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids: set[str] = set()
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts += 1
        for key, value in attrs:
            if key == "id" and value:
                self.ids.add(value)


def test_admin_page_is_lightweight_parseable_and_keeps_core_views():
    parser = PageParser()
    parser.feed(PAGE)
    parser.close()
    assert len(PAGE.encode("utf-8")) < 500_000
    assert {"view-overview", "view-catalog", "refreshBtn", "storageStatus", "updateStatus"} <= parser.ids
    assert parser.scripts >= 2


def test_page_does_not_load_protected_relative_enhancement_assets():
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', PAGE)
    assert scripts == ["/api/plugin/page/bridge-sdk.js"]
    assert "rollpig-inline-assets:start" not in PAGE
    assert 'src="./ui-feedback.js' not in PAGE
    for asset in (
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
        "enterprise-theme.css",
        "analytics-theme.css",
    ):
        assert f'src="./{asset}' not in PAGE
        assert f'href="./{asset}' not in PAGE


def test_modular_enhancement_sources_remain_versioned_but_are_not_bootstrapped():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
