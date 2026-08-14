#!/usr/bin/env python3
"""Atomically restore the frozen pre-v3.4 compatibility floor to a live source.

This is an operations migration for the canonical public-source catalog.  It
never overwrites current AstrBot metadata/images for an existing ID; it only
fills IDs that were lost during the v3.4 source cut-over, builds a fully
validated immutable release, backs up the previous canonical catalog, and then
atomically swings the public ``v1`` symlink.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from build_resource_source import build_source
from prepare_resource_catalog import merge_catalog


def migrate(
    catalog_root: Path,
    compatibility_root: Path,
    publish_root: Path,
    resource_version: str,
    *,
    dry_run: bool = False,
) -> dict:
    catalog_root = catalog_root.resolve()
    compatibility_root = compatibility_root.resolve()
    publish_root = publish_root.resolve()
    if not catalog_root.is_dir():
        raise ValueError(f"canonical catalog 不存在：{catalog_root}")
    if not compatibility_root.is_dir():
        raise ValueError(f"固定兼容快照不存在：{compatibility_root}")

    parent = catalog_root.parent
    candidate = Path(tempfile.mkdtemp(prefix=".compat-candidate-", dir=parent))
    shutil.rmtree(candidate)
    backup: Path | None = None
    release = publish_root / "releases" / resource_version
    if release.exists() or release.is_symlink():
        raise FileExistsError(f"不可變 release 已存在：{release}")

    try:
        summary = merge_catalog(catalog_root, compatibility_root, candidate)
        if dry_run:
            summary = {**summary, "dry_run": True, "resource_version": resource_version}
            return summary

        release.parent.mkdir(parents=True, exist_ok=True)
        manifest = build_source(candidate, release, resource_version)

        backup_root = publish_root / "catalog-backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / f"{resource_version}-pre-compat-{uuid.uuid4().hex[:8]}"
        catalog_root.rename(backup)
        try:
            candidate.rename(catalog_root)
            link = publish_root / f".v1.{uuid.uuid4().hex}.tmp"
            os.symlink(f"releases/{resource_version}", link)
            os.replace(link, publish_root / "v1")
        except Exception:
            failed = backup_root / f"failed-{resource_version}-{uuid.uuid4().hex[:8]}"
            if catalog_root.exists():
                catalog_root.rename(failed)
            backup.rename(catalog_root)
            if release.exists():
                shutil.rmtree(release, ignore_errors=True)
            raise

        return {
            **summary,
            "dry_run": False,
            "resource_version": resource_version,
            "published_pig_count": int(manifest["pig_count"]),
            "backup": str(backup),
            "release": str(release),
        }
    finally:
        if candidate.exists():
            shutil.rmtree(candidate, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--compat-root", type=Path, required=True)
    parser.add_argument("--publish-root", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = migrate(
        args.catalog_root,
        args.compat_root,
        args.publish_root,
        args.version,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
