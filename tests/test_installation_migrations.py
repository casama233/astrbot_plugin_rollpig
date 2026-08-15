from __future__ import annotations

from pathlib import Path

import installation_migrations
from installation_migrations import cleanup_legacy_installation_paths
from updater import PluginUpdateManager


ROOT = Path(__file__).resolve().parents[1]


def _write_page(root: Path, name: str, text: str = "page") -> Path:
    page = root / "pages" / name
    page.mkdir(parents=True, exist_ok=True)
    (page / "index.html").write_text(text, encoding="utf-8")
    return page


def _discover_pages(root: Path) -> list[str]:
    pages_root = root / "pages"
    return sorted(
        (
            page.name
            for page in pages_root.iterdir()
            if page.is_dir() and (page / "index.html").is_file()
        ),
        key=str.lower,
    )


def test_overlay_upgrade_legacy_pages_are_removed_and_pig_manager_is_default(tmp_path):
    # Reproduce the real upgrade shape: old release files remain on disk while
    # the new release merely overlays the renamed Page directories.
    _write_page(tmp_path, "ex-manager", "legacy EX manager")
    _write_page(tmp_path, "ex-public-source", "legacy EX source")
    _write_page(tmp_path, "pig-manager", "main manager")
    _write_page(tmp_path, "pig-manager-ex", "new EX manager")
    _write_page(tmp_path, "pig-manager-ex-public-source", "new EX source")

    assert _discover_pages(tmp_path)[0] == "ex-manager"

    removed = cleanup_legacy_installation_paths(tmp_path)

    assert removed == ["pages/ex-manager", "pages/ex-public-source"]
    assert _discover_pages(tmp_path) == [
        "pig-manager",
        "pig-manager-ex",
        "pig-manager-ex-public-source",
    ]
    assert not (tmp_path / "pages" / "ex-manager").exists()
    assert not (tmp_path / "pages" / "ex-public-source").exists()


def test_real_self_updater_overlay_converges_after_startup_migration(tmp_path):
    plugin = tmp_path / "plugin"
    data = tmp_path / "data"
    staging = tmp_path / "staging"
    backup = tmp_path / "backup"
    plugin.mkdir()
    data.mkdir()
    staging.mkdir()
    backup.mkdir()

    # Old installation before #109.
    _write_page(plugin, "ex-manager", "legacy EX manager")
    _write_page(plugin, "ex-public-source", "legacy EX source")
    _write_page(plugin, "pig-manager", "main manager")

    # New release payload after #109. The historical updater overlays these
    # paths but does not itself remove names absent from the archive.
    _write_page(staging, "pig-manager", "main manager v2")
    _write_page(staging, "pig-manager-ex", "new EX manager")
    _write_page(staging, "pig-manager-ex-public-source", "new EX source")

    manager = PluginUpdateManager(plugin, data)
    manager._overlay_install(staging, backup)
    assert _discover_pages(plugin)[0] == "ex-manager"

    cleanup_legacy_installation_paths(plugin)

    assert _discover_pages(plugin) == [
        "pig-manager",
        "pig-manager-ex",
        "pig-manager-ex-public-source",
    ]


def test_cleanup_does_not_touch_unrelated_or_user_owned_pages(tmp_path):
    _write_page(tmp_path, "pig-manager")
    _write_page(tmp_path, "pig-manager-ex")
    _write_page(tmp_path, "pig-manager-ex-public-source")
    _write_page(tmp_path, "my-local-tool")

    cleanup_legacy_installation_paths(tmp_path)

    assert (tmp_path / "pages" / "my-local-tool" / "index.html").is_file()


def test_cleanup_requires_replacement_page_before_removing_legacy_page(tmp_path):
    legacy = _write_page(tmp_path, "ex-manager")

    removed = cleanup_legacy_installation_paths(tmp_path)

    assert removed == []
    assert (legacy / "index.html").is_file()


def test_cleanup_neutralizes_legacy_page_when_directory_removal_fails(
    tmp_path, monkeypatch
):
    legacy = _write_page(tmp_path, "ex-manager")
    _write_page(tmp_path, "pig-manager-ex")

    def fail_rmtree(_path):
        raise OSError("simulated directory permission failure")

    monkeypatch.setattr(installation_migrations.shutil, "rmtree", fail_rmtree)

    removed = cleanup_legacy_installation_paths(tmp_path)

    assert removed == ["pages/ex-manager (disabled)"]
    assert legacy.is_dir()
    assert not (legacy / "index.html").exists()
    assert (legacy / "index.html.rollpig-legacy-disabled").is_file()
    assert "ex-manager" not in _discover_pages(tmp_path)


def test_cleanup_is_idempotent(tmp_path):
    _write_page(tmp_path, "ex-manager")
    _write_page(tmp_path, "pig-manager-ex")

    assert cleanup_legacy_installation_paths(tmp_path) == ["pages/ex-manager"]
    assert cleanup_legacy_installation_paths(tmp_path) == []


def test_star_entry_runs_installation_cleanup_before_base_initialization():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    init_block = source.split("    def __init__(self, context, config):", 1)[1].split(
        "    def _save_daily_report_state_locked", 1
    )[0]

    cleanup_pos = init_block.index("cleanup_legacy_installation_paths(")
    super_pos = init_block.index("super().__init__(context, config)")
    assert cleanup_pos < super_pos
