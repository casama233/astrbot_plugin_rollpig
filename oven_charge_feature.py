from __future__ import annotations

import datetime
import json
import time
from typing import Any

from astrbot.api import logger

try:
    from .gameplay_events import (
        EVENT_OVEN_REFILL_STARTED,
        EVENT_OVEN_REFILL_SUPPORTED,
        EVENT_OVEN_REFILL_SUCCEEDED,
    )
    from .services import OvenChargeService
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_events import (
        EVENT_OVEN_REFILL_STARTED,
        EVENT_OVEN_REFILL_SUPPORTED,
        EVENT_OVEN_REFILL_SUCCEEDED,
    )
    from services import OvenChargeService


class OvenChargeMixin:
    """User×group roast charges plus cooperative group refills.

    The old cooldown document remains untouched as a rollback/migration source.
    New charge/refill state lives in a focused feature document and uses the
    plugin's canonical identity helpers before persisting user keys.
    """

    OVEN_STATE_VERSION = 1
    OVEN_STATE_KEEP_DAYS = 3

    def __init__(self, context, config):
        super().__init__(context, config)
        self._init_oven_charge_feature()

    def _init_oven_charge_feature(self) -> None:
        config = self.config if hasattr(self.config, "get") else {}
        try:
            maximum = int(config.get("group_roast_max_charges", 2))
        except (TypeError, ValueError):
            maximum = 2
        self.group_roast_max_charges = min(5, max(1, maximum))

        try:
            recovery_hours = float(
                config.get(
                    "group_roast_charge_recovery_hours",
                    config.get("group_roast_cooldown_hours", 8),
                )
            )
        except (TypeError, ValueError):
            recovery_hours = 8
        self.group_roast_charge_recovery_seconds = int(
            min(72.0, max(1.0, recovery_hours)) * 3600
        )

        try:
            refill_limit = int(config.get("oven_refill_daily_limit", 2))
        except (TypeError, ValueError):
            refill_limit = 2
        self.oven_refill_daily_limit = min(5, max(1, refill_limit))

        self.oven_charge_service = OvenChargeService()
        self.oven_state_path = self.plugin_data_dir / "oven_state.json"
        default = {"version": self.OVEN_STATE_VERSION, "charges": {}, "refills": {}}
        try:
            loaded = self.load_json(self.oven_state_path, default)
        except Exception as exc:
            logger.warning(f"烤箱充能状态读取失败，已使用空状态：{exc}")
            loaded = default
        self.oven_state = loaded if isinstance(loaded, dict) else default
        self.oven_state["version"] = self.OVEN_STATE_VERSION
        self.oven_state.setdefault("charges", {})
        self.oven_state.setdefault("refills", {})
        with self._data_lock:
            if self._prune_oven_state_locked():
                self._save_oven_state_locked()

    @staticmethod
    def _oven_charge_key(group_id: str, actor_id: str) -> str:
        return json.dumps(
            [str(group_id), str(actor_id)],
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _save_oven_state_locked(self) -> None:
        self.save_json(self.oven_state_path, self.oven_state)

    def _prune_oven_state_locked(self) -> bool:
        refills = self.oven_state.setdefault("refills", {})
        if not isinstance(refills, dict):
            self.oven_state["refills"] = {}
            return True
        cutoff = (
            self._today() - datetime.timedelta(days=self.OVEN_STATE_KEEP_DAYS)
        ).isoformat()
        changed = False
        for date_key in list(refills):
            if str(date_key) < cutoff:
                refills.pop(date_key, None)
                changed = True
        return changed

    def _legacy_cooldown_at(self, group_id: str, storage_actor: str) -> float:
        cooldowns = getattr(self, "roast_state", {}).get("cooldowns", {})
        if not isinstance(cooldowns, dict):
            return 0.0
        try:
            return float(cooldowns.get(f"{group_id}:{storage_actor}", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _initial_oven_entry(
        self, group_id: str, storage_actor: str, now: float
    ) -> dict[str, float | int]:
        previous = self._legacy_cooldown_at(group_id, storage_actor)
        # A still-active v3.6.4 cooldown represents one already-spent roast. On
        # migration, preserve that cost but grant the second cell of the new 2/2
        # model instead of locking the player out completely.
        if previous > 0 and previous + self.group_roast_charge_recovery_seconds > now:
            return {
                "charges": max(0, self.group_roast_max_charges - 1),
                "anchor_at": previous,
            }
        return {"charges": self.group_roast_max_charges, "anchor_at": now}

    def _oven_entry_locked(
        self, group_id: str, storage_actor: str, now: float
    ) -> tuple[str, dict[str, Any]]:
        charges = self.oven_state.setdefault("charges", {})
        if not isinstance(charges, dict):
            charges = {}
            self.oven_state["charges"] = charges
        key = self._oven_charge_key(group_id, storage_actor)
        entry = charges.get(key)
        if not isinstance(entry, dict):
            entry = self._initial_oven_entry(group_id, storage_actor, now)
        return key, entry

    async def _consume_group_roast_cooldown(
        self, group_id: str, actor_id: str
    ) -> int:
        """Compatibility hook: spend one oven charge, or return recovery seconds."""
        storage_actor = self._storage_user_key(str(actor_id))
        now = time.time()
        with self._data_lock:
            key, entry = self._oven_entry_locked(str(group_id), storage_actor, now)
            result = self.oven_charge_service.consume(
                entry,
                now=now,
                max_charges=self.group_roast_max_charges,
                recovery_seconds=self.group_roast_charge_recovery_seconds,
            )
            self.oven_state.setdefault("charges", {})[key] = result["entry"]
            self._save_oven_state_locked()
        return int(result.get("remaining", 0) or 0)

    def _oven_charge_status(self, group_id: str, actor_id: str) -> dict[str, Any]:
        storage_actor = self._storage_user_key(str(actor_id))
        now = time.time()
        with self._data_lock:
            key, entry = self._oven_entry_locked(str(group_id), storage_actor, now)
            status = self.oven_charge_service.status(
                entry,
                now=now,
                max_charges=self.group_roast_max_charges,
                recovery_seconds=self.group_roast_charge_recovery_seconds,
            )
            self.oven_state.setdefault("charges", {})[key] = status["entry"]
            self._save_oven_state_locked()
        return status

    def _group_roast_unavailable_message(self, remaining: int) -> str:
        return (
            "🔥 烤箱能量已耗尽；下一格将在 "
            f"{self._format_cooldown(int(remaining))} 后恢复。"
        )

    def _active_group_members(self, group_id: str, draw_date: str) -> list[str]:
        values = self._daily_group_members(str(group_id), str(draw_date))
        return list(dict.fromkeys(str(item) for item in values if str(item)))

    def _actor_is_active_member(self, actor_id: str, members: list[str]) -> bool:
        safe = set(self._user_read_candidates(str(actor_id)))
        safe.add(self._storage_user_key(str(actor_id)))
        return bool(safe.intersection(str(item) for item in members))

    def _refill_bucket_locked(self, draw_date: str, group_id: str) -> dict[str, Any]:
        refills = self.oven_state.setdefault("refills", {})
        by_date = refills.setdefault(str(draw_date), {})
        if not isinstance(by_date, dict):
            by_date = {}
            refills[str(draw_date)] = by_date
        row = by_date.setdefault(
            str(group_id),
            {"successes": 0, "active": False, "supporters": []},
        )
        if not isinstance(row, dict):
            row = {"successes": 0, "active": False, "supporters": []}
            by_date[str(group_id)] = row
        return row

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

    async def oven_refill(self, event) -> None:
        self._claim_command_event(event)
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("烤箱补货只能在群聊中发起。"))
            return
        draw_date = self._today().isoformat()
        members = self._active_group_members(group_id, draw_date)
        if not self._actor_is_active_member(actor_id, members):
            await event.send(event.plain_result("先在本群抽一只今日小猪，再来组织烤箱补货。"))
            return
        if len(members) < 2:
            await event.send(event.plain_result("今天本群至少需要 2 位活跃玩家才能组织补货。"))
            return

        storage_actor = self._storage_user_key(actor_id)
        with self._data_lock:
            self._prune_oven_state_locked()
            row = self._refill_bucket_locked(draw_date, group_id)
            successes = int(row.get("successes", 0) or 0)
            if successes >= self.oven_refill_daily_limit:
                active = False
                required = 0
                supporters: list[str] = []
            elif bool(row.get("active")):
                active = True
                required = int(row.get("required", 0) or 0)
                supporters = [str(x) for x in row.get("supporters", []) if str(x)]
            else:
                active = False
                required = self.oven_charge_service.refill_requirement(
                    len(members), successes
                )
                supporters = [storage_actor]
                row.update(
                    {
                        "active": True,
                        "supporters": supporters,
                        "required": required,
                        "active_count": len(members),
                        "started_by": storage_actor,
                        "started_at": int(time.time()),
                    }
                )
                self._save_oven_state_locked()

        if successes >= self.oven_refill_daily_limit:
            await event.send(event.plain_result("🔥 本群今天的烤箱补货次数已经用完了。"))
            return
        if active:
            await event.send(
                event.plain_result(
                    f"🪵 补货进行中：{len(supporters)}/{required} 人已添煤；发送 /添煤 支持。"
                )
            )
            return

        self._record_oven_event(
            group_id,
            EVENT_OVEN_REFILL_STARTED,
            actor_id=storage_actor,
            draw_date=draw_date,
            metadata={
                "supporters": 1,
                "required": required,
                "active_users": len(members),
                "round": successes + 1,
            },
            event_id=f"oven-refill-start:{draw_date}:{group_id}:{successes + 1}",
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
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("添煤只能在群聊中使用。"))
            return
        draw_date = self._today().isoformat()
        members = self._active_group_members(group_id, draw_date)
        if not self._actor_is_active_member(actor_id, members):
            await event.send(event.plain_result("只有今天在本群参与过 RollPig 的群友才能添煤。"))
            return
        storage_actor = self._storage_user_key(actor_id)

        with self._data_lock:
            row = self._refill_bucket_locked(draw_date, group_id)
            if not bool(row.get("active")):
                state = "inactive"
                supporters: list[str] = []
                required = 0
                successes = int(row.get("successes", 0) or 0)
            else:
                supporters = [str(x) for x in row.get("supporters", []) if str(x)]
                required = int(row.get("required", 0) or 0)
                successes = int(row.get("successes", 0) or 0)
                if storage_actor in supporters:
                    state = "duplicate"
                else:
                    supporters.append(storage_actor)
                    row["supporters"] = supporters
                    state = "success" if len(supporters) >= required else "supported"
                    if state == "success":
                        row["active"] = False
                        row["successes"] = successes + 1
                        row["completed_at"] = int(time.time())
                    self._save_oven_state_locked()

        if state == "inactive":
            await event.send(event.plain_result("当前没有进行中的补货；先发送 /烤箱补货 发起。"))
            return
        if state == "duplicate":
            await event.send(event.plain_result("🪵 你已经给这轮补货添过煤了。"))
            return

        self._record_oven_event(
            group_id,
            EVENT_OVEN_REFILL_SUPPORTED,
            actor_id=storage_actor,
            draw_date=draw_date,
            metadata={
                "supporters": len(supporters),
                "required": required,
                "round": successes + 1,
            },
            event_id=(
                f"oven-refill-support:{draw_date}:{group_id}:"
                f"{successes + 1}:{storage_actor}"
            ),
        )
        if state != "success":
            await event.send(
                event.plain_result(
                    f"🪵 添煤成功！当前进度 {len(supporters)}/{required}。"
                )
            )
            return

        now = time.time()
        recipients = self._active_group_members(group_id, draw_date)
        restored = 0
        with self._data_lock:
            charges = self.oven_state.setdefault("charges", {})
            for member in recipients:
                storage_member = self._storage_user_key(member)
                key, entry = self._oven_entry_locked(group_id, storage_member, now)
                before = self.oven_charge_service.status(
                    entry,
                    now=now,
                    max_charges=self.group_roast_max_charges,
                    recovery_seconds=self.group_roast_charge_recovery_seconds,
                )
                updated = self.oven_charge_service.add_one(
                    entry,
                    now=now,
                    max_charges=self.group_roast_max_charges,
                    recovery_seconds=self.group_roast_charge_recovery_seconds,
                )
                charges[key] = updated
                if int(updated["charges"]) > int(before["charges"]):
                    restored += 1
            self._save_oven_state_locked()

        self._record_oven_event(
            group_id,
            EVENT_OVEN_REFILL_SUCCEEDED,
            actor_id=storage_actor,
            draw_date=draw_date,
            metadata={
                "supporters": len(supporters),
                "required": required,
                "active_users": len(recipients),
                "restored_users": restored,
                "round": successes + 1,
            },
            event_id=f"oven-refill-success:{draw_date}:{group_id}:{successes + 1}",
        )
        await event.send(
            event.plain_result(
                "⛽ 烤箱补货成功！"
                f"本群今日活跃玩家统一恢复 +1 格能量（实际恢复 {restored} 人）。"
            )
        )
