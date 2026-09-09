"""Temporary exact-revision patch application; removed before opening the PR."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess
import textwrap

BASE = '55edb30a3ccee0fe77a3ec368a92ea80b47d1c89'
EXPECTED = {
    'resource_failover_feature.py': '3b6903250bc54a516b6cfd896a7fe330d74a5b9d',
    'legacy_main.py': 'f61b5dbb56b9975bb135bca1cdbebd43ecb67e29',
    'storage/primary_manager.py': 'c3f35f0482948aa0783216f9628ebb4cd65a363f',
    'pages/pig-manager/index.html': '709d2b02824f75c42ca189459b312699e1274700',
}
sources = {}
for name, expected in EXPECTED.items():
    data = Path(name).read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if actual != expected:
        raise RuntimeError(f'refusing to patch unexpected revision: {name}: {actual}')
    sources[name] = data.decode('utf-8')


def replace(name, old, new):
    source = sources[name]
    if source.count(old) != 1:
        raise RuntimeError(f'patch must have exactly one match: {name}: {old[:100]!r}')
    sources[name] = source.replace(old, new, 1)


# Preserve provenance on no-op and distrust same-version caches without a hash
# recorded by a successful complete transaction (including old mislabelled caches).
name = 'legacy_main.py'
replace(name,
'''                    if (
                        not force
                        and version == self._cloud_state().get("resource_version")
''',
'''                    state = self._cloud_state()
                    manifest_hash = hashlib.sha256(manifest_raw).hexdigest()
                    if (
                        not force
                        and version == state.get("resource_version")
                        and manifest_hash == state.get("manifest_sha256")
''')
replace(name,
'''                            or (
                                self.resource_active_dir / "pig_ex_variants.json"
                            ).is_file()
''',
'''                            or (self.resource_active_dir / "pig_ex_variants.json").is_file()
''')
replace(name,
'''                        self.save_json(
                            self.resource_state_path,
                            {
                                "resource_version": version,
                                "synced_at": int(time.time()),
                            },
                        )
''',
'''                        state["synced_at"] = int(time.time())
                        self.save_json(self.resource_state_path, state)
''')
replace(name,
'''                    {"resource_version": version, "synced_at": int(time.time())},
''',
'''                    dict(resource_version=version, synced_at=int(time.time()),
                         manifest_sha256=manifest_hash),
''')
if len(sources[name].encode()) > len(Path(name).read_bytes()):
    raise RuntimeError('legacy shrink-only budget would grow')

name = 'resource_failover_feature.py'
replace(name,
'''        state["source_name"] = source_name
''',
'''        if source_name not in {"vercel", "github"}:
            state.pop("approved_manifest_sha256", None)
        state["source_name"] = source_name
''')
replace(name,
'''    async def sync_cloud_resources(self, force: bool = False) -> dict:
''',
'''    async def _sync_direct_resource_source(self, source_name, source_url, force):
        state = self._cloud_state()
        # A version string is not evidence of where the active bytes came from.
        # Unknown origins and mirror -> direct switches require a full transaction.
        different_origin = bool(state) and (
            state.get("source_name") != source_name
            or state.get("source_url") != source_url
            or bool(state.get("approved_manifest_sha256"))
        )
        result = await super().sync_cloud_resources(force=force or different_origin)
        if result.get("updated") is True:
            self._record_resource_origin(source_name, source_url)
        return result

    async def sync_cloud_resources(self, force: bool = False) -> dict:
''')
replace(name,
'''            result = await super().sync_cloud_resources(force=force)
            if configured_url:
                self._record_resource_origin("custom", configured_url)
            return result
''',
'''            return await self._sync_direct_resource_source("custom", configured_url, force)
''')
replace(name,
'''                    result = await super().sync_cloud_resources(force=force)
                    self._record_resource_origin(source_name, source_url)
''',
'''                    result = await self._sync_direct_resource_source(source_name, source_url, force)
''')
replace(name,
'''        if state.get("source_name") not in {"vercel", "github"}:
            return
        previous_hash = state.get("approved_manifest_sha256")
        review = parse_json(policy_raw)["approved_snapshots"].get(previous_hash, {})
        if previous_hash and review.get("status") == "approved":
''',
'''        previous_hash = str(state.get("approved_manifest_sha256") or "")
        mirror_origin = (
            bool(previous_hash)
            or state.get("source_name") in {"vercel", "github"}
            or state.get("source_url") in {
                self.VERCEL_RESOURCE_MANIFEST_URL, self.GITHUB_RESOURCE_MANIFEST_URL,
            }
        )
        if not mirror_origin:
            return
        review = parse_json(policy_raw)["approved_snapshots"].get(previous_hash, {})
        if previous_hash and isinstance(review, dict) and review.get("status") == "approved":
''')

# Check an existing database before any CREATE TABLE / migration can disguise an
# empty or unrelated file. mode=ro uses the WAL view; immutable=1 must not be used.
name = 'storage/primary_manager.py'
replace(name, 'import shutil\n', 'import shutil\nimport sqlite3\nfrom contextlib import closing\n')
replace(name,
'''    def _select_initial_backend(self) -> None:
''',
'''    def _preflight_existing_sqlite(self) -> None:
        """Read the existing SQL identity before the backend initializes tables."""
        with self.database_path.open("rb") as source:
            if source.read(16) != b"SQLite format 3\\x00":
                raise StorageMigrationError("既有数据库为空、被截断或不是 SQLite 文件")
        uri = self.database_path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(
            uri, uri=True, timeout=self.busy_timeout_ms / 1000,
        )) as connection:
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            required = {"schema_migrations", "documents", "identities", "daily_draws", "user_pigs"}
            if not required.issubset(tables):
                raise StorageMigrationError("既有数据库缺少 RollPig 核心表，禁止按新库初始化")
            version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
            if type(version) is not int or not 1 <= version <= 6:
                raise StorageMigrationError("既有数据库的 RollPig schema 版本不能核验")

    def _select_initial_backend(self) -> None:
''')
replace(name,
'''            try:
                candidate = self._new_sqlite()
''',
'''            try:
                self._preflight_existing_sqlite()
                candidate = self._new_sqlite()
''')

name = 'pages/pig-manager/index.html'
replace(name,
'''  const cached=d.source==='cloud'?(d.active_remote_source?`${sourceName(d.active_remote_source)}缓存`:'云端缓存（来源未记录）'):'内置兜底';
''',
'''  const cloud=d.source==='cloud'||d.source==='cloud+felis-direct';
  const bundled=d.source==='bundled'||d.source==='bundled+felis-direct';
  const felis=d.source==='cloud+felis-direct'||d.source==='bundled+felis-direct';
  const base=cloud?(d.active_remote_source?`${sourceName(d.active_remote_source)}缓存`:'云端缓存（来源未记录）'):bundled?'内置兜底':'来源状态未识别';
  const cached=base+(felis?' + Felis 官方直读':'');
''')
replace(name, '''${d.source==='cloud'?'ok':''}">当前资源''', '''${cloud?'ok':''}">当前资源''')

for name, source in sources.items():
    if name.endswith('.py'):
        ast.parse(source, filename=name)
    Path(name).write_text(source, encoding='utf-8')

# Keep the existing assertion meaningful: a state without an origin now forces
# verification instead of retaining the same-version shortcut.
path = Path('tests/test_resource_failover.py')
source = path.read_text(encoding='utf-8')
old = 'assert plugin.calls == [(plugin.OFFICIAL_RESOURCE_MANIFEST_URL, False)]'
assert source.count(old) == 1
source = source.replace(old, '# A legacy cache without recorded origin must be fully verified.\n    assert plugin.calls == [(plugin.OFFICIAL_RESOURCE_MANIFEST_URL, True)]')
path.write_text(source, encoding='utf-8')

# Reuse the actual transaction harness, not a replica of the cache shortcut.
path = Path('tests/test_reviewed_mirror.py')
with path.open('a', encoding='utf-8') as output:
    output.write(r'''


def _restore_direct_transport(monkeypatch):
    original = Transport._download_limited

    async def download(self, client, url, max_size, attempts=3):
        primary = self.OFFICIAL_RESOURCE_MANIFEST_URL.rsplit('/', 1)[0] + '/'
        if url.startswith(primary) or url.startswith('https://private.example/v1/'):
            self.downloads.append(url)
            raw = self.files[url.split('/v1/', 1)[1]]
            if len(raw) > max_size:
                raise ValueError('fixture exceeds download limit')
            return raw
        return await original(self, client, url, max_size, attempts)

    monkeypatch.setattr(Transport, '_download_limited', download)


def _change_direct_catalog(plugin):
    records = json.loads(plugin.files['pig.json'])
    records[0]['analysis'] = 'New primary bytes at the same resource version'
    old_size = len(plugin.files['pig.json'])
    plugin.files['pig.json'] = json.dumps(records).encode()
    manifest = json.loads(plugin.files['manifest.json'])
    manifest['pig_json']['size'] = len(plugin.files['pig.json'])
    manifest['pig_json']['sha256'] = digest(plugin.files['pig.json'])
    manifest['package_size'] += len(plugin.files['pig.json']) - old_size
    plugin.files['manifest.json'] = json.dumps(manifest).encode()


@pytest.mark.parametrize('target', ['primary', 'custom'])
def test_same_version_origin_switch_downloads_real_direct_bytes(tmp_path, monkeypatch, target):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    old_hash = plugin.state['approved_manifest_sha256']
    _restore_direct_transport(monkeypatch)
    _change_direct_catalog(plugin)
    if target == 'custom':
        plugin.resource_manifest_url = 'https://private.example/v1/manifest.json'
    plugin.downloads.clear()
    result = asyncio.run(plugin.sync_cloud_resources())
    assert result['updated'] is True
    assert plugin.state['source_name'] == target
    assert plugin.state['source_url'] == plugin.resource_manifest_url
    assert 'approved_manifest_sha256' not in plugin.state
    assert plugin.state['manifest_sha256'] == digest(plugin.files['manifest.json'])
    assert plugin.state['manifest_sha256'] != old_hash
    assert (plugin.resource_active_dir / 'pig.json').read_bytes() == plugin.files['pig.json']
    assert any(url.endswith('/images/test-pig.png') for url in plugin.downloads)


def test_real_same_version_noop_retains_mirror_origin_and_revocation(tmp_path, monkeypatch):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    before = dict(plugin.state)
    _restore_direct_transport(monkeypatch)
    # Exercise the real lower-level no-op; it must not discard metadata even if
    # a caller reaches it directly instead of the origin-switch forcing facade.
    result = asyncio.run(Legacy.sync_cloud_resources(plugin, force=False))
    assert result['updated'] is False
    for key in ('source_name', 'source_url', 'approved_manifest_sha256', 'manifest_sha256'):
        assert plugin.state[key] == before[key]
    plugin.policy['approved_snapshots'] = {}
    plugin._withdraw_revoked_mirror_cache(json.dumps(plugin.policy).encode())
    assert not plugin.resource_active_dir.exists()
    assert plugin.state == {}
    assert len(list(plugin.resource_root.glob('.withdrawn-*'))) == 1


def test_noop_result_cannot_relabel_mirror_as_primary(tmp_path, monkeypatch):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    before = dict(plugin.state)
    _restore_direct_transport(monkeypatch)

    async def no_update(self, force=False):
        assert force is True
        return {'updated': False, 'version': self.state['resource_version']}

    monkeypatch.setattr(Transport, 'sync_cloud_resources', no_update)
    result = asyncio.run(plugin.sync_cloud_resources())
    assert result['updated'] is False
    assert plugin.state == before


def test_failed_primary_switch_preserves_active_mirror_provenance(tmp_path, monkeypatch):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    before = dict(plugin.state)
    original = (plugin.resource_active_dir / 'pig.json').read_bytes()
    _restore_direct_transport(monkeypatch)
    plugin.files['pig.json'] += b'corrupt'
    plugin.resource_vercel_mirror_url = ''
    plugin.resource_github_fallback_enabled = False
    with pytest.raises(ValueError):
        asyncio.run(plugin.sync_cloud_resources())
    assert plugin.state == before
    assert (plugin.resource_active_dir / 'pig.json').read_bytes() == original


@pytest.mark.parametrize('label', ['primary', 'custom', ''])
def test_revocation_cannot_be_bypassed_by_changed_source_label(tmp_path, label):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    plugin.state['source_name'] = label
    plugin.state['source_url'] = plugin.OFFICIAL_RESOURCE_MANIFEST_URL
    plugin.policy['approved_snapshots'] = {}
    plugin._withdraw_revoked_mirror_cache(json.dumps(plugin.policy).encode())
    assert not plugin.resource_active_dir.exists()
    assert plugin.state == {}


def test_mirror_url_without_digest_is_not_treated_as_primary(tmp_path):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    plugin.state['source_name'] = 'primary'
    plugin.state.pop('approved_manifest_sha256')
    plugin._withdraw_revoked_mirror_cache(json.dumps(plugin.policy).encode())
    assert not plugin.resource_active_dir.exists()


@pytest.mark.parametrize('review', [None, [], 'approved', {'status': 'revoked'}])
def test_malformed_or_revoked_review_does_not_keep_mirror_active(tmp_path, review):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    plugin.policy['approved_snapshots'][plugin.state['approved_manifest_sha256']] = review
    plugin._withdraw_revoked_mirror_cache(json.dumps(plugin.policy).encode())
    assert not plugin.resource_active_dir.exists()


def test_legacy_mislabelled_cache_without_manifest_hash_is_reverified(tmp_path, monkeypatch):
    plugin = Harness(tmp_path)
    asyncio.run(plugin.sync_cloud_resources())
    # State left by the old same-version shortcut: primary label, no digest.
    plugin.state = {'resource_version': plugin.state['resource_version'], 'synced_at': 1,
                    'source_name': 'primary', 'source_url': plugin.OFFICIAL_RESOURCE_MANIFEST_URL}
    _restore_direct_transport(monkeypatch)
    _change_direct_catalog(plugin)
    plugin.downloads.clear()
    result = asyncio.run(plugin.sync_cloud_resources())
    assert result['updated'] is True
    assert any(url.endswith('/pig.json') for url in plugin.downloads)
    assert plugin.state['manifest_sha256'] == digest(plugin.files['manifest.json'])
    assert (plugin.resource_active_dir / 'pig.json').read_bytes() == plugin.files['pig.json']


def test_same_direct_origin_keeps_fast_path_and_extra_metadata(tmp_path, monkeypatch):
    plugin = Harness(tmp_path)
    _restore_direct_transport(monkeypatch)
    asyncio.run(plugin.sync_cloud_resources())
    plugin.state['audit_note'] = 'preserve on no-op'
    before = dict(plugin.state)
    plugin.downloads.clear()
    result = asyncio.run(plugin.sync_cloud_resources())
    assert result['updated'] is False
    assert all(url.endswith('/manifest.json') for url in plugin.downloads)
    for key, value in before.items():
        if key != 'synced_at':
            assert plugin.state[key] == value


def test_changed_manifest_at_same_version_is_not_a_noop(tmp_path, monkeypatch):
    plugin = Harness(tmp_path)
    _restore_direct_transport(monkeypatch)
    asyncio.run(plugin.sync_cloud_resources())
    _change_direct_catalog(plugin)
    assert asyncio.run(plugin.sync_cloud_resources())['updated'] is True
    assert (plugin.resource_active_dir / 'pig.json').read_bytes() == plugin.files['pig.json']
''')

Path('tests/test_existing_sqlite_preflight.py').write_text(r'''from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from storage import SQLitePrimaryStorage, SQLiteStorage, StorageManager, StorageMigrationError


@pytest.mark.parametrize('mode', ['auto', 'sqlite'])
@pytest.mark.parametrize('marker', [False, True])
@pytest.mark.parametrize('content', [b'', b'SQLite format 3\x00', b'not-a-database'])
def test_existing_empty_or_truncated_database_is_never_initialized(tmp_path, monkeypatch, mode, marker, content):
    database = tmp_path / 'rollpig.db'
    database.write_bytes(content)
    if marker:
        (tmp_path / 'storage_state.json').write_text(json.dumps({'active_backend': 'sqlite'}))
    history = tmp_path / 'pig_history.json'
    history.write_text('{"users":{"stale":{}}}')
    before = {path.name: path.read_bytes() for path in tmp_path.glob('*.json')}

    def forbidden(*args, **kwargs):
        pytest.fail('existing database preflight must happen before backend initialization')

    monkeypatch.setattr(StorageManager, '_new_sqlite', forbidden)
    with pytest.raises(StorageMigrationError, match='SQLite 需要恢复'):
        StorageManager(tmp_path, mode=mode)
    assert database.read_bytes() == content
    assert {path.name: path.read_bytes() for path in tmp_path.glob('*.json')} == before


@pytest.mark.parametrize('kind', ['empty-schema', 'unrelated'])
def test_valid_sqlite_file_without_rollpig_schema_is_not_bootstrapped(tmp_path, monkeypatch, kind):
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as connection:
        if kind == 'empty-schema':
            connection.execute('VACUUM')
        else:
            connection.execute('CREATE TABLE unrelated(value TEXT)')
            connection.commit()
    before = database.read_bytes()
    monkeypatch.setattr(StorageManager, '_new_sqlite', lambda *args: pytest.fail('must preflight first'))
    with pytest.raises(StorageMigrationError, match='核心表'):
        StorageManager(tmp_path)
    assert database.read_bytes() == before


@pytest.mark.parametrize('table', ['schema_migrations', 'documents', 'identities', 'daily_draws', 'user_pigs'])
def test_missing_core_table_is_not_recreated_before_validation(tmp_path, table):
    manager = StorageManager(tmp_path)
    manager.backend.checkpoint()
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as connection:
        connection.execute('PRAGMA journal_mode=DELETE')
        connection.execute(f'DROP TABLE {table}')
        connection.commit()
    before = database.read_bytes()
    with pytest.raises(StorageMigrationError, match='核心表'):
        StorageManager(tmp_path)
    assert database.read_bytes() == before


@pytest.mark.parametrize('version', [None, 0, 999])
def test_unverified_schema_version_does_not_trigger_migrations(tmp_path, version):
    manager = StorageManager(tmp_path)
    manager.backend.checkpoint()
    with closing(sqlite3.connect(tmp_path / 'rollpig.db')) as connection:
        connection.execute('DELETE FROM schema_migrations')
        if version is not None:
            connection.execute('INSERT INTO schema_migrations VALUES (?, 1)', (version,))
        connection.commit()
    with pytest.raises(StorageMigrationError, match='schema'):
        StorageManager(tmp_path)


def test_healthy_empty_database_and_new_install_remain_supported(tmp_path):
    first = StorageManager(tmp_path)
    assert isinstance(first.backend, SQLitePrimaryStorage)
    assert first.verify()['ok'] is True
    restarted = StorageManager(tmp_path)
    assert isinstance(restarted.backend, SQLitePrimaryStorage)
    assert restarted.verify()['ok'] is True


def test_valid_v2_database_still_upgrades(tmp_path):
    old = SQLiteStorage(tmp_path / 'rollpig.db', tmp_path, StorageManager.MANAGED_PATHS)
    old.save_json(tmp_path / 'pig_history.json', {'version': 1, 'users': {}, 'daily': {}, 'pig_snapshots': {}})
    old.checkpoint()
    manager = StorageManager(tmp_path)
    assert isinstance(manager.backend, SQLitePrimaryStorage)
    assert manager.verify()['schema_version'] == 6
    assert manager.verify()['ok'] is True


def test_preflight_reads_wal_schema_and_latest_committed_collection(tmp_path):
    manager = StorageManager(tmp_path)
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as keeper:
        keeper.execute('PRAGMA journal_mode=WAL')
        keeper.execute('PRAGMA wal_autocheckpoint=0')
        keeper.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()
        manager.backend.create_daily_draw(draw_date='2026-09-09', user_id='user-wal', pig={'id': 'pig-a', 'name': 'A'})
        assert Path(f'{database}-wal').stat().st_size > 0
        restarted = StorageManager(tmp_path)
        assert restarted.backend.get_user_collection(('user-wal',))['total_draws'] == 1
        assert restarted.verify()['ok'] is True


def test_readonly_preflight_uses_schema_from_wal_not_immutable_database(tmp_path):
    database = tmp_path / 'rollpig.db'
    with closing(sqlite3.connect(database)) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('PRAGMA wal_autocheckpoint=0')
        for name in ('documents', 'identities', 'daily_draws', 'user_pigs'):
            writer.execute(f'CREATE TABLE {name}(value TEXT)')
        writer.execute('CREATE TABLE schema_migrations(version INTEGER, applied_at INTEGER)')
        writer.execute('INSERT INTO schema_migrations VALUES (1, 1)')
        writer.commit()
        probe = StorageManager.__new__(StorageManager)
        probe.database_path = database
        probe.busy_timeout_ms = 1000
        before = database.read_bytes()
        probe._preflight_existing_sqlite()
        assert database.read_bytes() == before
        assert Path(f'{database}-wal').stat().st_size > 0


def test_empty_database_preserves_orphan_sidecar_evidence(tmp_path):
    database = tmp_path / 'rollpig.db'
    database.write_bytes(b'')
    for suffix in ('-wal', '-shm'):
        Path(f'{database}{suffix}').write_bytes(('evidence' + suffix).encode())
    with pytest.raises(StorageMigrationError, match='SQLite 需要恢复'):
        StorageManager(tmp_path)
    assert database.read_bytes() == b''
    for suffix in ('-wal', '-shm'):
        expected = ('evidence' + suffix).encode()
        assert Path(f'{database}{suffix}').read_bytes() == expected
        assert any(path.read_bytes() == expected for path in tmp_path.glob('.rollpig.db.preflight-*' + suffix))
''', encoding='utf-8')

Path('tests/browser/resource-source-label.test.mjs').write_text(r'''import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { JSDOM } from 'jsdom';

const page = fs.readFileSync(new URL('../../pages/pig-manager/index.html', import.meta.url), 'utf8');
const start = page.indexOf('function renderResourceStatus(d){');
const end = page.indexOf('\nasync function loadResourceStatus', start);
assert.ok(start >= 0 && end > start, 'exercise the actual production renderer');
const source = page.slice(start, end);

function render(status) {
  const dom = new JSDOM('<div id="syncStatus"></div><button id="syncBtn"></button>');
  const document = dom.window.document;
  const context = {
    resourceSnapshot: null,
    $: id => document.getElementById(id),
    esc: value => {
      const element = document.createElement('span');
      element.textContent = String(value);
      return element.innerHTML;
    },
    formatTime: value => String(value),
    setSyncFeedback: () => {},
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  context.renderResourceStatus({ enabled: true, manifest_url: 'https://example.invalid/v1/manifest.json', ...status });
  return { dom, label: document.querySelector('#syncStatus .pill'), button: document.getElementById('syncBtn') };
}

for (const remote of ['primary', 'vercel', 'github', 'custom']) {
  for (const overlay of [false, true]) {
    test(`cloud ${remote}, Felis overlay=${overlay}`, () => {
      const { dom, label } = render({ source: overlay ? 'cloud+felis-direct' : 'cloud', active_remote_source: remote });
      const names = { primary: 'AstrBot 主源', vercel: 'Vercel 镜像', github: 'GitHub 镜像', custom: '私人源' };
      assert.ok(label.textContent.includes(names[remote] + '缓存'));
      assert.equal(label.textContent.includes('Felis 官方直读'), overlay);
      assert.equal(label.textContent.includes('内置兜底'), false);
      assert.ok(label.classList.contains('ok'));
      dom.window.close();
    });
  }
}
for (const overlay of [false, true]) {
  test(`bundled, Felis overlay=${overlay}`, () => {
    const { dom, label } = render({ source: overlay ? 'bundled+felis-direct' : 'bundled', active_remote_source: 'vercel' });
    assert.ok(label.textContent.includes('内置兜底'));
    assert.equal(label.textContent.includes('Felis 官方直读'), overlay);
    assert.equal(label.textContent.includes('Vercel'), false);
    assert.equal(label.classList.contains('ok'), false);
    dom.window.close();
  });
}
for (const state of [undefined, '', 'future-source', 'future-source+felis-direct']) {
  test(`unknown source is not labelled bundled: ${state}`, () => {
    const { dom, label } = render({ source: state });
    assert.ok(label.textContent.includes('来源状态未识别'));
    assert.equal(label.textContent.includes('内置兜底'), false);
    dom.window.close();
  });
}
test('cloud without remote provenance remains cloud and shows the uncertainty', () => {
  const { dom, label } = render({ source: 'cloud+felis-direct' });
  assert.ok(label.textContent.includes('云端缓存（来源未记录）'));
  assert.ok(label.textContent.includes('Felis 官方直读'));
  dom.window.close();
});
test('source text stays escaped and running state still disables sync', () => {
  const { dom, label, button } = render({ source: 'cloud+felis-direct', active_remote_source: '<img src=x onerror=alert(1)>', running: true });
  assert.equal(label.querySelector('img'), null);
  assert.ok(label.textContent.includes('<img'));
  assert.equal(button.disabled, true);
  dom.window.close();
});
''', encoding='utf-8')

path = Path('tests/test_legacy_shrink_budget.py')
source = path.read_text(encoding='utf-8')
source = source.replace('LEGACY_MAIN_MAX_BYTES = 279_565', f'LEGACY_MAIN_MAX_BYTES = {len(sources["legacy_main.py"].encode()):_}')
path.write_text(source, encoding='utf-8')

path = Path('CHANGELOG.md')
source = path.read_text(encoding='utf-8')
heading = '## 未發佈\n\n'
entry = ('- 小修補：同版本同步保留快取實際來源及鏡像批准雜湊；來源切換、manifest 改變或舊快取缺少完整驗證記錄時重新校驗。撤回依據不再只看來源名稱。\n'
         '- 既有 SQLite 在建表／遷移前先唯讀核驗檔頭、核心表及 schema 版本；空檔案、截斷或非本插件資料庫停止載入，保留 WAL／SHM 恢復材料。新安裝及有效舊庫升級不變。\n'
         '- 管理頁完整顯示 cloud／bundled 與 Felis 直讀疊加來源；未知狀態不再誤報內置兜底。新增實際資源交易、資料庫及 DOM 回歸測試。\n\n')
if heading in source:
    source = source.replace(heading, heading + entry, 1)
else:
    lines = source.splitlines(keepends=True)
    source = lines[0] + '\n' + heading + entry + ''.join(lines[1:]).lstrip('\n')
path.write_text(source, encoding='utf-8')

path = Path('docs/SQLITE-RECOVERY.md')
source = path.read_text(encoding='utf-8')
source = source.replace('本頁描述維護第一批的未發佈變更；不是 v3.12.1 已有的行為。',
                        '資料權威與 JSON 預檢保護已隨維護版本提供；本次未發佈小修補再加入既有 SQLite 的建表前檢查。')
source = source.replace('## 管理員處理',
'''既有 `rollpig.db` 會在任何建表／遷移前核驗 SQLite 檔頭、RollPig 核心表和 schema 版本。0-byte、截斷或其他用途的 SQLite 檔案不會被當成全新安裝。檢查使用唯讀 SQLite 連線的 WAL 視圖，不使用忽略 WAL 的 immutable 模式；有效但尚無玩家的資料庫、新安裝和可支援的舊庫升級仍可使用。

這是防止錯誤初始化，不是自動救回已丟失資料，也不能證明一個結構健康的空庫必定沒有遺失歷史。

## 管理員處理''')
source = source.replace('公共鏡像仍停用；此資料恢復保護與素材鏡像授權是不同責任。',
                        '此資料恢復保護與素材鏡像授權是不同責任；鏡像目前行為見 [公共災備邊界](PUBLIC-MIRROR-FAIL-CLOSED.md)。')
path.write_text(source, encoding='utf-8')

path = Path('docs/PUBLIC-MIRROR-FAIL-CLOSED.md')
source = path.read_text(encoding='utf-8')
source += '''
## 同版本與來源記錄（本次未發佈小修補）

檢查過某個遠端不代表本地檔案已來自該遠端。同版本且沒有替換資源時，保留原 source_name、source_url 和鏡像批准雜湊；只有完整交易成功後才改寫來源。鏡像轉主源、切換私人源或来源未知時強制完整同步。

成功完整同步會保存 manifest_sha256。同一來源的同版本快取只有 manifest 雜湊也一致，才可略過重複下載；舊版曾遺失来源／批准資訊的快取缺少此記錄，會在下一次同步重新驗證，不能只憑版本號報成功。這不等於每次都重新校驗所有本地圖片；疑似損壞時仍可強制同步。

撤回檢查同時辨識批准雜湊、鏡像來源名稱與固定鏡像 URL，避免只改來源標籤就跳過撤回。成功完整取得主源資源後才移除旧鏡像批准記錄。批准表無法取得時仍不能推斷撤回已發生；沒有變更既有授權範圍或發布方式。
'''
path.write_text(source, encoding='utf-8')

for name in ['tests/test_existing_sqlite_preflight.py', 'tests/test_reviewed_mirror.py']:
    ast.parse(Path(name).read_text(encoding='utf-8'), filename=name)
subprocess.run(['git', 'diff', '--check'], check=True)
subprocess.run(['git', 'diff', '--stat'], check=True)
Path('/tmp/rollpig-patch-ready').write_text('exact baseline patched; full tests required before commit\n')
