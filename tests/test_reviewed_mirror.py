import asyncio
import copy
import io
import json
from pathlib import Path

import pytest
from PIL import Image

# Exercise the real legacy transaction methods without importing AstrBot's
# global handler registry into the unit-test process.
import ast
import hashlib
import logging
import re
import shutil
import time
import uuid
from urllib.parse import urljoin, urlsplit
import httpx
from services.resource_staging import stage_resource_images, promote_resource_staging
from ex_variants import validate_ex_variants
from roast_copy import validate_roast_copy_catalog


def load_legacy_transaction():
    source = Path(__file__).resolve().parents[1] / 'legacy_main.py'
    node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'RollPigPlugin')
    methods = {'sync_cloud_resources', '_validate_remote_url', '_resource_request_headers',
               '_download_manifest_item', '_validate_manifest_path', '_validate_pig_records',
               '_validate_image_dimensions', '_describe_sync_error', '_load_cloud_pigs'}
    fields = {'PLUGIN_NAME', 'RESOURCE_CLIENT_ID', 'RESOURCE_PROTOCOL_VERSION', 'OFFICIAL_RESOURCE_MANIFEST_URL',
              'RESOURCE_MANIFEST_MAX_SIZE', 'RESOURCE_PACKAGE_MAX_SIZE', 'RESOURCE_MAX_IMAGES',
              'RESOURCE_MAX_VARIANT_IMAGES', 'IMAGE_EXTENSIONS'}
    body = [n for n in node.body if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in methods)
            or (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in fields)]
    module = ast.Module(body=[ast.ClassDef(name='Legacy', bases=[], keywords=[], body=body, decorator_list=[])], type_ignores=[])
    namespace = dict(globals(), PILImage=Image, logger=logging.getLogger(__name__))
    exec(compile(ast.fix_missing_locations(module), str(source), 'exec'), namespace)
    return namespace['Legacy']


Legacy = load_legacy_transaction()
from resource_failover_feature import ResourceFailoverMixin
from services.mirror_snapshot import approved_review, fetch_snapshot
from services.snapshot_protocol import CLIENT, PROFILE, digest


def fixture():
    buffer = io.BytesIO()
    Image.new('RGB', (16, 16), '#ffd5df').save(buffer, format='PNG')
    encode = lambda value: json.dumps(value, ensure_ascii=False).encode()
    files = {
        'pig.json': encode([{'id': 'test-pig', 'name': '测试猪', 'description': 'fixture', 'analysis': 'fixture analysis'}]),
        'images/test-pig.png': buffer.getvalue(),
        'NOTICE.md': b'Synthetic fixture attribution',
        'LICENSES/test.txt': b'Synthetic fixture permission',
        'PROVENANCE.json': encode({'resource_count': 1, 'items': [{'id': 'test-pig', 'source': 'fixture', 'classification': 'synthetic'}]}),
    }
    def member(name):
        return {'path': name, 'filename': Path(name).name, 'size': len(files[name]), 'sha256': digest(files[name])}
    manifest = {
        'schema_version': 1, 'client': CLIENT, 'profile': PROFILE,
        'resource_version': '2026.09.05.1', 'generated_at': '2026-09-05T00:00:00Z',
        'pig_count': 1, 'pig_json': member('pig.json'), 'images': [member('images/test-pig.png')],
        'notice': member('NOTICE.md'), 'provenance': member('PROVENANCE.json'),
        'licenses': [member('LICENSES/test.txt')], 'package_size': sum(map(len, files.values())),
    }
    files['manifest.json'] = encode(manifest)
    review = {'status': 'approved', 'profile': PROFILE, 'primary_manifest_url': Legacy.OFFICIAL_RESOURCE_MANIFEST_URL,
              'review_url': 'https://example.invalid/review', 'files': {k: digest(v) for k, v in files.items()},
              'rights': {k: {'redistribution_verified': True, 'rights_basis': 'original-work', 'author': 'Fixture',
                             'source_url': 'https://example.invalid/source', 'evidence_url': 'https://example.invalid/evidence',
                             'review_note': 'Synthetic only'} for k in ['pig.json', 'images/test-pig.png']}}
    policy = {'schema_version': 2, 'approved_snapshots': {digest(files['manifest.json']): review}}
    return files, policy


class Client:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class Transport(Legacy):
    def _new_http_client(self, **kwargs):
        return Client()

    async def _download_limited(self, client, url, max_size, attempts=3):
        self.downloads.append(url)
        if url.startswith(self.OFFICIAL_RESOURCE_MANIFEST_URL.rsplit('/', 1)[0]):
            raise OSError('primary unavailable')
        if self.fail_vercel and 'vercel.app' in url:
            raise OSError('Vercel unavailable')
        name = url.split('/v1/', 1)[1]
        raw = self.files[name]
        assert len(raw) <= max_size
        return raw


class Harness(ResourceFailoverMixin, Transport):
    def __init__(self, root):
        self.resource_root = root / 'cloud'
        self.resource_root.mkdir()
        self.resource_active_dir = self.resource_root / 'active'
        self.resource_state_path = self.resource_root / 'state.json'
        self.resource_manifest_url = self.OFFICIAL_RESOURCE_MANIFEST_URL
        self.resource_vercel_mirror_url = self.VERCEL_RESOURCE_MANIFEST_URL
        self.resource_github_mirror_url = self.GITHUB_RESOURCE_MANIFEST_URL
        self.resource_github_fallback_enabled = True
        self.resource_sync_timeout = 10
        self.resource_max_file_size = 10 * 1024 * 1024
        self._resource_sync_lock = asyncio.Lock()
        self.files, self.policy = fixture()
        self.policy_reads = 0
        self.revoke_after_first_read = False
        self.fail_vercel = False
        self.downloads = []
        self.state = {}
        self.reloads = 0
        self.error = ''

    def _cloud_state(self):
        return dict(self.state)

    def save_json(self, path, data):
        assert path == self.resource_state_path
        self.state = dict(data)
        path.write_text(json.dumps(data))

    def _save_sync_status(self, error=''):
        self.error = error

    def _reload_catalog_layers(self):
        self.reloads += 1

    async def _read_mirror_policy(self):
        self.policy_reads += 1
        policy = copy.deepcopy(self.policy)
        if self.revoke_after_first_read and self.policy_reads > 1:
            next(iter(policy['approved_snapshots'].values()))['status'] = 'revoked'
        return json.dumps(policy).encode()


def test_primary_outage_activates_only_fully_verified_mirror_using_real_transaction(tmp_path):
    plugin = Harness(tmp_path)
    result = asyncio.run(plugin.sync_cloud_resources())
    assert result['source'] == 'vercel'
    assert plugin.resource_manifest_url == plugin.OFFICIAL_RESOURCE_MANIFEST_URL
    assert plugin.state['approved_manifest_sha256'] == digest(plugin.files['manifest.json'])
    assert (plugin.resource_active_dir / 'images/test-pig.png').read_bytes() == plugin.files['images/test-pig.png']
    assert plugin.reloads == 1
    assert plugin.policy_reads == 2
    # Preflight downloads once; the actual base transaction reads the reviewed
    # local bytes, preventing a second-manifest substitution by the mirror.
    assert len(plugin.downloads) == len(plugin.files) + 1
    assert not list(plugin.resource_root.glob('.mirror-review-*'))


def test_github_is_used_when_primary_and_vercel_are_unavailable(tmp_path):
    plugin = Harness(tmp_path)
    plugin.fail_vercel = True
    assert asyncio.run(plugin.sync_cloud_resources())['source'] == 'github'


def test_same_version_repairs_cache_with_verified_bytes(tmp_path):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    (plugin.resource_active_dir / 'images/test-pig.png').write_bytes(b'corrupt')
    asyncio.run(plugin.sync_cloud_resources())
    assert (plugin.resource_active_dir / 'images/test-pig.png').read_bytes() == plugin.files['images/test-pig.png']


def test_newer_local_source_is_never_downgraded(tmp_path):
    plugin = Harness(tmp_path)
    plugin.state = {'resource_version': '2026.09.06.1', 'source_name': 'primary'}
    with pytest.raises(ValueError, match='拒绝降级'):
        asyncio.run(plugin.sync_cloud_resources())
    assert plugin.state['resource_version'] == '2026.09.06.1'
    assert not plugin.resource_active_dir.exists()


@pytest.mark.parametrize('name', ['manifest.json', 'images/test-pig.png', 'NOTICE.md', 'LICENSES/test.txt', 'PROVENANCE.json'])
def test_corrupt_or_substituted_files_never_replace_active_cache(tmp_path, name):
    plugin = Harness(tmp_path)
    plugin.resource_active_dir.mkdir()
    marker = plugin.resource_active_dir / 'previous.txt'
    marker.write_text('keep previous')
    plugin.files[name] += b'changed'
    with pytest.raises(ValueError):
        asyncio.run(plugin.sync_cloud_resources())
    assert marker.read_text() == 'keep previous'
    assert plugin.reloads == 0


def test_withdrawal_during_transfer_never_activates(tmp_path):
    plugin = Harness(tmp_path)
    plugin.revoke_after_first_read = True
    with pytest.raises(ValueError, match='撤回'):
        asyncio.run(plugin.sync_cloud_resources())
    assert not plugin.resource_active_dir.exists()
    assert plugin.reloads == 0


def test_revoked_cached_mirror_is_removed_from_active_lookup(tmp_path):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    next(iter(plugin.policy['approved_snapshots'].values()))['status'] = 'revoked'
    with pytest.raises(ValueError, match='撤回'):
        asyncio.run(plugin.sync_cloud_resources())
    assert not plugin.resource_active_dir.exists()
    assert plugin.state == {}
    assert len(list(plugin.resource_root.glob('.withdrawn-*'))) == 1


def test_unavailable_policy_prevents_new_mirror_download(tmp_path):
    plugin = Harness(tmp_path)
    async def unavailable():
        raise OSError('GitHub approval registry unavailable')
    plugin._read_mirror_policy = unavailable
    with pytest.raises(ValueError, match='registry unavailable'):
        asyncio.run(plugin.sync_cloud_resources())
    assert plugin.downloads == [plugin.OFFICIAL_RESOURCE_MANIFEST_URL]


def test_cancel_snapshot_drains_all_downloads(tmp_path):
    files, policy = fixture()
    stopped = []
    async def scenario():
        started = asyncio.Event()
        async def download(url, limit):
            if url.endswith('manifest.json'):
                return files['manifest.json']
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.append(url)
        task = asyncio.create_task(fetch_snapshot(root=tmp_path, manifest_url=Harness.VERCEL_RESOURCE_MANIFEST_URL,
                                                  policy_raw=json.dumps(policy).encode(), download=download))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(stopped) == 4
        assert len(asyncio.all_tasks()) == 1
    asyncio.run(scenario())
