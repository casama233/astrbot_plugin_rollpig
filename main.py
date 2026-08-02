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
    PIGHUB_THUMBNAIL_SIZE = 160
    PIGHUB_THUMBNAIL_TTL = 7 * 24 * 3600
    PIGHUB_THUMBNAIL_MEMORY_LIMIT = 72
    PIGHUB_THUMBNAIL_FAILURE_TTL = 10 * 60
    ROAST_FORBIDDEN_IDS = {"human", "eaten", "mc_porkchop"}
    ROAST_FORBIDDEN_NAMES = {"人类", "人類", "吃掉了", "熟食形态", "熟食形態"}
    GROUP_ROAST_COOLDOWN_SECONDS = 8 * 60 * 60
    USER_AGENT = (
        "AstrBot-RollPig/1.8 (+https://github.com/casama233/astrbot_plugin_rollpig)"
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
        self.enable_group_roast: bool = self.config.get("enable_group_roast", True)
        self.enable_ai_roast_copy: bool = self.config.get("enable_ai_roast_copy", False)
        try:
            cooldown_hours = float(
                self.config.get(
                    "group_roast_cooldown_hours",
                    self.GROUP_ROAST_COOLDOWN_SECONDS / 3600,
                )
            )
        except (TypeError, ValueError):
            cooldown_hours = 8
        self.group_roast_cooldown_seconds = int(
            min(72, max(1, cooldown_hours)) * 60 * 60
        )
        image_theme = str(self.config.get("image_theme", "auto") or "auto").lower()
        self.image_theme = image_theme if image_theme in {"auto", "light", "dark"} else "auto"
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
        self.pighub_thumbnail_dir = self.plugin_data_dir / "pighub_thumbnails"
        self.history_path = self.plugin_data_dir / "pig_history.json"
        self.roast_state_path = self.plugin_data_dir / "roast_state.json"
        self.custom_image_dir = self.plugin_data_dir / "images"
        self._data_lock = threading.RLock()
        self._thumbnail_cache: dict[str, tuple[int, dict]] = {}
        self._pighub_preview_cache: dict[str, dict] = {}
        self._pighub_thumbnail_cache: dict[str, dict] = {}
        self._pighub_thumbnail_locks: dict[str, asyncio.Lock] = {}
        self._pighub_thumbnail_failures: dict[str, float] = {}
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
        self.pighub_thumbnail_dir.mkdir(parents=True, exist_ok=True)

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
        self.roast_state = self.load_json(
            self.roast_state_path,
            {"version": 1, "cooldowns": {}, "daily_backdoors": {}},
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
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/pighub/thumbnail",
            self.page_pighub_thumbnail,
            ["GET"],
            "PigHub 缓存缩略图",
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

    def _image_palette(self, now: datetime.datetime | None = None) -> dict[str, tuple[int, int, int] | bool]:
        """返回图片卡片的日／夜配色；自动模式在 19:00 至次日 06:59 使用夜色。"""
        current = now or datetime.datetime.now().astimezone()
        is_night = (
            self.image_theme == "dark"
            or (self.image_theme == "auto" and (current.hour >= 19 or current.hour < 7))
        )
        if is_night:
            return {
                "night": True,
                "canvas": (28, 22, 30),
                "surface": (48, 38, 48),
                "surface_muted": (62, 51, 61),
                "title": (255, 229, 238),
                "body": (239, 214, 225),
                "secondary": (209, 170, 186),
                "muted": (174, 144, 157),
                "accent": (255, 119, 158),
                "locked": (59, 52, 58),
                "locked_text": (174, 161, 168),
                "roast_canvas": (39, 25, 24),
                "roast_surface": (65, 38, 35),
                "roast_outline": (222, 116, 80),
                "roast_title": (255, 194, 158),
                "roast_body": (245, 203, 181),
            }
        return {
            "night": False,
            "canvas": (255, 247, 244),
            "surface": (255, 255, 255),
            "surface_muted": (239, 232, 233),
            "title": (72, 44, 51),
            "body": (82, 55, 63),
            "secondary": (145, 99, 110),
            "muted": (155, 109, 119),
            "accent": (223, 91, 116),
            "locked": (232, 226, 227),
            "locked_text": (130, 120, 123),
            "roast_canvas": (255, 239, 224),
            "roast_surface": (255, 250, 245),
            "roast_outline": (236, 133, 91),
            "roast_title": (169, 72, 49),
            "roast_body": (128, 89, 77),
        }

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

    def _pighub_thumbnail_path(self, image_url: str) -> Path:
        """将可信 URL 映射为固定文件名，避免把远端路径写入本地文件系统。"""
        digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()
        return self.pighub_thumbnail_dir / f"{digest}.png"

    @staticmethod
    def _make_pighub_thumbnail(raw: bytes, size: int) -> tuple[dict, bytes]:
        """校验远端图片后生成固定尺寸 PNG 与 Canvas RGBA 像素。"""
        with PILImage.open(io.BytesIO(raw)) as source:
            source.verify()
        with PILImage.open(io.BytesIO(raw)) as source:
            method = getattr(PILImage, "Resampling", PILImage).LANCZOS
            thumb = ImageOps.fit(
                ImageOps.exif_transpose(source).convert("RGBA"),
                (size, size),
                method,
            )
            payload = RollPigPlugin._rgba_pixel_payload(thumb, size)
            output = io.BytesIO()
            thumb.save(output, "PNG", optimize=True)
            return payload, output.getvalue()

    def _remember_pighub_thumbnail(self, image_url: str, payload: dict):
        if len(self._pighub_thumbnail_cache) >= self.PIGHUB_THUMBNAIL_MEMORY_LIMIT:
            self._pighub_thumbnail_cache.pop(next(iter(self._pighub_thumbnail_cache)))
        self._pighub_thumbnail_cache[image_url] = payload

    async def _pighub_thumbnail_pixels(self, image_url: str) -> dict:
        """优先复用内存／磁盘缩略图，只有缓存未命中时才请求 PigHub 图片。"""
        cached = self._pighub_thumbnail_cache.get(image_url)
        if cached:
            return cached
        failed_at = self._pighub_thumbnail_failures.get(image_url, 0)
        if time.time() - failed_at < self.PIGHUB_THUMBNAIL_FAILURE_TTL:
            raise ValueError("该图片暂时不可用，请稍后再试")
        lock = self._pighub_thumbnail_locks.setdefault(image_url, asyncio.Lock())
        async with lock:
            cached = self._pighub_thumbnail_cache.get(image_url)
            if cached:
                return cached
            failed_at = self._pighub_thumbnail_failures.get(image_url, 0)
            if time.time() - failed_at < self.PIGHUB_THUMBNAIL_FAILURE_TTL:
                raise ValueError("该图片暂时不可用，请稍后再试")
            path = self._pighub_thumbnail_path(image_url)
            now = time.time()

            def load_disk() -> dict | None:
                try:
                    if (
                        not path.exists()
                        or now - path.stat().st_mtime > self.PIGHUB_THUMBNAIL_TTL
                    ):
                        return None
                    with PILImage.open(path) as image:
                        return self._rgba_pixel_payload(
                            ImageOps.exif_transpose(image), self.PIGHUB_THUMBNAIL_SIZE
                        )
                except Exception:
                    path.unlink(missing_ok=True)
                    return None

            disk_payload = await asyncio.to_thread(load_disk)
            if disk_payload:
                self._remember_pighub_thumbnail(image_url, disk_payload)
                return disk_payload

            try:
                raw = await self._download_pighub_image(image_url)
                payload, png = await asyncio.to_thread(
                    self._make_pighub_thumbnail, raw, self.PIGHUB_THUMBNAIL_SIZE
                )
            except Exception:
                self._pighub_thumbnail_failures[image_url] = time.time()
                raise

            def save_disk():
                with tempfile.NamedTemporaryFile(
                    "wb", dir=self.pighub_thumbnail_dir, suffix=".tmp", delete=False
                ) as tmp:
                    tmp.write(png)
                    tmp_path = Path(tmp.name)
                tmp_path.replace(path)

            try:
                await asyncio.to_thread(save_disk)
            except Exception as exc:
                logger.warning(f"PigHub 缩略图缓存写入失败：{exc}")
            self._remember_pighub_thumbnail(image_url, payload)
            self._pighub_thumbnail_failures.pop(image_url, None)
            return payload

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
        group_id: str | None = None,
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
            group_changed = False
            if group_id:
                groups = day.setdefault("groups", {})
                group_users = groups.setdefault(str(group_id), [])
                if user_id not in group_users:
                    group_users.append(user_id)
                    group_changed = True
            if user_id in day_users:
                if user_id not in day_records:
                    day_records[user_id] = pig_id
                    if save:
                        self.save_json(self.history_path, self.history)
                    return True
                if (snapshot_changed or group_changed) and save:
                    self.save_json(self.history_path, self.history)
                return snapshot_changed or group_changed

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

    @staticmethod
    def _event_group_id(event: AstrMessageEvent) -> str:
        """返回群 ID；私聊或适配器未提供时返回空字符串。"""
        try:
            return str(event.get_group_id() or "")
        except (AttributeError, TypeError):
            return ""

    @staticmethod
    def _normalise_platform_user_id(value) -> str:
        """读取各适配器对象上的用户标识，拒绝空值与无意义对象字符串。"""
        if isinstance(value, (str, int)):
            result = str(value).strip()
            return result if result and result.lower() not in {"none", "null"} else ""
        return ""

    @classmethod
    def _object_user_id(cls, value) -> str:
        """从 AstrBot 组件或 Discord 等原生用户对象中提取稳定 ID。"""
        if isinstance(value, dict):
            for key in ("user_id", "userId", "qq", "id", "target_id"):
                result = cls._normalise_platform_user_id(value.get(key))
                if result:
                    return result
            return ""
        for attr in ("user_id", "userId", "qq", "id", "target_id"):
            result = cls._normalise_platform_user_id(getattr(value, attr, None))
            if result:
                return result
        return cls._normalise_platform_user_id(value)

    @staticmethod
    def _event_components(event: AstrMessageEvent) -> list:
        try:
            components = event.get_messages()
            return list(components or [])
        except (AttributeError, TypeError):
            return []

    def _native_mention_ids(self, event: AstrMessageEvent) -> list[str]:
        """补充 Discord 原生 mentions 等尚未规范化为 At 段的适配器数据。"""
        message_obj = getattr(event, "message_obj", None)
        raw_message = getattr(message_obj, "raw_message", None)
        targets = (message_obj, raw_message)
        result: list[str] = []
        for target in targets:
            mentions = (
                target.get("mentions", [])
                if isinstance(target, dict)
                else getattr(target, "mentions", [])
            )
            if isinstance(mentions, dict):
                mentions = mentions.values()
            for mention in mentions or []:
                user_id = self._object_user_id(mention)
                if user_id and user_id not in result:
                    result.append(user_id)
        return result

    def _reply_sender_id(self, event: AstrMessageEvent) -> str:
        """从统一 Reply 段及常见原生引用对象中读取原消息发送者。"""
        for component in self._event_components(event):
            component_name = component.__class__.__name__.lower()
            is_reply = component_name == "reply" or hasattr(component, "sender_id")
            if not is_reply:
                continue
            for attr in ("sender_id", "author_id", "user_id"):
                user_id = self._normalise_platform_user_id(
                    getattr(component, attr, None)
                )
                if user_id:
                    return user_id
            for attr in ("sender", "author", "user"):
                user_id = self._object_user_id(getattr(component, attr, None))
                if user_id:
                    return user_id

        message_obj = getattr(event, "message_obj", None)
        raw_message = getattr(message_obj, "raw_message", None)
        if isinstance(raw_message, dict):
            reference = raw_message.get("reference") or raw_message.get("reply_to")
            resolved = (
                reference.get("resolved")
                if isinstance(reference, dict)
                else None
            ) or raw_message.get("referenced_message")
            author = (
                resolved.get("author")
                if isinstance(resolved, dict)
                else getattr(resolved, "author", None)
            )
        else:
            reference = getattr(raw_message, "reference", None)
            resolved = getattr(reference, "resolved", None)
            author = getattr(resolved, "author", None)
        return self._object_user_id(author)

    async def _send_with_mention(
        self, event: AstrMessageEvent, user_id: str, text: str
    ) -> None:
        """优先发标准 @ 消息段；适配器不支持时仍发送可识别的纯文本。"""
        if self._event_group_id(event):
            try:
                await event.send(
                    event.chain_result([Comp.At(qq=user_id), Comp.Plain(text)])
                )
                return
            except Exception as exc:
                logger.warning(f"发送 @ 消息段失败，已回退文本：{exc}")
        await event.send(event.plain_result(f"@{user_id}{text}"))

    def _roast_block_reason(self, pig: dict | None) -> str | None:
        """检查一只当天小猪是否仍可被做成料理。"""
        if not pig:
            return "对方今天还没有抽取小猪。"
        pig_id = str(pig.get("id") or "").strip().lower()
        name = str(pig.get("name") or "").strip()
        if pig_id in self.ROAST_FORBIDDEN_IDS or name in self.ROAST_FORBIDDEN_NAMES:
            return f"对方今天是「{name or pig_id}」，不能被烧烤。"
        return None

    def _extract_roast_target_id(
        self, event: AstrMessageEvent, args: str = ""
    ) -> str:
        """优先取 @ 目标，其次取引用发送者，最后接受各平台格式的用户 ID。"""
        at_ids = self.get_at_ids(event)
        if at_ids:
            return at_ids[0]
        reply_sender_id = self._reply_sender_id(event)
        if reply_sender_id:
            return reply_sender_id
        raw_message = str(getattr(event, "message_str", "") or "")
        match = re.search(r'<@!?(\d+)>|qq="?(\d+)"?', raw_message)
        if match:
            return match.group(1) or match.group(2)
        candidate = str(args or "").strip()
        discord_mention = re.fullmatch(r"<@!?(\d+)>", candidate)
        if discord_mention:
            return discord_mention.group(1)
        candidate = candidate.removeprefix("@").strip()
        # Discord、Slack、飞书等用户 ID 不一定是纯数字；仅接受无空白的安全 ID。
        return candidate if re.fullmatch(r"[A-Za-z0-9_.:-]{2,128}", candidate) else ""

    def _save_roast_state(self) -> None:
        self.save_json(self.roast_state_path, self.roast_state)

    def _consume_group_roast_cooldown(
        self, group_id: str, actor_id: str
    ) -> int:
        """记录一次普通烤群友，返回剩余冷却秒数；0 表示已成功占用。"""
        key = f"{group_id}:{actor_id}"
        now = time.time()
        with self._data_lock:
            cooldowns = self.roast_state.setdefault("cooldowns", {})
            previous = float(cooldowns.get(key, 0) or 0)
            remaining = int(previous + self.group_roast_cooldown_seconds - now)
            if remaining > 0:
                return remaining
            cooldowns[key] = now
            self._save_roast_state()
        return 0

    def _consume_daily_backdoor(self, actor_id: str) -> bool:
        """普通后门每个用户每天仅消耗一次。"""
        key = f"{datetime.date.today().isoformat()}:{actor_id}"
        with self._data_lock:
            used = self.roast_state.setdefault("daily_backdoors", {})
            if used.get(key):
                return False
            used[key] = True
            # 只保留近期数据，避免状态文件无限增长。
            cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
            self.roast_state["daily_backdoors"] = {
                item: value
                for item, value in used.items()
                if item.split(":", 1)[0] >= cutoff
            }
            self._save_roast_state()
        return True

    @staticmethod
    def _format_cooldown(seconds: int) -> str:
        seconds = max(1, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes = max(1, math.ceil(remainder / 60)) if remainder else 0
        return f"{hours} 小时 {minutes} 分" if hours else f"{minutes} 分钟"

    async def _generate_ai_roast_copy(
        self, event: AstrMessageEvent, pig: dict
    ) -> str | None:
        """可选 AI 文案；模型不可用时静默回退到本地料理文案。"""
        if not self.enable_ai_roast_copy:
            return None
        prompt = (
            "为聊天机器人‘今日烤猪’写一句中文料理卡文案。"
            f"小猪名：{str(pig.get('name') or '小猪')[:30]}；"
            f"描述：{str(pig.get('description') or '')[:80]}。"
            "语气轻松、无攻击性、不含真实食物制作步骤；只输出一句不超过42个汉字的文案。"
        )
        try:
            response = None
            get_provider_id = getattr(self.context, "get_current_chat_provider_id", None)
            llm_generate = getattr(self.context, "llm_generate", None)
            umo = getattr(event, "unified_msg_origin", None)
            if callable(get_provider_id) and callable(llm_generate) and umo:
                provider_id = await get_provider_id(umo=umo)
                if provider_id:
                    response = await llm_generate(
                        chat_provider_id=provider_id, prompt=prompt
                    )
            if response is None:
                provider = self.context.get_using_provider()
                if provider is None:
                    return None
                response = await provider.text_chat(
                    prompt=prompt,
                    session_id=None,
                    contexts=[],
                    image_urls=[],
                    func_tool=None,
                    system_prompt="",
                )
            text = str(getattr(response, "completion_text", "") or "").strip()
            text = re.sub(r"\s+", " ", text).strip("“”\"' ")
            return text[:64] or None
        except Exception as exc:
            logger.warning(f"AI 烤猪文案生成失败，已回退本地文案：{exc}")
            return None

    async def _send_roast_card(
        self, event: AstrMessageEvent, pig: dict, user_id: str
    ) -> bool:
        output = None
        try:
            ai_copy = await self._generate_ai_roast_copy(event, pig)
            output = await asyncio.to_thread(
                self.render_roast_image, pig, user_id, ai_copy
            )
            await event.send(event.image_result(str(output.absolute())))
            return True
        except Exception as exc:
            logger.error(f"生成烤猪料理卡失败：{exc}", exc_info=True)
            await event.send(event.plain_result("料理卡生成失败，请稍后再试。"))
            return False
        finally:
            if output:
                output.unlink(missing_ok=True)

    async def _roast_group_target(
        self,
        event: AstrMessageEvent,
        target_id: str,
        *,
        bypass: bool = False,
    ) -> None:
        """执行烤群友结果。后门仅传入 bypass，不绕过目标资格。"""
        actor_id = str(event.get_sender_id())
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(event.plain_result("烤群友只能在群聊中使用。"))
            return
        if not target_id:
            await event.send(event.plain_result("请 @ 一位群友，或回复对方的消息后再使用。"))
            return
        if target_id == actor_id:
            await event.send(event.plain_result("不能对自己使用烤群友；请用 /今日烤猪。"))
            return
        target_pig = self._get_daily_pig(target_id, datetime.date.today())
        reason = self._roast_block_reason(target_pig)
        if reason:
            await event.send(event.plain_result(reason))
            return
        if not bypass:
            remaining = self._consume_group_roast_cooldown(group_id, actor_id)
            if remaining:
                await event.send(
                    event.plain_result(
                        f"烤架还在降温，请 {self._format_cooldown(remaining)} 后再试。"
                    )
                )
                return

        result = "success" if bypass else random.choices(
            ["success", "escape", "backlash"], weights=[60, 30, 10], k=1
        )[0]
        if result == "escape":
            await event.send(event.plain_result("💨 对方一溜烟逃走了，烤架上只剩一阵风。"))
            return
        if result == "backlash":
            actor_pig = self._get_daily_pig(actor_id, datetime.date.today())
            actor_reason = self._roast_block_reason(actor_pig)
            if actor_reason:
                await event.send(event.plain_result("🔥 烤架反噬了！但你今天没有可料理的小猪，侥幸躲过一劫。"))
                return
            await event.send(event.plain_result("🔥 烤架反噬！这次轮到你的今日小猪上桌。"))
            await self._send_roast_card(event, actor_pig, actor_id)
            return

        prefix = "🔥 后门生效，" if bypass else "🔥 烧烤成功，"
        await event.send(event.plain_result(f"{prefix}对方今天的小猪已被端上料理台。"))
        await self._send_roast_card(event, target_pig, target_id)

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
        palette = self._image_palette()
        pig_id = pig_data.get("id", "")
        pig_name = pig_data.get("name", "未知小猪")
        pig_desc = pig_data.get("description", "无描述")
        pig_analysis = pig_data.get("analysis", "无解析")

        # 1. 画布基础配置
        canvas_width = self.CANVAS_WIDTH
        canvas_height = self.CANVAS_HEIGHT
        canvas = PILImage.new("RGB", (canvas_width, canvas_height), palette["canvas"])
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
                fill=palette["accent"],
                font=error_font,
            )

        # 5.2 绘制名称（水平居中）
        name_y = avatar_y + avatar_h + spacing_avatar_name
        name_x = (canvas_width - name_w) // 2
        self._draw_bold_text(draw, (name_x, name_y), pig_name, name_font, palette["title"])

        # 5.3 绘制描述（水平居中）
        desc_y = name_y + name_h + spacing_name_desc
        desc_x = (canvas_width - desc_w) // 2
        draw.text((desc_x, desc_y), pig_desc, fill=palette["body"], font=desc_font)

        # 5.4 绘制解析（逐行水平居中）
        analysis_y = desc_y + desc_h + spacing_desc_analysis
        for line in analysis_lines:
            line_w, line_h = self._get_text_size(line, analysis_font)
            line_x = (canvas_width - line_w) // 2
            draw.text((line_x, analysis_y), line, fill=palette["secondary"], font=analysis_font)
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
        palette = self._image_palette()
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
        canvas = PILImage.new("RGB", (width, height), palette["canvas"])
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=52)
        stat_font = self.font_regular.font_variant(size=26)
        name_font = self.font_bold.font_variant(size=25)
        small_font = self.font_regular.font_variant(size=20)

        draw.rounded_rectangle((28, 24, 872, 195), 30, fill=palette["surface"])
        draw.text((58, 45), "我的猪圈 · 永久图鉴", font=title_font, fill=palette["title"])
        rate = (unlocked_count / total * 100) if total else 0
        stat = f"已解锁 {unlocked_count}/{total}  ·  收藏率 {rate:.1f}%"
        draw.text((60, 122), stat, font=stat_font, fill=palette["secondary"])

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
        draw.text((60, 158), growth, font=small_font, fill=palette["muted"])

        card_w, card_h = 260, 218
        gap_x, gap_y = 30, 28
        origin_x, origin_y = 30, 220
        for index, pig in enumerate(pigs):
            row, col = divmod(index, 3)
            x = origin_x + col * (card_w + gap_x)
            y = origin_y + row * (card_h + gap_y)
            pig_id = str(pig.get("id") or "")
            is_unlocked = pig_id in unlocked
            bg = palette["surface"] if is_unlocked else palette["locked"]
            draw.rounded_rectangle((x, y, x + card_w, y + card_h), 24, fill=bg)
            image_path = self.find_image_file(pig_id)
            if image_path:
                try:
                    thumb = self._fit_card_image(image_path, (130, 130))
                    if not is_unlocked:
                        thumb = ImageOps.grayscale(thumb).convert("RGBA")
                        shade = PILImage.new("RGBA", thumb.size, (20, 16, 23, 120))
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
                fill=palette["title"] if is_unlocked else palette["locked_text"],
            )
            count = int(unlocked[pig_id].get("count", 1)) if is_unlocked else 0
            label = f"EX Lv.{max(0, count - 1)} · ×{count}" if is_unlocked else "尚未解锁"
            label_w, _ = self._get_text_size(label, small_font)
            draw.text(
                (x + (card_w - label_w) // 2, y + 190),
                label,
                font=small_font,
                fill=palette["accent"] if is_unlocked else palette["muted"],
            )

        footer = f"第 {page}/{total_pages} 页  ·  使用 /我的猪圈 页码 翻页"
        footer_w, _ = self._get_text_size(footer, stat_font)
        draw.text(
            ((width - footer_w) // 2, 1210),
            footer,
            font=stat_font,
            fill=palette["secondary"],
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output, page

    def render_catalog_grid(
        self, pigs: list[dict], title: str, subtitle: str
    ) -> Path:
        """为随机小猪和本地搜索渲染轻量九宫格。"""
        palette = self._image_palette()
        pigs = pigs[:9]
        rows = max(1, math.ceil(len(pigs) / 3))
        width, height = 900, 155 + rows * 245 + 30
        canvas = PILImage.new("RGB", (width, height), palette["canvas"])
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=48)
        # 插件自带常规字体在部分环境的繁体字距异常，帮助卡统一使用
        # 已验证覆盖完整的粗体字，优先保证指令可读性。
        subtitle_font = self.font_bold.font_variant(size=21)
        name_font = self.font_bold.font_variant(size=25)
        desc_font = self.font_regular.font_variant(size=18)
        draw.rounded_rectangle((28, 22, 872, 132), 28, fill=palette["surface"])
        safe_title = title if len(title) <= 18 else title[:17] + "…"
        safe_subtitle = subtitle if len(subtitle) <= 36 else subtitle[:35] + "…"
        draw.text((56, 40), safe_title, font=title_font, fill=palette["title"])
        draw.text((58, 98), safe_subtitle, font=subtitle_font, fill=palette["secondary"])
        for index, pig in enumerate(pigs):
            row, col = divmod(index, 3)
            x, y = 30 + col * 290, 155 + row * 245
            draw.rounded_rectangle((x, y, x + 260, y + 218), 22, fill=palette["surface"])
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
            draw.text((x + (260 - name_w) // 2, y + 158), name, font=name_font, fill=palette["title"])
            desc = str(pig.get("description") or "")
            desc = desc if len(desc) <= 14 else desc[:13] + "…"
            desc_w, _ = self._get_text_size(desc, desc_font)
            draw.text((x + (260 - desc_w) // 2, y + 193), desc, font=desc_font, fill=palette["muted"])
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output

    def render_weekly_summary(self, user_id: str) -> Path:
        palette = self._image_palette()
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        canvas = PILImage.new("RGB", (900, 1080), palette["canvas"])
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=50)
        body_font = self.font_bold.font_variant(size=27)
        small_font = self.font_regular.font_variant(size=20)
        draw.rounded_rectangle((28, 22, 872, 135), 28, fill=palette["surface"])
        draw.text((56, 40), "本周小猪周报", font=title_font, fill=palette["title"])
        draw.text(
            (58, 101),
            f"{monday.isoformat()} — {(monday + datetime.timedelta(days=6)).isoformat()}",
            font=small_font,
            fill=palette["secondary"],
        )
        weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        collected = 0
        for index in range(7):
            day = monday + datetime.timedelta(days=index)
            pig = self._get_daily_pig(user_id, day)
            y = 155 + index * 125
            active = day <= today
            fill = palette["surface"] if pig else palette["surface_muted"]
            draw.rounded_rectangle((34, y, 866, y + 104), 22, fill=fill)
            draw.text((58, y + 19), weekday_names[index], font=body_font, fill=palette["body"])
            draw.text((58, y + 62), f"{day.month}/{day.day}", font=small_font, fill=palette["muted"])
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
                draw.text((378, y + 18), pig_name, font=body_font, fill=palette["title"])
                draw.text((378, y + 62), pig_desc, font=small_font, fill=palette["secondary"])
            else:
                status = "等待未来" if not active else "本日未抽取"
                draw.text((300, y + 37), status, font=body_font, fill=palette["muted"])
        summary = f"本周已签到 {collected}/7 天"
        summary_w, _ = self._get_text_size(summary, body_font)
        draw.text(((900 - summary_w) // 2, 1040), summary, font=body_font, fill=palette["accent"])
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output

    def render_roast_image(
        self, pig: dict, user_id: str, ai_copy: str | None = None
    ) -> Path:
        palette = self._image_palette()
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
        if ai_copy:
            recipe = "AI 私房"
            copy = ai_copy
        canvas = PILImage.new("RGB", (800, 870), palette["roast_canvas"])
        draw = ImageDraw.Draw(canvas)
        title_font = self.font_bold.font_variant(size=52)
        name_font = self.font_bold.font_variant(size=38)
        body_font = self.font_regular.font_variant(size=26)
        draw.rounded_rectangle((34, 28, 766, 830), 38, fill=palette["roast_surface"], outline=palette["roast_outline"], width=5)
        source = "AI 料理" if ai_copy else "本地料理"
        draw.text((64, 58), f"今日烤猪 · {source}", font=title_font, fill=palette["roast_title"])
        path = self.find_image_file(str(pig.get("id") or ""))
        if path:
            thumb = self._fit_card_image(path, (430, 430))
            warm = PILImage.new("RGBA", thumb.size, (232, 91, 38, 45))
            thumb = PILImage.alpha_composite(thumb, warm)
            canvas.paste(thumb.convert("RGB"), (185, 150))
        dish_name = f"{recipe}{pig.get('name', '小猪')}"
        dish_name = dish_name if len(dish_name) <= 16 else dish_name[:15] + "…"
        dish_w, _ = self._get_text_size(dish_name, name_font)
        draw.text(((800 - dish_w) // 2, 625), dish_name, font=name_font, fill=palette["roast_title"])
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
            draw.text(((800 - line_w) // 2, 705 + index * 42), line, font=body_font, fill=palette["roast_body"])
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output

    def render_help_image(self) -> Path:
        """渲染聊天指令帮助卡，避免在会话中输出冗长纯文本。"""
        palette = self._image_palette()
        at_entry = (
            ("/今日小猪 @某人", "查看对方今天的小猪（一次限一人）")
            if self.at_view_pig
            else ("@ 他人查看", "尚未开启；管理员请设置 at_view_pig")
        )
        sections = [
            (
                "每天一猪",
                [
                    ("/今日小猪", "抽取或查看今天的小猪"),
                    at_entry,
                    ("/昨日小猪", "查看昨天的结果"),
                    ("/明日小猪", "明天运势预测，不会提前解锁"),
                    ("/本周小猪", "生成本周七日小猪周报"),
                ],
            ),
            (
                "图鉴与探索",
                [
                    ("/我的猪圈 [页码]", "永久图鉴，例如 /我的猪圈 2"),
                    ("/随机小猪 [1-9]", "随机展示，不影响今日结果"),
                    ("/找猪／搜猪 关键词", "按名称、ID、描述或文案搜索"),
                ],
            ),
            (
                "烤猪玩法",
                [
                    ("/今日烤猪", "把今天的小猪做成趣味料理卡"),
                    ("/烤群友 @某人", "群聊 60% 成功／30% 逃脱／10% 反噬，8 小时冷却"),
                    ("/随机烤群友", "从今天在本群抽过猪的群友中随机挑选"),
                    ("后门口令 @某人", "打点后厨等每日一次；超管可用 /强行点火"),
                ],
            ),
            (
                "管理员",
                [
                    ("/同步小猪资源", "同步云端图鉴，保留本地修改"),
                    ("管理面板", "新增、编辑、删除小猪与 PigHub 选图"),
                ],
            ),
        ]
        width, height = 900, 1510
        canvas = PILImage.new("RGB", (width, height), palette["canvas"])
        draw = ImageDraw.Draw(canvas)
        # 帮助卡固定使用插件内置粗体：AstrBot 容器缺少完整 CJK 系统字体时，
        # 仍可稳定显示这套简体文案。
        title_font = self.font_bold.font_variant(size=52)
        subtitle_font = self.font_bold.font_variant(size=21)
        section_font = self.font_bold.font_variant(size=28)
        command_font = self.font_bold.font_variant(size=22)
        detail_font = self.font_bold.font_variant(size=19)
        footer_font = self.font_bold.font_variant(size=18)

        draw.rounded_rectangle((28, 24, 872, 166), 30, fill=palette["surface"])
        draw.text((60, 47), "今日小猪 · 指令帮助", font=title_font, fill=palette["title"])
        draw.text(
            (62, 116),
            "繁体／简体均可使用 · 每天来领一只属于你的小猪",
            font=subtitle_font,
            fill=palette["secondary"],
        )

        y = 190
        for section_name, entries in sections:
            card_height = 62 + len(entries) * 62 + 14
            draw.rounded_rectangle(
                (28, y, 872, y + card_height), 26, fill=palette["surface"]
            )
            draw.rounded_rectangle(
                (50, y + 18, 202, y + 54), 18, fill=palette["surface_muted"]
            )
            draw.text((68, y + 20), section_name, font=section_font, fill=palette["accent"])
            row_y = y + 72
            for command, detail in entries:
                draw.text((62, row_y), command, font=command_font, fill=palette["title"])
                draw.text((364, row_y + 2), detail, font=detail_font, fill=palette["secondary"])
                row_y += 62
            y += card_height + 20

        footer = "需要时输入 /猪猪帮助，即可再次查看此卡片"
        footer_w, _ = self._get_text_size(footer, footer_font)
        draw.text(
            ((width - footer_w) // 2, height - 55),
            footer,
            font=footer_font,
            fill=palette["muted"],
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG")
        return output

    def get_at_ids(self, event: AstrMessageEvent) -> list[str]:
        """获取统一 At 段与原生 mentions 中的用户 ID，并排除机器人自身。"""
        try:
            self_id = str(event.get_self_id() or "")
        except (AttributeError, TypeError):
            self_id = ""
        user_ids: list[str] = []
        for segment in self._event_components(event):
            class_name = segment.__class__.__name__.lower()
            if not (isinstance(segment, At) or class_name in {"at", "mention"}):
                continue
            user_id = self._object_user_id(segment)
            if user_id and user_id != self_id and user_id not in user_ids:
                user_ids.append(user_id)
        for user_id in self._native_mention_ids(event):
            if user_id and user_id != self_id and user_id not in user_ids:
                user_ids.append(user_id)
        return user_ids

    @filter.command(
        "猪猪帮助",
        alias={"豬豬幫助", "小猪帮助", "小豬幫助", "rollpig帮助", "rollpig幫助"},
    )
    async def rollpig_help(self, event: AstrMessageEvent):
        """展示今日小猪的完整指令说明。"""
        output = None
        try:
            output = self.render_help_image()
            await event.send(event.image_result(str(output.absolute())))
        except Exception as exc:
            logger.error(f"生成豬豬幫助圖片失敗：{exc}", exc_info=True)
            await event.send(event.plain_result("豬豬幫助圖片生成失敗，請查看後台日誌。"))
        finally:
            if output:
                output.unlink(missing_ok=True)

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
            at_ids = self.get_at_ids(event)
            if len(at_ids) > 1:
                await event.send(event.plain_result("一次只能抽取一个小猪哦！"))
                return
            if at_ids:
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
            self._record_unlock(
                user_id, pig, today_str, group_id=self._event_group_id(event)
            )
            await self.send_rendered_pig(event, pig, user_id)
            return

        if not self.pig_list:
            await event.send(event.plain_result("小猪信息加载失败，请检查后台报错！"))
            return

        pig = self._choose_daily_pig(user_id)
        user_records[user_id] = pig
        self.save_json(self.today_path, today_cache)
        self._record_unlock(
            user_id, pig, today_str, group_id=self._event_group_id(event)
        )

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
        """把自己的当天小猪做成趣味料理卡，不改变抽取结果。"""
        if not self.enable_roast:
            await event.send(event.plain_result("今日烤猪功能已在配置中关闭。"))
            return
        user_id = event.get_sender_id()
        pig = self._get_daily_pig(user_id, datetime.date.today())
        reason = self._roast_block_reason(pig)
        if reason:
            if not pig:
                reason = "请先使用 /今日小猪 抽取今天的小猪。"
            await event.send(event.plain_result(reason))
            return
        await self._send_roast_card(event, pig, str(user_id))

    @filter.command("烤群友", alias={"烤群友"})
    async def roast_group_member(self, event: AstrMessageEvent, args: str = ""):
        """在群聊中烧烤 @ 目标或引用消息的发送者。"""
        if not self.enable_roast or not self.enable_group_roast:
            await event.send(event.plain_result("烤群友功能已在配置中关闭。"))
            return
        target_id = self._extract_roast_target_id(event, args)
        await self._roast_group_target(event, target_id)

    @filter.command("随机烤群友", alias={"隨機烤群友"})
    async def roast_random_group_member(self, event: AstrMessageEvent):
        """从今天在当前群聊抽过小猪的成员中随机挑选一位。"""
        if not self.enable_roast or not self.enable_group_roast:
            await event.send(event.plain_result("烤群友功能已在配置中关闭。"))
            return
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(event.plain_result("随机烤群友只能在群聊中使用。"))
            return
        actor_id = str(event.get_sender_id())
        today = datetime.date.today()
        day = self.history.get("daily", {}).get(today.isoformat(), {})
        members = day.get("groups", {}).get(group_id, [])
        candidates = []
        for user_id in members if isinstance(members, list) else []:
            user_id = str(user_id)
            if user_id == actor_id:
                continue
            pig = self._get_daily_pig(user_id, today)
            if not self._roast_block_reason(pig):
                candidates.append(user_id)
        if not candidates:
            await event.send(
                event.plain_result("今天本群还没有可被随机烧烤的群友；请先让大家抽取今日小猪。")
            )
            return
        target_id = random.choice(candidates)
        # 先公布抽中的目标；即使随后逃脱或反噬，群里也知道本次随机点名的是谁。
        await self._send_with_mention(event, target_id, " 🎲 被随机烤群友抽中了。")
        await self._roast_group_target(event, target_id)

    @filter.command(
        "打点后厨",
        alias={
            "打點後廚",
            "偷换烤架",
            "偷換烤架",
            "贿赂主厨",
            "賄賂主廚",
            "加急生火",
            "强行点火",
            "強行點火",
        },
    )
    async def force_roast_group_member(
        self, event: AstrMessageEvent, args: str = ""
    ):
        """后门口令：绕过烤群友冷却与概率，但不绕过资格限制。"""
        if not self.enable_roast or not self.enable_group_roast:
            await event.send(event.plain_result("烤群友功能已在配置中关闭。"))
            return
        raw = str(getattr(event, "message_str", "") or "")
        is_super_phrase = "强行点火" in raw or "強行點火" in raw
        actor_id = str(event.get_sender_id())
        if is_super_phrase:
            if actor_id not in {str(item) for item in self.admins_id}:
                await event.send(event.plain_result("「强行点火」仅限 AstrBot 超级管理员使用。"))
                return
        target_id = self._extract_roast_target_id(event, args)
        group_id = self._event_group_id(event)
        target_pig = self._get_daily_pig(target_id, datetime.date.today()) if target_id else None
        if not group_id:
            await event.send(event.plain_result("烤群友只能在群聊中使用。"))
            return
        if not target_id:
            await event.send(event.plain_result("请 @ 一位群友，或回复对方的消息后再使用。"))
            return
        if target_id == actor_id:
            await event.send(event.plain_result("不能对自己使用烤群友；请用 /今日烤猪。"))
            return
        reason = self._roast_block_reason(target_pig)
        if reason:
            await event.send(event.plain_result(reason))
            return
        if not is_super_phrase and not self._consume_daily_backdoor(actor_id):
            await event.send(event.plain_result("普通后门每天只能使用一次，请明天再来。"))
            return
        await self._roast_group_target(event, target_id, bypass=True)

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
                if self._event_group_id(event):
                    await self._send_with_mention(event, user_id, intro)
                else:
                    await event.send(event.plain_result(intro))
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
        """管理面板：搜索本地缓存的 PigHub 索引。"""
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

    async def page_pighub_thumbnail(self):
        """管理页图格缩略图：服务端缓存并返回 Canvas 像素，避免直接跨域加载。"""
        try:
            image_url = str(request.query.get("url", "") or "").strip()
            self._validate_pighub_image_url(image_url)
            result = await self._pighub_thumbnail_pixels(image_url)
            return self._jsonify({"status": "ok", "data": result})
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.warning(f"PigHub 缩略图载入失败：{self._describe_sync_error(exc)}")
            return self._jsonify(
                {"status": "error", "message": "PigHub 缩略图载入失败"}
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
