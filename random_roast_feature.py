from __future__ import annotations

from astrbot.api import logger

try:
    from .gameplay_perks import roast_odds, serve_roast
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_perks import roast_odds, serve_roast


class RandomRoastMixin:
    """Random group-roast orchestration without owning AstrBot command registration."""

    def _random_roast_target_announcement(self, event, target_id: str):
        return self._mention_message(
            event,
            target_id,
            ' 头上！后厨拍板：今晚就宠幸你了。',
            before='🎲 命运转盘滴溜溜停在了 ',
        )

    async def roast_random_group_member(self, event):
        """Pick an eligible target, spend Charge, then announce and resolve the roast."""
        self._claim_command_event(event)
        if not self.enable_roast or not self.enable_group_roast:
            await event.send(
                event.plain_result(
                    '🔒 今天后厨不开“烤群友”这桌。管理员已经把灶台的火给掐了。'
                )
            )
            return

        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(
                event.plain_result(
                    '🎲 随机烤群友只能在群里转盘。私聊就你一个光杆司令，随机起来实在太不尊重概率学了。'
                )
            )
            return

        actor_id = self._event_sender_id(event)
        today = self._today()
        members = self._daily_group_members(group_id, today.isoformat())
        candidates: list[str] = []
        for raw_user_id in members if isinstance(members, list) else []:
            user_id = str(raw_user_id)
            if user_id == actor_id:
                continue
            pig = self._get_daily_pig(user_id, today)
            if self._roast_block_reason(pig):
                continue
            protected, _ = await self._roast_protection_status(group_id, user_id)
            if not protected and user_id not in candidates:
                candidates.append(user_id)

        target_id = ""
        target_pig = None
        while candidates:
            candidate = self.roast_service.choose_group_roast_target(candidates)
            candidate_pig = self._get_daily_pig(candidate, today)
            reason = self._roast_block_reason(candidate_pig)
            protected, _ = await self._roast_protection_status(group_id, candidate)
            if not reason and not protected:
                target_id = candidate
                target_pig = candidate_pig
                break
            candidates.remove(candidate)

        if not target_id or not target_pig:
            await event.send(
                event.plain_result(
                    '🎲 今天群里挑不出能下锅的群友：没抽猪的、已经端上桌的、还有套着保护罩的都被转盘踢出局啦。'
                )
            )
            return

        # Spend before the target announcement so an empty oven cannot be used as
        # a free random-mention machine. The chosen target is revalidated above
        # immediately before this atomic Charge write.
        charge_status = await self._consume_group_roast_charge(group_id, actor_id)
        if not charge_status.get("consumed"):
            remaining = int(charge_status.get("next_refill_seconds", 0) or 0)
            await event.send(
                event.plain_result(
                    f'🔥 烤箱火力已经见底（0/{self.group_roast_max_charges}）；下一格能量还要等 {self._format_cooldown(remaining)} 才能回满。'
                )
            )
            return

        await event.send(self._random_roast_target_announcement(event, target_id))

        charge_note = self._roast_charge_note(charge_status)
        result = roast_odds(self, group_id, target_id, mode="random")
        logger.info(
            "随机烤群友判定：group=%s actor=%s target=%s outcome=%s "
            "charge=%s/%s rng=isolated",
            group_id,
            actor_id,
            target_id,
            result,
            int(charge_status.get("charges", 0) or 0),
            int(charge_status.get("max_charges", self.group_roast_max_charges) or 0),
        )

        if result == "escape":
            self._record_roast_outcome_event(
                "roast_escape",
                group_id,
                actor_id=actor_id,
                target_id=target_id,
            )
            await event.send(
                event.plain_result(
                    '💨 随机点到的群友反应神速，一溜烟跑没影了，炉子空空如也。'
                    + charge_note
                )
            )
            return

        if result == "backlash":
            actor_pig = self._get_daily_pig(actor_id, today)
            actor_reason = self._roast_block_reason(actor_pig, subject="actor")
            victim_id = "" if actor_reason else actor_id
            self._record_roast_outcome_event(
                "roast_backlash",
                group_id,
                actor_id=actor_id,
                target_id=target_id,
                victim_id=victim_id,
            )
            if actor_reason:
                await event.send(
                    event.plain_result(
                        '🔥 运气背到家触发了反噬，好在你手里现在没有可烤的小猪，躲过一劫！'
                        + charge_note
                    )
                )
                return
            await event.send(
                event.plain_result(
                    '🔥 运气背到家，随机烤猪触发反噬，你自己的今日小猪惨遭烤熟。'
                    + charge_note
                )
            )
            await self._record_group_roast(group_id, actor_id)
            await self._send_roast_card(event, actor_pig, actor_id)
            return

        self._record_roast_outcome_event(
            "roast_success",
            group_id,
            actor_id=actor_id,
            target_id=target_id,
            victim_id=target_id,
        )
        await event.send(
            event.plain_result(
                '🔥 烧烤大功告成！对方今天刚抽的小猪已经被后厨连锅端走，连小围裙都没来得及系上。'
                + charge_note
            )
        )
        await self._record_group_roast(group_id, target_id)
        await serve_roast(self, event, target_pig, target_id, mode="random")
