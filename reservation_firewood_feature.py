from __future__ import annotations

from typing import Any

try:
    from .gameplay_events import EVENT_ROAST_RESERVATION_JOINED
    from .roast_reservations import (
        create_or_join_reservation,
        list_pending_reservations,
    )
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_events import EVENT_ROAST_RESERVATION_JOINED
    from roast_reservations import (
        create_or_join_reservation,
        list_pending_reservations,
    )


class ReservationFirewoodMixin:
    """Route the shared /添柴 surface without falling through to the chat model.

    The current oven-refill contract owns bare ``/添柴`` while a refill round is
    active. Reservation firewood remains available as ``/添柴 @目标`` and, when
    there is no active refill, bare ``/添柴`` may join the only pending trap.
    Compatibility aliases such as ``/添煤`` continue to call the refill handler
    directly from ``main.py``.
    """

    def _oven_refill_round_is_live(self, draw_date: str, group_id: str) -> bool:
        state = getattr(self, "oven_refill_state", {})
        if not isinstance(state, dict):
            return False
        dates = state.get("dates", {})
        by_date = dates.get(str(draw_date), {}) if isinstance(dates, dict) else {}
        row = by_date.get(str(group_id), {}) if isinstance(by_date, dict) else {}
        return bool(
            isinstance(row, dict)
            and (bool(row.get("active")) or bool(row.get("completing")))
        )

    async def firewood_support(self, event, args: str = "") -> None:
        """Claim /添柴 and route it to refill or reservation support."""
        self._claim_command_event(event)

        group_id = str(self._event_group_id(event) or "")
        if not group_id:
            await event.send(
                event.plain_result(
                    "🪵 柴火只认群聊里的锅。私聊先把木头放下。"
                )
            )
            return

        actor_id = str(self._event_sender_id(event) or "")
        if not actor_id:
            await event.send(
                event.plain_result(
                    "🧯 后厨看见一根柴自己飘进来了，但认不出是谁扔的。"
                    "无法确认添柴者，请稍后再试。"
                )
            )
            return

        draw_date = self._today().isoformat()
        requested_target = str(self._extract_roast_target_id(event, args) or "")

        # Keep PR #115's canonical behavior: while a refill round is live, a bare
        # /添柴 feeds that round. An explicit @ target always means reservation.
        if not requested_target and self._oven_refill_round_is_live(draw_date, group_id):
            await self.oven_refill_support(event)
            return

        if not getattr(self, "enable_roast_reservation", False):
            if not requested_target:
                await self.oven_refill_support(event)
                return
            await event.send(
                event.plain_result(
                    "🔒 预约烤猪今天没开锅。这个 @目标 没有地方塞柴。"
                )
            )
            return

        if not getattr(self, "enable_roast", False) or not getattr(
            self, "enable_group_roast", False
        ):
            if not requested_target:
                await self.oven_refill_support(event)
                return
            await event.send(
                event.plain_result(
                    "🔒 今天后厨没开群友这桌。预约烤猪也跟着熄火了。"
                )
            )
            return

        chosen: dict[str, Any] | None = None
        denial = ""
        joined_count = 0
        joined_target = ""

        # Creation/join and draw-trigger settlement share this lock. Selection and
        # the actual join therefore observe one coherent pending-reservation view.
        async with self._roast_reservation_lock:
            with self._data_lock:
                pending = list_pending_reservations(
                    self.roast_reservation_state,
                    draw_date,
                    group_id,
                )

            if requested_target:
                chosen = next(
                    (
                        row
                        for row in pending
                        if str(row.get("target_id") or "") == requested_target
                    ),
                    None,
                )
                if chosen is None:
                    denial = (
                        "🪵 这位群友名下没有待结算的锅，柴火拿错地方了。"
                        "先 /烤群友 @目标 埋伏一口。"
                    )
            elif not pending:
                denial = (
                    "🪵 现在既没有补货轮次，也没有待守的预约烤箱。"
                    "先 /烤箱补货 发车，或 /烤群友 @目标 埋伏一口。"
                )
            elif len(pending) > 1:
                denial = (
                    f"🪵 后厨同时蹲着 {len(pending)} 口预约锅，你这根柴不知道塞哪。"
                    "用 /添柴 @目标 指定；补货轮次进行中时，裸 /添柴 仍优先补货。"
                )
            else:
                chosen = pending[0]

            if chosen is not None and not denial:
                target_id = str(chosen.get("target_id") or "")
                chef_id = str(chosen.get("chef_id") or "")
                participants = [
                    str(item)
                    for item in chosen.get("participants", [])
                    if str(item)
                ]

                # The target may have drawn while this command was waiting for the
                # reservation lock. In that case the draw-trigger settlement owns
                # the trap; never create a second participant mutation now.
                if self._get_daily_pig(target_id, self._today()):
                    denial = (
                        "🔥 目标刚刚现身，原预约正在结算。"
                        "这根柴先别往已经掀开的锅里塞。"
                    )
                elif actor_id == target_id:
                    denial = (
                        "🪵 你就是锅里等着的食材，不能自己往锅底塞柴。"
                        "这叫利益冲突。"
                    )
                elif actor_id == chef_id:
                    denial = (
                        "🪵 你就是这口锅的主厨，开局已经算 1 人。"
                        "不能左手当主厨、右手再冒充群友——叫别人来 /添柴。"
                    )
                elif actor_id in participants:
                    denial = (
                        "🪵 你的名字已经在柴火簿上了。"
                        "再塞不加人头，只会让烤箱怀疑你有私情。"
                    )
                elif len(participants) >= self.roast_reservation_max_participants:
                    denial = (
                        "🪵 这口锅旁边已经挤满了，最多 "
                        f"{self.roast_reservation_max_participants} 人。"
                        "再来一个只能站窗外闻味。"
                    )
                else:
                    actor_pig = self._get_daily_pig(actor_id, self._today())
                    actor_reason = self._roast_block_reason(actor_pig, subject="actor")
                    if not actor_pig:
                        denial = (
                            "🪵 后厨只收今天有猪证的柴工。"
                            "先 /今日小猪，再回来扇火。"
                        )
                    elif actor_reason:
                        denial = f"🪵 这根柴暂时塞不进去：{actor_reason}"
                    else:
                        with self._data_lock:
                            result = create_or_join_reservation(
                                self.roast_reservation_state,
                                draw_date=draw_date,
                                group_id=group_id,
                                target_id=target_id,
                                actor_id=actor_id,
                                max_participants=self.roast_reservation_max_participants,
                            )
                            status = str(result.get("status") or "")
                            reservation = result.get("reservation") or {}
                            if status == "joined":
                                self._save_roast_reservations_locked()
                                joined_count = len(reservation.get("participants", []))
                                joined_target = target_id
                            elif status == "existing":
                                denial = (
                                    "🪵 你的名字已经在柴火簿上了。"
                                    "每人每口锅只算一次，再塞也不加人头。"
                                )
                            elif status == "full":
                                denial = (
                                    "🪵 这口锅旁边已经挤满了，最多 "
                                    f"{self.roast_reservation_max_participants} 人。"
                                    "后来者请去窗外排队闻味。"
                                )
                            elif status == "resolved":
                                denial = (
                                    "🔥 这口预约已经结算完了。"
                                    "柴来晚了，只能赶上下次开锅。"
                                )
                            else:
                                denial = (
                                    "🧯 你伸手塞柴时这口锅刚好变了状态。"
                                    "预约已经发生变化，请重新查看后再试。"
                                )

        if denial:
            await event.send(event.plain_result(denial))
            return

        if not joined_target:
            await event.send(
                event.plain_result(
                    "🧯 柴还在手里，但后厨找不到能接它的预约烤箱。"
                    "命令已经由插件处理，请重新查看预约后再试。"
                )
            )
            return

        writer = getattr(self, "_record_gameplay_event", None)
        if callable(writer):
            writer(
                group_id,
                EVENT_ROAST_RESERVATION_JOINED,
                actor_id=actor_id,
                target_id=joined_target,
                metadata={"participants": joined_count, "via": "firewood-command"},
                draw_date=draw_date,
                event_id=(
                    f"roast-reservation-join:{draw_date}:{group_id}:"
                    f"{joined_target}:{actor_id}"
                ),
            )
        await self._send_with_mention(
            event,
            joined_target,
            f" 🪵 又一根柴悄悄塞进来；现在共有 {joined_count} 人蹲锅。",
        )
