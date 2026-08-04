from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1.0"
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8").strip()
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
    assert len(PAGE.encode("utf-8")) < 550_000
    assert {"view-overview", "view-catalog", "refreshBtn", "storageStatus", "updateStatus"} <= parser.ids
    assert parser.scripts >= 3


def test_page_uses_only_bridge_as_external_script_and_inlines_the_small_bootstrap():
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', PAGE)
    assert scripts == ["/api/plugin/page/bridge-sdk.js"]
    assert "rollpig-inline-assets:start" not in PAGE
    assert 'src="./ui-feedback.js' not in PAGE
    match = re.search(r'<script data-rollpig-bootstrap="3.1.0">(.*?)</script>', PAGE, re.S)
    assert match and match.group(1).strip() == BOOTSTRAP
    assert len(BOOTSTRAP.encode("utf-8")) < 20_000
    assert "bridge.apiGet('ui/assets'" in BOOTSTRAP


def test_modular_sources_are_versioned_and_delivered_by_authenticated_api():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
    assert "ui/assets" in (ROOT / "main.py").read_text(encoding="utf-8")
    for asset in (
        "ui-feedback-core.js", "ui-enterprise.js", "ui-analytics.js",
        "enterprise-theme.css", "analytics-theme.css",
    ):
        assert asset in (ROOT / "main.py").read_text(encoding="utf-8")
