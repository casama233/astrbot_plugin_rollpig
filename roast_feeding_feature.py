from __future__ import annotations

import datetime
import hashlib
from copy import deepcopy

from astrbot.api import logger

try:
    from .gameplay_copy import GAMEPLAY_COPY
    from .rollpig_core import parse_config_bool
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_copy import GAMEPLAY_COPY
    from rollpig_core import parse_config_bool


class RoastFeedingMixin:
    """Trade the group's daily self-roast card for a one-day pig mutation."""

    _FEEDING_KINDS = ("spicy", "rich")
    _FEEDING_COMMANDS = {
        "投喂": False,
        "投餵": False,
        "明天投喂": True,
        "明天投餵": True,
    }

    def __init__(self, context, config):
        super().__init__(context, config)
        self._init_roast_feeding()

    def _init_roast_feeding(self) -> None:
        self.enable_roast_feeding = parse_config_bool(
            self.config.get("enable_roast_feeding", False), False
        )
        self._roast_feeding_path = self.plugin_data_dir / "roast_feeding.json"
        self._roast_feeding_state = {"version": 1, "days": {}}
        if self.enable_roast_feeding and self._roast_feeding_path.exists():
            try:
                state = self.load_json(
                    self._roast_feeding_path, self._roast_feeding_state
                )
                if not (
                    isinstance(state, dict)
                    and state.get("version") == 1
                    and isinstance(state.get("days"), dict)
                ):
                    raise ValueError("malformed feeding state")
                self._roast_feeding_state = state
            except (OSError, ValueError) as exc:
                logger.warning(f"料理卡投喂读取失败：{exc}")
                self.enable_roast_feeding = False

    @staticmethod
    def _feeding_copy(key: str, **values: object) -> str:
        return GAMEPLAY_COPY[key].format(**values)

    def _feeding_enabled(self) -> bool:
        return getattr(self, "enable_roast_feeding", False) and self.enable_roast

    @staticmethod
    def _feeding_group(state: dict, day: str, group: str) -> dict:
        return state["days"].setdefault(day, {}).setdefault(
            group, {"cards": {}, "effects": {}}
        )

    def _save_feeding_change(self, state: dict, day: str) -> None:
        # The same write consumes the card and sets the target's mutation.
        state["days"] = {key: value for key, value in state["days"].items() if key >= day}
        self.save_json(self._roast_feeding_path, state)
        self._roast_feeding_state = state

    def _feeding_effect(
        self, group_id: str, user_id: str, day: datetime.date | str
    ) -> str:
        if not group_id or not user_id or not self._feeding_enabled():
            return ""
        key = day.isoformat() if isinstance(day, datetime.date) else day
        with self._data_lock:
            bucket = self._roast_feeding_state["days"].get(key, {}).get(group_id, {})
            effects = bucket.get("effects", {})
            if not effects:
                return ""
            effect = effects.get(self._storage_user_key(user_id), "")
        return effect if effect in self._FEEDING_KINDS else ""

    async def _offer_self_roast_feed(
        self, event, pig: dict, *, day: datetime.date | None = None
    ) -> None:
        """Give the sender a transferable dish after a successful self-roast render."""
        if not self._feeding_enabled():
            return
        day = day or self._today()
        group = self._event_group_id(event)
        if not group or day != self._today():
            return
        owner = self._storage_user_key(self._event_sender_id(event))
        today = day.isoformat()
        if owner not in self._daily_group_members(group, today):
            return
        with self._data_lock:
            if day != self._today():
                return
            bucket = self._roast_feeding_state["days"].get(today, {}).get(group, {})
            kind = bucket.get("cards", {}).get(owner)
            if kind is None:
                digest = hashlib.sha256(f"{today}\0{pig['id']}".encode()).digest()
                kind = self._FEEDING_KINDS[digest[0] % len(self._FEEDING_KINDS)]
                state = deepcopy(self._roast_feeding_state)
                self._feeding_group(state, today, group)["cards"][owner] = kind
                try:
                    self._save_feeding_change(state, today)
                except OSError as exc:
                    logger.warning(f"料理卡投喂保存失败：{exc}")
                    kind = ""
        if kind == "":
            await event.send(event.plain_result(self._feeding_copy("feed_save_failed")))
        elif kind in self._FEEDING_KINDS:
            dish = self._feeding_copy(f"feed_{kind}_food")
            await event.send(
                event.plain_result(self._feeding_copy("feed_offer", dish=dish))
            )

    def _feed_target_in_group(
        self, group: str, user: str, day: datetime.date, tomorrow: bool
    ) -> bool:
        # A next-day bowl can be left for a member who skipped today's draw.
        for offset in range(7 if tomorrow else 1):
            roster_day = (day - datetime.timedelta(days=offset)).isoformat()
            if user in self._daily_group_members(group, roster_day):
                return True
        return False

    def _use_feeding_card(
        self, group: str, owner: str, target: str, day: datetime.date, tomorrow: bool
    ) -> tuple[str, str]:
        today = day.isoformat()
        due = (day + datetime.timedelta(days=int(tomorrow))).isoformat()
        with self._data_lock:
            if day != self._today():
                return "feed_no_dish", ""
            state = deepcopy(self._roast_feeding_state)
            cards = self._feeding_group(state, today, group)["cards"]
            kind = cards.get(owner)
            if kind == "used":
                return "feed_used", ""
            if kind not in self._FEEDING_KINDS:
                return "feed_no_dish", ""
            effects = self._feeding_group(state, due, group)["effects"]
            if target in effects:
                return "feed_slot_taken", ""
            effects[target] = kind
            cards[owner] = "used"
            try:
                self._save_feeding_change(state, today)
            except OSError as exc:
                logger.warning(f"料理卡投喂保存失败：{exc}")
                return "feed_save_failed", ""
        return ("feed_tomorrow" if tomorrow else "feed_today"), kind

    async def _feed_command(self, event, args: str) -> bool:
        parts = str(args or "").split(maxsplit=1)
        if not parts or parts[0] not in self._FEEDING_COMMANDS:
            return False
        self._claim_command_event(event)
        tomorrow = self._FEEDING_COMMANDS[parts[0]]
        if not self._feeding_enabled():
            key, kind, target_id = "feed_disabled", "", ""
        else:
            target_arg = parts[1] if len(parts) > 1 else ""
            key, kind, target_id = self._try_feed_command(event, target_arg, tomorrow)
        if kind:
            await self._send_with_mention(
                event,
                target_id,
                self._feeding_copy(
                    key,
                    dish=self._feeding_copy(f"feed_{kind}_food"),
                    mutation=self._feeding_copy(f"feed_{kind}_badge"),
                ),
            )
        else:
            await event.send(event.plain_result(self._feeding_copy(key)))
        return True

    def _try_feed_command(
        self, event, target_arg: str, tomorrow: bool
    ) -> tuple[str, str, str]:
        group = self._event_group_id(event)
        if not group:
            return "feed_group_only", "", ""
        target_id = self._extract_roast_target_id(event, target_arg)
        if not target_id:
            return "feed_target_required", "", ""
        owner = self._storage_user_key(self._event_sender_id(event))
        target = self._storage_user_key(target_id)
        if owner == target:
            return "feed_self", "", ""
        day = self._today()
        if not self._feed_target_in_group(group, target, day, tomorrow):
            return ("feed_tomorrow_eligible" if tomorrow else "feed_eligible"), "", ""
        key, kind = self._use_feeding_card(group, owner, target, day, tomorrow)
        return key, kind, target_id
