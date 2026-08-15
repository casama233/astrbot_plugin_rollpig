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
            await event.send(event.plain_result("🪵 烤群友功能已关闭，现在没有预约烤箱可以添柴。"))
            return
        if not getattr(self, "enable_roast_reservation", False):
            await event.send(event.plain_result("🪵 预约烤猪功能已关闭，现在不能添柴。"))
            return

        group_id = str(self._event_group_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("🪵 /添柴 只能在群聊里使用。"))
            return

        actor_id = str(self._event_sender_id(event) or "")
        if not actor_id:
            await event.send(event.plain_result("🪵 无法确认是谁在添柴，请稍后再试。"))
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
                        "🪵 这个目标当前没有待结算的预约烤箱；"
                        "先用 /烤群友 @目标 建立预约。"
                    )
            elif not pending:
                denial = "🪵 本群今天没有待添柴的预约烤箱。先用 /烤群友 @目标 埋伏一口。"
            elif len(pending) > 1:
                denial = (
                    f"🪵 本群今天有 {len(pending)} 口待结算预约烤箱；"
                    "请用 /添柴 @目标 指定要给哪一口添柴。"
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
                    denial = "🪵 你就是这口烤箱等着的食材，不能给自己的预约添柴。"
                elif actor_id == chef_id:
                    denial = (
                        "🪵 你就是这口预约烤箱的主厨，建立预约时已经算 1 人，"
                        "不能再给自己添柴。叫其他群友来 /添柴 吧。"
                    )
                elif actor_id in participants:
                    denial = "🪵 你已经给这口预约烤箱添过柴了；每人每张预约只计一次。"
                elif len(participants) >= self.roast_reservation_max_participants:
                    denial = (
                        "🪵 这口烤箱已经挤满了，最多 "
                        f"{self.roast_reservation_max_participants} 人围观添柴。"
                    )
                else:
                    actor_pig = self._get_daily_pig(actor_id, self._today())
                    actor_reason = self._roast_block_reason(actor_pig, subject="actor")
                    if not actor_pig:
                        denial = "🪵 想添柴前，请先用 /今日小豬 抽出自己今天可料理的小豬。"
                    elif actor_reason:
                        denial = f"🪵 现在不能添柴：{actor_reason}"
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
                                denial = "🪵 你已经给这口预约烤箱添过柴了；每人每张预约只计一次。"
                            elif status == "full":
                                denial = (
                                    "🪵 这口烤箱已经挤满了，最多 "
                                    f"{self.roast_reservation_max_participants} 人围观添柴。"
                                )
                            else:
                                denial = "🪵 这口预约烤箱刚刚发生了变化，请重新查看后再添柴。"

        if denial:
            await event.send(event.plain_result(denial))
            return

        if not joined_target:
            # Defensive terminal fallback: the command remains claimed even if a
            # future reservation status is added without updating this handler.
            await event.send(event.plain_result("🪵 没有找到可以加入的预约烤箱。"))
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
            f" 🪵 又有人悄悄添了一把柴；现在共有 {joined_count} 人蹲守。",
        )
