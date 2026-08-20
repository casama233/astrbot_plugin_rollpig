"""Felis upstream direct-read overlay for the non-commercial AstrBot client.

This feature intentionally does not create a public mirror.  It reads the
official upstream manifest, selects the audited 34 IDs, validates every byte,
and keeps the last complete local cache when the upstream is unavailable.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urljoin, urlsplit

from PIL import Image

try:
    from astrbot.api import logger
except ImportError:  # pragma: no cover - standalone unit tests
    import logging

    logger = logging.getLogger(__name__)


FELIS_DIRECT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/Felis2026/rollpig-resources/main/"
    "rollpig/manifest.json"
)
FELIS_DIRECT_SOURCE = "felis-upstream-direct"
FELIS_DIRECT_REPOSITORY_URL = "https://github.com/Felis2026/rollpig-resources"
FELIS_DIRECT_LICENSE_URL = (
    FELIS_DIRECT_REPOSITORY_URL + "/blob/main/RESOURCES-LICENSE.md"
)
FELIS_DIRECT_NOTICE = (
    "Felis 资源由非商业 Bot 客户端直接读取官方上游并在本机缓存；"
    "不在 curryudon 公共 CDN/Manifest 中重新托管。请保留来源与署名。"
)
FELIS_DIRECT_IDS = frozenset(
    {
        "awakened-pig",
        "bull-pig",
        "cage-pig",
        "cart-pig",
        "class-pig",
        "coding-pig",
        "doomsday-pig",
        "duel-pig",
        "emoji-king-pig",
        "flu-pig",
        "ground-impact-pig",
        "hannibal-pig",
        "jelly-pig",
        "katsu-rice-pig",
        "kiss-pig",
        "maid-pig",
        "mc-pig",
        "niuma-pig",
        "noob-pig",
        "parking-pig",
        "party-pig",
        "pig-rice",
        "police-pig",
        "room-check-pig",
        "samurai-pig",
        "screenshot-pig",
        "shit-pig",
        "shopping-pig",
        "smug-pig",
        "soup-pig",
        "squint-pig",
        "thief-pig",
        "trap-pig",
        "tv-pig",
    }
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class FelisDirectFeature:
    """Mixin implementing the isolated Felis overlay lifecycle."""

    FELIS_DIRECT_MANIFEST_URL = FELIS_DIRECT_MANIFEST_URL
    FELIS_DIRECT_IDS = FELIS_DIRECT_IDS
    FELIS_DIRECT_SOURCE = FELIS_DIRECT_SOURCE
    FELIS_DIRECT_NOTICE = FELIS_DIRECT_NOTICE
    FELIS_DIRECT_REPOSITORY_URL = FELIS_DIRECT_REPOSITORY_URL
    FELIS_DIRECT_LICENSE_URL = FELIS_DIRECT_LICENSE_URL
    FELIS_DIRECT_MAX_MANIFEST_SIZE = 2 * 1024 * 1024
    FELIS_DIRECT_MAX_FILE_SIZE = 10 * 1024 * 1024
    FELIS_DIRECT_MAX_TOTAL_SIZE = 32 * 1024 * 1024

    def _init_felis_direct(self) -> None:
        setting = self.config.get("felis_direct_enabled", True)
        self.felis_direct_enabled = (
            setting
            if isinstance(setting, bool)
            else str(setting).strip().lower() in {"1", "true", "yes", "on"}
        )
        configured = str(self.config.get("felis_direct_manifest_url", "") or "").strip()
        self.felis_direct_manifest_url = configured or self.FELIS_DIRECT_MANIFEST_URL
        self.felis_direct_root = self.plugin_data_dir / "felis_resources"
        self.felis_direct_active_dir = self.felis_direct_root / "active"
        self.felis_direct_state_path = self.felis_direct_root / "state.json"
        self.felis_direct_status_path = self.felis_direct_root / "status.json"
        self.felis_direct_lock = asyncio.Lock()
        self.felis_direct_root.mkdir(parents=True, exist_ok=True)
        self._recover_felis_direct_cache()

    def _felis_direct_json(self, path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, TypeError):
            return default

    def _felis_direct_atomic_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, path)

    def _felis_direct_state(self) -> dict:
        value = self._felis_direct_json(self.felis_direct_state_path, {})
        return value if isinstance(value, dict) else {}

    def _felis_direct_cached_pigs(self, active_dir: Path | None = None) -> list[dict]:
        active_dir = active_dir or self.felis_direct_active_dir
        raw = self._felis_direct_json(active_dir / "pig.json", None)
        manifest = self._felis_direct_json(active_dir / "manifest.json", None)
        image_dir = active_dir / "images"
        if not isinstance(raw, list) or not isinstance(manifest, dict) or not image_dir.is_dir():
            return []
        selected_metadata = [
            item
            for item in manifest.get("images", [])
            if isinstance(item, dict) and str(item.get("id") or "") in self.FELIS_DIRECT_IDS
        ]
        if len(selected_metadata) != len(self.FELIS_DIRECT_IDS):
            return []
        metadata = {
            str(item.get("id")): item
            for item in selected_metadata
        }
        if len(metadata) != len(self.FELIS_DIRECT_IDS):
            return []
        records: list[dict] = []
        for item in raw:
            if not isinstance(item, dict):
                return []
            pig_id = str(item.get("id") or "")
            if pig_id not in self.FELIS_DIRECT_IDS:
                return []
            if not all(str(item.get(key) or "").strip() for key in ("name", "description", "analysis")):
                return []
            meta = metadata.get(pig_id)
            if not isinstance(meta, dict):
                return []
            filename = str(meta.get("filename") or "")
            candidate = image_dir / filename
            expected_size = int(meta.get("size") or 0)
            expected_hash = str(meta.get("sha256") or "").lower().strip()
            if (
                Path(filename).name != filename
                or not candidate.is_file()
                or candidate.stat().st_size != expected_size
                or not _HASH_RE.fullmatch(expected_hash)
                or hashlib.sha256(candidate.read_bytes()).hexdigest() != expected_hash
            ):
                return []
            try:
                with Image.open(candidate) as image:
                    image.verify()
            except Exception:
                return []
            records.append(dict(item))
        return records if (
            len(records) == len(self.FELIS_DIRECT_IDS)
            and {item["id"] for item in records} == set(self.FELIS_DIRECT_IDS)
        ) else []

    def _recover_felis_direct_cache(self) -> bool:
        """Restore the last complete cache after an interrupted directory swap."""
        if self._felis_direct_cached_pigs(self.felis_direct_active_dir):
            return False
        previous = self.felis_direct_root / "previous"
        if not self._felis_direct_cached_pigs(previous):
            return False
        displaced = self.felis_direct_root / f".invalid-active-{uuid.uuid4().hex}"
        moved_invalid = self.felis_direct_active_dir.exists()
        if moved_invalid:
            self.felis_direct_active_dir.rename(displaced)
        try:
            previous.rename(self.felis_direct_active_dir)
        except Exception:
            if moved_invalid and displaced.exists() and not self.felis_direct_active_dir.exists():
                displaced.rename(self.felis_direct_active_dir)
            raise
        if displaced.exists():
            shutil.rmtree(displaced, ignore_errors=True)
        logger.warning("检测到中断的 Felis 缓存切换，已恢复最近一次完整缓存")
        return True

    def _felis_direct_status(self) -> dict:
        state = self._felis_direct_state()
        status = self._felis_direct_json(self.felis_direct_status_path, {})
        status = status if isinstance(status, dict) else {}
        cached = self._felis_direct_cached_pigs()
        current = "disabled" if not self.felis_direct_enabled else (
            "ready" if cached and not status.get("last_error") else
            "stale" if cached else "unavailable"
        )
        return {
            "enabled": bool(self.felis_direct_enabled),
            "source": self.FELIS_DIRECT_SOURCE,
            "manifest_url": self.felis_direct_manifest_url,
            "version": str(state.get("resource_version") or ""),
            "cached_ids": len(cached),
            "allowlisted_ids": len(self.FELIS_DIRECT_IDS),
            "state": current,
            "last_success_at": state.get("synced_at"),
            "last_error": str(status.get("last_error") or ""),
            "source_repository": self.FELIS_DIRECT_REPOSITORY_URL,
            "license_url": self.FELIS_DIRECT_LICENSE_URL,
            "legal_notice": self.FELIS_DIRECT_NOTICE,
        }

    def _felis_direct_validate_url(self, url: str) -> None:
        parsed = urlsplit(str(url or ""))
        expected = urlsplit(self.FELIS_DIRECT_MANIFEST_URL)
        if (
            parsed.scheme != "https"
            or parsed.netloc != expected.netloc
            or parsed.path != expected.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Felis manifest URL 仅允许官方 rollpig-resources 地址")

    @staticmethod
    def _felis_direct_validate_path(path: str) -> None:
        parsed = urlsplit(path)
        parts = str(path).split("/")
        if not path or parsed.scheme or parsed.netloc or path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in parts):
            raise ValueError(f"Felis manifest 文件路径无效：{path}")

    async def _felis_direct_download_item(self, client, base_url: str, meta: Mapping[str, Any], max_size: int) -> bytes:
        path = str(meta.get("path") or meta.get("filename") or "").strip()
        self._felis_direct_validate_path(path)
        expected_size = int(meta.get("size") or 0)
        expected_hash = str(meta.get("sha256") or "").lower().strip()
        if expected_size <= 0 or expected_size > max_size or not _HASH_RE.fullmatch(expected_hash):
            raise ValueError(f"Felis 文件元数据无效：{path}")
        data = await self._download_limited(client, urljoin(base_url, path), max_size)
        if len(data) != expected_size:
            raise ValueError(f"Felis 文件大小校验失败：{path}")
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError(f"Felis 文件 SHA-256 校验失败：{path}")
        return data

    async def sync_felis_direct_resources(self, force: bool = False) -> dict:
        """Download only the allowlist and atomically replace the local cache."""
        cached = self._felis_direct_cached_pigs()
        if not self.felis_direct_enabled:
            return {"updated": False, "version": str(self._felis_direct_state().get("resource_version") or ""), "cached": bool(cached)}
        async with self.felis_direct_lock:
            self._felis_direct_validate_url(self.felis_direct_manifest_url)
            staging = self.felis_direct_root / f".incoming-{uuid.uuid4().hex}"
            try:
                async with self._new_http_client(follow_redirects=False, extra_headers=self._resource_request_headers()) as client:
                    manifest_raw = await self._download_limited(client, self.felis_direct_manifest_url, self.FELIS_DIRECT_MAX_MANIFEST_SIZE)
                    manifest = json.loads(manifest_raw.decode("utf-8-sig"))
                    if not isinstance(manifest, dict) or manifest.get("schema_version") not in (1, "1"):
                        raise ValueError("Felis manifest 协议版本不受支持")
                    version = str(manifest.get("resource_version") or "").strip()
                    if not version:
                        raise ValueError("Felis manifest 缺少 resource_version")
                    if not force and version == str(self._felis_direct_state().get("resource_version") or "") and len(cached) == len(self.FELIS_DIRECT_IDS):
                        now = int(time.time())
                        self._felis_direct_atomic_json(self.felis_direct_state_path, {"resource_version": version, "synced_at": now, "source": self.felis_direct_manifest_url, "allowlisted_ids": sorted(self.FELIS_DIRECT_IDS)})
                        self._felis_direct_atomic_json(self.felis_direct_status_path, {"last_success_at": now, "last_error": "", "source": self.FELIS_DIRECT_SOURCE})
                        return {"updated": False, "version": version, "cached": True}
                    pig_meta, image_metas = manifest.get("pig_json"), manifest.get("images")
                    if not isinstance(pig_meta, dict) or not isinstance(image_metas, list):
                        raise ValueError("Felis manifest 缺少 pig_json/images")
                    pig_raw = await self._felis_direct_download_item(client, self.felis_direct_manifest_url, pig_meta, self.FELIS_DIRECT_MAX_FILE_SIZE)
                    pig_data = json.loads(pig_raw.decode("utf-8-sig"))
                    if not isinstance(pig_data, list):
                        raise ValueError("Felis pig.json 必须是数组")
                    records = [dict(item) for item in pig_data if isinstance(item, dict) and str(item.get("id") or "") in self.FELIS_DIRECT_IDS]
                    if (
                        len(records) != len(self.FELIS_DIRECT_IDS)
                        or {item["id"] for item in records} != set(self.FELIS_DIRECT_IDS)
                    ):
                        raise ValueError("Felis pig.json 未包含完整 34 项 allowlist")
                    if any(
                        not all(str(item.get(key) or "").strip() for key in ("name", "description", "analysis"))
                        for item in records
                    ):
                        raise ValueError("Felis pig.json 存在不完整记录")
                    metadata = {}
                    for item in image_metas:
                        if not isinstance(item, dict):
                            continue
                        pig_id = str(item.get("id") or "")
                        if pig_id in self.FELIS_DIRECT_IDS:
                            if pig_id in metadata:
                                raise ValueError(f"Felis 图片重复：{pig_id}")
                            metadata[pig_id] = item
                    if set(metadata) != set(self.FELIS_DIRECT_IDS):
                        raise ValueError("Felis manifest 未包含完整 34 项图片 allowlist")
                    staging_images = staging / "images"
                    staging_images.mkdir(parents=True, exist_ok=True)
                    (staging / "pig.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    total = len(pig_raw)
                    selected = {"schema_version": 1, "resource_version": version, "source": self.felis_direct_manifest_url, "allowlisted_ids": sorted(self.FELIS_DIRECT_IDS), "images": []}
                    for pig_id in sorted(self.FELIS_DIRECT_IDS):
                        meta = metadata[pig_id]
                        filename = str(meta.get("filename") or Path(str(meta.get("path") or "")).name)
                        if Path(filename).name != filename or Path(filename).stem != pig_id:
                            raise ValueError(f"Felis 图片文件名与 ID 不匹配：{filename}")
                        data = await self._felis_direct_download_item(client, self.felis_direct_manifest_url, meta, self.FELIS_DIRECT_MAX_FILE_SIZE)
                        total += len(data)
                        if total > self.FELIS_DIRECT_MAX_TOTAL_SIZE:
                            raise ValueError("Felis overlay 超过总大小上限")
                        try:
                            with Image.open(io.BytesIO(data)) as image:
                                image.verify()
                            with Image.open(io.BytesIO(data)) as image:
                                if not image.width or not image.height or image.width > 8192 or image.height > 8192:
                                    raise ValueError("图片尺寸无效")
                        except Exception as exc:
                            raise ValueError(f"Felis 图片校验失败：{filename}") from exc
                        canonical = f"{pig_id}{Path(filename).suffix.lower()}"
                        (staging_images / canonical).write_bytes(data)
                        selected["images"].append({"id": pig_id, "path": str(meta.get("path") or ""), "filename": canonical, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
                    (staging / "manifest.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    (staging / "NOTICE.md").write_text(f"来源：{self.FELIS_DIRECT_REPOSITORY_URL}\n资源协议：{self.FELIS_DIRECT_LICENSE_URL}\n\n{self.FELIS_DIRECT_NOTICE}\n版本：{version}\n", encoding="utf-8")
                    previous = self.felis_direct_root / "previous"
                    if previous.exists():
                        shutil.rmtree(previous)
                    moved_old = self.felis_direct_active_dir.exists()
                    if moved_old:
                        self.felis_direct_active_dir.rename(previous)
                    try:
                        staging.rename(self.felis_direct_active_dir)
                    except Exception:
                        if moved_old and previous.exists() and not self.felis_direct_active_dir.exists():
                            previous.rename(self.felis_direct_active_dir)
                        raise
                    now = int(time.time())
                    self._felis_direct_atomic_json(self.felis_direct_state_path, {"resource_version": version, "synced_at": now, "source": self.felis_direct_manifest_url, "allowlisted_ids": sorted(self.FELIS_DIRECT_IDS)})
                    self._felis_direct_atomic_json(self.felis_direct_status_path, {"last_success_at": now, "last_error": "", "source": self.FELIS_DIRECT_SOURCE})
                    self.resource_read_service.clear_cache()
                    self._reload_catalog_layers()
                    return {"updated": True, "version": version, "cached": True}
            except Exception as exc:
                self._felis_direct_atomic_json(self.felis_direct_status_path, {"last_error": str(exc), "failed_at": int(time.time()), "source": self.FELIS_DIRECT_SOURCE})
                if cached:
                    return {"updated": False, "version": str(self._felis_direct_state().get("resource_version") or ""), "cached": True, "stale": True}
                raise
            finally:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)

    async def _background_felis_direct_sync(self):
        """Keep the direct overlay fresh while retaining offline cache."""
        try:
            await asyncio.sleep(5)
            while True:
                try:
                    await self.sync_felis_direct_resources()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(f"Felis 直读资源同步失败，继续使用最近缓存：{exc}")
                interval = float(getattr(self, "resource_sync_interval_hours", 6) or 6)
                await asyncio.sleep(min(3600, max(1, interval) * 3600))
        except asyncio.CancelledError:
            pass
