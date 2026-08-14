from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_source_browser_has_authenticated_catalog_and_image_proxy():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    assert 'f"/{self.PLUGIN_NAME}/source/catalog"' in source
    assert 'f"/{self.PLUGIN_NAME}/source/catalog/image"' in source
    assert "self.OFFICIAL_RESOURCE_MANIFEST_URL" in source
    assert "_official_public_source_snapshot" in source
    assert 'for key in ("id", "name", "description", "analysis")' in source
    assert "_download_manifest_item" in source
    assert "_is_authorized_write_request(request)" in source


def test_public_source_browser_is_pighub_like_searchable_preview_ui():
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    for marker in (
        'id="publicSourceBrowseBtn"',
        'id="publicSourceModal"',
        'id="publicSourceSearch"',
        'id="publicSourceGrid"',
        'id="publicSourcePrev"',
        'id="publicSourceNext"',
        'id="publicSourceDetailModal"',
    ):
        assert marker in page
    assert "source/catalog',{search:publicSourceSearch" in page
    assert "source/catalog/image',{id:pigId,__rollpig_csrf:csrfToken}" in page
    assert "data-public-source-match" in page
    assert "查看现有猪" in page
