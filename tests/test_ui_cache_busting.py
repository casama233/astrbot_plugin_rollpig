from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.1.1"


def test_management_ui_version_is_consistent_without_source_cache():
    page = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")
    analytics = (ROOT / "pages/pig-manager/ui-analytics.js").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert f'data-rollpig-bootstrap="{VERSION}"' in page
    assert f"const VERSION = '{VERSION}'" in bootstrap
    assert f"const VERSION = '{VERSION}'" in analytics
    assert f'UI_ASSET_VERSION = "{VERSION}"' in main
    assert "sessionStorage" not in bootstrap
