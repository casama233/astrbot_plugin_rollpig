import asyncio
import threading
from pathlib import Path

import pytest

from services.resource_staging import promote_resource_staging, stage_resource_images


def options(tmp_path):
    images = tmp_path / 'images'
    variants = tmp_path / 'ex_variants'
    images.mkdir()
    variants.mkdir()

    async def download(meta):
        return b'image'

    return dict(
        image_metas=[{'filename': 'pig.png'}],
        variant_image_metas=[{'filename': 'pig.EX1.png'}],
        pig_ids={'pig'},
        normalized_ex={'pig': {1: {'image': 'pig.EX1.png'}}},
        has_ex_catalog=True,
        staging_images=images,
        staging_variants=variants,
        image_extensions={'png'},
        initial_size=10,
        max_package_size=20,
        download=download,
        validate_image=lambda data, filename: None,
    )


def test_stage_valid_base_and_ex_at_exact_budget(tmp_path):
    args = options(tmp_path)
    asyncio.run(stage_resource_images(**args))
    assert (tmp_path / 'images/pig.png').read_bytes() == b'image'
    assert (tmp_path / 'ex_variants/pig.EX1.png').read_bytes() == b'image'


@pytest.mark.parametrize(('field', 'value', 'error'), [
    ('image_metas', [{'filename': '../pig.png'}], '文件名无效'),
    ('variant_image_metas', [{'filename': '../pig.png'}], '文件名无效'),
    ('image_metas', [None], '条目无效'),
    ('variant_image_metas', [None], '条目无效'),
    ('pig_ids', {'missing'}, '缺少图片'),
    ('image_metas', [{'filename': 'pig.png'}] * 2, '重复图片'),
    ('variant_image_metas', [{'filename': 'pig.EX1.png'}] * 2, '重复 EX'),
    ('variant_image_metas', [], '缺少 EX'),
    ('normalized_ex', {}, '未引用 EX'),
    ('initial_size', 101, '总大小'),
])
def test_stage_rejects_invalid_packages(tmp_path, field, value, error):
    args = options(tmp_path)
    args['max_package_size'] = 100
    args[field] = value
    with pytest.raises(ValueError, match=error):
        asyncio.run(stage_resource_images(**args))


def test_actual_size_counts_base_and_variant_together(tmp_path):
    args = options(tmp_path)
    args['max_package_size'] = 19
    with pytest.raises(ValueError, match='总大小'):
        asyncio.run(stage_resource_images(**args))


@pytest.mark.parametrize('variant', [False, True])
def test_cancel_drains_downloads_before_return(tmp_path, variant):
    args = options(tmp_path)
    stopped = []

    async def scenario():
        started = asyncio.Event()

        async def download(meta):
            if variant and meta['filename'] == 'pig.png':
                return b'image'
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.append(meta['filename'])

        args['download'] = download
        task = asyncio.create_task(stage_resource_images(**args))
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert stopped == ['pig.EX1.png' if variant else 'pig.png']
        assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    asyncio.run(scenario())


def test_cancel_waits_for_started_filesystem_write(tmp_path, monkeypatch):
    args = options(tmp_path)
    started = threading.Event()
    release = threading.Event()
    original = Path.write_bytes

    def blocked_write(path, data):
        started.set()
        assert release.wait(5)
        return original(path, data)

    monkeypatch.setattr(Path, 'write_bytes', blocked_write)

    async def scenario():
        task = asyncio.create_task(stage_resource_images(**args))
        try:
            assert await asyncio.to_thread(started.wait, 2)
            task.cancel()
            await asyncio.sleep(0.02)
            assert not task.done()
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert (tmp_path / 'images/pig.png').read_bytes() == b'image'

    asyncio.run(scenario())


def test_failed_download_cancels_siblings(tmp_path):
    args = options(tmp_path)
    args['image_metas'] = [{'filename': name} for name in ['pig.png', 'other.png']]
    stopped = []

    async def scenario():
        started = asyncio.Event()

        async def download(meta):
            if meta['filename'] == 'pig.png':
                await started.wait()
                raise ValueError('broken image')
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.append(True)

        args['download'] = download
        with pytest.raises(ValueError, match='broken image'):
            await stage_resource_images(**args)
        assert stopped == [True]

    asyncio.run(scenario())


@pytest.mark.parametrize('fail', [False, True])
def test_promotion_preserves_previous_or_restores_active(tmp_path, monkeypatch, fail):
    staging, active, previous = [tmp_path / name for name in ['incoming', 'active', 'previous']]
    for path, value in [(staging, 'new'), (active, 'current'), (previous, 'old')]:
        path.mkdir()
        (path / 'value').write_text(value)
    original = Path.rename

    def rename(path, target):
        if fail and path == staging:
            raise OSError('promotion failed')
        return original(path, target)

    monkeypatch.setattr(Path, 'rename', rename)
    if fail:
        with pytest.raises(OSError, match='promotion failed'):
            promote_resource_staging(staging, active, previous)
        assert (active / 'value').read_text() == 'current'
        assert (staging / 'value').read_text() == 'new'
    else:
        promote_resource_staging(staging, active, previous)
        assert (active / 'value').read_text() == 'new'
        assert (previous / 'value').read_text() == 'current'
        assert not staging.exists()
