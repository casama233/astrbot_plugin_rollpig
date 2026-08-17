from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from astrbot.api import logger
from astrbot.api.web import request


class PigStudioAdminMixin:
    """Server-side configuration and outbound URL policy for Pig Studio."""

    PIG_STUDIO_REFERENCE_LIMIT = 120

    def __init__(self, context, config):
        super().__init__(context, config)
        self.pig_studio_runtime_config_path = (
            self.plugin_data_dir / "pig_studio_config.json"
        )
        self._load_pig_studio_runtime_config()
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/studio/config",
            self.page_studio_config,
            ["POST"],
            "安全配置 AI 小猪工坊生图通道",
        )

    def _load_pig_studio_runtime_config(self) -> None:
        path = getattr(self, "pig_studio_runtime_config_path", None)
        if not isinstance(path, Path):
            return
        try:
            data = self.load_json(path, {})
        except Exception as exc:
            logger.warning(f"AI 小猪工坊配置读取失败，继续使用插件配置：{exc}")
            return
        if not isinstance(data, dict):
            return
        if "enabled" in data:
            self.enable_pig_studio = self._studio_bool(
                data.get("enabled"), self.enable_pig_studio
            )
        if str(data.get("base_url") or "").strip():
            self.pig_studio_image_base_url = str(data["base_url"]).strip()
        if str(data.get("api_key") or "").strip():
            self.pig_studio_image_api_key = str(data["api_key"]).strip()
        if str(data.get("model") or "").strip():
            self.pig_studio_image_model = str(data["model"]).strip()[:128]
        try:
            max_batch = int(data.get("max_batch", self.pig_studio_max_batch))
        except (TypeError, ValueError):
            max_batch = self.pig_studio_max_batch
        self.pig_studio_max_batch = min(8, max(1, max_batch))

    @staticmethod
    def _studio_validate_base_url(value: Any) -> str:
        text = str(value or "").strip().rstrip("/")
        if not text:
            return ""
        parsed = urlsplit(text)
        host = (parsed.hostname or "").lower()
        loopback = host in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError("Base URL 必须使用 HTTPS；仅本机回环地址允许 HTTP")
        if (
            not host
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Base URL 格式无效")
        return text

    def _studio_safe_base_url(self) -> str:
        value = self._studio_validate_base_url(self.pig_studio_image_base_url)
        if not value:
            raise ValueError("尚未配置 AI 小猪工坊生图 Base URL")
        return value

    def _studio_reference_options(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for pig in getattr(self, "pig_list", []):
            if not isinstance(pig, dict):
                continue
            pig_id = str(pig.get("id") or "")
            if not pig_id or pig_id == "eaten":
                continue
            try:
                path = self.find_image_file(pig_id)
            except Exception:
                path = None
            if not path:
                continue
            items.append(
                {
                    "id": pig_id,
                    "name": str(pig.get("name") or pig_id)[:40],
                    "description": str(pig.get("description") or "")[:80],
                }
            )
            if len(items) >= self.PIG_STUDIO_REFERENCE_LIMIT:
                break
        return items

    def _studio_status_payload(self) -> dict[str, Any]:
        provider = self.context.get_using_provider()
        host = ""
        if self.pig_studio_image_base_url:
            try:
                host = urlsplit(self.pig_studio_image_base_url).hostname or ""
            except ValueError:
                host = ""
        return {
            "enabled": bool(self.enable_pig_studio),
            "planning_available": provider is not None,
            "image_configured": self._studio_image_configured(),
            "api_key_present": bool(self.pig_studio_image_api_key),
            "image_model": self.pig_studio_image_model
            if self._studio_image_configured()
            else str(self.pig_studio_image_model or ""),
            "image_host": host,
            "max_batch": self.pig_studio_max_batch,
            "draft_ttl_minutes": self.PIG_STUDIO_DRAFT_TTL_SECONDS // 60,
            "reference_mode": "catalog-pig",
            "references": self._studio_reference_options(),
        }

    async def page_studio_status(self):
        try:
            return self._jsonify({"status": "ok", "data": self._studio_status_payload()})
        except Exception as exc:
            logger.error(f"读取 AI 小猪工坊状态失败：{exc}", exc_info=True)
            return self._jsonify(
                {"status": "error", "message": "读取 AI 小猪工坊状态失败"}
            )

    async def page_studio_config(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify(
                    {"status": "error", "message": "请求来源或令牌无效"}
                )
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")

            base_url = self._studio_validate_base_url(payload.get("base_url"))
            model = re.sub(
                r"\s+", " ", str(payload.get("model") or "")
            ).strip()[:128]
            if not model:
                raise ValueError("生图模型不能为空")
            try:
                max_batch = int(payload.get("max_batch", self.pig_studio_max_batch))
            except (TypeError, ValueError) as exc:
                raise ValueError("批量上限无效") from exc
            max_batch = min(8, max(1, max_batch))

            api_key = str(payload.get("api_key") or "").strip()
            clear_api_key = bool(payload.get("clear_api_key", False))
            if clear_api_key:
                next_key = ""
            elif api_key:
                if len(api_key) > 4096:
                    raise ValueError("API Key 长度异常")
                next_key = api_key
            else:
                next_key = str(self.pig_studio_image_api_key or "")

            data = {
                "enabled": self._studio_bool(payload.get("enabled"), True),
                "base_url": base_url,
                "api_key": next_key,
                "model": model,
                "max_batch": max_batch,
            }
            self.save_json(self.pig_studio_runtime_config_path, data)
            self.enable_pig_studio = bool(data["enabled"])
            self.pig_studio_image_base_url = base_url
            self.pig_studio_image_api_key = next_key
            self.pig_studio_image_model = model
            self.pig_studio_max_batch = max_batch
            return self._jsonify(
                {
                    "status": "ok",
                    "data": self._studio_status_payload(),
                    "message": "AI 小猪工坊配置已保存；API Key 不会回传到浏览器",
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"保存 AI 小猪工坊配置失败：{exc}", exc_info=True)
            return self._jsonify(
                {"status": "error", "message": "保存 AI 小猪工坊配置失败"}
            )

    async def _studio_download_generated_url(self, url: str) -> bytes:
        """Fetch provider-hosted output without becoming an arbitrary URL fetcher.

        V1 intentionally accepts external generated-image URLs only when they use
        HTTPS and resolve to the same hostname as the configured image API. Image
        providers that use a separate CDN should return a data URL instead.
        """
        parsed = urlsplit(str(url or ""))
        base = urlsplit(self._studio_safe_base_url())
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or (parsed.hostname or "").lower() != (base.hostname or "").lower()
        ):
            raise ValueError(
                "生图服务返回了非同源图片地址；请让提供商返回 base64/data URL"
            )
        timeout = min(120.0, max(10.0, float(self.ai_generation_timeout)))
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=bool(getattr(self, "resource_use_system_proxy", False)),
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            if len(response.content) > self.PIG_STUDIO_MAX_RESPONSE_BYTES:
                raise ValueError("生图服务返回的图片超过大小上限")
            return bytes(response.content)
