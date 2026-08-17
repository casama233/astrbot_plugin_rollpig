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
    assert 'version: "3.7.0"' in metadata
    assert "AstrBot-RollPig/3.6.5" in main
    assert "AstrBot-RollPig-Safe-Updater/" in updater
    assert "analyticsLoadBtn" in bootstrap
    assert "sessionStorage" not in bootstrap
    assert "v3.1.2 readable typography override" in css
    assert "同步任务已启动；已关闭自动轮询" in page
    assert '.github/release-v${VERSION}.md' in release_workflow
    assert '--notes-file "$notes_file"' in release_workflow


def test_release_packages_ship_round_cjk_font_and_use_it_before_dejavu():
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
    assert not (ROOT / "resource/font/可爱字体.ttf").exists()
    assert excluded_preferred_font not in release_workflow
    assert excluded_preferred_font not in marketplace_workflow
    assert f'test -f "dist/$PLUGIN_NAME/{preferred_font}"' in release_workflow
    assert f'test -f "dist/$plugin_name/{preferred_font}"' in marketplace_workflow

    regular_start = entrypoint.index("def _init_regular_font")
    bold_start = entrypoint.index("def _init_bold_font")
    regular_block = entrypoint[regular_start:bold_start]
    bold_block = entrypoint[bold_start:]

    assert regular_block.index('self.font_dir / "荆南麦圆体.otf"') < regular_block.index(
        '"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"'
    )
    assert bold_block.index('self.font_dir / "荆南麦圆体.otf"') < bold_block.index(
        '"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"'
    )
