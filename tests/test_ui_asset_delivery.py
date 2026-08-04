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


def test_ui_asset_endpoint_is_read_only_and_uses_a_fixed_whitelist():
    builder = ast.get_source_segment(MAIN, method("_build_ui_asset_bundle")) or ""
    endpoint = ast.get_source_segment(MAIN, method("page_ui_assets")) or ""
    assert "self.UI_ASSET_FILES" in builder
    assert ".resolve()" in builder
    assert "path.parent != root" in builder
    assert "UI_ASSET_MAX_FILE_BYTES" in builder
    assert "UI_ASSET_MAX_TOTAL_BYTES" in builder
    assert "asyncio.to_thread(self._build_ui_asset_bundle)" in endpoint
    assert len(method("page_ui_assets").args.args) == 1
    for filename in (
        "enterprise-theme.css", "analytics-theme.css", "ui-feedback-core.js",
        "ui-enterprise.js", "ui-analytics.js",
    ):
        assert filename in MAIN


def test_inline_bootstrap_matches_maintenance_source_and_has_failure_boundaries():
    match = re.search(r'<script data-rollpig-bootstrap="3.1.0">(.*?)</script>', PAGE, re.S)
    assert match and match.group(1).strip() == BOOTSTRAP.strip()
    for marker in (
        "uiEnhancementStatus", "reportModuleError", "sessionStorage",
        "checksum-mismatch", "核心数据总览、猪猪图鉴和管理操作不受影响",
        "bridge.apiGet('ui/assets'", "pageToken",
    ):
        assert marker in BOOTSTRAP
    assert 'src="./ui-' not in PAGE
    assert 'href="./enterprise-theme.css' not in PAGE
