from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "pig-manager" / "index.html"


def page_text() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_main_manager_ex_entrypoints_are_visible():
    text = page_text()
    assert "EX 1–5" in text
    assert "管理 EX" in text
    assert "openExManager" in text
    assert "ex/variants" in text


def test_main_manager_ex_editor_supports_level_write_reset_and_image_preview():
    text = page_text()
    assert "ex/variants/save" in text
    assert "ex/variants/delete" in text
    assert "ex/variants/image" in text
    assert "EX Lv.${level}" in text
    assert "留空＝繼承" in text


def test_public_source_preview_has_actions_instead_of_close_only():
    text = page_text()
    assert "publicSourceExSummary" in text
    assert "publicSourceManageEx" in text
    assert "publicSourceEditLocal" in text
    assert "管理本地 EX" in text
    assert "編輯本地資料" in text


def test_ex_manager_is_responsive_and_not_a_hidden_standalone_only_flow():
    text = page_text()
    assert ".ex-manager-modal" in text
    assert ".ex-level-tabs" in text
    assert "@media(max-width:760px)" in text
