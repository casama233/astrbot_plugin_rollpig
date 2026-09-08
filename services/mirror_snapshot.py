"""Fetch a complete reviewed mirror into temporary storage before game activation."""
from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urljoin

from .publication_policy import validate_publication
from .snapshot_protocol import MAX_MANIFEST, digest, parse_json, validate_manifest


def approved_review(policy_raw: bytes, manifest_raw: bytes) -> dict:
    policy = parse_json(policy_raw)
    if (not isinstance(policy, dict) or type(policy.get('schema_version')) is not int
            or policy['schema_version'] != 2 or not isinstance(policy.get('approved_snapshots'), dict)):
        raise ValueError('镜像批准清单格式无效')
    review = policy['approved_snapshots'].get(digest(manifest_raw))
    if not isinstance(review, dict) or review.get('status') != 'approved':
        raise ValueError('镜像快照未获批准或已撤回')
    return review


async def fetch_snapshot(*, root: Path, manifest_url: str, policy_raw: bytes, download) -> dict:
    raw = await download(manifest_url, MAX_MANIFEST)
    review = approved_review(policy_raw, raw)
    manifest, members = validate_manifest(raw)
    policy_path = root / 'policy.json'
    policy_path.write_bytes(policy_raw)
    snapshot = root / 'snapshot'
    snapshot.mkdir()
    (snapshot / 'manifest.json').write_bytes(raw)
    # Download only protocol-declared paths. An approval cannot introduce a
    # token, arbitrary URL, or extra file into the candidate tree.
    requests = list(members)
    if 'health.json' in review.get('files', {}):
        requests.append({'path': 'health.json', 'size': MAX_MANIFEST})
    semaphore = asyncio.Semaphore(4)

    async def fetch(member):
        async with semaphore:
            data = await download(urljoin(manifest_url, member['path']), member['size'])
        if member.get('sha256') and (len(data) != member['size'] or digest(data) != member['sha256']):
            raise ValueError('镜像文件大小或 SHA-256 不一致：' + member['path'])
        if digest(data) != review.get('files', {}).get(member['path']):
            raise ValueError('镜像文件与独立批准记录不一致：' + member['path'])
        path = snapshot / member['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        # Each file is capped at 10 MiB. Finish the write before yielding so
        # cancellation cannot leave a background writer after temp cleanup.
        path.write_bytes(data)

    tasks = [asyncio.create_task(fetch(member)) for member in requests]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    result = validate_publication(snapshot, policy_path)
    return {**result, 'root': snapshot, 'manifest': manifest}
