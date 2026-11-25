from __future__ import annotations

import datetime

try:
    from .gameplay_copy import GAMEPLAY_COPY
    from .roast_mutations import MUTATIONS, NO_ODDS_DELTA, RoastMode
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_copy import GAMEPLAY_COPY
    from roast_mutations import MUTATIONS, NO_ODDS_DELTA, RoastMode


def roast_odds(
    plugin, group_id: str, target_id: str, *, bypass: bool = False, mode: RoastMode = "direct"
) -> str:
    choose = plugin.roast_service.choose_group_roast_outcome
    if bypass:
        return choose(bypass=True)
    perks = getattr(plugin, "_active_pig_perks", None)
    if perks:
        effect_id, aura = perks(group_id, target_id, plugin._today())
        mutation = MUTATIONS.get(effect_id)
        delta = (
            mutation.odds_delta
            if mutation and mutation.odds_mode in (None, mode)
            else NO_ODDS_DELTA
        )
        if delta != NO_ODDS_DELTA or aura:
            return choose(odds_delta=delta, aura=aura)
    return choose()


async def serve_roast(
    plugin, event, pig: dict, user_id: str, *,
    own: bool = False, draw_date: str = "", mode: RoastMode = "direct",
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
        pig = prepare(event, pig, user_id, draw_date=draw_date, mode=mode)
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
        self, event, pig: dict, user_id: str, *,
        draw_date: str = "", mode: RoastMode = "direct",
    ) -> dict:
        day = datetime.date.fromisoformat(draw_date) if draw_date else self._today()
        effect_id, _ = self._active_pig_perks(self._event_group_id(event), user_id, day)
        mutation = MUTATIONS.get(effect_id)
        if mutation and mutation.roast_ex and mutation.roast_mode in (None, mode):
            return {
                **pig,
                "_extra_ex": mutation.roast_ex,
                "_roast_bonus_copy": mutation.roast_copy,
            }
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
            effect_id, aura = self._active_pig_perks(
                self._event_group_id(event), str(user_id), self._today()
            )
            stamps = []
            notices = []
            mutation = MUTATIONS.get(effect_id)
            if mutation:
                stamps.append(GAMEPLAY_COPY[f"feed_{mutation.food}_badge"])
                notices.append(GAMEPLAY_COPY[f"feed_{effect_id}_notice"])
            if aura:
                stamps.append(GAMEPLAY_COPY["weekly_aura_badge"])
                notices.append(GAMEPLAY_COPY["weekly_aura_notice"])
            if stamps:
                pig_data = {
                    **pig_data,
                    "_extra_ex": int(aura) + (mutation.draw_ex if mutation else 0),
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
