"""Validated image staging and directory promotion, independent of AstrBot state."""

from __future__ import annotations

import asyncio
import re
import shutil
from collections.abc import Awaitable, Callable, Collection
from pathlib import Path


async def _write_bytes(path: Path, data: bytes) -> None:
    # A cancelled to_thread await does not stop the filesystem write. Drain it
    # before allowing the caller to remove staging or close its HTTP client.
    task = asyncio.create_task(asyncio.to_thread(path.write_bytes, data))
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


async def stage_resource_images(
    *,
    image_metas: list,
    variant_image_metas: list,
    pig_ids: set[str],
    normalized_ex: dict,
    has_ex_catalog: bool,
    staging_images: Path,
    staging_variants: Path,
    image_extensions: Collection[str],
    initial_size: int,
    max_package_size: int,
    download: Callable[[dict], Awaitable[bytes]],
    validate_image: Callable[[bytes, str], None],
) -> None:
    """Download within a shared budget; return only after every task has stopped."""
    # 公共包接近两百张图；较低并发对慢速反代和家庭网络更稳定。
    semaphore = asyncio.Semaphore(4)
    budget_lock = asyncio.Lock()
    package_total = initial_size
    if package_total > max_package_size:
        raise ValueError("云资源包总大小超过 128 MiB")

    async def fetch_base_image(meta):
        nonlocal package_total
        if not isinstance(meta, dict):
            raise ValueError("manifest 图片条目无效")
        filename = str(meta.get("filename") or "")
        if (
            Path(filename).name != filename
            or Path(filename).suffix.lower().lstrip(".")
            not in image_extensions
            or not re.fullmatch(
                r"[a-z0-9][a-z0-9_-]{0,63}",
                Path(filename).stem,
            )
        ):
            raise ValueError(f"图片文件名无效：{filename}")
        async with semaphore:
            data = await download(meta)
        async with budget_lock:
            package_total += len(data)
            if package_total > max_package_size:
                raise ValueError("云资源包总大小超过 128 MiB")
        return filename, data

    async def fetch_variant_image(meta):
        nonlocal package_total
        if not isinstance(meta, dict):
            raise ValueError("manifest EX 差分图片条目无效")
        filename = str(meta.get("filename") or "")
        if (
            Path(filename).name != filename
            or Path(filename).suffix.lower().lstrip(".")
            not in image_extensions
            or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", filename
            )
        ):
            raise ValueError(f"EX 差分图片文件名无效：{filename}")
        async with semaphore:
            data = await download(meta)
        async with budget_lock:
            package_total += len(data)
            if package_total > max_package_size:
                raise ValueError("云资源包总大小超过 128 MiB")
        return filename, data

    async def fetch_and_store_base(meta):
        filename, data = await fetch_base_image(meta)
        validate_image(data, filename)
        await _write_bytes(staging_images / filename, data)
        return filename

    async def fetch_and_store_variant(meta):
        filename, data = await fetch_variant_image(meta)
        validate_image(data, filename)
        await _write_bytes(staging_variants / filename, data)
        return filename

    tasks = [
        asyncio.create_task(fetch_and_store_base(meta))
        for meta in image_metas
    ]
    filenames: list[str] = []
    try:
        for task in asyncio.as_completed(tasks):
            filenames.append(await task)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    if len(filenames) != len(set(filenames)):
        raise ValueError("云资源 manifest 存在重复图片文件名")
    image_ids = {Path(name).stem for name in filenames}
    missing = pig_ids.difference(image_ids)
    if missing:
        raise ValueError(
            f"云资源缺少图片：{', '.join(sorted(missing)[:10])}"
        )

    variant_tasks = [
        asyncio.create_task(fetch_and_store_variant(meta))
        for meta in variant_image_metas
    ]
    variant_filenames: list[str] = []
    try:
        for task in asyncio.as_completed(variant_tasks):
            variant_filenames.append(await task)
    except BaseException:
        for task in variant_tasks:
            task.cancel()
        await asyncio.gather(*variant_tasks, return_exceptions=True)
        raise
    if len(variant_filenames) != len(set(variant_filenames)):
        raise ValueError("云资源 manifest 存在重复 EX 差分图片文件名")
    if has_ex_catalog:
        declared_variant_images = {
            str(item.get("image") or "")
            for levels in normalized_ex.values()
            for item in levels.values()
            if str(item.get("image") or "")
        }
        fetched_variant_images = set(variant_filenames)
        missing_variant = declared_variant_images.difference(
            fetched_variant_images
        )
        extra_variant = fetched_variant_images.difference(
            declared_variant_images
        )
        if missing_variant:
            raise ValueError(
                "云资源缺少 EX 差分图片："
                + ", ".join(sorted(missing_variant)[:10])
            )
        if extra_variant:
            raise ValueError(
                "云资源存在未引用 EX 差分图片："
                + ", ".join(sorted(extra_variant)[:10])
            )


def promote_resource_staging(staging: Path, active: Path, previous: Path) -> None:
    """Keep the old active directory recoverable if promotion fails."""
    if previous.exists():
        shutil.rmtree(previous)
    moved_old = False
    try:
        if active.exists():
            active.rename(previous)
            moved_old = True
        staging.rename(active)
    except Exception:
        if moved_old and previous.exists() and not active.exists():
            previous.rename(active)
        raise
