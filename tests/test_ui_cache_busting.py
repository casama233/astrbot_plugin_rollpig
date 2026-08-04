from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.3"
PAGE = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
    encoding="utf-8"
)
LOADER = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(
    encoding="utf-8"
)


def test_versioned_loader_precedes_inline_module():
    external = f'<script src="./ui-feedback.js?v={VERSION}"></script>'
    assert external in PAGE
    assert PAGE.index(external) < PAGE.index('<script type="module">')


def test_loader_versions_every_enterprise_asset():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
    assert "stylesheet.href = versioned(href)" in LOADER
    assert "script.src = versioned(src)" in LOADER
    for asset in (
        "enterprise-theme.css",
        "analytics-theme.css",
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert asset in LOADER
    for asset in (
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert f"{asset}?v={VERSION}" in LOADER
