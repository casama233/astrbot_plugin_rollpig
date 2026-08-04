from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.4"
PAGE = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(encoding="utf-8")


def test_authenticated_plugin_page_uses_no_protected_asset_subrequests():
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', PAGE)
    assert scripts == ["/api/plugin/page/bridge-sdk.js"]
    assert 'src="./ui-feedback.js' not in PAGE
    assert 'href="./enterprise-theme.css' not in PAGE
    assert 'href="./analytics-theme.css' not in PAGE
    for asset in (
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert f'src="./{asset}' not in PAGE


def test_inline_bundle_is_versioned_ordered_and_matches_sources():
    markers = (
        "data-rollpig-enterprise-theme",
        "data-rollpig-analytics-theme",
        "data-rollpig-feedback-core",
        "data-rollpig-enterprise-ui",
        "data-rollpig-analytics-ui",
    )
    for marker in markers:
        assert marker in PAGE
    assert PAGE.count(f'data-version="{VERSION}"') == len(markers)
    assert PAGE.index('/api/plugin/page/bridge-sdk.js') < PAGE.index('data-rollpig-feedback-core')
    assert PAGE.index('data-rollpig-analytics-ui') < PAGE.index('<script type="module">')

    for source in (
        "enterprise-theme.css",
        "analytics-theme.css",
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        payload = (ROOT / "pages" / "pig-manager" / source).read_text(encoding="utf-8")
        if source.endswith(".js"):
            payload = payload.replace("</script", r"<\/script")
        assert payload in PAGE, source


def test_modular_loader_remains_versioned_for_maintenance_only():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
