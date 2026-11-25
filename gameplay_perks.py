from __future__ import annotations

import datetime

try:
    from .gameplay_copy import GAMEPLAY_COPY
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_copy import GAMEPLAY_COPY


def roast_odds(plugin, group_id: str, target_id: str, *, bypass: bool = False) -> str:
    choose = plugin.roast_service.choose_group_roast_outcome
    if bypass:
        return choose(bypass=True)
    perks = getattr(plugin, "_active_pig_perks", None)
    if perks:
        mutation, aura = perks(group_id, target_id, plugin._today())
        if mutation == "spicy" or aura:
            return choose(spicy=mutation == "spicy", aura=aura)
    return choose()


async def serve_roast(
    plugin, event, pig: dict, user_id: str, *, own: bool = False, draw_date: str = ""
) -> bool:
    if own:
        offer = getattr(plugin, "_offer_self_roast_feed", None)
        day = plugin._today() if offer else None
        sent = await plugin._send_roast_card(event, pig, user_id)
        if sent and offer:
            await offer(event, pig, day=day)
        return sent

    prepare = getattr(plugin, "_decorate_successful_roast", None)
    if prepare:
        pig = prepare(event, pig, user_id, draw_date=draw_date)
    return await plugin._send_roast_card(event, pig, user_id)


class GameplayPerksMixin:
    """Translate group effects into the day’s roast odds and card decorations."""

    def _active_pig_perks(
        self, group_id: str, user_id: str, day: datetime.date
    ) -> tuple[str, bool]:
        if not group_id:
            return "", False
        mutation = self._feeding_effect(group_id, user_id, day)
        aura = self._weekly_aura(group_id, user_id, day)
        if mutation or aura:
            members = self._daily_group_members(group_id, day.isoformat())
            if not set(self._user_read_candidates(user_id)).intersection(members):
                return "", False
        return mutation, aura

    def _decorate_successful_roast(
        self, event, pig: dict, user_id: str, *, draw_date: str = ""
    ) -> dict:
        day = datetime.date.fromisoformat(draw_date) if draw_date else self._today()
        mutation, _ = self._active_pig_perks(self._event_group_id(event), user_id, day)
        if mutation == "rich":
            return {**pig, "_extra_ex": 1, "_rich_roast": True}
        return pig

    async def send_rendered_pig(
        self,
        event,
        pig_data: dict,
        user_id: str,
        intro: str = '。这是为你派发的今日小猪：',
        fallback_title: str = "今日小猪",
    ):
        if fallback_title == "今日小猪" and not self._roast_block_reason(pig_data):
            mutation, aura = self._active_pig_perks(
                self._event_group_id(event), str(user_id), self._today()
            )
            stamps = []
            notices = []
            if mutation:
                stamps.append(GAMEPLAY_COPY[f"feed_{mutation}_badge"])
                notices.append(GAMEPLAY_COPY[f"feed_{mutation}_notice"])
            if aura:
                stamps.append(GAMEPLAY_COPY["weekly_aura_badge"])
                notices.append(GAMEPLAY_COPY["weekly_aura_notice"])
            if stamps:
                pig_data = {
                    **pig_data,
                    "_extra_ex": int(aura),
                    "_pig_card_stamps": tuple(stamps),
                    "_perk_notice": "\n".join(notices),
                }
                intro = "\n".join([intro, *notices])
        return await super().send_rendered_pig(
            event, pig_data, user_id, intro=intro, fallback_title=fallback_title
        )

    async def send_fallback_msg(self, event, pig_data: dict, title: str = "今日小猪"):
        if notice := pig_data.get("_perk_notice"):
            pig_data = {**pig_data, "analysis": f"{pig_data.get('analysis', '')}\n{notice}"}
        return await super().send_fallback_msg(event, pig_data, title)
