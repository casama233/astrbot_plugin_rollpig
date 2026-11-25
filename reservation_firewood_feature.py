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
                    '🪵 柴火只认群聊里的灶台，私聊先把木柴抱回去吧。'
                )
            )
            return

        actor_id = str(self._event_sender_id(event) or "")
        if not actor_id:
            await event.send(
                event.plain_result(
                    '🧯 灶台边凭空多出一根柴，却没看清是谁丢的。无法识别添柴人，请稍后再试。'
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
                    '🔒 预约烤猪功能今日未开启，这位 @目标 没灶台可塞柴。'
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
                    '🔒 今日未开放群友烤制专场，预约烤猪也随之熄火了。'
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
                        '🪵 这位群友名下还没有待开锅的预约，柴火送错灶了。先发送 /烤群友 @目标 架起一口锅。'
                    )
            elif not pending:
                denial = (
                    '🪵 当前既没有补货车次，也没有待守候的预约烤炉。先用 /烤箱补货 发车，或用 /烤群友 @目标 架锅。'
                )
            elif len(pending) > 1:
                denial = (
                    f'🪵 场内同时架着 {len(pending)} 口预约锅，这根柴不知该往哪塞。请用 /添柴 @目标 指定目标；补货期间，单独发送 /添柴 仍优先用于补货。'
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
                        '🔥 目标刚刚现身，原预约正在开锅结算中，这根柴就先别往里塞了。'
                    )
                elif actor_id == target_id:
                    denial = (
                        '🪵 你自己就是锅里待烤的食材，哪有自己往灶底添柴的道理，这属于利益冲突。'
                    )
                elif actor_id == chef_id:
                    denial = (
                        '🪵 你本就是这口锅的发起人，开局已计入 1 人。别左手点火右手装路人，快喊别人来 /添柴。'
                    )
                elif actor_id in participants:
                    denial = (
                        '🪵 你的大名已经记在添柴名册上了。重复塞柴不加人头，只会让人怀疑你和锅里有私情。'
                    )
                elif len(participants) >= self.roast_reservation_max_participants:
                    denial = (
                        f'🪵 这口锅边已经围得水泄不通，上限 {self.roast_reservation_max_participants} 人。再来一位只能站窗外闻香味了。'
                    )
                else:
                    actor_pig = self._get_daily_pig(actor_id, self._today())
                    actor_reason = self._roast_block_reason(actor_pig, subject="actor")
                    if not actor_pig:
                        denial = (
                            '🪵 今日还没领取猪籍，灶台拒收你的柴火。先发送 /今日小猪，再回来扇风点火。'
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
                                    '🪵 你的名字已在添柴名册中。每口锅每人仅计一次，多塞也不加人头。'
                                )
                            elif status == "full":
                                denial = (
                                    f'🪵 这口锅旁已经站满了，最多容纳 {self.roast_reservation_max_participants} 人。后来者请移步窗外排队闻香。'
                                )
                            elif status == "resolved":
                                denial = (
                                    '🔥 这份预约已经完成结算。柴火送晚一步，只能等下次开炉了。'
                                )
                            else:
                                denial = (
                                    '🧯 你刚伸手添柴，锅里的局势就变了。预约状态已刷新，请重新查看后再试。'
                                )

        if denial:
            await event.send(event.plain_result(denial))
            return

        if not joined_target:
            await event.send(
                event.plain_result(
                    '🧯 柴火攥在手里，却没找着对应的预约锅。指令已受理，请重新查看预约状态后再试。'
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
            f' 🪵 又一根木柴悄悄塞进灶底；当前共有 {joined_count} 人守锅。',
        )
