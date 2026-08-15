from __future__ import annotations

import asyncio
import datetime
import time
from typing import Any

from astrbot.api import logger

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
    """Cooperative group refill orchestration over the Phase 3A charge contract.

    Refill campaign metadata intentionally lives in a small auxiliary JSON file.
    Charge ownership remains in the existing JSON/SQLite charge authority.
    """

    OVEN_REFILL_STATE_VERSION = 1
    OVEN_REFILL_KEEP_DAYS = 3

    def __init__(self, context, config):
        super().__init__(context, config)
        self._init_oven_refill_feature()

    @staticmethod
    def _oven_refill_bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return bool(default)
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return bool(default)

    def _init_oven_refill_feature(self) -> None:
        config = self.config if hasattr(self.config, "get") else {}
        self.enable_oven_refill = self._oven_refill_bool(
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
            maximum = int(config.get("oven_refill_max_base_supporters", 8))
        except (TypeError, ValueError):
            maximum = 8
        self.oven_refill_max_base_supporters = min(
            50, max(self.oven_refill_min_supporters, maximum)
        )
        try:
            extra = int(config.get("oven_refill_extra_supporters_per_success", 2))
        except (TypeError, ValueError):
            extra = 2
        self.oven_refill_extra_supporters_per_success = min(10, max(0, extra))
        self.oven_refill_service = OvenRefillService()

        self.oven_refill_state_path = self.plugin_data_dir / "oven_refill_state.json"
        default = {"version": self.OVEN_REFILL_STATE_VERSION, "dates": {}}
        try:
            loaded = self.load_json(self.oven_refill_state_path, default)
        except Exception as exc:
            logger.warning(f"烤箱补货状态读取失败，已使用空状态：{exc}")
            loaded = default
        self.oven_refill_state = loaded if isinstance(loaded, dict) else default
        self.oven_refill_state["version"] = self.OVEN_REFILL_STATE_VERSION
        self.oven_refill_state.setdefault("dates", {})
        with self._data_lock:
            changed = self._recover_interrupted_refills_locked()
            changed = self._prune_oven_refills_locked() or changed
            if changed:
                self._save_oven_refill_state_locked()

    def _save_oven_refill_state_locked(self) -> None:
        self.save_json(self.oven_refill_state_path, self.oven_refill_state)

    def _recover_interrupted_refills_locked(self) -> bool:
        """Turn crash-interrupted completion markers into restartable rounds."""
        dates = self.oven_refill_state.get("dates", {})
        if not isinstance(dates, dict):
            self.oven_refill_state["dates"] = {}
            return True
        changed = False
        for groups in dates.values():
            if not isinstance(groups, dict):
                continue
            for row in groups.values():
                if isinstance(row, dict) and bool(row.get("completing")):
                    row["completing"] = False
                    row["active"] = False
                    row["failed_reason"] = "interrupted"
                    changed = True
        return changed

    def _prune_oven_refills_locked(self) -> bool:
        dates = self.oven_refill_state.setdefault("dates", {})
        if not isinstance(dates, dict):
            self.oven_refill_state["dates"] = {}
            return True
        cutoff = (
            self._today() - datetime.timedelta(days=self.OVEN_REFILL_KEEP_DAYS)
        ).isoformat()
        changed = False
        for date_key in list(dates):
            if str(date_key) < cutoff:
                dates.pop(date_key, None)
                changed = True
        return changed

    def _refill_bucket_locked(self, draw_date: str, group_id: str) -> dict[str, Any]:
        dates = self.oven_refill_state.setdefault("dates", {})
        by_date = dates.setdefault(str(draw_date), {})
        if not isinstance(by_date, dict):
            by_date = {}
            dates[str(draw_date)] = by_date
        row = by_date.setdefault(
            str(group_id),
            {
                "successes": 0,
                "round": 0,
                "active": False,
                "completing": False,
                "supporters": [],
            },
        )
        if not isinstance(row, dict):
            row = {
                "successes": 0,
                "round": 0,
                "active": False,
                "completing": False,
                "supporters": [],
            }
            by_date[str(group_id)] = row
        return row

    def _oven_active_group_members(self, group_id: str, draw_date: str) -> list[str]:
        values = self._daily_group_members(str(group_id), str(draw_date))
        return list(dict.fromkeys(str(item) for item in values if str(item)))

    def _oven_actor_is_active(self, actor_id: str, members: list[str]) -> bool:
        safe = set(self._user_read_candidates(str(actor_id)))
        safe.add(self._storage_user_key(str(actor_id)))
        return bool(safe.intersection(str(item) for item in members))

    def _oven_storage_members(self, members: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                self._storage_user_key(str(item)) for item in members if str(item)
            )
        )

    def _refill_requirement(self, active_count: int, successes: int) -> int:
        return self.oven_refill_service.refill_requirement(
            active_count,
            successes,
            ratio_percent=self.oven_refill_support_ratio_percent,
            minimum_supporters=self.oven_refill_min_supporters,
            maximum_base_supporters=self.oven_refill_max_base_supporters,
            extra_per_success=self.oven_refill_extra_supporters_per_success,
        )

    def _start_refill_round(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_count: int,
        now: float,
    ) -> dict[str, Any]:
        with self._data_lock:
            self._prune_oven_refills_locked()
            row = self._refill_bucket_locked(draw_date, group_id)
            successes = int(row.get("successes", 0) or 0)
            if successes >= self.oven_refill_daily_limit:
                return {"state": "limit", "successes": successes}
            if bool(row.get("completing")):
                return {"state": "busy"}
            if bool(row.get("active")):
                supporters = [
                    str(item) for item in row.get("supporters", []) if str(item)
                ]
                return {
                    "state": "active",
                    "successes": successes,
                    "round": int(row.get("round", 0) or 0),
                    "required": int(row.get("required", 0) or 0),
                    "supporters": supporters,
                }

            required = self._refill_requirement(active_count, successes)
            round_no = int(row.get("round", 0) or 0) + 1
            row.update(
                {
                    "active": True,
                    "completing": False,
                    "round": round_no,
                    "required": required,
                    "active_count": int(active_count),
                    "started_by": str(actor_id),
                    "started_at": float(now),
                    "supporters": [str(actor_id)],
                }
            )
            row.pop("failed_reason", None)
            self._save_oven_refill_state_locked()
            return {
                "state": "started",
                "successes": successes,
                "round": round_no,
                "required": required,
                "supporters": [str(actor_id)],
            }

    def _add_refill_support(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        now: float,
    ) -> dict[str, Any]:
        """Atomically reserve a supporter and, when due, the completion right."""
        with self._data_lock:
            row = self._refill_bucket_locked(draw_date, group_id)
            if bool(row.get("completing")):
                return {"state": "busy"}
            if not bool(row.get("active")):
                return {"state": "inactive"}
            supporters = [
                str(item) for item in row.get("supporters", []) if str(item)
            ]
            required = int(row.get("required", 0) or 0)
            round_no = int(row.get("round", 0) or 0)
            if actor_id in supporters:
                return {
                    "state": "duplicate",
                    "round": round_no,
                    "required": required,
                    "supporters": supporters,
                }
            supporters.append(str(actor_id))
            row["supporters"] = supporters
            if len(supporters) < required:
                self._save_oven_refill_state_locked()
                return {
                    "state": "supported",
                    "round": round_no,
                    "required": required,
                    "supporters": supporters,
                }

            # Exactly one caller owns completion. Expensive charge writes happen
            # after releasing _data_lock, avoiding cross-thread lock inversion.
            row["active"] = False
            row["completing"] = True
            row["completion_started_at"] = float(now)
            self._save_oven_refill_state_locked()
            return {
                "state": "complete",
                "round": round_no,
                "required": required,
                "supporters": supporters,
            }

    def _finish_refill_round(
        self,
        *,
        draw_date: str,
        group_id: str,
        round_no: int,
        restored_users: int,
        active_users: int,
        now: float,
    ) -> dict[str, Any]:
        with self._data_lock:
            row = self._refill_bucket_locked(draw_date, group_id)
            if int(row.get("round", 0) or 0) != int(round_no):
                return {"state": "stale"}
            row["active"] = False
            row["completing"] = False
            row["completed_at"] = float(now)
            row["restored_users"] = int(restored_users)
            row["active_users"] = int(active_users)
            if restored_users > 0:
                row["successes"] = int(row.get("successes", 0) or 0) + 1
                row.pop("failed_reason", None)
                state = "succeeded"
            else:
                row["failed_reason"] = "no_missing_charges"
                state = "failed"
            self._save_oven_refill_state_locked()
            return {"state": state, "successes": int(row.get("successes", 0) or 0)}

    async def _grant_one_oven_charge(
        self, group_id: str, storage_actor: str, now: float
    ) -> bool:
        if getattr(self.storage, "supports_domain_writes", False):
            result = await asyncio.to_thread(
                self.storage.grant_roast_charge,
                group_id=str(group_id),
                actor_id=str(storage_actor),
                now=float(now),
                max_charges=self.group_roast_max_charges,
                recovery_seconds=self.group_roast_cooldown_seconds,
            )
            roast = result.get("roast_state") if isinstance(result, dict) else None
            if isinstance(roast, dict):
                with self._data_lock:
                    self.roast_state = roast
            return bool(isinstance(result, dict) and result.get("increased"))

        with self._data_lock:
            charge_states = self.roast_state.setdefault("roast_charges", {})
            if not isinstance(charge_states, dict):
                charge_states = {}
                self.roast_state["roast_charges"] = charge_states
            cooldowns = self.roast_state.setdefault("cooldowns", {})
            key = f"{group_id}:{storage_actor}"
            entry = charge_states.get(key)
            if not isinstance(entry, dict):
                try:
                    legacy_last_used = float(cooldowns.get(key, 0) or 0)
                except (AttributeError, TypeError, ValueError):
                    legacy_last_used = 0.0
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
            self._save_roast_state()
            return bool(updated.get("increased"))

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
        if not self.enable_oven_refill:
            await event.send(event.plain_result("🔒 今天后厨不收煤。管理员把补货玩法关掉了，再塞也只会弄脏地板。"))
            return
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("🚪 煤车只进群聊。私聊里没有烤箱，也没有群友帮你搬煤。"))
            return
        draw_date = self._today().isoformat()
        members = self._oven_active_group_members(group_id, draw_date)
        if not self._oven_actor_is_active(actor_id, members):
            await event.send(event.plain_result("🐷 先在本群抽一只 /今日小猪 再来搬煤；后厨不收路过的临时工。"))
            return
        if len(members) < 2:
            await event.send(event.plain_result("🐷 一个人搬煤不叫补货，叫加班。今天本群至少要有 2 位养过猪的群友。"))
            return

        storage_actor = self._storage_user_key(actor_id)
        result = self._start_refill_round(
            draw_date=draw_date,
            group_id=group_id,
            actor_id=storage_actor,
            active_count=len(members),
            now=time.time(),
        )
        state = str(result.get("state") or "")
        if state == "limit":
            await event.send(event.plain_result("🔥 今天的煤车班次用完了。后厨宣布收工，剩下的火请靠时间自己长回来。"))
            return
        if state == "busy":
            await event.send(event.plain_result("⛽ 煤刚倒进去，后厨正在数铲子。等这轮结算完再敲门。"))
            return
        if state == "active":
            supporters = result.get("supporters", [])
            await event.send(
                event.plain_result(
                    f"🪵 煤车还没装满：{len(supporters)}/{int(result.get('required', 0) or 0)} 人已添煤。再叫群友 /添煤，别让主厨一个人扛。"
                )
            )
            return
        if state != "started":
            await event.send(event.plain_result("🧯 补货没发动起来。烤箱今天有点闹脾气，稍后再试。"))
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
                "🔥 猪圈能源危机，煤车发车！\n"
                f"今日活跃：{len(members)} 人 · 需要：{required} 人\n"
                "发起人已经先铲 1 份；其余群友输入 /添煤，别让煤车空着回去。"
            )
        )

    async def oven_refill_support(self, event) -> None:
        self._claim_command_event(event)
        if not self.enable_oven_refill:
            await event.send(event.plain_result("🔒 今天后厨不收煤。管理员把补货玩法关掉了，再塞也只会弄脏地板。"))
            return
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("🪵 煤只能往群里那口烤箱塞。私聊先把铲子放下。"))
            return
        draw_date = self._today().isoformat()
        members = self._oven_active_group_members(group_id, draw_date)
        if not self._oven_actor_is_active(actor_id, members):
            await event.send(event.plain_result("🪵 后厨认人：今天先在本群玩过 RollPig，才有资格往煤车里铲一份。"))
            return

        storage_actor = self._storage_user_key(actor_id)
        result = self._add_refill_support(
            draw_date=draw_date,
            group_id=group_id,
            actor_id=storage_actor,
            now=time.time(),
        )
        state = str(result.get("state") or "")
        if state == "inactive":
            await event.send(event.plain_result("🪵 现在没有煤车在等人。先 /烤箱补货 发车，再回来添煤。"))
            return
        if state == "busy":
            await event.send(event.plain_result("⛽ 煤刚倒进去，后厨正在数铲子。等这轮结算完再敲门。"))
            return
        if state == "duplicate":
            await event.send(event.plain_result("🪵 你这铲煤已经算过了。再铲不加进度，只会让后厨怀疑你想把烤箱埋了。"))
            return

        supporters = [str(item) for item in result.get("supporters", []) if str(item)]
        required = int(result.get("required", 0) or 0)
        round_no = int(result.get("round", 0) or 0)
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
                f"oven-refill-support:{draw_date}:{group_id}:{round_no}:{storage_actor}"
            ),
        )
        if state == "supported":
            await event.send(
                event.plain_result(
                    f"🪵 这铲算数！煤车进度 {len(supporters)}/{required}。"
                )
            )
            return
        if state != "complete":
            await event.send(event.plain_result("🧯 这铲煤没记进账。补货状态异常，稍后再试。"))
            return

        storage_members = self._oven_storage_members(members)
        restored = 0
        completed_at = time.time()
        for storage_member in storage_members:
            if await self._grant_one_oven_charge(
                group_id, storage_member, completed_at
            ):
                restored += 1
        finish = self._finish_refill_round(
            draw_date=draw_date,
            group_id=group_id,
            round_no=round_no,
            restored_users=restored,
            active_users=len(storage_members),
            now=time.time(),
        )
        if finish.get("state") == "failed":
            self._record_oven_event(
                group_id,
                EVENT_OVEN_REFILL_FAILED,
                actor_id=storage_actor,
                draw_date=draw_date,
                metadata={
                    "reason": "no_missing_charges",
                    "supporters": len(supporters),
                    "required": required,
                    "active_users": len(storage_members),
                    "round": round_no,
                },
                event_id=f"oven-refill-failed:{draw_date}:{group_id}:{round_no}",
            )
            await event.send(
                event.plain_result(
                    "🧯 人凑齐了，结果烤箱自己先充满了。这轮煤白搬，但不扣今日补货次数——至少地板更黑了。"
                )
            )
            return
        if finish.get("state") != "succeeded":
            await event.send(event.plain_result("🧯 煤车到站后账本对不上。补货结算状态异常，稍后再试。"))
            return

        self._record_oven_event(
            group_id,
            EVENT_OVEN_REFILL_SUCCEEDED,
            actor_id=storage_actor,
            draw_date=draw_date,
            metadata={
                "supporters": len(supporters),
                "required": required,
                "active_users": len(storage_members),
                "restored_users": restored,
                "round": round_no,
            },
            event_id=f"oven-refill-success:{draw_date}:{group_id}:{round_no}",
        )
        await event.send(
            event.plain_result(
                "⛽ 煤车到站，后厨重新通电！"
                f"本群今天有 {restored} 位活跃群友各捡回 1 格 Charge。烤箱又可以干坏事了。"
            )
        )
