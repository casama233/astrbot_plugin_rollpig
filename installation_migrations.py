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
)

# Never delete a legacy Page unless its replacement actually exists in the
# installed release. This makes the migration fail-safe if an incomplete package
# is ever loaded.
LEGACY_PAGE_REPLACEMENTS: dict[str, str] = {
    "ex-manager": "pig-manager-ex",
    "ex-public-source": "pig-manager-ex-public-source",
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

        # The current tombstones are Plugin Pages. Require the renamed Page to
        # be present before deleting the legacy path so an incomplete install
        # cannot accidentally remove the only working management surface.
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
                    f"检测到旧 Plugin Page {legacy}，但新版替代页面不存在；为避免误删已跳过迁移。",
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
                    f"旧 Plugin Page 目录无法完整删除（{exc}），已停用其 index.html：{legacy}",
                )
                continue
            _log(
                logger,
                "error",
                f"无法清理旧 RollPig 安装路径 {legacy}：{exc}。请检查插件目录权限。",
            )

    if removed:
        _log(
            logger,
            "info",
            "已清理 RollPig 旧版残留路径：" + ", ".join(removed),
        )
    return removed
