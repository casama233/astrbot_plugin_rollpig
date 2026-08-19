"""Official public-resource failover for RollPig.

The production curryudon source remains authoritative. Vercel and GitHub are
read-only disaster-recovery mirrors and are only consulted when the configured
source is the official RollPig source and a higher-priority source cannot be
used.
"""

from __future__ import annotations

import json
import re
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

        candidates: list[tuple[str, str]] = [("primary", primary)]
        if self.resource_vercel_mirror_url:
            candidates.append(("vercel", self.resource_vercel_mirror_url))
        if self.resource_github_fallback_enabled and self.resource_github_mirror_url:
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
        """Cheap strict probe before a potentially expensive full package sync."""
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
        configured_url = str(getattr(self, "resource_manifest_url", "") or "").strip()
        sources = self._official_resource_sources()
        if not sources or sources[0][0] == "custom":
            result = await super().sync_cloud_resources(force=force)
            if configured_url:
                self._record_resource_origin("custom", configured_url)
            return result

        failures: list[str] = []
        try:
            for source_name, source_url in sources:
                try:
                    candidate_version = await self._probe_official_resource_manifest(
                        source_url
                    )
                    if source_name != "primary" and self._fallback_would_downgrade(
                        candidate_version
                    ):
                        current = str(
                            self._cloud_state().get("resource_version") or ""
                        ).strip()
                        raise ValueError(
                            f"备用源版本 {candidate_version} 旧于本地 {current}，拒绝降级"
                        )

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

        message = "公共猪源全部不可用；继续使用最近一次已验证缓存或内置资源：" + "；".join(
            failures
        )
        self._save_sync_status(error=message)
        raise ValueError(message)

    def _sync_status(self) -> dict:
        payload = super()._sync_status()
        if not isinstance(payload, dict):
            return payload
        state = self._cloud_state()
        payload["active_remote_source"] = str(state.get("source_name") or "")
        payload["active_remote_url"] = str(state.get("source_url") or "")
        payload["source_chain"] = [
            {"name": name, "url": url}
            for name, url in self._official_resource_sources()
        ]
        return payload
