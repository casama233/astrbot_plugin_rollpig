from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v330_release_contract_is_readable_lazy_and_versioned():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")
    page = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    css = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    assert 'version: "3.3.0"' in metadata
    assert "AstrBot-RollPig/3.3.0" in main
    assert "AstrBot-RollPig-Safe-Updater/3.3.0" in updater
    assert "analyticsLoadBtn" in bootstrap
    assert "sessionStorage" not in bootstrap
    assert "v3.1.2 readable typography override" in css
    assert "同步任务已启动；已关闭自动轮询" in page
    assert '.github/release-v${VERSION}.md' in release_workflow
    assert '--notes-file "$notes_file"' in release_workflow
