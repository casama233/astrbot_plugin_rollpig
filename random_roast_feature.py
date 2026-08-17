from __future__ import annotations

from astrbot.api import logger


class RandomRoastMixin:
    """Random group-roast orchestration without owning AstrBot command registration."""

    async def roast_random_group_member(self, event):
        """Pick an eligible target, spend Charge, then announce and resolve the roast."""
        self._claim_command_event(event)
        if not self.enable_roast or not self.enable_group_roast:
            await event.send(
                event.plain_result(
                    "🔒 今天后厨不开群友这桌。管理员已经把烤群友的火关了。"
                )
            )
            return

        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(
                event.plain_result(
                    "🎲 随机烤群友只能在群里转盘。私聊只有你一个，随机得有点侮辱概率学。"
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
                    "🎲 今天本群没有可随机下锅的群友：没抽、已上桌或有保护的都被转盘剔除了。"
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
                    "🔥 烤箱能量已耗尽（"
                    f"0/{self.group_roast_max_charges}）；下一格将在 "
                    f"{self._format_cooldown(remaining)} 后恢复。"
                )
            )
            return

        await self._send_with_mention(
            event,
            target_id,
            " 🎲 随机转盘停在你头上。后厨说：就你了。",
        )

        charge_note = self._roast_charge_note(charge_status)
        result = self.roast_service.choose_group_roast_outcome()
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
                    "💨 对方一溜烟跑了，烤架上只剩一阵风。后厨连盐都白撒了。"
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
                        "🔥 烤架反噬了！翻面一看你今天没有可料理的小猪——"
                        "这次不是技术好，是锅里没货。"
                        + charge_note
                    )
                )
                return
            await event.send(
                event.plain_result(
                    "🔥 烤架反噬！火舌顺着锅沿爬回来，这次轮到你的今日小猪上桌。"
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
                "🔥 烧烤成功，对方今天的小猪已经被后厨端走，围裙都没来得及系。"
                + charge_note
            )
        )
        await self._record_group_roast(group_id, target_id)
        await self._send_roast_card(event, target_pig, target_id)
