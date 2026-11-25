from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


# RollPig's self-updater historically installs releases as an overlay. Paths that
# were intentionally removed or renamed therefore need an explicit tombstone so
# old installations converge to the current release layout after restart.
LEGACY_PATH_TOMBSTONES: tuple[tuple[str, ...], ...] = (
    ("pages", "ex-manager"),
    ("pages", "ex-public-source"),
    ("pages", "pig-manager-ex"),
    ("pages", "pig-manager-ex-public-source"),
    ("pages", "pig-manager", "studio-integration.js"),
    ("pig_studio_admin.py",),
    ("pig_studio_feature.py",),
    ("command_actor_feature.py",),
    ("message_layout.py",),
)

# Never delete a retired Page unless the canonical manager actually exists in
# the installed release. This makes the migration fail-safe if an incomplete
# package is ever loaded.
LEGACY_PAGE_REPLACEMENTS: dict[str, str] = {
    "ex-manager": "pig-manager",
    "ex-public-source": "pig-manager",
    "pig-manager-ex": "pig-manager",
    "pig-manager-ex-public-source": "pig-manager",
}


def _log(logger: Any, level: str, message: str) -> None:
    target = getattr(logger, level, None)
    if callable(target):
        target(message)


def _path_exists(path: Path) -> bool:
    """Return True for normal paths and broken symlinks without following them."""

    return os.path.lexists(path)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def _disable_plugin_page_entry(page_dir: Path) -> bool:
    """Best-effort fallback when a legacy Page directory cannot be removed.

    AstrBot only discovers first-level Page directories that contain
    ``index.html``. Renaming that exact entry file is enough to stop a stale Page
    from becoming ``pages[0]`` while leaving the rest of the directory untouched
    for manual inspection.
    """

    entry = page_dir / "index.html"
    if not _path_exists(entry):
        return True
    disabled = page_dir / "index.html.rollpig-legacy-disabled"
    try:
        os.replace(entry, disabled)
    except OSError:
        return False
    return True


def cleanup_legacy_installation_paths(
    plugin_root: Path | str,
    *,
    logger: Any = None,
) -> list[str]:
    """Remove known obsolete program paths left by historical overlay upgrades.

    Only explicit RollPig-owned tombstones are touched. User data and unrelated
    files are deliberately outside this migration boundary.
    """

    root = Path(plugin_root).resolve()
    removed: list[str] = []

    for parts in LEGACY_PATH_TOMBSTONES:
        legacy = root.joinpath(*parts)
        if not _path_exists(legacy):
            continue

        # First-level Page tombstones require the canonical manager to be
        # present, so an incomplete install cannot accidentally remove the only
        # working management surface. Nested assets and Python modules are
        # explicit RollPig-owned program paths and never include plugin_data.
        if len(parts) == 2 and parts[0] == "pages":
            replacement_name = LEGACY_PAGE_REPLACEMENTS.get(parts[1])
            replacement_entry = (
                root / "pages" / str(replacement_name) / "index.html"
                if replacement_name
                else None
            )
            if replacement_entry is None or not replacement_entry.is_file():
                _log(
                    logger,
                    "warning",
                    f'发现了旧版 Plugin Page {legacy}，但新版替代页面还没就位；怕误删文件，这次先不动它。',
                )
                continue

        try:
            _remove_path(legacy)
            removed.append("/".join(parts))
            continue
        except OSError as exc:
            # If directory removal is blocked, neutralize only index.html. This
            # is sufficient because AstrBot's Page discovery requires it.
            if len(parts) == 2 and parts[0] == "pages" and _disable_plugin_page_entry(legacy):
                removed.append("/".join(parts) + " (disabled)")
                _log(
                    logger,
                    "warning",
                    f'旧 Plugin Page 目录没能彻底清干净（{exc}），不过已经把它的 index.html 停用了：{legacy}',
                )
                continue
            _log(
                logger,
                "error",
                f'清理旧版 RollPig 残留路径 {legacy} 时受阻：{exc}。麻烦检查一下插件目录的读写权限。',
            )

    if removed:
        _log(
            logger,
            "info",
            '已顺利扫除 RollPig 旧版残留路径：' + ", ".join(removed),
        )
    return removed
