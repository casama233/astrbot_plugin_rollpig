from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v305_release_contract_restores_admin_page_availability():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    loader = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(encoding="utf-8")
    assert 'version: "3.0.5"' in metadata
    assert 'AstrBot-RollPig/3.0.5' in main
    assert 'AstrBot-RollPig-Safe-Updater/3.0.5' in updater
    assert '/analytics/insights' in main
    assert '<script src="./ui-feedback.js?v=3.0.5"></script>' in page
    assert '<script type="module">' in page
    assert 'id="view-overview"' in page
    assert 'id="view-catalog"' in page
    assert "rollpig-inline-assets:start" not in page
    assert "const ASSET_VERSION = '3.0.5'" in loader
