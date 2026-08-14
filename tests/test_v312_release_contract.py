from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v340_release_contract_is_readable_lazy_and_versioned():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")
    page = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    css = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    assert 'version: "3.5.0"' in metadata
    assert "AstrBot-RollPig/3.5.0" in main
    assert "AstrBot-RollPig-Safe-Updater/3.5.0" in updater
    assert "analyticsLoadBtn" in bootstrap
    assert "sessionStorage" not in bootstrap
    assert "v3.1.2 readable typography override" in css
    assert "同步任务已启动；已关闭自动轮询" in page
    assert '.github/release-v${VERSION}.md' in release_workflow
    assert '--notes-file "$notes_file"' in release_workflow


def test_release_packages_ship_title_font_and_keep_cjk_fallback():
    entrypoint = (ROOT / "main.py").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github/workflows/release.yml").read_text(
        encoding="utf-8"
    )
    marketplace_workflow = (
        ROOT / ".github/workflows/marketplace-package.yml"
    ).read_text(encoding="utf-8")

    preferred_font = "resource/font/荆南麦圆体.otf"
    excluded_preferred_font = f"--exclude '{preferred_font}'"

    assert (ROOT / preferred_font).is_file()
    assert excluded_preferred_font not in release_workflow
    assert excluded_preferred_font not in marketplace_workflow
    assert f'test -f "dist/$PLUGIN_NAME/{preferred_font}"' in release_workflow
    assert f'test -f "dist/$plugin_name/{preferred_font}"' in marketplace_workflow

    preferred_index = entrypoint.index('self.font_dir / "荆南麦圆体.otf"')
    bundled_fallback_index = entrypoint.index('self.font_dir / "可爱字体.ttf"')
    dejavu_index = entrypoint.index(
        '"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"'
    )
    assert preferred_index < bundled_fallback_index < dejavu_index
