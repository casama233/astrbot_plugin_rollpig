from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")


def method(name: str):
    tree = ast.parse(MAIN)
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin")
    return next(node for node in plugin.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)


def test_ui_asset_endpoint_is_read_only_and_only_serves_analytics():
    builder = ast.get_source_segment(MAIN, method("_build_ui_asset_bundle")) or ""
    endpoint = ast.get_source_segment(MAIN, method("page_ui_assets")) or ""
    assert "self.UI_ASSET_FILES" in builder
    assert ".resolve()" in builder
    assert "path.parent != root" in builder
    assert "asyncio.to_thread(self._build_ui_asset_bundle)" in endpoint
    assert '("analytics-theme", "style", "analytics-theme.css")' in MAIN
    assert '("ui-analytics", "script", "ui-analytics.js")' in MAIN
    assert "enterprise-theme.css" not in MAIN
    assert "ui-feedback-core.js" not in MAIN
    assert "ui-enterprise.js" not in MAIN


def test_inline_bootstrap_matches_source_and_is_click_only():
    match = re.search(r'<script data-rollpig-bootstrap="3.1.2">(.*?)</script>', PAGE, re.S)
    assert match and match.group(1).strip() == BOOTSTRAP.strip()
    assert "analyticsLoadBtn" in BOOTSTRAP
    assert "button.addEventListener('click', load" in BOOTSTRAP
    assert "bridge.apiGet('ui/assets'" in BOOTSTRAP
    assert "sessionStorage" not in BOOTSTRAP
    assert "MutationObserver" not in BOOTSTRAP
    assert "setInterval" not in BOOTSTRAP
    assert "\n  load();\n" not in BOOTSTRAP
