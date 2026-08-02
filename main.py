import asyncio
import base64
import datetime
import hashlib
import io
import json
import math
import random
import re
import shutil
import tempfile
import threading
import time
import uuid
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import httpx

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools, register
from astrbot.api.web import json_response, request
from astrbot.core import AstrBotConfig
from astrbot.core.message.components import At

# 修复导入冲突：PIL的Image重命名为PILImage
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, ImageOps


class RollPigPlugin(Star):
    PLUGIN_NAME = "astrbot_plugin_rollpig"
    IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "gif")
    CATALOG_PAGE_SIZE = 12
    CANVAS_WIDTH = 800  # 画布宽度
    CANVAS_HEIGHT = 800  # 画布高度
    AVATAR_SIZE = 280  # 头像大小
    SPACING_AVATAR_NAME = 20  # 头像与名称间距
    SPACING_NAME_DESC = 25  # 名称与描述间距
    SPACING_DESC_ANALYSIS = 30  # 描述与解析间距
    DESC_FONT_SIZE = 32  # 描述字体大小
    ANALYSIS_FONT_SIZE = 28  # 解析字体大小
    ANALYSIS_LINE_HEIGHT_FACTOR = 1.6  # 解析行高因子
    ANALYSIS_WIDTH_RATIO = 0.85  # 解析宽度比例
    NAME_FONT_SIZE = 66  # 名称字体大小
    RESOURCE_MANIFEST_MAX_SIZE = 1024 * 1024
    RESOURCE_PACKAGE_MAX_SIZE = 128 * 1024 * 1024
    RESOURCE_MAX_IMAGES = 500
    PIGHUB_API_URLS = (
        "https://pighub.top/api/images?sort=2&limit=200",
        "https://pighub.top/api/images?sort=2",
        "https://pighub.top/api/all-images",
    )
    PIGHUB_ORIGIN = "https://pighub.top/"
    PIGHUB_IMAGE_BASE_URL = "https://pighub.top/data/"
    USER_AGENT = (
        "AstrBot-RollPig/1.6 (+https://github.com/MegSopern/astrbot_plugin_rollpig)"
    )

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config or {}

        # 配置项
        self.admins_id: list[str] = context.get_config().get("admins_id", [])
        self.at_view_pig: bool = self.config.get("at_view_pig", False)
        self.enable_new_pig_pity: bool = self.config.get(
            "enable_new_pig_pity", True
        )
        try:
            pity_step = int(self.config.get("pity_step_percent", 15))
        except (TypeError, ValueError):
            pity_step = 15
        self.pity_step_percent = min(50, max(0, pity_step))
        self.enable_roast: bool = self.config.get("enable_roast", True)
        self.resource_sync_enabled = self.config.get(
            "resource_sync_enabled", True
        )
        self.resource_manifest_url = str(
            self.config.get(
                "resource_manifest_url",
                "https://pig.felislab.cc/resources/rollpig/manifest.json",
            )
            or ""
        ).strip()
        try:
            sync_hours = float(
                self.config.get("resource_sync_interval_hours", 24)
            )
        except (TypeError, ValueError):
            sync_hours = 24
        self.resource_sync_interval_hours = min(168, max(1, sync_hours))
        try:
            sync_timeout = float(self.config.get("resource_sync_timeout", 30))
        except (TypeError, ValueError):
            sync_timeout = 30
        self.resource_sync_timeout = min(120, max(2, sync_timeout))
        proxy_setting = self.config.get("resource_use_system_proxy", False)
        self.resource_use_system_proxy = (
            proxy_setting
            if isinstance(proxy_setting, bool)
            else str(proxy_setting).strip().lower() in {"1", "true", "yes", "on"}
        )
        try:
            max_file_mb = int(self.config.get("resource_max_file_size_mb", 10))
        except (TypeError, ValueError):
            max_file_mb = 10
        self.resource_max_file_size = min(50, max(1, max_file_mb)) * 1024 * 1024

        # 初始化路径
        self.plugin_dir = Path(__file__).parent
        self.plugin_data_dir = StarTools.get_data_dir("astrbot_plugin_rollpig")
        self.res_dir = self.plugin_dir / "resource"
        self.font_dir = self.res_dir / "font"  # 插件内字体目录（跨平台优先）
        self.piginfo_path = self.res_dir / "pig.json"
        self.image_dir = self.res_dir / "image"
        self.catalog_path = self.plugin_data_dir / "pig_catalog.json"
        self.local_overrides_path = self.plugin_data_dir / "local_overrides.json"
        self.tombstones_path = self.plugin_data_dir / "deleted_pigs.json"
        self.resource_root = self.plugin_data_dir / "cloud_resources"
        self.resource_active_dir = self.resource_root / "active"
        self.resource_state_path = self.resource_root / "state.json"
        self.resource_status_path = self.resource_root / "sync_status.json"
        self.pighub_cache_path = self.plugin_data_dir / "pighub_images.json"
        self.history_path = self.plugin_data_dir / "pig_history.json"
        self.custom_image_dir = self.plugin_data_dir / "images"
        self._data_lock = threading.RLock()
        self._thumbnail_cache: dict[str, tuple[int, dict]] = {}
        self._pighub_preview_cache: dict[str, dict] = {}
        self._resource_sync_lock = asyncio.Lock()
        self._pighub_lock = asyncio.Lock()
        self._background_task: asyncio.Task | None = None
        self._manual_sync_task: asyncio.Task | None = None
        self._pighub_images: list[dict] = []
        self._pighub_cached_at = 0.0

        # 创建必要目录（自动创建font文件夹）
        self.plugin_data_dir.mkdir(parents=True, exist_ok=True)
        self.font_dir.mkdir(parents=True, exist_ok=True)
        self.custom_image_dir.mkdir(parents=True, exist_ok=True)
        self.resource_root.mkdir(parents=True, exist_ok=True)

        # 初始化数据
        bundled_pigs = self.load_json(self.piginfo_path, [])
        self._bundled_pigs = self._validate_pig_records(bundled_pigs)
        self._migrate_catalog_layers()
        self._reload_catalog_layers()
        self._load_pighub_cache()
        if not self.pig_list:
            logger.error("小猪信息为空或不存在，请检查资源文件！")
        self.today_path = self.plugin_data_dir / "rollpig_today.json"
        self.history = self.load_json(
            self.history_path,
            {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}},
        )
        self._migrate_today_to_history()

        # 初始化字体（优先插件内自定义字体，跨平台兼容）
        self.font_regular = self._init_regular_font()  # 常规字体（描述/解析）
        self.font_bold = self._init_bold_font()  # 加粗字体（名称）

        # AstrBot Plugin Pages 数据接口；页面文件位于 pages/pig-manager。
        self._jsonify = json_response
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/overview",
            self.page_overview,
            ["GET"],
            "今日小猪统计总览",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/pigs",
            self.page_pigs,
            ["GET"],
            "今日小猪图鉴管理",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/pigs/save",
            self.page_pig_save,
            ["POST"],
            "新增或编辑小猪",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/pigs/delete",
            self.page_pig_delete,
            ["POST"],
            "删除小猪",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/resources/status",
            self.page_resource_status,
            ["GET"],
            "今日小猪云资源状态",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/resources/sync",
            self.page_resource_sync,
            ["POST"],
            "同步今日小猪云资源",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/pighub",
            self.page_pighub,
            ["GET"],
            "PigHub 图片挑选器",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/pighub/preview",
            self.page_pighub_preview,
            ["GET"],
            "PigHub 图片预览",
        )

        if self.resource_sync_enabled:
            try:
                self._background_task = asyncio.get_running_loop().create_task(
                    self._background_resource_sync()
                )
            except RuntimeError:
                logger.info("当前尚无事件循环，将在手动同步时检查云端资源")

    def _load_font(
        self, font_candidates: list[str | Path], size: int, purpose: str
    ) -> ImageFont.FreeTypeFont | None:
        """
        通用字体加载器，按候选顺序加载可用字体\n
        :param font_candidates: 字体路径候选列表
        :param size: 字体大小
        :param purpose: 字体用途描述
        :return: 加载的字体对象，失败则返回默认字体
        """
        for font_path in font_candidates:
            if Path(font_path).exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except Exception as e:
                    logger.warning(f"加载{purpose}字体{font_path}失败：{e}")
                    continue
        logger.warning(f"未找到{purpose}字体，使用默认字体")
        return ImageFont.load_default()

    def _init_regular_font(self) -> ImageFont.FreeTypeFont | None:
        """初始化常规字体（可爱字体，用于描述/解析）"""
        font_paths = [
            self.font_dir / "可爱字体.ttf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "常规")

    def _init_bold_font(self) -> ImageFont.FreeTypeFont | None:
        """初始化加粗字体（荆南麦圆体，用于名称）"""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Bold.otf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        return self._load_font(font_paths, self.NAME_FONT_SIZE, "加粗")

    def _get_text_size(
        self, text: str, font: ImageFont.FreeTypeFont
    ) -> tuple[int, int]:
        """
        兼容PIL不同版本的文字尺寸计算\n
        :param text: 文字内容
        :param font: 字体对象
        :return: 文字宽高元组
        """
        draw = ImageDraw.Draw(PILImage.new("RGB", (1, 1)))
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])
        except:
            return draw.textsize(text, font=font)

    def _draw_bold_text(
        self,
        draw: ImageDraw.ImageDraw,
        pos: tuple,
        text: str,
        font: ImageFont.FreeTypeFont,
        fill: tuple,
    ):
        """
        模拟文字加粗（兜底方案）\n
        :param draw: ImageDraw对象
        :param pos: 文字位置
        :param text: 文字内容
        :param font: 字体对象
        :param fill: 文字颜色
        """
        x, y = pos
        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for ox, oy in offsets:
            draw.text((x + ox, y + oy), text, fill=fill, font=font)
        draw.text((x, y), text, fill=fill, font=font)

    def load_json(self, path: Path, default):
        """
        加载JSON文件\n
        :param path: 文件路径
        :param default: 默认值（文件不存在或解析失败时使用）
        :return: 解析后的数据对象
        """
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return default
        try:
            return json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError:
            logger.error(f"JSON文件解析失败，重置为默认值：{path}")
            path.write_text(
                json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return default

    def save_json(self, path: Path, data):
        """
        保存JSON数据\n
        :param path: 文件路径
        :param data: 数据对象
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        with self._data_lock:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(payload)
                tmp_path = Path(tmp.name)
            tmp_path.replace(path)

    def _validate_pig_records(self, records) -> list[dict]:
        """校验并复制一份图鉴记录，避免坏云包污染运行中快照。"""
        if not isinstance(records, list):
            raise ValueError("pig.json 必须是数组")
        result: list[dict] = []
        seen: set[str] = set()
        for raw in records:
            if not isinstance(raw, dict):
                raise ValueError("pig.json 中存在无效记录")
            item = dict(raw)
            pig_id = str(item.get("id") or "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError(f"小猪 ID 无效：{pig_id}")
            if pig_id in seen:
                raise ValueError(f"小猪 ID 重复：{pig_id}")
            for key in ("name", "description", "analysis"):
                if not str(item.get(key) or "").strip():
                    raise ValueError(f"{pig_id} 缺少 {key}")
            item["id"] = pig_id
            seen.add(pig_id)
            result.append(item)
        return result

    def _migrate_catalog_layers(self):
        """把旧版整份 catalog 无损拆成“本地覆盖 + 删除屏蔽”。"""
        if self.local_overrides_path.exists() and self.tombstones_path.exists():
            return
        legacy = (
            self.load_json(self.catalog_path, self._bundled_pigs)
            if self.catalog_path.exists()
            else self._bundled_pigs
        )
        try:
            legacy = self._validate_pig_records(legacy)
        except ValueError as exc:
            logger.warning(f"旧图鉴无法迁移，改用内置资源：{exc}")
            legacy = self._bundled_pigs
        bundled_map = {item["id"]: item for item in self._bundled_pigs}
        legacy_ids = {item["id"] for item in legacy}
        overrides = [
            item
            for item in legacy
            if item["id"] not in bundled_map or item != bundled_map[item["id"]]
        ]
        tombstones = sorted(set(bundled_map).difference(legacy_ids))
        self.save_json(self.local_overrides_path, overrides)
        self.save_json(self.tombstones_path, tombstones)
        logger.info(
            f"图鉴已迁移为分层存储：本地覆盖 {len(overrides)}，删除屏蔽 {len(tombstones)}"
        )

    def _load_cloud_pigs(self) -> list[dict] | None:
        pig_json = self.resource_active_dir / "pig.json"
        image_dir = self.resource_active_dir / "images"
        if not pig_json.exists() or not image_dir.is_dir():
            return None
        try:
            records = self._validate_pig_records(
                json.loads(pig_json.read_text(encoding="utf-8-sig"))
            )
            for item in records:
                if not any(
                    (image_dir / f"{item['id']}.{ext}").exists()
                    for ext in self.IMAGE_EXTENSIONS
                ):
                    raise ValueError(f"云资源缺少图片：{item['id']}")
            return records
        except Exception as exc:
            logger.warning(f"云资源缓存无效，回退内置资源：{exc}")
            return None

    def _reload_catalog_layers(self):
        """云端／内置作基底，本地记录覆盖，tombstone 最后屏蔽。"""
        cloud = self._load_cloud_pigs()
        base = cloud or self._bundled_pigs
        self._catalog_source = "cloud" if cloud else "bundled"
        try:
            overrides = self._validate_pig_records(
                self.load_json(self.local_overrides_path, [])
            )
        except ValueError as exc:
            logger.error(f"本地小猪覆盖层无效，暂不加载：{exc}")
            overrides = []
        raw_tombstones = self.load_json(self.tombstones_path, [])
        tombstones = {
            str(item)
            for item in raw_tombstones
            if re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", str(item))
        }
        override_map = {item["id"]: item for item in overrides}
        merged: list[dict] = []
        used: set[str] = set()
        for item in base:
            pig_id = item["id"]
            if pig_id in tombstones:
                continue
            merged.append(dict(override_map.get(pig_id, item)))
            used.add(pig_id)
        for item in overrides:
            if item["id"] not in used and item["id"] not in tombstones:
                merged.append(dict(item))
        self.pig_list = merged
        self.save_json(self.catalog_path, merged)
        self._thumbnail_cache.clear()

    def _cloud_state(self) -> dict:
        if not self.resource_state_path.exists():
            return {}
        try:
            data = json.loads(self.resource_state_path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _sync_status(self) -> dict:
        status = {}
        if self.resource_status_path.exists():
            try:
                data = json.loads(self.resource_status_path.read_text("utf-8"))
                if isinstance(data, dict):
                    status = data
            except Exception:
                pass
        state = self._cloud_state()
        return {
            "enabled": bool(self.resource_sync_enabled),
            "source": self._catalog_source,
            "version": str(state.get("resource_version") or "builtin"),
            "last_success": int(state.get("synced_at") or 0),
            "last_attempt": int(status.get("last_attempt") or 0),
            "last_error": str(status.get("last_error") or ""),
            "interval_hours": self.resource_sync_interval_hours,
            "manifest_url": self.resource_manifest_url,
            "local_overrides": len(self.load_json(self.local_overrides_path, [])),
            "deleted_count": len(self.load_json(self.tombstones_path, [])),
            "running": bool(
                self._manual_sync_task and not self._manual_sync_task.done()
            ),
        }

    def _save_sync_status(self, *, error: str = ""):
        self.save_json(
            self.resource_status_path,
            {"last_attempt": int(time.time()), "last_error": error[:500]},
        )

    def _describe_sync_error(self, exc: Exception) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return (
                "下载逾时：云端在读取时限内没有完成响应。"
                "插件已重试并保留原有资源，请稍后再试。"
            )
        if isinstance(exc, httpx.HTTPStatusError):
            return f"云端返回 HTTP {exc.response.status_code}"
        if isinstance(exc, httpx.TransportError):
            detail = str(exc).strip() or type(exc).__name__
            return f"网络连接失败：{detail}"
        return str(exc).strip() or type(exc).__name__

    def _validate_remote_url(self, url: str, label: str):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            raise ValueError(f"{label} 必须是有效 HTTPS 地址")

    def _validate_manifest_path(self, path: str):
        parsed = urlsplit(path)
        parts = path.split("/")
        if (
            not path
            or parsed.scheme
            or parsed.netloc
            or path.startswith("/")
            or "\\" in path
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ValueError(f"manifest 文件路径无效：{path}")

    async def _download_limited(
        self,
        client: httpx.AsyncClient,
        url: str,
        max_size: int,
        attempts: int = 3,
    ) -> bytes:
        last_error: Exception | None = None
        attempts = max(1, attempts)
        for attempt in range(attempts):
            try:
                return await self._download_limited_once(client, url, max_size)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {408, 425, 429, 500, 502, 503, 504}:
                    raise
                last_error = exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
            if attempt < attempts - 1:
                delay = 0.8 * (2**attempt) + random.random() * 0.3
                logger.warning(
                    f"资源下载失败，{delay:.1f} 秒后重试 "
                    f"({attempt + 1}/{attempts})：{url} ({type(last_error).__name__})"
                )
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    async def _download_limited_once(
        self, client: httpx.AsyncClient, url: str, max_size: int
    ) -> bytes:
        total = 0
        chunks: list[bytes] = []
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            if response.url.scheme != "https":
                raise ValueError(f"远程地址发生了非 HTTPS 跳转：{url}")
            length = response.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > max_size:
                raise ValueError(f"远程文件超过大小上限：{url}")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > max_size:
                    raise ValueError(f"远程文件超过大小上限：{url}")
                chunks.append(chunk)
        return b"".join(chunks)

    def _new_http_client(
        self,
        *,
        follow_redirects: bool,
        request_timeout: float | None = None,
    ) -> httpx.AsyncClient:
        """公共资源默认直连，避免错误的环境代理阻塞 TLS；可由配置显式启用代理。"""
        timeout_seconds = (
            self.resource_sync_timeout
            if request_timeout is None
            else min(30, max(3, request_timeout))
        )
        read_timeout = (
            max(45, timeout_seconds)
            if request_timeout is None
            else timeout_seconds
        )
        options = {
            "timeout": httpx.Timeout(
                connect=timeout_seconds,
                read=read_timeout,
                write=timeout_seconds,
                pool=max(15, timeout_seconds),
            ),
            "follow_redirects": follow_redirects,
            "headers": {"User-Agent": self.USER_AGENT},
            "trust_env": self.resource_use_system_proxy,
        }
        return httpx.AsyncClient(**options)

    async def _download_manifest_item(
        self,
        client: httpx.AsyncClient,
        manifest_url: str,
        meta: dict,
        max_size: int,
    ) -> bytes:
        path = str(meta.get("path") or meta.get("filename") or "").strip()
        self._validate_manifest_path(path)
        expected_size = meta.get("size")
        if expected_size is not None and int(expected_size) > max_size:
            raise ValueError(f"文件超过大小上限：{path}")
        expected_hash = str(meta.get("sha256") or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError(f"manifest 缺少有效 SHA-256：{path}")
        data = await self._download_limited(
            client, urljoin(manifest_url, path), max_size
        )
        if expected_size is not None and len(data) != int(expected_size):
            raise ValueError(f"文件大小校验失败：{path}")
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError(f"SHA-256 校验失败：{path}")
        return data

    async def sync_cloud_resources(self, force: bool = False) -> dict:
        """事务式同步：完整下载、校验后才原子替换 active。"""
        async with self._resource_sync_lock:
            if not self.resource_manifest_url:
                raise ValueError("未配置云资源 manifest URL")
            self._validate_remote_url(self.resource_manifest_url, "manifest URL")
            staging = self.resource_root / f".incoming-{uuid.uuid4().hex}"
            previous = self.resource_root / "previous"
            try:
                async with self._new_http_client(follow_redirects=True) as client:
                    manifest_raw = await self._download_limited(
                        client,
                        self.resource_manifest_url,
                        self.RESOURCE_MANIFEST_MAX_SIZE,
                    )
                    manifest = json.loads(manifest_raw.decode("utf-8-sig"))
                    if not isinstance(manifest, dict):
                        raise ValueError("manifest 必须是 JSON 对象")
                    version = str(manifest.get("resource_version") or "").strip()
                    if not version:
                        raise ValueError("manifest 缺少 resource_version")
                    if (
                        not force
                        and version == self._cloud_state().get("resource_version")
                        and self._load_cloud_pigs()
                    ):
                        self.save_json(
                            self.resource_state_path,
                            {
                                "resource_version": version,
                                "synced_at": int(time.time()),
                            },
                        )
                        self._save_sync_status()
                        return {"updated": False, "version": version}
                    pig_meta = manifest.get("pig_json")
                    image_metas = manifest.get("images")
                    if not isinstance(pig_meta, dict):
                        raise ValueError("manifest 缺少 pig_json")
                    if not isinstance(image_metas, list):
                        raise ValueError("manifest 缺少 images")
                    if len(image_metas) > self.RESOURCE_MAX_IMAGES:
                        raise ValueError("云资源图片数量超过 500")
                    declared_total = int(pig_meta.get("size") or 0) + sum(
                        int(meta.get("size") or 0)
                        for meta in image_metas
                        if isinstance(meta, dict)
                    )
                    if declared_total > self.RESOURCE_PACKAGE_MAX_SIZE:
                        raise ValueError("云资源包声明大小超过 128 MiB")
                    pig_raw = await self._download_manifest_item(
                        client,
                        self.resource_manifest_url,
                        pig_meta,
                        min(self.resource_max_file_size, 2 * 1024 * 1024),
                    )
                    pigs = self._validate_pig_records(
                        json.loads(pig_raw.decode("utf-8-sig"))
                    )
                    staging_images = staging / "images"
                    staging_images.mkdir(parents=True, exist_ok=True)
                    (staging / "pig.json").write_bytes(pig_raw)
                    # 公共包接近两百张图；较低并发对慢速反代和家庭网络更稳定。
                    semaphore = asyncio.Semaphore(4)
                    budget_lock = asyncio.Lock()
                    package_total = len(pig_raw)

                    async def fetch_image(meta):
                        nonlocal package_total
                        if not isinstance(meta, dict):
                            raise ValueError("manifest 图片条目无效")
                        filename = str(meta.get("filename") or "")
                        if (
                            Path(filename).name != filename
                            or Path(filename).suffix.lower().lstrip(".")
                            not in self.IMAGE_EXTENSIONS
                            or not re.fullmatch(
                                r"[a-z0-9][a-z0-9_-]{0,63}",
                                Path(filename).stem,
                            )
                        ):
                            raise ValueError(f"图片文件名无效：{filename}")
                        async with semaphore:
                            data = await self._download_manifest_item(
                                client,
                                self.resource_manifest_url,
                                meta,
                                self.resource_max_file_size,
                            )
                        async with budget_lock:
                            package_total += len(data)
                            if package_total > self.RESOURCE_PACKAGE_MAX_SIZE:
                                raise ValueError("云资源包总大小超过 128 MiB")
                        return filename, data

                    downloads = await asyncio.gather(
                        *(fetch_image(meta) for meta in image_metas)
                    )
                    filenames = [filename for filename, _ in downloads]
                    if len(filenames) != len(set(filenames)):
                        raise ValueError("云资源 manifest 存在重复图片文件名")
                    for filename, data in downloads:
                        try:
                            with PILImage.open(io.BytesIO(data)) as image:
                                image.verify()
                        except Exception as exc:
                            raise ValueError(f"图片内容无效：{filename}") from exc
                        (staging_images / filename).write_bytes(data)
                    pig_ids = {item["id"] for item in pigs}
                    image_ids = {Path(name).stem for name, _ in downloads}
                    missing = pig_ids.difference(image_ids)
                    if missing:
                        raise ValueError(
                            f"云资源缺少图片：{', '.join(sorted(missing)[:10])}"
                        )

                if previous.exists():
                    shutil.rmtree(previous)
                moved_old = False
                try:
                    if self.resource_active_dir.exists():
                        self.resource_active_dir.rename(previous)
                        moved_old = True
                    staging.rename(self.resource_active_dir)
                except Exception:
                    if moved_old and previous.exists() and not self.resource_active_dir.exists():
                        previous.rename(self.resource_active_dir)
                    raise
                self.save_json(
                    self.resource_state_path,
                    {"resource_version": version, "synced_at": int(time.time())},
                )
                self._save_sync_status()
                self._reload_catalog_layers()
                return {"updated": True, "version": version}
            except Exception as exc:
                self._save_sync_status(error=self._describe_sync_error(exc))
                raise
            finally:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)

    async def _background_resource_sync(self):
        try:
            await asyncio.sleep(random.randint(30, 120))
            while True:
                try:
                    state = self._cloud_state()
                    due = time.time() - float(state.get("synced_at") or 0)
                    if due >= self.resource_sync_interval_hours * 3600:
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

    def _normalise_pighub_item(self, raw) -> dict | None:
        if not isinstance(raw, dict):
            return None
        thumbnail = raw.get("thumbnail") or raw.get("image_url")
        if not isinstance(thumbnail, str) or not thumbnail:
            return None
        if thumbnail.startswith(("http://", "https://")):
            image_url = thumbnail
        elif thumbnail.startswith("/"):
            image_url = urljoin(self.PIGHUB_ORIGIN, thumbnail)
        else:
            image_url = self.PIGHUB_IMAGE_BASE_URL + thumbnail.split("/")[-1]
        parsed = urlsplit(image_url)
        image_url = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                quote(parsed.path, safe="/%"),
                parsed.query,
                "",
            )
        )
        try:
            self._validate_pighub_image_url(image_url)
        except ValueError:
            return None
        filename = str(raw.get("filename") or parsed.path.split("/")[-1])
        return {
            "title": str(raw.get("title") or filename or "未命名小猪"),
            "filename": filename,
            "image_url": image_url,
        }

    def _load_pighub_cache(self):
        if not self.pighub_cache_path.exists():
            return
        try:
            payload = json.loads(self.pighub_cache_path.read_text("utf-8-sig"))
            images = [
                item
                for item in (
                    self._normalise_pighub_item(raw)
                    for raw in payload.get("images", [])
                )
                if item
            ]
            self._pighub_images = images
            self._pighub_cached_at = float(payload.get("cached_at") or 0)
        except Exception as exc:
            logger.warning(f"PigHub 本地索引缓存读取失败：{exc}")

    async def _refresh_pighub(self, force: bool = False) -> bool:
        if (
            not force
            and self._pighub_images
            and time.time() - self._pighub_cached_at < 12 * 3600
        ):
            return True
        async with self._pighub_lock:
            if (
                not force
                and self._pighub_images
                and time.time() - self._pighub_cached_at < 12 * 3600
            ):
                return True
            last_error = None
            async with self._new_http_client(
                follow_redirects=True, request_timeout=12
            ) as client:
                for url in self.PIGHUB_API_URLS:
                    try:
                        raw = await self._download_limited(
                            client, url, 2 * 1024 * 1024, attempts=1
                        )
                        payload = json.loads(raw.decode("utf-8-sig"))
                        if not isinstance(payload, dict):
                            raise ValueError("返回值不是 JSON 对象")
                        source = (
                            payload.get("data")
                            if isinstance(payload.get("data"), list)
                            else payload.get("images")
                        )
                        if not isinstance(source, list):
                            raise ValueError("返回值缺少 data/images")
                        images = [
                            item
                            for item in (
                                self._normalise_pighub_item(raw_item)
                                for raw_item in source
                            )
                            if item
                        ]
                        if not images:
                            raise ValueError("返回图集为空")
                        self._pighub_images = images
                        self._pighub_cached_at = time.time()
                        self.save_json(
                            self.pighub_cache_path,
                            {
                                "cached_at": int(self._pighub_cached_at),
                                "images": images,
                            },
                        )
                        return True
                    except Exception as exc:
                        last_error = exc
                        logger.warning(f"PigHub 接口不可用，尝试备用入口：{url} ({exc})")
            if self._pighub_images:
                return True
            raise ValueError(f"PigHub 暂时不可用：{last_error}")

    def _validate_pighub_image_url(self, url: str):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "pighub.top"
            or parsed.username
            or not parsed.path.startswith(("/data/", "/images/"))
        ):
            raise ValueError("只允许导入 pighub.top/data/ 或 /images/ 下的图片")

    async def _download_pighub_image(self, url: str) -> bytes:
        self._validate_pighub_image_url(url)
        async with self._new_http_client(follow_redirects=False) as client:
            return await self._download_limited(
                client, url, self.resource_max_file_size
            )

    def _migrate_today_to_history(self):
        """把升级前当天已抽取的结果补进永久图鉴，且可重复安全执行。"""
        today_cache = self.load_json(self.today_path, {"date": "", "records": {}})
        draw_date = str(today_cache.get("date") or "")
        if not draw_date:
            return
        changed = False
        for user_id, pig in today_cache.get("records", {}).items():
            changed = self._record_unlock(
                str(user_id), pig, draw_date, save=False
            ) or changed
        if changed:
            self.save_json(self.history_path, self.history)

    def _record_unlock(
        self,
        user_id: str,
        pig_data: dict,
        draw_date: str | None = None,
        *,
        save: bool = True,
    ) -> bool:
        """记录每日抽取和永久解锁。一天同一用户只统计一次。"""
        draw_date = draw_date or datetime.date.today().isoformat()
        pig_id = str(pig_data.get("id") or "").strip()
        if not pig_id:
            return False
        with self._data_lock:
            users = self.history.setdefault("users", {})
            daily = self.history.setdefault("daily", {})
            snapshots = self.history.setdefault("pig_snapshots", {})
            pig_snapshot = dict(pig_data)
            snapshot_changed = snapshots.get(pig_id) != pig_snapshot
            snapshots[pig_id] = pig_snapshot
            day = daily.setdefault(
                draw_date,
                {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
            )
            day_users = day.setdefault("users", [])
            day_records = day.setdefault("records", {})
            if user_id in day_users:
                if user_id not in day_records:
                    day_records[user_id] = pig_id
                    if save:
                        self.save_json(self.history_path, self.history)
                    return True
                if snapshot_changed and save:
                    self.save_json(self.history_path, self.history)
                return snapshot_changed

            user = users.setdefault(
                user_id,
                {"total_draws": 0, "active_days": 0, "pigs": {}},
            )
            pigs = user.setdefault("pigs", {})
            unlocked = pig_id not in pigs
            record = pigs.setdefault(
                pig_id,
                {
                    "first_unlocked": draw_date,
                    "last_drawn": draw_date,
                    "count": 0,
                },
            )
            record["last_drawn"] = draw_date
            record["count"] = int(record.get("count", 0)) + 1
            user["total_draws"] = int(user.get("total_draws", 0)) + 1
            user["active_days"] = int(user.get("active_days", 0)) + 1
            user["duplicate_streak"] = (
                0 if unlocked else int(user.get("duplicate_streak", 0)) + 1
            )
            day_users.append(user_id)
            day_records[user_id] = pig_id
            day["draws"] = int(day.get("draws", 0)) + 1
            if unlocked:
                day["new_unlocks"] = int(day.get("new_unlocks", 0)) + 1
            if save:
                self.save_json(self.history_path, self.history)
            return True

    def _get_user_collection(self, user_id: str) -> dict:
        user = self.history.get("users", {}).get(str(user_id), {})
        return user if isinstance(user, dict) else {}

    def _reload_catalog(self):
        self.pig_list = self.load_json(self.catalog_path, [])
        self._thumbnail_cache.clear()

    def _find_catalog_pig(self, pig_id: str) -> dict | None:
        return next(
            (pig for pig in self.pig_list if str(pig.get("id")) == pig_id),
            None,
        )

    def _choose_daily_pig(self, user_id: str) -> dict:
        """随机抽取；连续重复时逐步提高重抽到新猪的机会。"""
        chosen = random.choice(self.pig_list)
        if not self.enable_new_pig_pity:
            return chosen
        user = self._get_user_collection(user_id)
        unlocked_ids = set(user.get("pigs", {}))
        unseen = [
            pig for pig in self.pig_list if str(pig.get("id")) not in unlocked_ids
        ]
        if not unseen or str(chosen.get("id")) not in unlocked_ids:
            return chosen
        streak = int(user.get("duplicate_streak", 0))
        reroll_chance = min(0.80, streak * self.pity_step_percent / 100)
        return random.choice(unseen) if random.random() < reroll_chance else chosen

    def _get_daily_pig(self, user_id: str, date_value: datetime.date) -> dict | None:
        day = self.history.get("daily", {}).get(date_value.isoformat(), {})
        pig_id = str(day.get("records", {}).get(str(user_id), ""))
        if not pig_id:
            return None
        return self._find_catalog_pig(pig_id) or self.history.get(
            "pig_snapshots", {}
        ).get(pig_id)

    def find_image_file(self, pig_id: str) -> Path | None:
        """
        查找对应ID的图片文件\n
        :param pig_id: 小猪ID
        :return: 图片文件路径，未找到返回None
        """
        # 本地管理员图片永远优先，其次云端基底，最后才是插件内置兜底。
        for directory in (
            self.custom_image_dir,
            self.resource_active_dir / "images",
            self.image_dir,
        ):
            for ext in self.IMAGE_EXTENSIONS:
                file = directory / f"{pig_id}.{ext}"
                if file.exists():
                    logger.debug(f"找到的小猪图片文件：{file.absolute()}")
                    return file
        logger.warning(f"未找到小猪ID {pig_id} 对应的图片文件")
        return None

    def render_pig_image(self, pig_data: dict) -> Path | None:
        """
        整体居中渲染（垂直+水平双居中）\n
        :param pig_data: 小猪数据字典
        :return: 生成的图片临时文件路径，失败返回None
        """
        pig_id = pig_data.get("id", "")
        pig_name = pig_data.get("name", "未知小猪")
        pig_desc = pig_data.get("description", "无描述")
        pig_analysis = pig_data.get("analysis", "无解析")

        # 1. 画布基础配置
        canvas_width = self.CANVAS_WIDTH
        canvas_height = self.CANVAS_HEIGHT
        canvas = PILImage.new("RGB", (canvas_width, canvas_height), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)

        # 2. 预加载所有元素并计算尺寸（用于总高度计算）
        # 2.1 头像尺寸【核心修改：放大到280x280】
        avatar_w, avatar_h = self.AVATAR_SIZE, self.AVATAR_SIZE
        avatar = None
        avatar_path = self.find_image_file(pig_id)
        if avatar_path:
            try:
                avatar = PILImage.open(avatar_path)
                avatar.thumbnail((avatar_w, avatar_h))
                # 居中裁剪（保证正方形，适配新尺寸：280/2=140）
                if avatar.size != (avatar_w, avatar_h):
                    center_x = avatar.width // 2
                    center_y = avatar.height // 2
                    half = self.AVATAR_SIZE // 2
                    crop_box = (
                        center_x - half,
                        center_y - half,
                        center_x + half,
                        center_y + half,
                    )
                    avatar = avatar.crop(crop_box)
            except Exception as e:
                logger.error(f"加载小猪图片失败：{str(e)}")
                avatar = None

        # 2.2 名称尺寸
        name_font = self.font_bold
        name_w, name_h = self._get_text_size(pig_name, name_font)

        # 2.3 描述尺寸
        desc_font = self.font_regular.font_variant(
            size=self.DESC_FONT_SIZE
        )  # 匹配示例的描述字号
        desc_w, desc_h = self._get_text_size(pig_desc, desc_font)

        # 2.4 解析尺寸（自动换行后）
        analysis_font = self.font_regular.font_variant(size=self.ANALYSIS_FONT_SIZE)
        line_height = int(
            self.ANALYSIS_FONT_SIZE * self.ANALYSIS_LINE_HEIGHT_FACTOR
        )  # 匹配示例的行间距
        max_analysis_width = int(
            canvas_width * self.ANALYSIS_WIDTH_RATIO
        )  # 更宽的解析区域
        # 解析文字换行
        analysis_lines = []
        current_line = ""
        for char in pig_analysis:
            current_line += char
            line_w, _ = self._get_text_size(current_line, analysis_font)
            if line_w > max_analysis_width:
                analysis_lines.append(current_line[:-1])
                current_line = char
        if current_line:
            analysis_lines.append(current_line)
        # 计算解析总高度
        analysis_total_h = len(analysis_lines) * line_height

        # 3. 计算整体内容总高度（所有元素+间距）
        spacing_avatar_name = (
            self.SPACING_AVATAR_NAME
        )  # 头像放大后，间距从30调小到20，避免布局拥挤
        spacing_name_desc = self.SPACING_NAME_DESC  # 名称到描述的间距保持
        spacing_desc_analysis = self.SPACING_DESC_ANALYSIS  # 描述到解析的间距保持
        total_content_h = (
            avatar_h
            + spacing_avatar_name
            + name_h
            + spacing_name_desc
            + desc_h
            + spacing_desc_analysis
            + analysis_total_h
        )

        # 4. 计算垂直居中的起始Y坐标（核心：让整个内容块在画布中垂直居中）
        start_y = (canvas_height - total_content_h) // 2

        # 5. 绘制所有元素（基于起始Y坐标，保证整体居中）
        # 5.1 绘制头像（水平+垂直居中）
        avatar_x = (canvas_width - avatar_w) // 2
        avatar_y = start_y
        if avatar:
            canvas.paste(
                avatar,
                (avatar_x, avatar_y),
                mask=avatar if avatar.mode == "RGBA" else None,
            )
        else:
            # 头像加载失败时的提示（适配新尺寸）
            error_font = self.font_regular.font_variant(size=24)
            error_text = "图片加载失败"
            error_w, error_h = self._get_text_size(error_text, error_font)
            error_x = (canvas_width - error_w) // 2
            draw.text(
                (error_x, avatar_y + 120),  # 从90调到120，适配280高度的头像居中
                error_text,
                fill=(255, 0, 0),
                font=error_font,
            )

        # 5.2 绘制名称（水平居中）
        name_y = avatar_y + avatar_h + spacing_avatar_name
        name_x = (canvas_width - name_w) // 2
        self._draw_bold_text(draw, (name_x, name_y), pig_name, name_font, (0, 0, 0))

        # 5.3 绘制描述（水平居中）
        desc_y = name_y + name_h + spacing_name_desc
        desc_x = (canvas_width - desc_w) // 2
        draw.text((desc_x, desc_y), pig_desc, fill=(85, 85, 85), font=desc_font)

        # 5.4 绘制解析（逐行水平居中）
        analysis_y = desc_y + desc_h + spacing_desc_analysis
        for line in analysis_lines:
            line_w, line_h = self._get_text_size(line, analysis_font)
            line_x = (canvas_width - line_w) // 2
            draw.text((line_x, analysis_y), line, fill=(51, 51, 51), font=analysis_font)
            analysis_y += line_height

        # 6. 保存临时文件
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                canvas.save(tmp_path, format="PNG", quality=95)
            logger.debug(f"合成图片成功，临时文件路径：{tmp_path.absolute()}")
            if not tmp_path.exists():
                logger.error(f"临时文件创建失败：{tmp_path}")
                return None
            return tmp_path
        except Exception as e:
            logger.error(f"合成图片失败：{str(e)}")
            return None

    def _fit_card_image(self, path: Path, size: tuple[int, int]) -> PILImage.Image:
        with PILImage.open(path) as source:
            frame = ImageOps.exif_transpose(source).convert("RGBA")
            method = getattr(PILImage, "Resampling", PILImage).LANCZOS
            return ImageOps.fit(frame, size, method=method)

    def render_pigsty_image(self, user_id: str, page: int) -> tuple[Path, int]:
        """渲染用户永久图鉴；未解锁条目以灰阶卡片显示。"""
        total = len(self.pig_list)
        total_pages = max(1, math.ceil(total / self.CATALOG_PAGE_SIZE))
        page = min(max(1, page), total_pages)
        user = self._get_user_collection(user_id)
        unlocked = user.get("pigs", {}) if isinstance(user, dict) else {}
        unlocked_count = len(set(unlocked).intersection(
            str(pig.get("id")) for pig in self.pig_list
        ))
        start = (page - 1) * self.CATALOG_PAGE_SIZE
        pigs = self.pig_list[start : start + self.CATALOG_PAGE_SIZE]

        width, height = 900, 1260
        canvas = PILImage.new("RGB", (width, height), (255, 247, 244))
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=52)
        stat_font = self.font_regular.font_variant(size=26)
        name_font = self.font_bold.font_variant(size=25)
        small_font = self.font_regular.font_variant(size=20)

        draw.rounded_rectangle((28, 24, 872, 195), 30, fill=(255, 255, 255))
        draw.text((58, 45), "我的猪圈 · 永久图鉴", font=title_font, fill=(72, 44, 51))
        rate = (unlocked_count / total * 100) if total else 0
        stat = f"已解锁 {unlocked_count}/{total}  ·  收藏率 {rate:.1f}%"
        draw.text((60, 122), stat, font=stat_font, fill=(132, 91, 101))

        favorite_id = ""
        favorite_count = 0
        for item_id, record in unlocked.items():
            count = int(record.get("count", 0))
            if count > favorite_count:
                favorite_id, favorite_count = item_id, count
        favorite = self._find_catalog_pig(favorite_id) if favorite_id else None
        favorite_name = str(favorite.get("name")) if favorite else "暂无"
        favorite_name = (
            favorite_name if len(favorite_name) <= 10 else favorite_name[:9] + "…"
        )
        highest_ex = max(
            (max(0, int(record.get("count", 0)) - 1) for record in unlocked.values()),
            default=0,
        )
        growth = (
            f"本命 {favorite_name}  ·  最高 EX Lv.{highest_ex}  ·  "
            f"累计 {int(user.get('total_draws', 0))} 次"
        )
        draw.text((60, 158), growth, font=small_font, fill=(155, 109, 119))

        card_w, card_h = 260, 218
        gap_x, gap_y = 30, 28
        origin_x, origin_y = 30, 220
        for index, pig in enumerate(pigs):
            row, col = divmod(index, 3)
            x = origin_x + col * (card_w + gap_x)
            y = origin_y + row * (card_h + gap_y)
            pig_id = str(pig.get("id") or "")
            is_unlocked = pig_id in unlocked
            bg = (255, 255, 255) if is_unlocked else (232, 226, 227)
            draw.rounded_rectangle((x, y, x + card_w, y + card_h), 24, fill=bg)
            image_path = self.find_image_file(pig_id)
            if image_path:
                try:
                    thumb = self._fit_card_image(image_path, (130, 130))
                    if not is_unlocked:
                        thumb = ImageOps.grayscale(thumb).convert("RGBA")
                        shade = PILImage.new("RGBA", thumb.size, (45, 40, 42, 105))
                        thumb = PILImage.alpha_composite(thumb, shade)
                    mask = PILImage.new("L", thumb.size, 0)
                    ImageDraw.Draw(mask).rounded_rectangle(
                        (0, 0, 129, 129), 22, fill=255
                    )
                    canvas.paste(thumb.convert("RGB"), (x + 65, y + 16), mask)
                except Exception as exc:
                    logger.warning(f"渲染图鉴小猪 {pig_id} 失败：{exc}")
            name = str(pig.get("name") or "未知小猪")
            if len(name) > 9:
                name = name[:8] + "…"
            name_w, _ = self._get_text_size(name, name_font)
            draw.text(
                (x + (card_w - name_w) // 2, y + 155),
                name,
                font=name_font,
                fill=(68, 48, 54) if is_unlocked else (130, 120, 123),
            )
            count = int(unlocked[pig_id].get("count", 1)) if is_unlocked else 0
            label = f"EX Lv.{max(0, count - 1)} · ×{count}" if is_unlocked else "尚未解锁"
            label_w, _ = self._get_text_size(label, small_font)
            draw.text(
                (x + (card_w - label_w) // 2, y + 190),
                label,
                font=small_font,
                fill=(223, 91, 116) if is_unlocked else (145, 136, 139),
            )

        footer = f"第 {page}/{total_pages} 页  ·  使用 /我的猪圈 页码 翻页"
        footer_w, _ = self._get_text_size(footer, stat_font)
        draw.text(
            ((width - footer_w) // 2, 1210),
            footer,
            font=stat_font,
            fill=(132, 91, 101),
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output, page

    def render_catalog_grid(
        self, pigs: list[dict], title: str, subtitle: str
    ) -> Path:
        """为随机小猪和本地搜索渲染轻量九宫格。"""
        pigs = pigs[:9]
        rows = max(1, math.ceil(len(pigs) / 3))
        width, height = 900, 155 + rows * 245 + 30
        canvas = PILImage.new("RGB", (width, height), (255, 247, 244))
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=48)
        subtitle_font = self.font_regular.font_variant(size=23)
        name_font = self.font_bold.font_variant(size=25)
        desc_font = self.font_regular.font_variant(size=18)
        draw.rounded_rectangle((28, 22, 872, 132), 28, fill=(255, 255, 255))
        safe_title = title if len(title) <= 18 else title[:17] + "…"
        safe_subtitle = subtitle if len(subtitle) <= 36 else subtitle[:35] + "…"
        draw.text((56, 40), safe_title, font=title_font, fill=(72, 44, 51))
        draw.text((58, 98), safe_subtitle, font=subtitle_font, fill=(145, 99, 110))
        for index, pig in enumerate(pigs):
            row, col = divmod(index, 3)
            x, y = 30 + col * 290, 155 + row * 245
            draw.rounded_rectangle((x, y, x + 260, y + 218), 22, fill=(255, 255, 255))
            path = self.find_image_file(str(pig.get("id") or ""))
            if path:
                try:
                    thumb = self._fit_card_image(path, (140, 140))
                    mask = PILImage.new("L", thumb.size, 0)
                    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 139, 139), 20, fill=255)
                    canvas.paste(thumb.convert("RGB"), (x + 60, y + 12), mask)
                except Exception as exc:
                    logger.warning(f"渲染小猪列表图片失败：{exc}")
            name = str(pig.get("name") or "未知小猪")
            name = name if len(name) <= 9 else name[:8] + "…"
            name_w, _ = self._get_text_size(name, name_font)
            draw.text((x + (260 - name_w) // 2, y + 158), name, font=name_font, fill=(72, 44, 51))
            desc = str(pig.get("description") or "")
            desc = desc if len(desc) <= 14 else desc[:13] + "…"
            desc_w, _ = self._get_text_size(desc, desc_font)
            draw.text((x + (260 - desc_w) // 2, y + 193), desc, font=desc_font, fill=(145, 120, 127))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output

    def render_weekly_summary(self, user_id: str) -> Path:
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        canvas = PILImage.new("RGB", (900, 1080), (255, 247, 244))
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=50)
        body_font = self.font_bold.font_variant(size=27)
        small_font = self.font_regular.font_variant(size=20)
        draw.rounded_rectangle((28, 22, 872, 135), 28, fill=(255, 255, 255))
        draw.text((56, 40), "本周小猪周报", font=title_font, fill=(72, 44, 51))
        draw.text(
            (58, 101),
            f"{monday.isoformat()} — {(monday + datetime.timedelta(days=6)).isoformat()}",
            font=small_font,
            fill=(145, 99, 110),
        )
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        collected = 0
        for index in range(7):
            day = monday + datetime.timedelta(days=index)
            pig = self._get_daily_pig(user_id, day)
            y = 155 + index * 125
            active = day <= today
            fill = (255, 255, 255) if pig else (239, 232, 233)
            draw.rounded_rectangle((34, y, 866, y + 104), 22, fill=fill)
            draw.text((58, y + 19), weekday_names[index], font=body_font, fill=(82, 55, 63))
            draw.text((58, y + 62), f"{day.month}/{day.day}", font=small_font, fill=(150, 126, 132))
            if pig:
                collected += 1
                path = self.find_image_file(str(pig.get("id") or ""))
                if path:
                    try:
                        thumb = self._fit_card_image(path, (82, 82))
                        canvas.paste(thumb.convert("RGB"), (270, y + 11))
                    except Exception:
                        pass
                pig_name = str(pig.get("name") or "未知小猪")
                pig_desc = str(pig.get("description") or "")
                pig_name = pig_name if len(pig_name) <= 14 else pig_name[:13] + "…"
                pig_desc = pig_desc if len(pig_desc) <= 28 else pig_desc[:27] + "…"
                draw.text((378, y + 18), pig_name, font=body_font, fill=(72, 44, 51))
                draw.text((378, y + 62), pig_desc, font=small_font, fill=(145, 99, 110))
            else:
                status = "等待未来" if not active else "本日未抽取"
                draw.text((300, y + 37), status, font=body_font, fill=(155, 143, 147))
        summary = f"本周已签到 {collected}/7 天"
        summary_w, _ = self._get_text_size(summary, body_font)
        draw.text(((900 - summary_w) // 2, 1040), summary, font=body_font, fill=(216, 82, 112))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output

    def render_roast_image(self, pig: dict, user_id: str) -> Path:
        recipes = [
            ("蜜汁脆皮", "外脆里嫩，甜度刚好，今日烦恼全部烤化。"),
            ("炭火蒜香", "火候拉满，蒜香扑鼻，猪圈厨神认证出品。"),
            ("椒盐黄金", "咸香酥脆，一口下去好运值直接加满。"),
            ("慢烤照烧", "低温慢烤锁住快乐，再刷上一层闪亮好运。"),
            ("香草熔岩", "表面平静，内心滚烫，是今天最有戏的小猪料理。"),
        ]
        seed = f"{user_id}:{datetime.date.today().isoformat()}:{pig.get('id')}"
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        recipe, copy = recipes[digest[0] % len(recipes)]
        canvas = PILImage.new("RGB", (800, 870), (255, 239, 224))
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=52)
        name_font = self.font_bold.font_variant(size=38)
        body_font = self.font_regular.font_variant(size=26)
        draw.rounded_rectangle((34, 28, 766, 830), 38, fill=(255, 250, 245), outline=(236, 133, 91), width=5)
        draw.text((64, 58), "今日烤猪 · 本地料理", font=title_font, fill=(169, 72, 49))
        path = self.find_image_file(str(pig.get("id") or ""))
        if path:
            thumb = self._fit_card_image(path, (430, 430))
            warm = PILImage.new("RGBA", thumb.size, (232, 91, 38, 45))
            thumb = PILImage.alpha_composite(thumb, warm)
            canvas.paste(thumb.convert("RGB"), (185, 150))
        dish_name = f"{recipe}{pig.get('name', '小猪')}"
        dish_name = dish_name if len(dish_name) <= 16 else dish_name[:15] + "…"
        dish_w, _ = self._get_text_size(dish_name, name_font)
        draw.text(((800 - dish_w) // 2, 625), dish_name, font=name_font, fill=(133, 57, 44))
        lines, current = [], ""
        for char in copy:
            candidate = current + char
            if self._get_text_size(candidate, body_font)[0] > 640:
                lines.append(current)
                current = char
            else:
                current = candidate
        if current:
            lines.append(current)
        for index, line in enumerate(lines):
            line_w, _ = self._get_text_size(line, body_font)
            draw.text(((800 - line_w) // 2, 705 + index * 42), line, font=body_font, fill=(128, 89, 77))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output

    def get_at_ids(self, event: AstrMessageEvent) -> list[str]:
        """
        获取QQ被at用户的id列表
        :param event: Aiocqhttp消息事件对象
        :return: 被at用户的id列表（排除自己）
        """
        return [
            str(seg.qq)
            for seg in event.get_messages()
            if (isinstance(seg, At) and str(seg.qq) != event.get_self_id())  # 排除自己
        ]

    @filter.command(
        "今日小猪",
        alias={
            "今日小豬",
            "今天是什么小猪",
            "今天是什麼小豬",
            "抽小猪",
            "抽小豬",
            "我的小猪",
            "我的小豬",
            "rollpig",
        },
    )
    async def roll_pig(self, event: AstrMessageEvent):
        """抽取今日小猪／今日小豬"""
        today_str = datetime.date.today().isoformat()
        user_id = event.get_sender_id()
        if self.at_view_pig:
            parts = event.message_str.strip().split()
            at_ids = self.get_at_ids(event)
            if len(at_ids) > 1:
                await event.send(event.plain_result("一次只能抽取一个小猪哦！"))
                return
            if len(parts) >= 2 and at_ids:
                if at_ids[0] not in self.admins_id:
                    user_id = at_ids[0]
                else:
                    await event.send(event.plain_result("你这只小猪，不许对主人不敬！"))
                    return
        today_cache = self.load_json(self.today_path, {"date": "", "records": {}})
        if today_cache.get("date") != today_str:
            today_cache = {"date": today_str, "records": {}}
        user_records = today_cache["records"]

        if user_id in user_records:
            pig = user_records[user_id]
            self._record_unlock(user_id, pig, today_str)
            await self.send_rendered_pig(event, pig, user_id)
            return

        if not self.pig_list:
            await event.send(event.plain_result("小猪信息加载失败，请检查后台报错！"))
            return

        pig = self._choose_daily_pig(user_id)
        user_records[user_id] = pig
        self.save_json(self.today_path, today_cache)
        self._record_unlock(user_id, pig, today_str)

        await self.send_rendered_pig(event, pig, user_id)

    @filter.command(
        "我的猪圈",
        alias={"我的豬圈", "小猪图鉴", "小豬圖鑑", "猪圈", "豬圈"},
    )
    async def my_pigsty(self, event: AstrMessageEvent, args: str = ""):
        """查看永久解锁的小猪图鉴，可附带页码。"""
        page = 1
        raw = str(args or "").strip()
        if raw:
            try:
                page = int(raw.split()[0])
            except ValueError:
                await event.send(
                    event.plain_result("页码格式不正确，例如：/我的猪圈 2")
                )
                return
        total_pages = max(1, math.ceil(len(self.pig_list) / self.CATALOG_PAGE_SIZE))
        if page < 1 or page > total_pages:
            await event.send(
                event.plain_result(f"页码范围为 1-{total_pages}。")
            )
            return
        output = None
        try:
            output, _ = await asyncio.to_thread(
                self.render_pigsty_image, event.get_sender_id(), page
            )
            await event.send(event.image_result(str(output.absolute())))
        except Exception as exc:
            logger.error(f"生成我的猪圈失败：{exc}", exc_info=True)
            user = self._get_user_collection(event.get_sender_id())
            unlocked = len(user.get("pigs", {}))
            await event.send(
                event.plain_result(
                    f"【我的猪圈】已解锁 {unlocked}/{len(self.pig_list)}，"
                    f"图鉴图片生成失败，请查看后台日志。"
                )
            )
        finally:
            if output:
                output.unlink(missing_ok=True)

    @filter.command("昨日小猪", alias={"昨日小豬", "昨天小猪", "昨天小豬"})
    async def yesterday_pig(self, event: AstrMessageEvent):
        """查看昨天抽到的小猪。"""
        pig = self._get_daily_pig(
            event.get_sender_id(), datetime.date.today() - datetime.timedelta(days=1)
        )
        if not pig:
            await event.send(event.plain_result("昨天没有找到你的小猪记录。"))
            return
        await self.send_rendered_pig(
            event,
            pig,
            event.get_sender_id(),
            intro=". 这是你的昨日小猪：",
            fallback_title="昨日小猪",
        )

    @filter.command("明日小猪", alias={"明日小豬", "明天小猪", "明天小豬"})
    async def tomorrow_pig(self, event: AstrMessageEvent):
        """给出每天固定、但不会提前解锁图鉴的明日预测。"""
        if not self.pig_list:
            await event.send(event.plain_result("小猪图鉴为空。"))
            return
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        user_id = event.get_sender_id()
        digest = hashlib.sha256(f"{user_id}:{tomorrow.isoformat()}".encode()).digest()
        pig = self.pig_list[int.from_bytes(digest[:4], "big") % len(self.pig_list)]
        stars = 1 + digest[4] % 5
        await event.send(
            event.plain_result(
                f"明日猪运：{'★' * stars}{'☆' * (5 - stars)}（预测不会提前解锁图鉴）"
            )
        )
        await self.send_rendered_pig(
            event,
            pig,
            user_id,
            intro=". 这是你的明日小猪预测：",
            fallback_title="明日小猪预测",
        )

    @filter.command(
        "本周小猪",
        alias={"本周小豬", "本週小猪", "本週小豬", "本周猪报", "本週豬報"},
    )
    async def weekly_pigs(self, event: AstrMessageEvent):
        """生成本周七日抽取总结。"""
        output = None
        try:
            output = await asyncio.to_thread(
                self.render_weekly_summary, event.get_sender_id()
            )
            await event.send(event.image_result(str(output.absolute())))
        except Exception as exc:
            logger.error(f"生成本周小猪失败：{exc}", exc_info=True)
            await event.send(event.plain_result("本周小猪周报生成失败，请查看后台日志。"))
        finally:
            if output:
                output.unlink(missing_ok=True)

    @filter.command(
        "随机小猪",
        alias={"随机小豬", "隨機小猪", "隨機小豬", "随机猪", "隨機豬"},
    )
    async def random_pigs(self, event: AstrMessageEvent, args: str = ""):
        """从本地图鉴随机展示 1-9 只小猪，不影响每日抽取。"""
        raw = str(args or "").strip()
        try:
            amount = int(raw.split()[0]) if raw else 1
        except ValueError:
            amount = 0
        if not 1 <= amount <= 9:
            await event.send(event.plain_result("随机数量范围为 1-9，例如：/随机小猪 5"))
            return
        pigs = random.sample(self.pig_list, min(amount, len(self.pig_list)))
        output = None
        try:
            output = await asyncio.to_thread(
                self.render_catalog_grid,
                pigs,
                "随机小猪",
                f"本次随机展示 {len(pigs)} 只 · 不影响今日结果与永久解锁",
            )
            await event.send(event.image_result(str(output.absolute())))
        finally:
            if output:
                output.unlink(missing_ok=True)

    @filter.command("找猪", alias={"找豬", "搜猪", "搜豬"})
    async def find_pigs(self, event: AstrMessageEvent, keyword: str = ""):
        """在管理员维护的本地图鉴内搜索。"""
        query = str(keyword or "").strip().lower()
        if not query:
            await event.send(event.plain_result("请输入关键词，例如：/找猪 玩偶"))
            return
        matches = [
            pig
            for pig in self.pig_list
            if query
            in " ".join(
                str(pig.get(key, ""))
                for key in ("id", "name", "description", "analysis")
            ).lower()
        ]
        if not matches:
            await event.send(event.plain_result(f"没有找到与「{keyword}」相关的小猪。"))
            return
        output = None
        try:
            output = await asyncio.to_thread(
                self.render_catalog_grid,
                matches[:9],
                f"找猪 · {keyword}",
                f"共找到 {len(matches)} 只，当前展示前 {min(9, len(matches))} 只",
            )
            await event.send(event.image_result(str(output.absolute())))
        finally:
            if output:
                output.unlink(missing_ok=True)

    @filter.command("今日烤猪", alias={"今日烤豬", "烤猪", "烤豬"})
    async def roast_today_pig(self, event: AstrMessageEvent):
        """生成纯本地趣味料理卡，不改变今日结果。"""
        if not self.enable_roast:
            await event.send(event.plain_result("今日烤猪功能已在配置中关闭。"))
            return
        user_id = event.get_sender_id()
        pig = self._get_daily_pig(user_id, datetime.date.today())
        if not pig:
            await event.send(event.plain_result("请先使用 /今日小猪 抽取今天的小猪。"))
            return
        output = None
        try:
            output = await asyncio.to_thread(self.render_roast_image, pig, user_id)
            await event.send(event.image_result(str(output.absolute())))
        except Exception as exc:
            logger.error(f"生成今日烤猪失败：{exc}", exc_info=True)
            await event.send(event.plain_result("今日烤猪料理失败，请稍后再试。"))
        finally:
            if output:
                output.unlink(missing_ok=True)

    @filter.command(
        "同步小猪资源",
        alias={"同步小豬資源", "刷新小猪图鉴", "刷新小豬圖鑑"},
    )
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def sync_pig_resources_command(self, event: AstrMessageEvent):
        """管理员手动刷新公有小猪资源；本地覆盖与删除屏蔽不会被改动。"""
        try:
            result = await self.sync_cloud_resources(force=False)
            action = "已更新" if result["updated"] else "已是最新"
            await event.send(
                event.plain_result(
                    f"小猪云资源{action}：{result['version']}\n"
                    "本地新增、修改和删除屏蔽均已保留。"
                )
            )
        except Exception as exc:
            await event.send(
                event.plain_result(
                    f"小猪云资源同步失败：{self._describe_sync_error(exc)}\n"
                    "已继续使用旧缓存或内置资源。"
                )
            )

    async def send_rendered_pig(
        self,
        event: AstrMessageEvent,
        pig_data: dict,
        user_id: str,
        intro: str = ". 这是你的今日小猪：",
        fallback_title: str = "今日小猪",
    ):
        """合成并发送小猪图片"""
        # 使用线程池异步执行CPU密集型任务
        img_path = await asyncio.to_thread(self.render_pig_image, pig_data)
        if img_path and img_path.exists():
            try:
                chain = [Comp.Plain(intro)]
                group_id = event.get_group_id()
                if group_id:
                    chain.insert(0, Comp.At(qq=user_id))
                await event.send(event.chain_result(chain))
                await event.send(event.image_result(str(img_path.absolute())))
                logger.info("合成图片发送成功")
                return
            except Exception as e:
                logger.error(f"发送合成图片失败：{str(e)}")
            finally:
                try:
                    img_path.unlink(missing_ok=True)
                except Exception as cleanup_err:
                    logger.warning(f"清理临时图片失败：{cleanup_err}")

        await self.send_fallback_msg(event, pig_data, fallback_title)

    async def send_fallback_msg(
        self, event: AstrMessageEvent, pig_data: dict, title: str = "今日小猪"
    ):
        """降级发送：原始图片 + 纯文本"""
        pig_name = pig_data.get("name", "未知小猪")
        pig_desc = pig_data.get("description", "无描述")
        pig_analysis = pig_data.get("analysis", "无解析")
        pig_id = pig_data.get("id", "")

        text_msg = (
            f"【{title}】\n名称：{pig_name}\n描述：{pig_desc}\n解析：{pig_analysis}"
        )
        msg_chain = []

        avatar_path = self.find_image_file(pig_id)
        if avatar_path and avatar_path.exists():
            try:
                msg_chain.append(Comp.Image.fromFileSystem(str(avatar_path.absolute())))
            except Exception as e:
                logger.error(f"发送原始图片失败：{str(e)}")
                text_msg += "\n\n（图片发送失败，仅展示文字信息）"

        msg_chain.append(Comp.Plain(text_msg))
        await event.send(event.chain_result(msg_chain))

    def _is_same_origin_request(self, request) -> bool:
        host = request.headers.get("Host", "") if request else ""
        origin = request.headers.get("Origin", "") if request else ""
        referer = request.headers.get("Referer", "") if request else ""
        sec_fetch_site = request.headers.get("Sec-Fetch-Site", "") if request else ""
        if sec_fetch_site and sec_fetch_site not in {
            "same-origin",
            "same-site",
            "none",
        }:
            return False
        if origin:
            return host and origin.split("://", 1)[-1].split("/", 1)[0] == host
        if referer:
            return host and referer.split("://", 1)[-1].split("/", 1)[0] == host
        return sec_fetch_site == "none"

    def _catalog_aggregates(self) -> tuple[Counter, Counter]:
        draws: Counter = Counter()
        collectors: Counter = Counter()
        for user in self.history.get("users", {}).values():
            for pig_id, record in user.get("pigs", {}).items():
                draws[pig_id] += int(record.get("count", 0))
                collectors[pig_id] += 1
        return draws, collectors

    @staticmethod
    def _rgba_pixel_payload(image: PILImage.Image, size: int) -> dict:
        """返回保留透明通道的 Canvas 像素，绕过沙箱中的图片 URL。"""
        method = getattr(PILImage, "Resampling", PILImage).LANCZOS
        fitted = ImageOps.fit(image.convert("RGBA"), (size, size), method)
        return {
            "width": size,
            "height": size,
            "rgba": base64.b64encode(fitted.tobytes()).decode("ascii"),
        }

    def _thumbnail_pixels(self, pig_id: str) -> dict:
        path = self.find_image_file(pig_id)
        if not path:
            return {}
        modified = path.stat().st_mtime_ns
        cached = self._thumbnail_cache.get(pig_id)
        if cached and cached[0] == modified:
            return cached[1]
        try:
            with PILImage.open(path) as source:
                # 卡片实际显示约 180px；使用 192px 并保留 PNG 透明通道，避免
                # 低分辨率 RGB 预览被放大后看起来像破图。
                result = self._rgba_pixel_payload(ImageOps.exif_transpose(source), 192)
            self._thumbnail_cache[pig_id] = (modified, result)
            return result
        except Exception as exc:
            logger.warning(f"生成 {pig_id} 管理页缩略图失败：{exc}")
            return {}

    def _normalise_uploaded_image(self, content: str) -> bytes:
        if not content:
            raise ValueError("请选择小猪图片")
        if "," in content:
            content = content.split(",", 1)[1]
        try:
            raw = base64.b64decode(content, validate=True)
        except Exception as exc:
            raise ValueError("图片内容不是有效的 Base64 数据") from exc
        if not raw:
            raise ValueError("图片文件为空")
        if len(raw) > 10 * 1024 * 1024:
            raise ValueError("原始图片不能超过 10MB")
        return self._normalise_image_bytes(raw)

    def _normalise_image_bytes(self, raw: bytes) -> bytes:
        """上传与 PigHub 导入共用同一套 512×512 图片规范。"""
        try:
            with PILImage.open(io.BytesIO(raw)) as source:
                source.verify()
            with PILImage.open(io.BytesIO(raw)) as source:
                source = ImageOps.exif_transpose(source)
                width, height = source.size
                if width < 256 or height < 256:
                    raise ValueError("图片宽高至少需要 256×256 像素")
                if width > 8192 or height > 8192 or width * height > 25_000_000:
                    raise ValueError("图片尺寸过大，最高支持 8192×8192")
                method = getattr(PILImage, "Resampling", PILImage).LANCZOS
                normalized = ImageOps.fit(source.convert("RGBA"), (512, 512), method)
                output = io.BytesIO()
                normalized.save(output, "PNG", optimize=True)
                return output.getvalue()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("无法读取图片，请上传 PNG/JPG/WEBP/GIF") from exc

    def _write_custom_image(self, pig_id: str, data: bytes):
        target = self.custom_image_dir / f"{pig_id}.png"
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=self.custom_image_dir,
            prefix=f".{pig_id}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)
        for ext in self.IMAGE_EXTENSIONS:
            old = self.custom_image_dir / f"{pig_id}.{ext}"
            if old != target:
                old.unlink(missing_ok=True)

    async def page_overview(self):
        """管理面板：总体指标、趋势与热门小猪。"""
        try:
            today = datetime.date.today()
            users = self.history.get("users", {})
            catalog_ids = {str(pig.get("id")) for pig in self.pig_list}
            total_users = len(users)
            total_draws = sum(int(u.get("total_draws", 0)) for u in users.values())
            unlocked_counts = [
                len(set(u.get("pigs", {})).intersection(catalog_ids))
                for u in users.values()
            ]
            average_unlocked = (
                sum(unlocked_counts) / total_users if total_users else 0
            )
            average_rate = (
                average_unlocked / len(catalog_ids) * 100 if catalog_ids else 0
            )
            daily = self.history.get("daily", {})
            trend = []
            for offset in range(13, -1, -1):
                day = today - datetime.timedelta(days=offset)
                item = daily.get(day.isoformat(), {})
                trend.append(
                    {
                        "date": f"{day.month}/{day.day}",
                        "users": len(item.get("users", [])),
                        "draws": int(item.get("draws", 0)),
                        "new_unlocks": int(item.get("new_unlocks", 0)),
                    }
                )
            draws, collectors = self._catalog_aggregates()
            names = {
                str(pig.get("id")): str(pig.get("name") or pig.get("id"))
                for pig in self.pig_list
            }
            top_pigs = [
                {
                    "id": pig_id,
                    "name": names.get(pig_id, pig_id),
                    "draws": count,
                    "collectors": collectors[pig_id],
                }
                for pig_id, count in draws.most_common(10)
                if pig_id in names
            ]
            today_item = daily.get(today.isoformat(), {})
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "metrics": {
                            "total_users": total_users,
                            "total_draws": total_draws,
                            "catalog_count": len(catalog_ids),
                            "today_users": len(today_item.get("users", [])),
                            "average_unlocked": round(average_unlocked, 2),
                            "average_unlock_rate": round(average_rate, 2),
                        },
                        "trend": trend,
                        "top_pigs": top_pigs,
                    },
                }
            )
        except Exception as exc:
            logger.error(f"今日小猪管理页总览失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "获取统计数据失败"})

    async def page_pigs(self):
        """管理面板：分页检索小猪和缩略图。"""
        try:
            query = str(request.query.get("search", "") or "").strip().lower()
            try:
                page = max(1, int(request.query.get("page", 1)))
            except (TypeError, ValueError):
                page = 1
            filtered = [
                pig
                for pig in self.pig_list
                if not query
                or query
                in " ".join(
                    str(pig.get(key, ""))
                    for key in ("id", "name", "description", "analysis")
                ).lower()
            ]
            page_size = 18
            pages = max(1, math.ceil(len(filtered) / page_size))
            page = min(page, pages)
            items = filtered[(page - 1) * page_size : page * page_size]
            draws, collectors = self._catalog_aggregates()
            payload = []
            for pig in items:
                item = dict(pig)
                pig_id = str(item.get("id") or "")
                item.update(
                    {
                        "thumbnail": self._thumbnail_pixels(pig_id),
                        "draws": draws[pig_id],
                        "collectors": collectors[pig_id],
                        "custom_image": any(
                            (self.custom_image_dir / f"{pig_id}.{ext}").exists()
                            for ext in self.IMAGE_EXTENSIONS
                        ),
                    }
                )
                payload.append(item)
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "items": payload,
                        "page": page,
                        "pages": pages,
                        "total": len(filtered),
                    },
                }
            )
        except Exception as exc:
            logger.error(f"今日小猪管理页列表失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "获取小猪列表失败"})

    async def page_pig_save(self):
        """管理面板：校验、标准化图片，并新增或修改完整小猪资料。"""
        try:
            if not self._is_same_origin_request(request):
                return self._jsonify({"status": "error", "message": "请求来源无效"})
            payload = await request.json(default={})
            if not isinstance(payload, dict):
                return self._jsonify({"status": "error", "message": "请求数据无效"})
            original_id = str(payload.get("original_id") or "").strip()
            pig_id = str(payload.get("id") or "").strip().lower()
            name = str(payload.get("name") or "").strip()
            description = str(payload.get("description") or "").strip()
            analysis = str(payload.get("analysis") or "").strip()
            image_content = str(payload.get("image") or "")
            pighub_url = str(payload.get("pighub_url") or "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError("ID 仅支持 1-64 位小写字母、数字、- 和 _")
            if original_id and original_id != pig_id:
                raise ValueError("编辑时不能修改 ID；如需新 ID，请新增小猪")
            if not name or len(name) > 30:
                raise ValueError("名称必填且不能超过 30 个字符")
            if not description or len(description) > 80:
                raise ValueError("描述必填且不能超过 80 个字符")
            if not analysis or len(analysis) > 500:
                raise ValueError("文案必填且不能超过 500 个字符")

            existing = self._find_catalog_pig(original_id or pig_id)
            if not original_id and existing:
                raise ValueError("该 ID 已存在")
            if original_id and not existing:
                raise ValueError("要编辑的小猪不存在")
            if not existing and not image_content and not pighub_url:
                raise ValueError("新增小猪必须上传图片或从 PigHub 选择图片")
            if image_content:
                normalized_image = await asyncio.to_thread(
                    self._normalise_uploaded_image, image_content
                )
            elif pighub_url:
                remote_image = await self._download_pighub_image(pighub_url)
                normalized_image = await asyncio.to_thread(
                    self._normalise_image_bytes, remote_image
                )
            else:
                normalized_image = None
            record = {
                "id": pig_id,
                "name": name,
                "description": description,
                "analysis": analysis,
            }
            if pighub_url:
                record["source_url"] = pighub_url
            elif existing and existing.get("source_url"):
                record["source_url"] = existing["source_url"]
            with self._data_lock:
                overrides = self._validate_pig_records(
                    self.load_json(self.local_overrides_path, [])
                )
                override_index = next(
                    (
                        i
                        for i, item in enumerate(overrides)
                        if str(item.get("id")) == pig_id
                    ),
                    None,
                )
                if override_index is None:
                    overrides.append(record)
                else:
                    overrides[override_index] = record
                tombstones = {
                    str(item)
                    for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.discard(pig_id)
                if normalized_image:
                    self._write_custom_image(pig_id, normalized_image)
                self.save_json(self.local_overrides_path, overrides)
                self.save_json(self.tombstones_path, sorted(tombstones))
                self._reload_catalog_layers()
            logger.info(f"管理页{'编辑' if existing else '新增'}小猪：{pig_id}")
            return self._jsonify(
                {
                    "status": "ok",
                    "message": "小猪资料已保存，图片已统一为 512×512 PNG",
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"今日小猪管理页保存失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "保存小猪失败"})

    async def page_pig_delete(self):
        """管理面板：删除目录记录；历史解锁统计保留。"""
        try:
            if not self._is_same_origin_request(request):
                return self._jsonify({"status": "error", "message": "请求来源无效"})
            payload = await request.json(default={})
            pig_id = str(payload.get("id") if isinstance(payload, dict) else "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError("小猪 ID 无效")
            if not self._find_catalog_pig(pig_id):
                raise ValueError("小猪不存在")
            with self._data_lock:
                overrides = [
                    dict(item)
                    for item in self.load_json(self.local_overrides_path, [])
                    if str(item.get("id")) != pig_id
                ]
                tombstones = {
                    str(item)
                    for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.add(pig_id)
                self.save_json(self.local_overrides_path, overrides)
                self.save_json(self.tombstones_path, sorted(tombstones))
                for ext in self.IMAGE_EXTENSIONS:
                    (self.custom_image_dir / f"{pig_id}.{ext}").unlink(
                        missing_ok=True
                    )
                self._reload_catalog_layers()
            logger.info(f"管理页删除小猪：{pig_id}")
            return self._jsonify(
                {"status": "ok", "message": "小猪已删除，历史解锁统计已保留"}
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"今日小猪管理页删除失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "删除小猪失败"})

    async def page_resource_status(self):
        """管理面板：返回分层资源状态。"""
        return self._jsonify({"status": "ok", "data": self._sync_status()})

    async def page_resource_sync(self):
        """管理面板：在后台同步，避免两百张图片阻塞 Dashboard 请求。"""
        try:
            if not self._is_same_origin_request(request):
                return self._jsonify({"status": "error", "message": "请求来源无效"})
            if self._manual_sync_task and not self._manual_sync_task.done():
                return self._jsonify(
                    {
                        "status": "ok",
                        "data": {"started": False, "sync": self._sync_status()},
                        "message": "已有云资源同步任务运行中",
                    }
                )
            self._save_sync_status()
            self._manual_sync_task = asyncio.create_task(
                self._run_manual_resource_sync()
            )
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {"started": True, "sync": self._sync_status()},
                    "message": "云资源同步已在后台开始",
                }
            )
        except Exception as exc:
            message = self._describe_sync_error(exc)
            logger.warning(f"管理页启动小猪资源同步失败：{message}")
            return self._jsonify(
                {
                    "status": "error",
                    "message": f"同步启动失败，已继续使用现有资源：{message}",
                }
            )

    async def _run_manual_resource_sync(self):
        try:
            result = await self.sync_cloud_resources(force=False)
            logger.info(
                f"管理页云资源同步完成：{result.get('version')} "
                f"updated={result.get('updated')}"
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                f"管理页同步小猪资源失败：{self._describe_sync_error(exc)}"
            )

    async def page_pighub(self):
        """管理面板：搜索 PigHub 图片索引，图片本体仅在保存时由服务端下载。"""
        try:
            refresh = str(request.query.get("refresh", "0")) == "1"
            await self._refresh_pighub(force=refresh)
            query = str(request.query.get("search", "") or "").strip().lower()
            try:
                page = max(1, int(request.query.get("page", 1)))
            except (TypeError, ValueError):
                page = 1
            matches = [
                item
                for item in self._pighub_images
                if not query
                or query in f"{item['title']} {item['filename']}".lower()
            ]
            page_size = 18
            pages = max(1, math.ceil(len(matches) / page_size))
            page = min(page, pages)
            items = matches[(page - 1) * page_size : page * page_size]
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "items": items,
                        "page": page,
                        "pages": pages,
                        "total": len(matches),
                        "cached_at": int(self._pighub_cached_at),
                    },
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"管理页读取 PigHub 失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "PigHub 暂时不可用"})

    async def page_pighub_preview(self):
        """由服务端下载 PigHub 图片并以 Canvas 像素返回，避免 iframe 跨域。"""
        try:
            image_url = str(request.query.get("url", "") or "").strip()
            self._validate_pighub_image_url(image_url)
            cached = self._pighub_preview_cache.get(image_url)
            if cached:
                return self._jsonify({"status": "ok", "data": cached})
            raw = await self._download_pighub_image(image_url)

            def build_preview() -> dict:
                with PILImage.open(io.BytesIO(raw)) as source:
                    source.verify()
                with PILImage.open(io.BytesIO(raw)) as source:
                    return self._rgba_pixel_payload(
                        ImageOps.exif_transpose(source), 192
                    )

            result = await asyncio.to_thread(build_preview)
            if len(self._pighub_preview_cache) >= 32:
                self._pighub_preview_cache.pop(next(iter(self._pighub_preview_cache)))
            self._pighub_preview_cache[image_url] = result
            return self._jsonify({"status": "ok", "data": result})
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.warning(f"PigHub 图片预览失败：{self._describe_sync_error(exc)}")
            return self._jsonify(
                {"status": "error", "message": "PigHub 图片预览载入失败"}
            )

    async def terminate(self):
        """插件卸载清理"""
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        if self._manual_sync_task and not self._manual_sync_task.done():
            self._manual_sync_task.cancel()
            try:
                await self._manual_sync_task
            except asyncio.CancelledError:
                pass
        logger.info("今日小猪插件已卸载")
