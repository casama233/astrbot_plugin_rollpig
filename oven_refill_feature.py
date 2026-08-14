from __future__ import annotations

import time
from typing import Any

try:
    from .gameplay_events import (
        EVENT_OVEN_REFILL_FAILED,
        EVENT_OVEN_REFILL_STARTED,
        EVENT_OVEN_REFILL_SUCCEEDED,
        EVENT_OVEN_REFILL_SUPPORTED,
    )
    from .roast_charges import add_roast_charge_state, bootstrap_legacy_cooldown
    from .services import OvenRefillService
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_events import (
        EVENT_OVEN_REFILL_FAILED,
        EVENT_OVEN_REFILL_STARTED,
        EVENT_OVEN_REFILL_SUCCEEDED,
        EVENT_OVEN_REFILL_SUPPORTED,
    )
    from roast_charges import add_roast_charge_state, bootstrap_legacy_cooldown
    from services import OvenRefillService


class OvenRefillMixin:
    """Cooperative group refill orchestration over the Phase 3A charge contract."""

    def __init__(self, context, config):
        super().__init__(context, config)
        self._init_oven_refill_feature()

    def _init_oven_refill_feature(self) -> None:
        config = self.config if hasattr(self.config, "get") else {}
        self.enable_oven_refill = self._config_bool(
            config.get("enable_oven_refill", True), True
        )
        try:
            daily_limit = int(config.get("oven_refill_daily_limit", 2))
        except (TypeError, ValueError):
            daily_limit = 2
        self.oven_refill_daily_limit = min(5, max(1, daily_limit))
        try:
            ratio = int(config.get("oven_refill_support_ratio_percent", 30))
        except (TypeError, ValueError):
            ratio = 30
        self.oven_refill_support_ratio_percent = min(100, max(1, ratio))
        try:
            minimum = int(config.get("oven_refill_min_supporters", 3))
        except (TypeError, ValueError):
            minimum = 3
        self.oven_refill_min_supporters = min(20, max(2, minimum))
        try:
            extra = int(config.get("oven_refill_extra_supporters_per_success", 2))
        except (TypeError, ValueError):
            extra = 2
        self.oven_refill_extra_supporters_per_success = min(10, max(0, extra))
        self.oven_refill_service = OvenRefillService()

    def _oven_active_group_members(self, group_id: str, draw_date: str) -> list[str]:
        values = self._daily_group_members(str(group_id), str(draw_date))
        return list(dict.fromkeys(str(item) for item in values if str(item)))

    def _oven_actor_is_active(self, actor_id: str, members: list[str]) -> bool:
        safe = set(self._user_read_candidates(str(actor_id)))
        safe.add(self._storage_user_key(str(actor_id)))
        return bool(safe.intersection(str(item) for item in members))

    def _oven_storage_members(self, members: list[str]) -> list[str]:
        return list(
            dict.fromkeys(self._storage_user_key(str(item)) for item in members if str(item))
        )

    def _record_oven_event(
        self,
        group_id: str,
        kind: str,
        *,
        actor_id: str,
        draw_date: str,
        metadata: dict[str, Any],
        event_id: str,
    ) -> None:
        writer = getattr(self, "_record_gameplay_event", None)
        if callable(writer):
            writer(
                str(group_id),
                kind,
                actor_id=str(actor_id),
                metadata=metadata,
                draw_date=str(draw_date),
                event_id=event_id,
            )

    def _json_refill_bucket(self, draw_date: str, group_id: str) -> dict[str, Any]:
        root = self.roast_state.setdefault("oven_refills", {})
        if not isinstance(root, dict):
            root = {}
            self.roast_state["oven_refills"] = root
        by_date = root.setdefault(str(draw_date), {})
        if not isinstance(by_date, dict):
            by_date = {}
            root[str(draw_date)] = by_date
        row = by_date.setdefault(
            str(group_id),
            {"successes": 0, "round": 0, "active": False, "supporters": []},
        )
        if not isinstance(row, dict):
            row = {"successes": 0, "round": 0, "active": False, "supporters": []}
            by_date[str(group_id)] = row
        return row

    def _json_start_refill(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_count: int,
        now: float,
    ) -> dict[str, Any]:
        with self._data_lock:
            row = self._json_refill_bucket(draw_date, group_id)
            successes = int(row.get("successes", 0) or 0)
            if successes >= self.oven_refill_daily_limit:
                return {"state": "limit", "successes": successes}
            if bool(row.get("active")):
                supporters = [str(item) for item in row.get("supporters", []) if str(item)]
                return {
                    "state": "active",
                    "successes": successes,
                    "round": int(row.get("round", 0) or 0),
                    "required": int(row.get("required", 0) or 0),
                    "supporters": supporters,
                }
            required = self.oven_refill_service.refill_requirement(
                active_count,
                successes,
                ratio_percent=self.oven_refill_support_ratio_percent,
                minimum_supporters=self.oven_refill_min_supporters,
                extra_per_success=self.oven_refill_extra_supporters_per_success,
            )
            round_no = int(row.get("round", 0) or 0) + 1
            row.update(
                {
                    "active": True,
                    "round": round_no,
                    "required": required,
                    "active_count": int(active_count),
                    "started_by": str(actor_id),
                    "started_at": float(now),
                    "supporters": [str(actor_id)],
                }
            )
            self._save_roast_state()
            return {
                "state": "started",
                "successes": successes,
                "round": round_no,
                "required": required,
                "supporters": [str(actor_id)],
            }

    def _json_support_refill(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_members: list[str],
        now: float,
    ) -> dict[str, Any]:
        with self._data_lock:
            row = self._json_refill_bucket(draw_date, group_id)
            if not bool(row.get("active")):
                return {"state": "inactive"}
            supporters = [str(item) for item in row.get("supporters", []) if str(item)]
            if actor_id in supporters:
                return {
                    "state": "duplicate",
                    "round": int(row.get("round", 0) or 0),
                    "required": int(row.get("required", 0) or 0),
                    "supporters": supporters,
                }
            supporters.append(str(actor_id))
            row["supporters"] = supporters
            required = int(row.get("required", 0) or 0)
            round_no = int(row.get("round", 0) or 0)
            if len(supporters) < required:
                self._save_roast_state()
                return {
                    "state": "supported",
                    "round": round_no,
                    "required": required,
                    "supporters": supporters,
                }

            charge_states = self.roast_state.setdefault("roast_charges", {})
            if not isinstance(charge_states, dict):
                charge_states = {}
                self.roast_state["roast_charges"] = charge_states
            cooldowns = self.roast_state.setdefault("cooldowns", {})
            restored = 0
            for storage_member in active_members:
                key = f"{group_id}:{storage_member}"
                entry = charge_states.get(key)
                if not isinstance(entry, dict):
                    legacy_last_used = (
                        float(cooldowns.get(key, 0) or 0)
                        if isinstance(cooldowns, dict)
                        else 0
                    )
                    entry = bootstrap_legacy_cooldown(
                        legacy_last_used,
                        now=now,
                        max_charges=self.group_roast_max_charges,
                        recovery_seconds=self.group_roast_cooldown_seconds,
                    )
                updated = add_roast_charge_state(
                    entry,
                    now=now,
                    max_charges=self.group_roast_max_charges,
                    recovery_seconds=self.group_roast_cooldown_seconds,
                )
                charge_states[key] = {
                    "charges": int(updated["charges"]),
                    "refill_anchor": float(updated["refill_anchor"]),
                }
                if updated.get("increased"):
                    restored += 1

            row["active"] = False
            row["completed_at"] = float(now)
            if restored > 0:
                row["successes"] = int(row.get("successes", 0) or 0) + 1
                state = "succeeded"
            else:
                row["failed_reason"] = "no_missing_charges"
                state = "failed"
            self._save_roast_state()
            return {
                "state": state,
                "round": round_no,
                "required": required,
                "supporters": supporters,
                "restored_users": restored,
                "active_users": len(active_members),
            }

    async def oven_refill(self, event) -> None:
        self._claim_command_event(event)
        if not self.enable_oven_refill:
            await event.send(event.plain_result("烤箱补货当前未启用。"))
            return
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("烤箱补货只能在群聊中发起。"))
            return
        draw_date = self._today().isoformat()
        members = self._oven_active_group_members(group_id, draw_date)
        if not self._oven_actor_is_active(actor_id, members):
            await event.send(event.plain_result("先在本群抽一只今日小猪，再来组织烤箱补货。"))
            return
        if len(members) < 2:
            await event.send(event.plain_result("今天本群至少需要 2 位活跃玩家才能组织补货。"))
            return

        storage_actor = self._storage_user_key(actor_id)
        now = time.time()
        if getattr(self.storage, "supports_domain_writes", False):
            result = await __import__("asyncio").to_thread(
                self.storage.start_oven_refill,
                draw_date=draw_date,
                group_id=group_id,
                actor_id=storage_actor,
                active_count=len(members),
                now=now,
                daily_limit=self.oven_refill_daily_limit,
                ratio_percent=self.oven_refill_support_ratio_percent,
                minimum_supporters=self.oven_refill_min_supporters,
                extra_per_success=self.oven_refill_extra_supporters_per_success,
            )
        else:
            result = self._json_start_refill(
                draw_date=draw_date,
                group_id=group_id,
                actor_id=storage_actor,
                active_count=len(members),
                now=now,
            )

        state = str(result.get("state") or "")
        if state == "limit":
            await event.send(event.plain_result("🔥 本群今天的烤箱补货次数已经用完了。"))
            return
        if state == "active":
            supporters = result.get("supporters", [])
            await event.send(
                event.plain_result(
                    f"🪵 补货进行中：{len(supporters)}/{int(result.get('required', 0) or 0)} 人已添煤；发送 /添煤 支持。"
                )
            )
            return
        if state != "started":
            await event.send(event.plain_result("烤箱补货暂时无法发起，请稍后再试。"))
            return

        round_no = int(result.get("round", 0) or 0)
        required = int(result.get("required", 0) or 0)
        self._record_oven_event(
            group_id,
            EVENT_OVEN_REFILL_STARTED,
            actor_id=storage_actor,
            draw_date=draw_date,
            metadata={
                "supporters": 1,
                "required": required,
                "active_users": len(members),
                "round": round_no,
            },
            event_id=f"oven-refill-start:{draw_date}:{group_id}:{round_no}",
        )
        await event.send(
            event.plain_result(
                "🔥 猪圈能源危机！烤箱补货已发起。\n"
                f"今日活跃：{len(members)} 人 · 需要支持：{required} 人\n"
                "发起者已自动添煤 1 份；发送 /添煤 继续支援。"
            )
        )

    async def oven_refill_support(self, event) -> None:
        self._claim_command_event(event)
        if not self.enable_oven_refill:
            await event.send(event.plain_result("烤箱补货当前未启用。"))
            return
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("添煤只能在群聊中使用。"))
            return
        draw_date = self._today().isoformat()
        members = self._oven_active_group_members(group_id, draw_date)
        if not self._oven_actor_is_active(actor_id, members):
            await event.send(event.plain_result("只有今天在本群参与过 RollPig 的群友才能添煤。"))
            return
        storage_actor = self._storage_user_key(actor_id)
        storage_members = self._oven_storage_members(members)
        now = time.time()
        if getattr(self.storage, "supports_domain_writes", False):
            result = await __import__("asyncio").to_thread(
                self.storage.support_oven_refill,
                draw_date=draw_date,
                group_id=group_id,
                actor_id=storage_actor,
                active_actor_ids=storage_members,
                now=now,
                max_charges=self.group_roast_max_charges,
                recovery_seconds=self.group_roast_cooldown_seconds,
            )
        else:
            result = self._json_support_refill(
                draw_date=draw_date,
                group_id=group_id,
                actor_id=storage_actor,
                active_members=storage_members,
                now=now,
            )

        state = str(result.get("state") or "")
        if state == "inactive":
            await event.send(event.plain_result("当前没有进行中的补货；先发送 /烤箱补货 发起。"))
            return
        if state == "duplicate":
            await event.send(event.plain_result("🪵 你已经给这轮补货添过煤了。"))
            return

        supporters = [str(item) for item in result.get("supporters", []) if str(item)]
        required = int(result.get("required", 0) or 0)
        round_no = int(result.get("round", 0) or 0)
        if state in {"supported", "succeeded", "failed"}:
            self._record_oven_event(
                group_id,
                EVENT_OVEN_REFILL_SUPPORTED,
                actor_id=storage_actor,
                draw_date=draw_date,
                metadata={
                    "supporters": len(supporters),
                    "required": required,
                    "round": round_no,
                },
                event_id=(
                    f"oven-refill-support:{draw_date}:{group_id}:"
                    f"{round_no}:{storage_actor}"
                ),
            )
        if state == "supported":
            await event.send(
                event.plain_result(
                    f"🪵 添煤成功！当前进度 {len(supporters)}/{required}。"
                )
            )
            return
        if state == "failed":
            self._record_oven_event(
                group_id,
                EVENT_OVEN_REFILL_FAILED,
                actor_id=storage_actor,
                draw_date=draw_date,
                metadata={
                    "reason": "no_missing_charges",
                    "supporters": len(supporters),
                    "required": required,
                    "active_users": int(result.get("active_users", 0) or 0),
                    "round": round_no,
                },
                event_id=f"oven-refill-failed:{draw_date}:{group_id}:{round_no}",
            )
            await event.send(
                event.plain_result(
                    "🧯 添煤刚好达标，但大家的烤箱能量已经自行恢复满了；本轮作废，不计入今日补货次数。"
                )
            )
            return
        if state != "succeeded":
            await event.send(event.plain_result("添煤状态异常，请稍后再试。"))
            return

        restored = int(result.get("restored_users", 0) or 0)
        active_users = int(result.get("active_users", len(storage_members)) or 0)
        self._record_oven_event(
            group_id,
            EVENT_OVEN_REFILL_SUCCEEDED,
            actor_id=storage_actor,
            draw_date=draw_date,
            metadata={
                "supporters": len(supporters),
                "required": required,
                "active_users": active_users,
                "restored_users": restored,
                "round": round_no,
            },
            event_id=f"oven-refill-success:{draw_date}:{group_id}:{round_no}",
        )
        await event.send(
            event.plain_result(
                "⛽ 烤箱补货成功！"
                f"本群今日活跃玩家统一恢复 +1 格能量（实际恢复 {restored} 人）。"
            )
        )
