from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v303_release_contract_and_analytics_assets():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    storage = (ROOT / "storage" / "sqlite_storage.py").read_text(
        encoding="utf-8"
    )
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
        encoding="utf-8"
    )
    loader = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(
        encoding="utf-8"
    )
    assert 'version: "3.0.3"' in metadata
    assert 'AstrBot-RollPig/3.0.3' in main
    assert 'AstrBot-RollPig-Safe-Updater/3.0.3' in updater
    assert '/analytics/insights' in main
    assert 'get_dashboard_insights' in storage
    assert 'schema_version = 5' in storage
    assert 'sql-primary-v2.14' in storage
    assert './ui-feedback.js?v=3.0.3' in page
    assert "const ASSET_VERSION = '3.0.3'" in loader
    assert './analytics-theme.css' in loader
    assert './ui-analytics.js' in loader
