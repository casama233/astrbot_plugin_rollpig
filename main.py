"""RollPig plugin entry point.

AstrBot command decorators intentionally live in this module. Business logic may
remain in ``legacy_main`` or focused feature mixins during the gradual refactor,
but helper modules must not register commands themselves. Thin wrappers below
delegate to the inherited implementation and keep AstrBot handler ownership,
priority and unload semantics bound to the real Star entry point.
"""

import asyncio
import hashlib
import json
import os
import shutil
import threading
import uuid

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter

try:
    from .daily_report_feature import DailyReportMixin
    from .ex_variant_feature import ExVariantMixin
    from .legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from .permanent_collection_feature import PermanentCollectionMixin
    from .roast_reservation_feature import RoastReservationMixin
    from .state_persistence import DebouncedSnapshotWriter
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_feature import DailyReportMixin
    from ex_variant_feature import ExVariantMixin
    from legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from permanent_collection_feature import PermanentCollectionMixin
    from roast_reservation_feature import RoastReservationMixin
    from state_persistence import DebouncedSnapshotWriter


class RollPigPlugin(
    RoastReservationMixin,
    DailyReportMixin,
    ExVariantMixin,
    PermanentCollectionMixin,
    _BaseRollPigPlugin,
):
    """RollPig Plus with growth, roast reservations and rich daily reports."""

    HELP_RENDER_CACHE_VERSION = 1
    DAILY_REPORT_STATE_FLUSH_DELAY_SECONDS = 2.0

    def __init__(self, context, config):
        config_view = config if hasattr(config, "get") else {}
        try:
            render_concurrency = int(config_view.get("image_render_concurrency", 2))
        except (TypeError, ValueError):
            render_concurrency = 2
        self.image_render_concurrency = min(8, max(1, render_concurrency))
        self._image_render_slots = threading.BoundedSemaphore(
            self.image_render_concurrency
        )
        self._help_render_cache_lock = threading.Lock()
        super().__init__(context, config)
        self._help_render_cache_dir = self.plugin_data_dir / "render_cache" / "help"
        self._help_render_cache_dir.mkdir(parents=True, exist_ok=True)
        self._daily_report_state_writer = DebouncedSnapshotWriter(
            state_lock=self._data_lock,
            snapshot_factory=lambda: self.daily_report_state,
            write_snapshot=lambda snapshot: self.save_json(
                self.daily_report_state_path, snapshot
            ),
            delay_seconds=self.DAILY_REPORT_STATE_FLUSH_DELAY_SECONDS,
            on_error=lambda exc: logger.warning(
                f"猪圈日报状态延迟落盘失败，将自动重试：{exc}"
            ),
        )

    def _save_daily_report_state_locked(self) -> None:
        """Coalesce hot report metadata writes after startup initialization."""
        writer = getattr(self, "_daily_report_state_writer", None)
        if writer is None:
            return super()._save_daily_report_state_locked()
        writer.mark_dirty()

    async def terminate(self):
        """Drain report work, then force the newest debounced snapshot to disk."""
        task = getattr(self, "_daily_report_task", None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        writer = getattr(self, "_daily_report_state_writer", None)
        if writer is not None:
            try:
                await asyncio.to_thread(writer.close_and_flush)
            except Exception as exc:
                logger.warning(f"插件卸载时最终保存猪圈日报状态失败：{exc}")
        await super().terminate()

    def _run_with_render_slot(self, renderer, *args, **kwargs):
        """Apply CPU backpressure without occupying the asyncio event loop."""
        with self._image_render_slots:
            return renderer(*args, **kwargs)

    def _help_render_cache_path(self):
        palette = self._image_palette()
        identity = {
            "version": self.HELP_RENDER_CACHE_VERSION,
            "night": bool(palette.get("night")),
            "at_view_pig": bool(getattr(self, "at_view_pig", False)),
            "enable_roast": bool(getattr(self, "enable_roast", True)),
            "enable_group_roast": bool(getattr(self, "enable_group_roast", True)),
            "enable_group_eat": bool(getattr(self, "enable_group_eat", True)),
            "enable_daily_report": bool(getattr(self, "enable_daily_report", True)),
            "enable_roast_reservation": bool(
                getattr(self, "enable_roast_reservation", True)
            ),
        }
        digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16]
        return self._help_render_cache_dir / f"help-{digest}.png"

    def _ensure_help_image_cache(self):
        """Render the nearly-static help card once per effective configuration."""
        cache_path = self._help_render_cache_path()
        try:
            if cache_path.is_file() and cache_path.stat().st_size > 0:
                return cache_path
        except OSError:
            pass

        with self._help_render_cache_lock:
            try:
                if cache_path.is_file() and cache_path.stat().st_size > 0:
                    return cache_path
            except OSError:
                pass

            rendered = self._run_with_render_slot(super().render_help_image)
            if rendered is None:
                raise RuntimeError("帮助图片渲染没有生成文件")
            staging = cache_path.with_name(
                f".{cache_path.name}.{uuid.uuid4().hex}.tmp"
            )
            try:
                shutil.copyfile(rendered, staging)
                staging.replace(cache_path)
            finally:
                rendered.unlink(missing_ok=True)
                staging.unlink(missing_ok=True)
            return cache_path

    def render_help_image(self):
        """Return an expendable hardlink/copy while retaining the cached master."""
        cache_path = self._ensure_help_image_cache()
        output = cache_path.with_name(f"help-send-{uuid.uuid4().hex}.png")
        try:
            os.link(cache_path, output)
        except OSError:
            shutil.copyfile(cache_path, output)
        return output

    def render_pig_image(self, pig_data):
        return self._run_with_render_slot(super().render_pig_image, pig_data)

    def render_pigsty_image(self, user_id, page):
        return self._run_with_render_slot(super().render_pigsty_image, user_id, page)

    def render_catalog_grid(self, pigs, title, subtitle):
        return self._run_with_render_slot(
            super().render_catalog_grid, pigs, title, subtitle
        )

    def render_weekly_summary(self, user_id):
        return self._run_with_render_slot(super().render_weekly_summary, user_id)

    def render_roast_image(self, pig, user_id, ai_copy=None):
        return self._run_with_render_slot(
            super().render_roast_image, pig, user_id, ai_copy
        )

    def render_daily_report_image(self, report):
        return self._run_with_render_slot(super().render_daily_report_image, report)

    # BEGIN MAIN COMMAND REGISTRATION
    # Decorators stay on the real Star entry module; implementations live below.
    @filter.command('猪猪帮助', alias={'豬豬幫助', '小猪帮助', '小豬幫助', 'rollpig帮助', 'rollpig幫助'}, priority=1000)
    async def rollpig_help(self, event: AstrMessageEvent):
        """展示今日小猪的完整指令说明。"""
        try:
            await asyncio.to_thread(self._ensure_help_image_cache)
        except Exception as exc:
            logger.warning(f"预生成豬豬幫助圖片缓存失败，将使用原渲染流程：{exc}")
        return await super().rollpig_help(event)

    @filter.command('今日小猪', alias={'今日小豬', '今天是什么小猪', '今天是什麼小豬', '抽小猪', '抽小豬', '我的小猪', '我的小豬', 'rollpig'}, priority=1000)
    async def roll_pig(self, event: AstrMessageEvent):
        """Draw for self; mentioning another user is strictly read-only."""
        return await super().roll_pig(event)

    @filter.command('我的猪圈', alias={'我的豬圈', '小猪图鉴', '小豬圖鑑', '猪圈', '豬圈'}, priority=1000)
    async def my_pigsty(self, event: AstrMessageEvent, args: str=''):
        """查看永久解锁的小猪图鉴，可附带页码。"""
        return await super().my_pigsty(event, args)

    @filter.command('昨日小猪', alias={'昨日小豬', '昨天小猪', '昨天小豬'}, priority=1000)
    async def yesterday_pig(self, event: AstrMessageEvent):
        """查看昨天抽到的小猪。"""
        return await super().yesterday_pig(event)

    @filter.command('明日小猪', alias={'明日小豬', '明天小猪', '明天小豬'}, priority=1000)
    async def tomorrow_pig(self, event: AstrMessageEvent):
        """给出每天固定、但不会提前解锁图鉴的明日预测。"""
        return await super().tomorrow_pig(event)

    @filter.command('本周小猪', alias={'本周小豬', '本週小猪', '本週小豬', '本周猪报', '本週豬報'}, priority=1000)
    async def weekly_pigs(self, event: AstrMessageEvent):
        """生成本周七日抽取总结。"""
        return await super().weekly_pigs(event)

    @filter.command('随机小猪', alias={'随机小豬', '隨機小猪', '隨機小豬', '随机猪', '隨機豬'}, priority=1000)
    async def random_pigs(self, event: AstrMessageEvent, args: str=''):
        """从本地图鉴随机展示 1-9 只小猪，不影响每日抽取。"""
        return await super().random_pigs(event, args)

    @filter.command('找猪', alias={'找豬', '搜猪', '搜豬'}, priority=1000)
    async def find_pigs(self, event: AstrMessageEvent, keyword: str=''):
        """在管理员维护的本地图鉴内搜索。"""
        return await super().find_pigs(event, keyword)

    @filter.command('今日烤猪', alias={'今日烤豬', '烤猪', '烤豬'}, priority=1000)
    async def roast_today_pig(self, event: AstrMessageEvent):
        """把自己的当天小猪做成趣味料理卡，不改变抽取结果。"""
        return await super().roast_today_pig(event)

    @filter.command('烤群友', alias={'烤群友'}, priority=1000)
    async def roast_group_member(self, event: AstrMessageEvent, args: str=''):
        """在群聊中烧烤 @ 目标或引用消息的发送者。"""
        return await super().roast_group_member(event, args)

    @filter.command('随机烤群友', alias={'隨機烤群友'}, priority=1000)
    async def roast_random_group_member(self, event: AstrMessageEvent):
        """从今天在当前群聊抽过小猪的成员中随机挑选一位。"""
        return await super().roast_random_group_member(event)

    @filter.command('吃群友', alias={'吃群友'}, priority=1000)
    async def eat_group_member(self, event: AstrMessageEvent, args: str=''):
        """低概率吃掉 @ 目标；失败者会把自己吃掉。"""
        return await super().eat_group_member(event, args)

    @filter.command('随机吃群友', alias={'隨機吃群友'}, priority=1000)
    async def eat_random_group_member(self, event: AstrMessageEvent):
        """从当天当前群可被吃的成员中随机选择一位。"""
        return await super().eat_random_group_member(event)

    @filter.command('打点后厨', alias={'打點後廚', '偷换烤架', '偷換烤架', '贿赂主厨', '賄賂主廚', '加急生火', '强行点火', '強行點火'}, priority=1000)
    async def force_roast_group_member(self, event: AstrMessageEvent, args: str=''):
        """后门口令：绕过烤群友冷却与概率，但不绕过资格限制。"""
        return await super().force_roast_group_member(event, args)

    @filter.command('猪圈日报', alias={'豬圈日報', '今日猪圈日报', '今日豬圈日報'}, priority=1000)
    async def pigsty_daily_report(self, event: AstrMessageEvent):
        """Render the current group's rich report; manual views never sacrifice."""
        return await super().pigsty_daily_report(event)
    # END MAIN COMMAND REGISTRATION

    # Keep the management UI cache contract visible at the plugin entry point.
    UI_ASSET_VERSION = "3.1.2"

    def _init_regular_font(self):
        """Load the packaged full CJK font before platform fallbacks.

        Marketplace archives have a strict 16 MB ceiling. Release builds keep
        荆南麦圆体.otf as the single bundled full CJK face so both body text and
        titles remain readable without silently falling through to DejaVu.
        """
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "常规")

    def _init_bold_font(self):
        """Load the packaged full CJK title font before platform fallbacks."""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Bold.otf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        return self._load_font(font_paths, self.NAME_FONT_SIZE, "加粗")

    def _init_traditional_font(self):
        """Use the packaged full CJK face for traditional/AI copy before system fallbacks."""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "HanyiYongZiXiaoXiongMaoFan.ttf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "繁体兜底")
