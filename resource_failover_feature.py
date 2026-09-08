"""Official public-resource failover for RollPig.

The production curryudon source remains authoritative. Public disaster-recovery
mirrors accept only complete snapshots matching the independent reviewed
publication policy. Custom/private resource sources keep their existing semantics.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
import tempfile
from pathlib import Path

try:
    from .services.mirror_snapshot import approved_review, fetch_snapshot
    from .services.publication_policy import validate_publication
    from .services.snapshot_protocol import MAX_PROVENANCE, parse_json
except ImportError:
    from services.mirror_snapshot import approved_review, fetch_snapshot
    from services.publication_policy import validate_publication
    from services.snapshot_protocol import MAX_PROVENANCE, parse_json
from urllib.parse import urlsplit

from astrbot.api import logger


class ResourceFailoverMixin:
    """Add ordered official-source failover without changing custom-source semantics."""

    VERCEL_RESOURCE_MANIFEST_URL = (
        "https://rollpig-public-source-mirror.vercel.app/v1/manifest.json"
    )
    GITHUB_RESOURCE_MANIFEST_URL = (
        "https://raw.githubusercontent.com/casama233/rollpig-public-source-mirror/"
        "main/public/v1/manifest.json"
    )

    # The authority for mirror approval is fixed independently of mirror URLs.
    MIRROR_POLICY_URL = (
        "https://api.github.com/repos/casama233/rollpig-public-source-mirror/"
        "contents/publication-approvals.json?ref=main"
    )
    PUBLIC_MIRROR_FAIL_CLOSED = False

    def __init__(self, context, config):
        config_view = config if hasattr(config, "get") else {}
        self.resource_vercel_mirror_url = str(
            config_view.get(
                "resource_vercel_mirror_url",
                self.VERCEL_RESOURCE_MANIFEST_URL,
            )
            or ""
        ).strip()
        github_setting = config_view.get("resource_github_fallback_enabled", True)
        self.resource_github_fallback_enabled = (
            github_setting
            if isinstance(github_setting, bool)
            else str(github_setting).strip().lower() in {"1", "true", "yes", "on"}
        )
        self.resource_github_mirror_url = str(
            config_view.get(
                "resource_github_mirror_url",
                self.GITHUB_RESOURCE_MANIFEST_URL,
            )
            or ""
        ).strip()
        super().__init__(context, config)

    @staticmethod
    def _official_resource_version_key(value: object) -> tuple[int, ...] | None:
        text = str(value or "").strip()
        if not re.fullmatch(r"\d+(?:\.\d+)+", text):
            return None
        return tuple(int(part) for part in text.split("."))

    def _official_resource_sources(self) -> list[tuple[str, str]]:
        """Return the ordered source chain, deduplicated by normalized URL."""
        configured = str(getattr(self, "resource_manifest_url", "") or "").strip()
        primary = str(getattr(self, "OFFICIAL_RESOURCE_MANIFEST_URL", "") or "").strip()
        if configured != primary:
            # A private/custom source is an explicit operator choice. Never leak
            # into the public source chain behind their back.
            return [("custom", configured)] if configured else []

        if self.PUBLIC_MIRROR_FAIL_CLOSED:
            # Do not consult Vercel/GitHub even when legacy persisted config still
            # points at them. A primary outage must fall back to the client's last
            # validated local cache/bundled resources, not an unaudited mirror.
            return [("primary", primary)] if primary else []

        candidates: list[tuple[str, str]] = [("primary", primary)]
        if self.resource_vercel_mirror_url == self.VERCEL_RESOURCE_MANIFEST_URL:
            candidates.append(("vercel", self.resource_vercel_mirror_url))
        if (self.resource_github_fallback_enabled
                and self.resource_github_mirror_url == self.GITHUB_RESOURCE_MANIFEST_URL):
            candidates.append(("github", self.resource_github_mirror_url))

        result: list[tuple[str, str]] = []
        seen: set[str] = set()
        for name, url in candidates:
            normalized = url.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append((name, normalized))
        return result

    async def _probe_official_resource_manifest(self, url: str) -> str:
        """Strictly preflight an official source before transactional sync."""
        self._validate_remote_url(url, "manifest URL")
        async with self._new_http_client(
            follow_redirects=True,
            request_timeout=min(12.0, float(self.resource_sync_timeout)),
            extra_headers=self._resource_request_headers(),
        ) as client:
            raw = await self._download_limited(
                client,
                url,
                self.RESOURCE_MANIFEST_MAX_SIZE,
                attempts=1,
            )
        manifest = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest 必须是 JSON 对象")
        if manifest.get("schema_version") not in (1, "1"):
            raise ValueError("镜像资源源缺少 Resource Protocol v1 标识")
        if str(manifest.get("client") or "").strip() != self.RESOURCE_CLIENT_ID:
            raise ValueError("镜像资源源客户端标识不匹配")
        version = str(manifest.get("resource_version") or "").strip()
        if not version:
            raise ValueError("manifest 缺少 resource_version")
        return version

    def _fallback_would_downgrade(self, candidate_version: str) -> bool:
        current_version = str(self._cloud_state().get("resource_version") or "").strip()
        current_key = self._official_resource_version_key(current_version)
        candidate_key = self._official_resource_version_key(candidate_version)
        return bool(
            current_key is not None
            and candidate_key is not None
            and candidate_key < current_key
        )

    def _record_resource_origin(self, source_name: str, source_url: str) -> None:
        state = dict(self._cloud_state())
        if not state:
            return
        state["source_name"] = source_name
        state["source_url"] = source_url
        self.save_json(self.resource_state_path, state)

    async def sync_cloud_resources(self, force: bool = False) -> dict:
        # Hold this across preflight, policy validation, staging and origin save;
        # the base lock alone does not protect temporary source selection.
        if not hasattr(self, "_resource_failover_lock"):
            self._resource_failover_lock = asyncio.Lock()
        async with self._resource_failover_lock:
            return await self._sync_with_failover(force)

    async def _sync_with_failover(self, force: bool) -> dict:
        configured_url = str(getattr(self, "resource_manifest_url", "") or "").strip()
        sources = self._official_resource_sources()
        if not sources or sources[0][0] == "custom":
            result = await super().sync_cloud_resources(force=force)
            if configured_url:
                self._record_resource_origin("custom", configured_url)
            return result

        self._resource_sync_sources = sources
        failures: list[str] = []
        try:
            for source_name, source_url in sources:
                try:
                    if source_name != "primary":
                        result = await self._sync_reviewed_mirror(source_name, source_url, force)
                        return {**result, "source": source_name, "source_url": source_url}
                    await self._probe_official_resource_manifest(source_url)
                    self.resource_manifest_url = source_url
                    result = await super().sync_cloud_resources(force=force)
                    self._record_resource_origin(source_name, source_url)
                    if failures:
                        logger.warning(
                            "公共猪源已自动切换到 %s；此前失败：%s",
                            source_name,
                            "；".join(failures),
                        )
                    return {
                        **result,
                        "source": source_name,
                        "source_url": source_url,
                    }
                except Exception as exc:
                    host = str(urlsplit(source_url).hostname or source_name)
                    failures.append(f"{source_name}({host}): {type(exc).__name__}: {exc}")
                    logger.warning(
                        "公共猪源 %s 不可用，尝试下一优先级来源：%s",
                        source_name,
                        exc,
                    )
        finally:
            self.resource_manifest_url = configured_url
            self._resource_sync_sources = None

        message = "公共猪源全部不可用；继续使用最近一次已验证缓存或内置资源：" + "；".join(
            failures
        )
        self._save_sync_status(error=message)
        raise ValueError(message)

    async def _read_mirror_policy(self) -> bytes:
        async with self._new_http_client(
            follow_redirects=False,
            request_timeout=min(12.0, float(self.resource_sync_timeout)),
            extra_headers={"Accept": "application/vnd.github.raw+json", "Cache-Control": "no-cache"},
        ) as client:
            raw = await super()._download_limited(
                client, self.MIRROR_POLICY_URL + "&checked=" + str(time.time_ns()),
                MAX_PROVENANCE, attempts=1,
            )
        policy = parse_json(raw)
        if (not isinstance(policy, dict) or type(policy.get("schema_version")) is not int
                or policy["schema_version"] != 2 or not isinstance(policy.get("approved_snapshots"), dict)):
            raise ValueError("镜像批准清单格式无效")
        return raw

    def _withdraw_revoked_mirror_cache(self, policy_raw: bytes) -> None:
        state = self._cloud_state()
        if state.get("source_name") not in {"vercel", "github"}:
            return
        previous_hash = state.get("approved_manifest_sha256")
        review = parse_json(policy_raw)["approved_snapshots"].get(previous_hash, {})
        if previous_hash and review.get("status") == "approved":
            return
        # Keep recovery materials, but remove withdrawn files from active lookup.
        active = self.resource_active_dir
        if active.exists():
            quarantined = self.resource_root / (".withdrawn-" + str(time.time_ns()))
            active.rename(quarantined)
        self.save_json(self.resource_state_path, {})
        self._reload_catalog_layers()
        self._save_sync_status(error="已撤回的镜像缓存已停用，继续使用内置及本地资源")

    async def _sync_reviewed_mirror(self, source_name, source_url, force):
        policy_raw = await self._read_mirror_policy()
        self._withdraw_revoked_mirror_cache(policy_raw)
        with tempfile.TemporaryDirectory(prefix=".mirror-review-", dir=self.resource_root) as temporary:
            async with self._new_http_client(
                follow_redirects=False, extra_headers=self._resource_request_headers(),
            ) as client:
                async def download(url, limit):
                    return await super(ResourceFailoverMixin, self)._download_limited(
                        client, url, limit, attempts=1,
                    )
                candidate = await fetch_snapshot(
                    root=Path(temporary), manifest_url=source_url,
                    policy_raw=policy_raw, download=download,
                )
            if self._fallback_would_downgrade(candidate["resource_version"]):
                raise ValueError("备用源版本旧于本地，拒绝降级")
            # Recheck after downloads. A withdrawal during transfer must not win
            # a race with activation, even when the resource version is unchanged.
            latest_policy = await self._read_mirror_policy()
            self._withdraw_revoked_mirror_cache(latest_policy)
            approved_review(latest_policy, (candidate["root"] / "manifest.json").read_bytes())
            (Path(temporary) / "policy.json").write_bytes(latest_policy)
            validate_publication(candidate["root"], Path(temporary) / "policy.json")
            self.resource_manifest_url = source_url
            self._reviewed_mirror_snapshot = (source_url.rsplit("/", 1)[0] + "/", candidate["root"])
            try:
                result = await super().sync_cloud_resources(force=True)
            finally:
                self._reviewed_mirror_snapshot = None
            self._record_resource_origin(source_name, source_url)
            state = self._cloud_state()
            state["approved_manifest_sha256"] = candidate["manifest_sha256"]
            self.save_json(self.resource_state_path, state)
            return result

    async def _download_limited(self, client, url, max_size, attempts=3):
        reviewed = getattr(self, "_reviewed_mirror_snapshot", None)
        if reviewed and url.startswith(reviewed[0]):
            relative = url[len(reviewed[0]):]
            from_path = reviewed[1] / relative
            if not from_path.resolve().is_relative_to(reviewed[1].resolve()):
                raise ValueError("镜像路径越界")
            raw = from_path.read_bytes()
            if len(raw) > max_size:
                raise ValueError("镜像文件超过单档大小限制")
            return raw
        return await super()._download_limited(client, url, max_size, attempts=attempts)

    def _initial_resource_sync_delay_seconds(self, *, damaged_cache: bool) -> int:
        """Fresh lightweight installs should expand quickly without a startup herd."""
        if damaged_cache:
            return 5
        state = self._cloud_state()
        if not str(state.get("resource_version") or "").strip():
            return random.randint(3, 10)
        return random.randint(30, 120)

    async def _background_resource_sync(self):
        """Keep the base sync loop semantics but accelerate a first-ever sync."""
        try:
            damaged_cache = self._cloud_cache_needs_repair()
            await asyncio.sleep(
                self._initial_resource_sync_delay_seconds(damaged_cache=damaged_cache)
            )
            while True:
                try:
                    state = self._cloud_state()
                    due = time.time() - float(state.get("synced_at") or 0)
                    if self._cloud_cache_needs_repair():
                        logger.warning("检测到云资源缓存不完整，立即尝试原子重新同步")
                        await self.sync_cloud_resources(force=True)
                    elif due >= self.resource_sync_interval_hours * 3600:
                        await self.sync_cloud_resources()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(f"今日小猪云资源后台同步失败，继续使用现有资源：{exc}")
                await asyncio.sleep(
                    min(3600, self.resource_sync_interval_hours * 3600)
                )
        except asyncio.CancelledError:
            pass

    def _sync_status(self) -> dict:
        payload = super()._sync_status()
        if not isinstance(payload, dict):
            return payload
        state = self._cloud_state()
        payload["active_remote_source"] = str(state.get("source_name") or "")
        payload["active_remote_url"] = str(state.get("source_url") or "")
        payload["public_mirror_fail_closed"] = bool(self.PUBLIC_MIRROR_FAIL_CLOSED)
        payload["public_mirror_policy"] = "reviewed-snapshot-only"
        payload["approved_manifest_sha256"] = str(state.get("approved_manifest_sha256") or "")
        payload["source_chain"] = [
            {"name": name, "url": url}
            for name, url in (getattr(self, "_resource_sync_sources", None) or self._official_resource_sources())
        ]
        return payload
