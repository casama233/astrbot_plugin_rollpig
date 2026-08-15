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
    """Expose reservation firewood as a real terminal command.

    Before this mixin existed, "添柴" was only a gameplay label: another user
    had to repeat ``/烤群友 @目标`` to join an existing reservation. A literal
    ``/添柴`` therefore was not claimed by RollPig and could fall through to the
    chat model. Every path in this handler claims the event first and answers
    with deterministic plugin copy instead.
    """

    async def roast_reservation_add_firewood(self, event, args: str = "") -> None:
        self._claim_command_event(event)

        if not self.enable_roast or not self.enable_group_roast:
            await event.send(
                event.plain_result(
                    "🔒 今天后厨不收柴。烤群友玩法已关，这根木头先留着。"
                )
            )
            return
        if not getattr(self, "enable_roast_reservation", False):
            await event.send(
                event.plain_result(
                    "🔒 预约烤猪今天没开锅。没有埋伏，就没有地方塞这根柴。"
                )
            )
            return

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
        chosen: dict[str, Any] | None = None
        denial = ""
        joined_count = 0
        joined_target = ""

        # Settlement uses the same async lock. Keeping selection + validation +
        # join under it prevents a target from resolving between those steps.
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
                    "🪵 今天这群没有待守的烤箱。"
                    "先 /烤群友 @目标 埋伏一口，再来添柴。"
                )
            elif len(pending) > 1:
                denial = (
                    f"🪵 后厨同时蹲着 {len(pending)} 口锅，你这根柴不知道塞哪。"
                    "用 /添柴 @目标 指定。"
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

                if actor_id == target_id:
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
                            else:
                                denial = (
                                    "🧯 你伸手塞柴时这口锅刚好变了状态。"
                                    "预约已经发生变化，请重新查看后再试。"
                                )

        if denial:
            await event.send(event.plain_result(denial))
            return

        if not joined_target:
            # Defensive terminal fallback: the command remains claimed even if a
            # future reservation status is added without updating this handler.
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
