from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
main_path = ROOT / "main.py"
main = main_path.read_text(encoding="utf-8")
start = main.index("    async def roll_pig(self, event: AstrMessageEvent):")
end = main.index('    @filter.command(\n        "我的猪圈"', start)
new_roll = r'''    async def roll_pig(self, event: AstrMessageEvent):
        """Draw for self; mentioning another user is strictly read-only."""
        today_str = self._today().isoformat()
        actor_id = self._event_sender_id(event)
        target_id = actor_id
        viewing_other = False
        if self.at_view_pig:
            at_ids = self.get_at_ids(event)
            if len(at_ids) > 1:
                await event.send(event.plain_result("一次只能查看一个小猪哦！"))
                return
            if at_ids:
                target_id = at_ids[0]
                viewing_other = target_id != actor_id
                if self._is_admin_id(event, target_id):
                    await event.send(event.plain_result("你这只小猪，不许对主人不敬！"))
                    return

        response_text = ""
        pig_to_send: dict | None = None
        send_user_id = actor_id
        group_id = self._event_group_id(event)
        if getattr(self.storage, "supports_domain_writes", False):
            if viewing_other:
                pig_to_send = self._get_daily_pig(target_id, self._today())
                if pig_to_send:
                    send_user_id = target_id
                else:
                    response_text = "对方今天还没有抽取小猪；查看不会替对方抽取。"
            else:
                storage_id = self._storage_user_key(actor_id)
                candidates = tuple(self._user_read_candidates(actor_id))
                probe = await asyncio.to_thread(
                    self.storage.create_daily_draw,
                    draw_date=today_str,
                    user_id=storage_id,
                    user_candidates=candidates,
                    pig=None,
                    group_id=group_id,
                    penalty_should_fail=(
                        random.randrange(100) < self.eaten_next_day_failure_percent
                    ),
                )
                self._apply_domain_write_result(probe)
                status = str(probe.get("status") or "")
                if status == "penalty-blocked":
                    response_text = (
                        "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                    )
                elif status == "needs-pig":
                    if not self.pig_list:
                        response_text = "小猪信息加载失败，请检查后台报错！"
                    else:
                        proposed = self._choose_daily_pig(storage_id)
                        result = await asyncio.to_thread(
                            self.storage.create_daily_draw,
                            draw_date=today_str,
                            user_id=storage_id,
                            user_candidates=candidates,
                            pig=proposed,
                            group_id=group_id,
                            penalty_should_fail=False,
                        )
                        self._apply_domain_write_result(result)
                        if result.get("status") in {"created", "existing"}:
                            pig_to_send = result.get("pig") or proposed
                        elif result.get("status") == "penalty-blocked":
                            response_text = (
                                "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                            )
                        else:
                            response_text = "今日小猪写入失败，请稍后再试。"
                elif status == "existing":
                    pig_to_send = probe.get("pig")
                else:
                    response_text = "今日小猪写入失败，请稍后再试。"
        else:
            async with self._daily_draw_lock:
                today_cache = self.load_json(
                    self.today_path, {"date": "", "records": {}}
                )
                if today_cache.get("date") != today_str:
                    today_cache = {"date": today_str, "records": {}}
                user_records = today_cache.setdefault("records", {})
                existing_key = next(
                    (
                        candidate
                        for candidate in self._user_read_candidates(target_id)
                        if candidate in user_records
                    ),
                    "",
                )
                existing = user_records.get(existing_key) if existing_key else None

                if viewing_other:
                    if existing:
                        pig_to_send = existing
                        send_user_id = target_id
                    else:
                        response_text = "对方今天还没有抽取小猪；查看不会替对方抽取。"
                elif self._consume_eaten_penalty(str(actor_id), today_str):
                    response_text = (
                        "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                    )
                elif existing:
                    changed = self._record_unlock(
                        existing_key,
                        existing,
                        today_str,
                        group_id=group_id,
                        save=False,
                    )
                    if changed:
                        self.save_json(self.history_path, self.history)
                    pig_to_send = existing
                elif not self.pig_list:
                    response_text = "小猪信息加载失败，请检查后台报错！"
                else:
                    storage_id = self._storage_user_key(actor_id)
                    pig_to_send = self._choose_daily_pig(storage_id)
                    user_records[storage_id] = pig_to_send
                    self._record_unlock(
                        storage_id,
                        pig_to_send,
                        today_str,
                        group_id=group_id,
                        save=False,
                    )
                    self.save_json_batch(
                        {self.today_path: today_cache, self.history_path: self.history}
                    )

        if response_text:
            await event.send(event.plain_result(response_text))
            return
        if pig_to_send:
            await self.send_rendered_pig(event, pig_to_send, send_user_id)

'''
main_path.write_text(main[:start] + new_roll + main[end:], encoding="utf-8")

regression_path = ROOT / "tests/test_source_regressions.py"
regression = regression_path.read_text(encoding="utf-8")
regression = regression.replace("assert 'supports_domain_writes' in MAIN", "assert 'supports_domain_writes' in SOURCE")
regression = regression.replace("assert 'self.storage.create_daily_draw' in MAIN", "assert 'self.storage.create_daily_draw' in SOURCE")
regression = regression.replace("assert 'self.storage.replace_daily_pig_with_eaten' in MAIN", "assert 'self.storage.replace_daily_pig_with_eaten' in SOURCE")
regression = regression.replace("assert 'await self._replace_today_with_eaten_persisted' in MAIN", "assert 'await self._replace_today_with_eaten_persisted' in SOURCE")
regression_path.write_text(regression, encoding="utf-8")
