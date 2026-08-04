from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v310_release_contract_uses_authenticated_progressive_enhancement():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    page = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")
    assert 'version: "3.1.0"' in metadata
    assert 'AstrBot-RollPig/3.1.0' in main
    assert 'AstrBot-RollPig-Safe-Updater/3.1.0' in updater
    assert '/analytics/insights' in main
    assert '/ui/assets' in main
    assert 'UI_ASSET_FILES' in main
    assert 'page_ui_assets' in main
    assert '<script data-rollpig-bootstrap="3.1.0">' in page
    assert 'src="./ui-feedback.js' not in page
    assert "bridge.apiGet('ui/assets'" in bootstrap
    assert "core data" not in bootstrap.lower()
