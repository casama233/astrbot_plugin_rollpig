from __future__ import annotations

import asyncio
import datetime
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

try:
    from .rollpig_core import special_pig_state
    from .services.eat_service import EatService
except ImportError:  # pragma: no cover - direct module loading compatibility
    from rollpig_core import special_pig_state
    from services.eat_service import EatService


class EatFeatureMixin:
    """Richer /吃群友 rules without reusing the roast-charge economy.

    The eat game has its own identity:
    * two bites per actor/group/day by default;
    * at most one successful meal per actor/group/day;
    * success / escape / backlash outcomes;
    * cooked targets are easier to eat;
    * yesterday's successful victim receives one-day digestive protection.

    Attempt/outcome bookkeeping uses the shared gameplay event stream so limits
    survive restarts and remain available to future report/analytics layers.
    """

    EVENT_EAT_ATTEMPT = "eat_attempt"
    EVENT_EAT_SUCCESS = "eat_outcome_success"
    EVENT_EAT_ESCAPE = "eat_outcome_escape"
    EVENT_EAT_BACKLASH = "eat_outcome_backlash"

    def __init__(self, context, config):
        super().__init__(context, config)
        config_view = config if hasattr(config, "get") else {}

        self.eat_escape_percent = self._eat_int_config(
            config_view, "eat_escape_percent", 20, 0, 80
        )
        self.eat_cooked_bonus_percent = self._eat_int_config(
            config_view, "eat_cooked_bonus_percent", 10, 0, 40
        )
        self.eat_daily_attempt_limit = self._eat_int_config(
            config_view, "eat_daily_attempt_limit", 2, 1, 10
        )
        self.eat_daily_success_limit = min(
            self.eat_daily_attempt_limit,
            self._eat_int_config(
                config_view, "eat_daily_success_limit", 1, 1, 5
            ),
        )
        self.enable_eat_protection = self._eat_bool_config(
            config_view.get("enable_eat_protection", True), True
        )
        self.eat_protection_threshold = self._eat_int_config(
            config_view, "eat_protection_threshold", 1, 1, 10
        )
        self.eat_service = EatService()
        self._eat_action_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._eat_success_claims: set[tuple[str, str, str]] = set()

    @staticmethod
    def _eat_bool_config(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return default

    @staticmethod
    def _eat_int_config(
        config: Any,
        key: str,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        try:
            value = int(config.get(key, default))
        except (AttributeError, TypeError, ValueError):
            value = default
        return min(maximum, max(minimum, value))

    def _eat_action_lock(self, group_id: str, actor_id: str) -> asyncio.Lock:
        key = (str(group_id), str(actor_id))
        lock = self._eat_action_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._eat_action_locks[key] = lock
        return lock

    def _eat_day_events(
        self, group_id: str, day: datetime.date
    ) -> list[dict[str, Any]]:
        reader = getattr(self, "_report_events", None)
        if not callable(reader):
            return []
        try:
            rows = reader(str(group_id), day.isoformat())
        except Exception as exc:
            logger.warning(f"读取吃群友胃口账本失败：{exc}")
            return []
        return [dict(item) for item in rows if isinstance(item, dict)]

    def _eat_actor_stats(self, group_id: str, actor_id: str) -> tuple[int, int]:
        actor_id = str(actor_id)
        attempts = 0
        successes = 0
        for item in self._eat_day_events(group_id, self._today()):
            if str(item.get("actor_id") or "") != actor_id:
                continue
            kind = str(item.get("kind") or "")
            if kind == self.EVENT_EAT_ATTEMPT:
                attempts += 1
            elif kind == self.EVENT_EAT_SUCCESS:
                successes += 1
        claim_key = (self._today().isoformat(), str(group_id), actor_id)
        if claim_key in self._eat_success_claims:
            successes = max(1, successes)
        return attempts, successes

    def _eat_limit_reason(self, group_id: str, actor_id: str) -> str | None:
        attempts, successes = self._eat_actor_stats(group_id, actor_id)
        if successes >= self.eat_daily_success_limit:
            return (
                "🍚 你今天在本群已经吃饱了（"
                f"{successes}/{self.eat_daily_success_limit} 顿）。"
                "后厨拒绝把幸运连杀升级成灭门宴；明天再来。"
            )
        if attempts >= self.eat_daily_attempt_limit:
            return (
                "🥢 你今天在本群的胃口额度已经用完（"
                f"{attempts}/{self.eat_daily_attempt_limit} 口）。"
                "筷子已被后厨暂扣，明天自动归还。"
            )
        return None

    def _record_eat_event(
        self,
        group_id: str,
        kind: str,
        *,
        actor_id: str,
        target_id: str,
        victim_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        recorder = getattr(self, "_record_gameplay_event", None)
        if not callable(recorder):
            logger.warning(
                "共享 gameplay event 记录器不可用；为避免绕过胃口限制，本次吃群友已取消"
            )
            return False
        try:
            return bool(
                recorder(
                    str(group_id),
                    kind,
                    actor_id=str(actor_id),
                    target_id=str(target_id),
                    victim_id=str(victim_id),
                    metadata=metadata,
                )
            )
        except Exception as exc:
            logger.warning(f"记录吃群友事件失败：{exc}")
            return False

    def _claim_eat_attempt(
        self,
        group_id: str,
        actor_id: str,
        target_id: str,
        *,
        weights: tuple[int, int, int],
        cooked_bonus: int,
    ) -> bool:
        return self._record_eat_event(
            group_id,
            self.EVENT_EAT_ATTEMPT,
            actor_id=actor_id,
            target_id=target_id,
            metadata={
                "success_percent": weights[0],
                "escape_percent": weights[1],
                "backlash_percent": weights[2],
                "cooked_bonus_percent": cooked_bonus,
            },
        )

    def _eat_protection_status(
        self, group_id: str, target_id: str
    ) -> tuple[bool, int]:
        if not self.enable_eat_protection:
            return False, 0
        yesterday = self._today() - datetime.timedelta(days=1)
        target_id = str(target_id)
        count = sum(
            1
            for item in self._eat_day_events(group_id, yesterday)
            if str(item.get("kind") or "") == self.EVENT_EAT_SUCCESS
            and str(item.get("victim_id") or "") == target_id
        )
        return count >= self.eat_protection_threshold, count

    @staticmethod
    def _eat_protection_message(count: int) -> str:
        return (
            f"🛡️ 对方昨天在本群被成功吃了 {count} 次，今天进入『餐后观察期』。"
            "猪圈医生说至少隔一天再端上桌。"
        )

    def _eat_outcome_note(
        self,
        weights: tuple[int, int, int],
        *,
        cooked_bonus: int,
        attempts_after: int,
    ) -> str:
        success, escape, backlash = weights
        bonus_note = (
            f"；熟食诱惑 +{cooked_bonus}%" if cooked_bonus > 0 else ""
        )
        return (
            f"\n📊 本次：吃到 {success}% / 溜走 {escape}% / 反噬 {backlash}%{bonus_note}"
            f"\n🥢 今日胃口：{attempts_after}/{self.eat_daily_attempt_limit}"
        )

    async def _eat_group_target(
        self, event: AstrMessageEvent, target_id: str
    ) -> None:
        actor_id = self._event_sender_id(event)
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(
                event.plain_result("🍴 吃群友只能在群聊开席。私聊不供应自助餐。")
            )
            return
        if not target_id:
            await event.send(
                event.plain_result(
                    "🎯 先 @ 一位群友，或回复他的消息。后厨不能对着空气下锅。"
                )
            )
            return
        if target_id == actor_id:
            await event.send(
                event.plain_result("🍴 不能吃自己。后厨还没穷到要做闭环供应链。")
            )
            return

        async with self._eat_action_lock(group_id, actor_id):
            limit_reason = self._eat_limit_reason(group_id, actor_id)
            if limit_reason:
                await event.send(event.plain_result(limit_reason))
                return

            actor_pig = self._get_daily_pig(actor_id, self._today())
            actor_reason = self._eat_actor_block_reason(actor_pig)
            if actor_reason:
                await event.send(event.plain_result(actor_reason))
                return
            target_pig = self._get_daily_pig(target_id, self._today())
            target_reason = self._eat_target_block_reason(target_pig)
            if target_reason:
                await event.send(event.plain_result(target_reason))
                return

            protected, roast_count = await self._roast_protection_status(
                group_id, target_id
            )
            if protected:
                await event.send(
                    event.plain_result(self._roast_protection_message(roast_count))
                )
                return
            eat_protected, eat_count = self._eat_protection_status(
                group_id, target_id
            )
            if eat_protected:
                await event.send(
                    event.plain_result(self._eat_protection_message(eat_count))
                )
                return

            cooked = special_pig_state(target_pig) == "cooked"
            cooked_bonus = self.eat_cooked_bonus_percent if cooked else 0
            weights = self.eat_service.outcome_weights(
                self.eat_success_percent,
                self.eat_escape_percent,
                success_bonus_percent=cooked_bonus,
            )
            if not self._claim_eat_attempt(
                group_id,
                actor_id,
                target_id,
                weights=weights,
                cooked_bonus=cooked_bonus,
            ):
                await event.send(
                    event.plain_result(
                        "🧯 胃口账本没有记住这一筷子。为了防止无限续杯，本次吃群友已取消，请稍后再试。"
                    )
                )
                return

            attempts_after, _ = self._eat_actor_stats(group_id, actor_id)
            outcome = self.eat_service.choose_eat_outcome(
                success_percent=self.eat_success_percent,
                escape_percent=self.eat_escape_percent,
                success_bonus_percent=cooked_bonus,
            )
            note = self._eat_outcome_note(
                weights,
                cooked_bonus=cooked_bonus,
                attempts_after=attempts_after,
            )

            if outcome == "escape":
                self._record_eat_event(
                    group_id,
                    self.EVENT_EAT_ESCAPE,
                    actor_id=actor_id,
                    target_id=target_id,
                )
                await self._send_with_mention(
                    event,
                    target_id,
                    " 🏃 筷子刚伸过去，对方连猪带盘滑走了。你没吃到，他也没被吃掉；这一口胃口照样消耗。"
                    + note,
                )
                return

            if outcome == "success":
                eaten = await self._replace_today_with_eaten_persisted(
                    target_id, group_id, actor_id, "eat_success"
                )
                if not eaten:
                    await event.send(
                        event.plain_result(
                            "🧯 嘴已经张开，但猪圈账本没记住这一口。吃群友状态写入失败；胃口额度不会回滚，请稍后再试。"
                        )
                    )
                    return
                self._eat_success_claims.add(
                    (self._today().isoformat(), str(group_id), str(actor_id))
                )
                self._record_eat_event(
                    group_id,
                    self.EVENT_EAT_SUCCESS,
                    actor_id=actor_id,
                    target_id=target_id,
                    victim_id=target_id,
                )
                await self._send_with_mention(
                    event,
                    target_id,
                    self._eat_success_message(target_pig)
                    + f"\n🍚 主厨今天在本群已经吃饱（1/{self.eat_daily_success_limit} 顿），不能继续连吃。"
                    + note,
                )
                return

            eaten = await self._replace_today_with_eaten_persisted(
                actor_id, group_id, actor_id, "eat_failure"
            )
            if not eaten:
                await event.send(
                    event.plain_result(
                        "🧯 反噬已经发生，但猪圈账本没记住这一口。状态写入失败；胃口额度不会回滚，请稍后再试。"
                    )
                )
                return
            self._record_eat_event(
                group_id,
                self.EVENT_EAT_BACKLASH,
                actor_id=actor_id,
                target_id=target_id,
                victim_id=actor_id,
            )
            await self._send_with_mention(
                event,
                actor_id,
                " 🍴 下嘴失败，餐桌当场反噬：没吃到别人，反而把自己吃没了。明天抽猪仍可能触发被吃后的重复猪惩罚。"
                + note,
            )

    async def eat_random_group_member(self, event: AstrMessageEvent):
        """Random eat target selection using private RNG and appetite rules."""
        self._claim_command_event(event)
        if not self.enable_group_eat:
            await event.send(event.plain_result("吃群友功能已在配置中关闭。"))
            return
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(
                event.plain_result(
                    "随机🍴 吃群友只能在群聊开席。私聊不供应自助餐。"
                )
            )
            return
        actor_id = self._event_sender_id(event)
        limit_reason = self._eat_limit_reason(group_id, actor_id)
        if limit_reason:
            await event.send(event.plain_result(limit_reason))
            return
        actor_pig = self._get_daily_pig(actor_id, self._today())
        actor_reason = self._eat_actor_block_reason(actor_pig)
        if actor_reason:
            await event.send(event.plain_result(actor_reason))
            return

        members = self._daily_group_members(group_id, self._today().isoformat())
        candidates: list[str] = []
        for user_id in members if isinstance(members, list) else []:
            user_id = str(user_id)
            if user_id == actor_id:
                continue
            pig = self._get_daily_pig(user_id, self._today())
            protected, _ = await self._roast_protection_status(group_id, user_id)
            eat_protected, _ = self._eat_protection_status(group_id, user_id)
            if (
                not self._eat_target_block_reason(pig)
                and not protected
                and not eat_protected
            ):
                candidates.append(user_id)
        if not candidates:
            await event.send(
                event.plain_result(
                    "🍴 今天本群没有可吃的群友：没抽、已吃、人类、烤后保护或餐后观察期都被菜单剔除了。后厨只能啃筷子。"
                )
            )
            return
        target_id = self.eat_service.choose_group_eat_target(candidates)
        await self._send_with_mention(
            event, target_id, " 🎲 餐桌抽签抽中了你。这不是荣誉。"
        )
        await self._eat_group_target(event, target_id)

    async def eat_appetite_status(self, event: AstrMessageEvent):
        """Show today's per-group eat limits and effective probabilities."""
        self._claim_command_event(event)
        if not self.enable_group_eat:
            await event.send(event.plain_result("吃群友功能已在配置中关闭。"))
            return
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(
                event.plain_result("🥢 胃口是群聊状态；私聊没有公用餐桌。")
            )
            return
        actor_id = self._event_sender_id(event)
        attempts, successes = self._eat_actor_stats(group_id, actor_id)
        normal = self.eat_service.outcome_weights(
            self.eat_success_percent,
            self.eat_escape_percent,
        )
        cooked = self.eat_service.outcome_weights(
            self.eat_success_percent,
            self.eat_escape_percent,
            success_bonus_percent=self.eat_cooked_bonus_percent,
        )
        await event.send(
            event.plain_result(
                "🥢 【今日胃口】\n"
                f"尝试：{attempts}/{self.eat_daily_attempt_limit}\n"
                f"成功进食：{successes}/{self.eat_daily_success_limit}\n"
                f"普通目标：吃到 {normal[0]}% / 溜走 {normal[1]}% / 反噬 {normal[2]}%\n"
                f"熟食目标：吃到 {cooked[0]}% / 溜走 {cooked[1]}% / 反噬 {cooked[2]}%\n"
                "成功吃到一位后当天本群立即吃饱；昨天被成功吃过的群友今天默认进入餐后观察期。"
            )
        )
