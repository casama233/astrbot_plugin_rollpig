from __future__ import annotations

import asyncio
from typing import Any

from astrbot.api import logger

try:
    from .gameplay_events import (
        EVENT_ROAST_BACKLASH,
        EVENT_ROAST_ESCAPE,
        EVENT_ROAST_RESERVATION_CREATED,
        EVENT_ROAST_RESERVATION_JOINED,
        EVENT_ROAST_RESERVATION_TRIGGERED,
        EVENT_ROAST_SUCCESS,
    )
    from .roast_reservations import (
        create_or_join_reservation,
        ensure_reservation_state,
        get_reservation,
        prune_reservations,
        resolve_reservation,
    )
    from .rollpig_core import parse_config_bool
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_events import (
        EVENT_ROAST_BACKLASH,
        EVENT_ROAST_ESCAPE,
        EVENT_ROAST_RESERVATION_CREATED,
        EVENT_ROAST_RESERVATION_JOINED,
        EVENT_ROAST_RESERVATION_TRIGGERED,
        EVENT_ROAST_SUCCESS,
    )
    from roast_reservations import (
        create_or_join_reservation,
        ensure_reservation_state,
        get_reservation,
        prune_reservations,
        resolve_reservation,
    )
    from rollpig_core import parse_config_bool


class RoastReservationMixin:
    """Turn explicit roasts against not-yet-drawn targets into same-group traps."""

    ROAST_RESERVATION_KEEP_DAYS = 2

    def __init__(self, context, config):
        super().__init__(context, config)
        self._init_roast_reservations()

    def _init_roast_reservations(self) -> None:
        config = self.config if hasattr(self.config, "get") else {}
        self.enable_roast_reservation = parse_config_bool(
            config.get("enable_roast_reservation", True), True
        )
        try:
            maximum = int(config.get("roast_reservation_max_participants", 12))
        except (TypeError, ValueError):
            maximum = 12
        self.roast_reservation_max_participants = min(20, max(2, maximum))
        self.roast_reservation_state_path = (
            self.plugin_data_dir / "roast_reservations.json"
        )
        default = {"version": 1, "reservations": {}}
        try:
            loaded = self.load_json(self.roast_reservation_state_path, default)
        except Exception as exc:
            logger.warning(f"预约烤猪状态读取失败，已使用空状态：{exc}")
            loaded = default
        self.roast_reservation_state = ensure_reservation_state(loaded)
        self._roast_reservation_lock = asyncio.Lock()
        with self._data_lock:
            if prune_reservations(
                self.roast_reservation_state,
                self._today(),
                self.ROAST_RESERVATION_KEEP_DAYS,
            ):
                self._save_roast_reservations_locked()

    def _save_roast_reservations_locked(self) -> None:
        self.save_json(
            self.roast_reservation_state_path, self.roast_reservation_state
        )

    def _pending_roast_reservation(
        self, draw_date: str, group_id: str, target_id: str
    ) -> dict[str, Any] | None:
        with self._data_lock:
            row = get_reservation(
                self.roast_reservation_state, draw_date, group_id, target_id
            )
        return row if row and str(row.get("status") or "") == "pending" else None

    async def _create_or_join_roast_reservation(
        self,
        event,
        *,
        group_id: str,
        actor_id: str,
        target_id: str,
    ) -> bool:
        """Reserve an absent target; creator pays one charge, later users join free."""
        today = self._today().isoformat()
        actor_pig = self._get_daily_pig(actor_id, self._today())
        actor_reason = self._roast_block_reason(actor_pig, subject="actor")
        if actor_reason:
            await event.send(
                event.plain_result(
                    '🔥 想要设伏坑人，得先证明自己今日也是只可下锅的小猪。请先 /今日小猪。'
                    if not actor_pig
                    else actor_reason
                )
            )
            return True

        protected, roast_count = await self._roast_protection_status(
            group_id, target_id
        )
        if protected:
            await event.send(
                event.plain_result(self._roast_protection_message(roast_count))
            )
            return True

        # Creation/join and post-draw settlement share one lock. The target state is
        # re-read only after acquiring it, closing the window where the target could
        # draw between the caller's first check and reservation creation.
        async with self._roast_reservation_lock:
            with self._data_lock:
                existing = get_reservation(
                    self.roast_reservation_state, today, group_id, target_id
                )

            existing_status = str((existing or {}).get("status") or "")
            if existing_status == "pending":
                # If the target has already appeared, the pending trap belongs to
                # the draw-trigger settlement. Do not fall through to a second
                # ordinary roast while that settlement is waiting for this lock.
                if self._get_daily_pig(target_id, self._today()):
                    await event.send(
                        event.plain_result(
                            '🔥 目标刚一露头，先前的埋伏锅便已掀盖。切勿往正在结算的锅里硬塞第二把柴。'
                        )
                    )
                    return True

                with self._data_lock:
                    result = create_or_join_reservation(
                        self.roast_reservation_state,
                        draw_date=today,
                        group_id=group_id,
                        target_id=target_id,
                        actor_id=actor_id,
                        max_participants=self.roast_reservation_max_participants,
                    )
                    if result.get("status") in {"joined", "existing"}:
                        self._save_roast_reservations_locked()
                status = str(result.get("status") or "")
                reservation = result.get("reservation") or {}
                participants = reservation.get("participants", [])
                if status == "full":
                    await event.send(
                        event.plain_result(
                            f'🪵 这口锅边已经围满 {self.roast_reservation_max_participants} 人。再挤进来就只能站窗外闻个香味了。'
                        )
                    )
                elif status == "existing":
                    await event.send(
                        event.plain_result('🪵 你早就在这口锅旁蹲守多时了。重复签到可不会多发你一把小板凳。')
                    )
                else:
                    writer = getattr(self, "_record_gameplay_event", None)
                    if callable(writer):
                        writer(
                            group_id,
                            EVENT_ROAST_RESERVATION_JOINED,
                            actor_id=actor_id,
                            target_id=target_id,
                            metadata={"participants": len(participants)},
                            draw_date=today,
                            event_id=(
                                f"roast-reservation-join:{today}:{group_id}:"
                                f"{target_id}:{actor_id}"
                            ),
                        )
                    await self._send_with_mention(
                        event,
                        target_id,
                        f' 🪵 又一根干柴悄然入灶；当前已有 {len(participants)} 人围锅蹲守。',
                    )
                return True

            if existing_status == "resolved":
                # A resolved same-day reservation is terminal. Return to the
                # ordinary roast path instead of reopening the trap.
                return False

            if self._get_daily_pig(target_id, self._today()):
                return False

            charge_status = await self._consume_group_roast_charge(group_id, actor_id)
            if not charge_status.get("consumed"):
                remaining = int(charge_status.get("next_refill_seconds", 0) or 0)
                await event.send(
                    event.plain_result(
                        f'🔥 炉火能量已彻底耗尽（0/{self.group_roast_max_charges}），下一格需等待 {self._format_cooldown(remaining)} 方能自动恢复。眼下设伏也只能守着一口冷锅。'
                    )
                )
                return True
            with self._data_lock:
                result = create_or_join_reservation(
                    self.roast_reservation_state,
                    draw_date=today,
                    group_id=group_id,
                    target_id=target_id,
                    actor_id=actor_id,
                    max_participants=self.roast_reservation_max_participants,
                )
                prune_reservations(
                    self.roast_reservation_state,
                    self._today(),
                    self.ROAST_RESERVATION_KEEP_DAYS,
                )
                self._save_roast_reservations_locked()
            reservation = result.get("reservation") or {}
            writer = getattr(self, "_record_gameplay_event", None)
            if callable(writer):
                writer(
                    group_id,
                    EVENT_ROAST_RESERVATION_CREATED,
                    actor_id=actor_id,
                    target_id=target_id,
                    metadata={"participants": 1},
                    draw_date=today,
                    event_id=f"roast-reservation:{today}:{group_id}:{target_id}",
                )
            await self._send_with_mention(
                event,
                target_id,
                f'🔥 你今日虽未抽猪，但埋伏大锅已替你支好。只待你在本群 /今日小猪，即刻开盖结算。\n主厨率先蹲点，至多 {self.roast_reservation_max_participants} 人可围炉；输入 /添柴 @你 即可入伙，继续 /烤群友 @你 亦可。'
                + self._roast_charge_note(charge_status),
            )
            logger.info(
                "创建预约烤猪：group=%s target=%s chef=%s id=%s",
                group_id,
                target_id,
                actor_id,
                reservation.get("id", ""),
            )
            return True

    async def _roast_group_target(
        self,
        event,
        target_id: str,
        *,
        bypass: bool = False,
    ) -> None:
        """Intercept only explicit normal roasts whose target has not drawn yet."""
        if bypass or not self.enable_roast_reservation:
            return await super()._roast_group_target(
                event, target_id, bypass=bypass
            )
        actor_id = self._event_sender_id(event)
        group_id = self._event_group_id(event)
        if not group_id or not target_id or target_id == actor_id:
            return await super()._roast_group_target(
                event, target_id, bypass=bypass
            )
        target_pig = self._get_daily_pig(target_id, self._today())
        if target_pig:
            return await super()._roast_group_target(
                event, target_id, bypass=bypass
            )
        handled = await self._create_or_join_roast_reservation(
            event,
            group_id=str(group_id),
            actor_id=str(actor_id),
            target_id=str(target_id),
        )
        if not handled:
            return await super()._roast_group_target(
                event, target_id, bypass=bypass
            )

    async def _settle_roast_reservation(
        self,
        event,
        reservation: dict[str, Any],
        target_pig: dict | None,
        *,
        group_id: str,
        target_id: str,
        draw_date: str,
    ) -> None:
        chef_id = str(reservation.get("chef_id") or "")
        participants = [
            str(item)
            for item in reservation.get("participants", [])
            if str(item)
        ]
        if not chef_id:
            return
        outcome = str(reservation.get("outcome") or "")
        writer = getattr(self, "_record_gameplay_event", None)
        if callable(writer):
            writer(
                group_id,
                EVENT_ROAST_RESERVATION_TRIGGERED,
                actor_id=chef_id,
                target_id=target_id,
                metadata={
                    "participants": len(participants),
                    "outcome": outcome,
                },
                draw_date=draw_date,
                event_id=f"roast-reservation-trigger:{draw_date}:{group_id}:{target_id}",
            )

        if outcome == "blocked":
            await event.send(event.plain_result(
                self._roast_block_reason(target_pig, subject="target")
            ))
            return

        await self._send_with_mention(
            event,
            target_id,
            f'🔥 你前脚刚领完猪，埋伏锅后脚便掀了盖！\n主厨携 {max(0, len(participants) - 1)} 位添柴群友正式开启结算。',
        )

        if outcome == "escape":
            if callable(writer):
                writer(
                    group_id,
                    EVENT_ROAST_ESCAPE,
                    actor_id=chef_id,
                    target_id=target_id,
                    metadata={"reserved": True},
                    draw_date=draw_date,
                    event_id=f"roast-reservation-outcome:{draw_date}:{group_id}:{target_id}",
                )
            await event.send(
                event.plain_result('💨 主厨早就架好炉子蹲点啦，可惜你刚一抽猪就警觉开溜，惊险逃过一劫！')
            )
            return

        if outcome == "backlash":
            chef_pig = self._get_daily_pig(chef_id, self._today())
            chef_reason = self._roast_block_reason(chef_pig, subject="actor")
            victim_id = "" if chef_reason else chef_id
            if callable(writer):
                writer(
                    group_id,
                    EVENT_ROAST_BACKLASH,
                    actor_id=chef_id,
                    target_id=target_id,
                    victim_id=victim_id,
                    metadata={"reserved": True},
                    draw_date=draw_date,
                    event_id=f"roast-reservation-outcome:{draw_date}:{group_id}:{target_id}",
                )
            if chef_reason:
                await event.send(
                    event.plain_result(
                        '🔥 烤架本欲反噬主厨，翻面一瞧：主厨今日并无可供料理的小猪。这一口算他命硬。'
                    )
                )
                return
            await self._send_with_mention(
                event,
                chef_id,
                ' 🔥 设伏意外翻车，烤架顺着火舌反咬主厨一口。\n这回轮到主厨的小猪亲自上桌。',
            )
            await self._record_group_roast(group_id, chef_id, draw_date)
            await self._send_roast_card(event, chef_pig, chef_id)
            return

        if callable(writer):
            writer(
                group_id,
                EVENT_ROAST_SUCCESS,
                actor_id=chef_id,
                target_id=target_id,
                victim_id=target_id,
                metadata={"reserved": True},
                draw_date=draw_date,
                event_id=f"roast-reservation-outcome:{draw_date}:{group_id}:{target_id}",
            )
        await event.send(
            event.plain_result('🔥 蹲守成功！主厨早早备好了烤箱，你刚抽出的今日小猪瞬间被烤得滋滋冒油。')
        )
        await self._record_group_roast(group_id, target_id, draw_date)
        await self._send_roast_card(event, target_pig, target_id)

    async def _trigger_roast_reservation_after_draw(
        self, event, pig_data: dict, user_id: str, fallback_title: str
    ) -> None:
        if fallback_title != "今日小猪" or not self.enable_roast_reservation:
            return
        sender_id = str(self._event_sender_id(event))
        group_id = str(self._event_group_id(event) or "")
        target_id = str(user_id)
        if not group_id or sender_id != target_id:
            return
        today = self._today()
        draw_date = today.isoformat()

        # The pending check must happen while holding the same lock used by
        # reservation creation. Otherwise a draw can observe "no reservation"
        # immediately before a racing request creates one and leaves it stranded.
        async with self._roast_reservation_lock:
            pending = self._pending_roast_reservation(
                draw_date, group_id, target_id
            )
            if not pending:
                return
            target_pig = self._get_daily_pig(target_id, today)
            blocked = self._roast_block_reason(target_pig, subject="target")
            outcome = "blocked" if blocked else self.roast_service.choose_group_roast_outcome()
            with self._data_lock:
                resolved = resolve_reservation(
                    self.roast_reservation_state,
                    draw_date=draw_date,
                    group_id=group_id,
                    target_id=target_id,
                    outcome=outcome,
                )
                if resolved:
                    self._save_roast_reservations_locked()
        if not resolved:
            return
        try:
            await self._settle_roast_reservation(
                event,
                resolved,
                target_pig,
                group_id=group_id,
                target_id=target_id,
                draw_date=draw_date,
            )
        except Exception as exc:
            # The state was marked resolved before any delivery. This avoids a
            # duplicate roast if an adapter times out after accepting the message.
            logger.warning(f"预约烤猪结算投递状态不确定，不会自动重复结算：{exc}")

    async def send_rendered_pig(
        self,
        event,
        pig_data: dict,
        user_id: str,
        intro: str = '。这是为你派发的今日小猪：',
        fallback_title: str = "今日小猪",
    ):
        result = await super().send_rendered_pig(
            event,
            pig_data,
            user_id,
            intro=intro,
            fallback_title=fallback_title,
        )
        await self._trigger_roast_reservation_after_draw(
            event, pig_data, str(user_id), fallback_title
        )
        return result
