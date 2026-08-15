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
    OVEN_REFILL_DEFAULT_TIMEOUT_MINUTES = 120

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
        try:
            timeout_minutes = int(
                config.get(
                    "oven_refill_round_timeout_minutes",
                    self.OVEN_REFILL_DEFAULT_TIMEOUT_MINUTES,
                )
            )
        except (TypeError, ValueError):
            timeout_minutes = self.OVEN_REFILL_DEFAULT_TIMEOUT_MINUTES
        self.oven_refill_round_timeout_minutes = min(720, max(5, timeout_minutes))
        self.oven_refill_round_timeout_seconds = (
            self.oven_refill_round_timeout_minutes * 60
        )
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

    @staticmethod
    def _safe_nonnegative_int(value: Any, default: int = 0) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return max(0, int(default))

    def _recover_interrupted_refills_locked(self) -> bool:
        """Fail closed when a process died after completion had already started.

        Charge grants are durable domain writes while campaign metadata is a small
        sidecar document. After a hard process crash there is no safe way to prove
        which member grant was the final committed one. Replaying the round could
        therefore grant a second charge. Once settlement has started we consume one
        daily success slot on recovery and close the round instead of replaying it.
        """

        dates = self.oven_refill_state.get("dates", {})
        if not isinstance(dates, dict):
            self.oven_refill_state["dates"] = {}
            return True
        changed = False
        recovered_at = time.time()
        for groups in dates.values():
            if not isinstance(groups, dict):
                continue
            for row in groups.values():
                if not isinstance(row, dict) or not bool(row.get("completing")):
                    continue
                successes = self._safe_nonnegative_int(row.get("successes"))
                row["successes"] = min(
                    self.oven_refill_daily_limit, successes + 1
                )
                row["completing"] = False
                row["active"] = False
                row["settlement_state"] = "interrupted"
                row["failed_reason"] = "interrupted_counted"
                row["completed_at"] = recovered_at
                changed = True
                logger.warning(
                    "检测到烤箱补货在结算阶段异常中断；已封账并计入一次补货，避免重复发放能量"
                )
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

    def _oven_refill_available(self) -> bool:
        return bool(
            self.enable_oven_refill
            and getattr(self, "enable_roast", False)
            and getattr(self, "enable_group_roast", False)
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

    def _expire_refill_round_locked(self, row: dict[str, Any], now: float) -> bool:
        if not bool(row.get("active")):
            return False
        try:
            started_at = float(row.get("started_at", 0) or 0)
        except (TypeError, ValueError):
            started_at = 0.0
        now_value = float(now)
        expired = started_at <= 0 or (
            now_value >= started_at
            and now_value - started_at >= self.oven_refill_round_timeout_seconds
        )
        if not expired:
            return False
        row["active"] = False
        row["completing"] = False
        row["expired_at"] = now_value
        row["settlement_state"] = "expired"
        row["failed_reason"] = "expired"
        return True

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
            successes = self._safe_nonnegative_int(row.get("successes"))
            if successes >= self.oven_refill_daily_limit:
                return {"state": "limit", "successes": successes}
            if bool(row.get("completing")):
                return {"state": "busy"}
            if self._expire_refill_round_locked(row, now):
                self._save_oven_refill_state_locked()
            if bool(row.get("active")):
                supporters = [
                    str(item) for item in row.get("supporters", []) if str(item)
                ]
                return {
                    "state": "active",
                    "successes": successes,
                    "round": self._safe_nonnegative_int(row.get("round")),
                    "required": self._safe_nonnegative_int(row.get("required")),
                    "supporters": supporters,
                }

            required = self._refill_requirement(active_count, successes)
            round_no = self._safe_nonnegative_int(row.get("round")) + 1
            row.update(
                {
                    "active": True,
                    "completing": False,
                    "round": round_no,
                    "required": required,
                    "active_count": int(active_count),
                    "started_by": str(actor_id),
                    "started_at": float(now),
                    "settlement_state": "collecting",
                    "supporters": [str(actor_id)],
                }
            )
            for key in (
                "failed_reason",
                "settlement_error",
                "expired_at",
                "completed_at",
                "completion_started_at",
                "restored_users",
                "active_users",
            ):
                row.pop(key, None)
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
            if self._expire_refill_round_locked(row, now):
                self._save_oven_refill_state_locked()
                return {"state": "expired"}
            if not bool(row.get("active")):
                return {"state": "inactive"}
            supporters = [
                str(item) for item in row.get("supporters", []) if str(item)
            ]
            required = self._safe_nonnegative_int(row.get("required"))
            round_no = self._safe_nonnegative_int(row.get("round"))
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
            row["settlement_state"] = "settling"
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
        settlement_error: str = "",
    ) -> dict[str, Any]:
        with self._data_lock:
            row = self._refill_bucket_locked(draw_date, group_id)
            if self._safe_nonnegative_int(row.get("round")) != int(round_no):
                return {"state": "stale"}
            row["active"] = False
            row["completing"] = False
            row["completed_at"] = float(now)
            row["restored_users"] = int(restored_users)
            row["active_users"] = int(active_users)
            successes = self._safe_nonnegative_int(row.get("successes"))
            if settlement_error:
                # A storage error after settlement started may be ambiguous: some
                # grants can already be durable. Fail closed and consume the round
                # so a retry cannot grant the same members a second charge.
                row["successes"] = min(
                    self.oven_refill_daily_limit, successes + 1
                )
                row["settlement_state"] = "degraded"
                row["failed_reason"] = "grant_error"
                row["settlement_error"] = str(settlement_error)[:300]
                state = "degraded"
            elif restored_users > 0:
                row["successes"] = min(
                    self.oven_refill_daily_limit, successes + 1
                )
                row["settlement_state"] = "succeeded"
                row.pop("failed_reason", None)
                row.pop("settlement_error", None)
                state = "succeeded"
            else:
                row["settlement_state"] = "failed"
                row["failed_reason"] = "no_missing_charges"
                row.pop("settlement_error", None)
                state = "failed"
            self._save_oven_refill_state_locked()
            return {
                "state": state,
                "successes": self._safe_nonnegative_int(row.get("successes")),
            }

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
            await event.send(event.plain_result("🔒 今天后厨不收柴。管理员把补货玩法关掉了，再塞也只会弄脏地板。"))
            return
        if not self._oven_refill_available():
            await event.send(
                event.plain_result("🔒 烤群友这桌已经关火，补货也跟着歇业。先让管理员把后厨主开关打开。")
            )
            return
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("🚪 柴车只进群聊。私聊里没有烤箱，也没有群友帮你扛木头。"))
            return
        draw_date = self._today().isoformat()
        members = self._oven_active_group_members(group_id, draw_date)
        if not self._oven_actor_is_active(actor_id, members):
            await event.send(event.plain_result("🐷 先在本群抽一只 /今日小猪 再来搬柴；后厨不收路过的临时工。"))
            return
        if len(members) < 2:
            await event.send(event.plain_result("🐷 一个人搬柴不叫补货，叫加班。今天本群至少要有 2 位养过猪的群友。"))
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
            await event.send(event.plain_result("🔥 今天的柴车班次用完了。后厨宣布收工，剩下的火请靠时间自己长回来。"))
            return
        if state == "busy":
            await event.send(event.plain_result("⛽ 柴刚塞进去，后厨正在数木头。等这轮结算完再敲门。"))
            return
        if state == "active":
            supporters = result.get("supporters", [])
            await event.send(
                event.plain_result(
                    f"🪵 柴堆还没满：{len(supporters)}/{int(result.get('required', 0) or 0)} 人已添柴；继续 /添柴，别让主厨一个人扛。"
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
                "🔥 猪圈能源危机，柴车发车！\n"
                f"今日活跃：{len(members)} 人 · 需要：{required} 人\n"
                "发起人已经先塞 1 把；其余群友输入 /添柴，别让柴车空着回去。"
            )
        )

    async def oven_refill_support(self, event) -> None:
        self._claim_command_event(event)
        if not self.enable_oven_refill:
            await event.send(event.plain_result("烤箱补货当前未启用。"))
            return
        if not self._oven_refill_available():
            await event.send(
                event.plain_result("烤群友玩法当前未启用，烤箱补货不可用。")
            )
            return
        group_id = str(self._event_group_id(event) or "")
        actor_id = str(self._event_sender_id(event) or "")
        if not group_id:
            await event.send(event.plain_result("🪵 柴只能往群里那口烤箱塞。私聊先把木头放下。"))
            return
        draw_date = self._today().isoformat()
        members = self._oven_active_group_members(group_id, draw_date)
        if not self._oven_actor_is_active(actor_id, members):
            await event.send(event.plain_result("🪵 后厨认人：今天先在本群玩过 RollPig，才有资格往柴堆里塞一把。"))
            return

        storage_actor = self._storage_user_key(actor_id)
        result = self._add_refill_support(
            draw_date=draw_date,
            group_id=group_id,
            actor_id=storage_actor,
            now=time.time(),
        )
        state = str(result.get("state") or "")
        if state == "expired":
            await event.send(
                event.plain_result(
                    "⌛ 上一轮柴火等到凉了，已经超时收摊。重新 /烤箱补货 发一车。"
                )
            )
            return
        if state == "inactive":
            await event.send(event.plain_result("🪵 现在没有柴车在等人。先 /烤箱补货 发车，再回来添柴。"))
            return
        if state == "busy":
            await event.send(event.plain_result("⛽ 本轮补货正在结算，请稍后再试。"))
            return
        if state == "duplicate":
            await event.send(event.plain_result("🪵 你这把柴已经算过了。再塞不加进度，只会让后厨怀疑你想把烤箱埋了。"))
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
                    f"🪵 这把算数！柴堆进度 {len(supporters)}/{required}。"
                )
            )
            return
        if state != "complete":
            await event.send(event.plain_result("🧯 这把柴没记进账。补货状态异常，稍后再试。"))
            return

        storage_members = self._oven_storage_members(members)
        restored = 0
        completed_at = time.time()
        settlement_error = ""
        for storage_member in storage_members:
            try:
                if await self._grant_one_oven_charge(
                    group_id, storage_member, completed_at
                ):
                    restored += 1
            except Exception as exc:
                settlement_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "烤箱补货能量发放异常，停止本轮剩余写入并封账："
                    f"group={group_id} round={round_no} member={storage_member} error={exc}"
                )
                break

        finish = self._finish_refill_round(
            draw_date=draw_date,
            group_id=group_id,
            round_no=round_no,
            restored_users=restored,
            active_users=len(storage_members),
            now=time.time(),
            settlement_error=settlement_error,
        )
        if finish.get("state") == "degraded":
            self._record_oven_event(
                group_id,
                EVENT_OVEN_REFILL_FAILED,
                actor_id=storage_actor,
                draw_date=draw_date,
                metadata={
                    "reason": "grant_error",
                    "supporters": len(supporters),
                    "required": required,
                    "active_users": len(storage_members),
                    "restored_users": restored,
                    "round": round_no,
                },
                event_id=f"oven-refill-failed:{draw_date}:{group_id}:{round_no}",
            )
            await event.send(
                event.plain_result(
                    "⚠️ 补货结算遇到存储异常；"
                    f"已确认恢复 {restored} 人。后厨为防重复发火已把本轮封账，并计入今日补货次数。"
                )
            )
            return
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
                    "🧯 人凑齐了，结果烤箱自己先充满了。这轮柴白搬，但不扣今日补货次数——至少地板上多了一堆木屑。"
                )
            )
            return
        if finish.get("state") != "succeeded":
            await event.send(event.plain_result("🧯 柴车到站后账本对不上。补货结算状态异常，请稍后再试。"))
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
                "⛽ 柴车到站，后厨重新通电！"
                f"本群今天有 {restored} 位活跃群友各捡回 1 格 Charge。烤箱又可以干坏事了。"
            )
        )
