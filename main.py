"""RollPig plugin entry point.

AstrBot command decorators intentionally live in this module. Business logic may
remain in ``legacy_main`` or focused feature mixins during the gradual refactor,
but helper modules must not register commands themselves. Thin wrappers below
delegate to the inherited implementation and keep AstrBot handler ownership,
priority and unload semantics bound to the real Star entry point.
"""

import asyncio
import threading
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter

try:
    from .animated_image_feature import AnimatedImageMixin
    from .command_actor_feature import CommandActorMentionMixin
    from .daily_report_feature import DailyReportMixin
    from .ex_admin_feature import ExAdminMixin
    from .ex_public_source_feature import ExPublicSourceMixin
    from .ex_variant_feature import ExVariantMixin
    from .help_feature import HelpFeatureMixin
    from .installation_migrations import cleanup_legacy_installation_paths
    from .legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from .message_layout import mention_body_on_new_line
    from .oven_refill_feature import OvenRefillMixin
    from .permanent_collection_feature import PermanentCollectionMixin
    from .pig_studio_admin import PigStudioAdminMixin
    from .pig_studio_feature import PigStudioMixin
    from .renderers.daily_report import render_daily_report_dashboard
    from .reservation_firewood_feature import ReservationFirewoodMixin
    from .roast_reservation_feature import RoastReservationMixin
    from .state_persistence import DebouncedSnapshotWriter
except ImportError:  # pragma: no cover - direct module loading compatibility
    from animated_image_feature import AnimatedImageMixin
    from command_actor_feature import CommandActorMentionMixin
    from daily_report_feature import DailyReportMixin
    from ex_admin_feature import ExAdminMixin
    from ex_public_source_feature import ExPublicSourceMixin
    from ex_variant_feature import ExVariantMixin
    from help_feature import HelpFeatureMixin
    from installation_migrations import cleanup_legacy_installation_paths
    from legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from message_layout import mention_body_on_new_line
    from oven_refill_feature import OvenRefillMixin
    from permanent_collection_feature import PermanentCollectionMixin
    from pig_studio_admin import PigStudioAdminMixin
    from pig_studio_feature import PigStudioMixin
    from renderers.daily_report import render_daily_report_dashboard
    from reservation_firewood_feature import ReservationFirewoodMixin
    from roast_reservation_feature import RoastReservationMixin
    from state_persistence import DebouncedSnapshotWriter


class RollPigPlugin(
    CommandActorMentionMixin,
    AnimatedImageMixin,
    ReservationFirewoodMixin,
    OvenRefillMixin,
    HelpFeatureMixin,
    RoastReservationMixin,
    DailyReportMixin,
    PigStudioAdminMixin,
    PigStudioMixin,
    ExPublicSourceMixin,
    ExAdminMixin,
    ExVariantMixin,
    PermanentCollectionMixin,
    _BaseRollPigPlugin,
):
    """RollPig Plus with growth, roast reservations and rich daily reports."""

    DAILY_REPORT_STATE_FLUSH_DELAY_SECONDS = 2.0

    def __init__(self, context, config):
        # Historical self-updates were overlay installs, so paths removed from a
        # newer release could survive indefinitely. Reconcile explicit
        # tombstones before AstrBot serves Plugin Pages; its Page discovery reads
        # the filesystem dynamically, so removing legacy ex-manager entries here
        # restores pig-manager as the default surface on affected installations.
        cleanup_legacy_installation_paths(
            Path(__file__).resolve().parent, logger=logger
        )

        config_view = config if hasattr(config, "get") else {}
        try:
            render_concurrency = int(config_view.get("image_render_concurrency", 2))
        except (TypeError, ValueError):
            render_concurrency = 2
        self.image_render_concurrency = min(8, max(1, render_concurrency))
        self._image_render_slots = threading.BoundedSemaphore(
            self.image_render_concurrency
        )
        super().__init__(context, config)
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
        writer = getattr(self, "_daily_report_state_writer", None)
        if writer is None:
            return super()._save_daily_report_state_locked()
        writer.mark_dirty()

    async def terminate(self):
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
        with self._image_render_slots:
            return renderer(*args, **kwargs)

    async def _send_with_mention(self, event, user_id: str, text: str) -> None:
        formatted = (
            mention_body_on_new_line(text)
            if self._event_group_id(event)
            else str(text or "")
        )
        await super()._send_with_mention(event, user_id, formatted)

    def render_pig_image(self, pig_data):
        return self._run_with_render_slot(super().render_pig_image, pig_data)

    def render_pigsty_image(self, user_id, page):
        return self._run_with_render_slot(super().render_pigsty_image, user_id, page)

    def render_catalog_grid(self, pigs, title, subtitle):
        return self._run_with_render_slot(super().render_catalog_grid, pigs, title, subtitle)

    def render_weekly_summary(self, user_id):
        return self._run_with_render_slot(super().render_weekly_summary, user_id)

    def render_roast_image(self, pig, user_id, ai_copy=None, local_copy=None):
        return self._run_with_render_slot(
            super().render_roast_image, pig, user_id, ai_copy, local_copy
        )

    def render_daily_report_image(self, report):
        return self._run_with_render_slot(render_daily_report_dashboard, self, report)

    # BEGIN MAIN COMMAND REGISTRATION
    @filter.command('猪猪帮助', alias={'豬豬幫助', '小猪帮助', '小豬幫助', 'rollpig帮助', 'rollpig幫助'}, priority=1000)
    async def rollpig_help(self, event: AstrMessageEvent):
        return await super().rollpig_help(event)

    @filter.command('今日小猪', alias={'今日小豬', '今天是什么小猪', '今天是什麼小豬', '抽小猪', '抽小豬', '我的小猪', '我的小豬', 'rollpig'}, priority=1000)
    async def roll_pig(self, event: AstrMessageEvent):
        return await super().roll_pig(event)

    @filter.command('我的猪圈', alias={'我的豬圈', '小猪图鉴', '小豬圖鑑', '猪圈', '豬圈'}, priority=1000)
    async def my_pigsty(self, event: AstrMessageEvent, args: str=''):
        return await super().my_pigsty(event, args)

    @filter.command('昨日小猪', alias={'昨日小豬', '昨天小猪', '昨天小豬'}, priority=1000)
    async def yesterday_pig(self, event: AstrMessageEvent):
        return await super().yesterday_pig(event)

    @filter.command('明日小猪', alias={'明日小豬', '明天小猪', '明天小豬'}, priority=1000)
    async def tomorrow_pig(self, event: AstrMessageEvent):
        return await super().tomorrow_pig(event)

    @filter.command('本周小猪', alias={'本周小豬', '本週小猪', '本週小豬', '本周猪报', '本週豬報'}, priority=1000)
    async def weekly_pigs(self, event: AstrMessageEvent):
        return await super().weekly_pigs(event)

    @filter.command('随机小猪', alias={'随机小豬', '隨機小猪', '隨機小豬', '随机猪', '隨機豬'}, priority=1000)
    async def random_pigs(self, event: AstrMessageEvent, args: str=''):
        return await super().random_pigs(event, args)

    @filter.command('找猪', alias={'找豬', '搜猪', '搜豬'}, priority=1000)
    async def find_pigs(self, event: AstrMessageEvent, keyword: str=''):
        return await super().find_pigs(event, keyword)

    @filter.command('今日烤猪', alias={'今日烤豬', '烤猪', '烤豬'}, priority=1000)
    async def roast_today_pig(self, event: AstrMessageEvent):
        return await super().roast_today_pig(event)

    @filter.command('烤群友', alias={'烤群友'}, priority=1000)
    async def roast_group_member(self, event: AstrMessageEvent, args: str=''):
        return await super().roast_group_member(event, args)

    @filter.command('随机烤群友', alias={'隨機烤群友'}, priority=1000)
    async def roast_random_group_member(self, event: AstrMessageEvent):
        """Pick only currently roastable, unprotected targets and spend before pinging."""
        self._claim_command_event(event)
        if not self.enable_roast or not self.enable_group_roast:
            await event.send(event.plain_result("🔒 今天后厨不开群友这桌。管理员已经把烤群友的火关了。"))
            return
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(event.plain_result("🎲 随机烤群友只能在群里转盘。私聊只有你一个，随机得有点侮辱概率学。"))
            return

        actor_id = self._event_sender_id(event)
        today = self._today()
        members = self._daily_group_members(group_id, today.isoformat())
        candidates: list[str] = []
        for raw_user_id in members if isinstance(members, list) else []:
            user_id = str(raw_user_id)
            if user_id == actor_id:
                continue
            pig = self._get_daily_pig(user_id, today)
            if self._roast_block_reason(pig):
                continue
            protected, _ = await self._roast_protection_status(group_id, user_id)
            if not protected:
                candidates.append(user_id)

        target_id = ""
        target_pig = None
        while candidates:
            candidate = self.roast_service.choose_group_roast_target(candidates)
            candidate_pig = self._get_daily_pig(candidate, today)
            reason = self._roast_block_reason(candidate_pig)
            protected, _ = await self._roast_protection_status(group_id, candidate)
            if not reason and not protected:
                target_id = candidate
                target_pig = candidate_pig
                break
            candidates.remove(candidate)

        if not target_id or not target_pig:
            await event.send(
                event.plain_result("🎲 今天本群没有可随机下锅的群友：没抽、已上桌或有保护的都被转盘剔除了。")
            )
            return

        # Spend first. A user with 0 Charge must not be able to spam random @mentions.
        charge_status = await self._consume_group_roast_charge(group_id, actor_id)
        if not charge_status.get("consumed"):
            remaining = int(charge_status.get("next_refill_seconds", 0) or 0)
            await event.send(
                event.plain_result(
                    "🔥 烤箱能量已耗尽（"
                    f"0/{self.group_roast_max_charges}）；下一格将在 "
                    f"{self._format_cooldown(remaining)} 后恢复。"
                )
            )
            return

        await self._send_with_mention(
            event,
            target_id,
            " 🎲 随机转盘停在你头上。后厨说：就你了。",
        )

        charge_note = self._roast_charge_note(charge_status)
        result = self.roast_service.choose_group_roast_outcome()
        logger.info(
            "随机烤群友判定：group=%s actor=%s target=%s outcome=%s charge=%s/%s rng=isolated",
            group_id,
            actor_id,
            target_id,
            result,
            int(charge_status.get("charges", 0) or 0),
            int(charge_status.get("max_charges", 0) or 0),
        )
        if result == "escape":
            self._record_roast_outcome_event(
                "roast_escape",
                group_id,
                actor_id=actor_id,
                target_id=target_id,
            )
            await event.send(
                event.plain_result("💨 对方一溜烟跑了，烤架上只剩一阵风。后厨连盐都白撒了。" + charge_note)
            )
            return

        if result == "backlash":
            actor_pig = self._get_daily_pig(actor_id, today)
            actor_reason = self._roast_block_reason(actor_pig, subject="actor")
            victim_id = "" if actor_reason else actor_id
            self._record_roast_outcome_event(
                "roast_backlash",
                group_id,
                actor_id=actor_id,
                target_id=target_id,
                victim_id=victim_id,
            )
            if actor_reason:
                await event.send(
                    event.plain_result(
                        "🔥 烤架反噬了！翻面一看你今天没有可料理的小猪——这次不是技术好，是锅里没货。"
                        + charge_note
                    )
                )
                return
            await event.send(
                event.plain_result("🔥 烤架反噬！火舌顺着锅沿爬回来，这次轮到你的今日小猪上桌。" + charge_note)
            )
            await self._record_group_roast(group_id, actor_id)
            await self._send_roast_card(event, actor_pig, actor_id)
            return

        self._record_roast_outcome_event(
            "roast_success",
            group_id,
            actor_id=actor_id,
            target_id=target_id,
            victim_id=target_id,
        )
        await event.send(
            event.plain_result("🔥 烧烤成功，对方今天的小猪已经被后厨端走，围裙都没来得及系。" + charge_note)
        )
        await self._record_group_roast(group_id, target_id)
        await self._send_roast_card(event, target_pig, target_id)

    @filter.command('吃群友', alias={'吃群友'}, priority=1000)
    async def eat_group_member(self, event: AstrMessageEvent, args: str=''):
        return await super().eat_group_member(event, args)

    @filter.command('随机吃群友', alias={'隨機吃群友'}, priority=1000)
    async def eat_random_group_member(self, event: AstrMessageEvent):
        return await super().eat_random_group_member(event)

    @filter.command('打点后厨', alias={'打點後廚', '偷换烤架', '偷換烤架', '贿赂主厨', '賄賂主廚', '加急生火', '强行点火', '強行點火'}, priority=1000)
    async def force_roast_group_member(self, event: AstrMessageEvent, args: str=''):
        return await super().force_roast_group_member(event, args)

    @filter.command('烤箱补货', alias={'烤箱補貨', '烤箱补给', '烤箱補給'}, priority=1000)
    async def oven_refill(self, event: AstrMessageEvent):
        return await super().oven_refill(event)

    @filter.command('添柴', alias={'加柴'}, priority=1000)
    async def firewood_support(self, event: AstrMessageEvent, args: str=''):
        return await super().firewood_support(event, args)

    @filter.command('添煤', alias={'加煤', '烤箱添煤', '烤箱添柴'}, priority=1000)
    async def oven_refill_support_compat(self, event: AstrMessageEvent):
        return await super().oven_refill_support(event)

    @filter.command('猪圈日报', alias={'豬圈日報', '今日猪圈日报', '今日豬圈日報'}, priority=1000)
    async def pigsty_daily_report(self, event: AstrMessageEvent, args: str=''):
        return await super().pigsty_daily_report(event, args)

    @filter.command('猪圈日报状态', alias={'豬圈日報狀態', '猪圈日报狀態', '豬圈日報状态', '今日猪圈日报状态', '今日豬圈日報狀態'}, priority=1000)
    async def pigsty_daily_report_status(self, event: AstrMessageEvent):
        return await super().pigsty_daily_report(event, '狀態')

    @filter.command('猪圈日报开启', alias={'豬圈日報開啟', '猪圈日报開啟', '豬圈日報开启', '猪圈日报启用', '豬圈日報啟用', '今日猪圈日报开启', '今日豬圈日報開啟'}, priority=1000)
    async def pigsty_daily_report_enable(self, event: AstrMessageEvent):
        return await super().pigsty_daily_report(event, '開啟')

    @filter.command('猪圈日报关闭', alias={'豬圈日報關閉', '猪圈日报關閉', '豬圈日報关闭', '今日猪圈日报关闭', '今日豬圈日報關閉'}, priority=1000)
    async def pigsty_daily_report_disable(self, event: AstrMessageEvent):
        return await super().pigsty_daily_report(event, '關閉')
    # END MAIN COMMAND REGISTRATION

    UI_ASSET_VERSION = "3.2.0"

    def _build_analytics_insights(self):
        """Attach safe feature-state metadata needed by the admin dashboard."""
        data = super()._build_analytics_insights()
        if not isinstance(data, dict):
            return data
        enabled = bool(getattr(self, "enable_ai_roast_copy", False))
        feature_flags = data.setdefault("feature_flags", {})
        if isinstance(feature_flags, dict):
            feature_flags["ai_roast_copy_enabled"] = enabled
        operations = data.setdefault("operations", {})
        if isinstance(operations, dict):
            ai = operations.setdefault("ai", {})
            if isinstance(ai, dict):
                ai["enabled"] = enabled
        return data

    def _init_regular_font(self):
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
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Bold.otf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        return self._load_font(font_paths, self.NAME_FONT_SIZE, "加粗")

    def _init_traditional_font(self):
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
