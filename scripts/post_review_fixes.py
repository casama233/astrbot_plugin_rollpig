from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
PAGE = ROOT / "pages" / "pig-manager" / "index.html"
CHANGELOG = ROOT / "CHANGELOG.md"
TESTS = ROOT / "tests"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


main = MAIN.read_text(encoding="utf-8")

# Initialization must not call _now() before self.timezone exists.
main = replace_once(
    main,
    '''            self.timezone = (
                self._now().tzinfo
                if timezone_name.lower() in {"", "local", "system"}
                else ZoneInfo(timezone_name)
            )
        except ZoneInfoNotFoundError:
            logger.warning(f"未知时区 {timezone_name}，已回退系统时区")
            self.timezone = self._now().tzinfo
''',
    '''            self.timezone = (
                datetime.datetime.now().astimezone().tzinfo
                if timezone_name.lower() in {"", "local", "system"}
                else ZoneInfo(timezone_name)
            )
        except ZoneInfoNotFoundError:
            logger.warning(f"未知时区 {timezone_name}，已回退系统时区")
            self.timezone = datetime.datetime.now().astimezone().tzinfo
''',
    "timezone initialization",
)

main = replace_once(
    main,
    "        self._page_write_lock = asyncio.Lock()\n",
    "",
    "unused page lock",
)

old_storage = '''    def _storage_user_key(self, user_id: str) -> str:
        candidates = self._identity_candidates(str(user_id))
        users = getattr(self, "history", {}).get("users", {})
        for candidate in candidates:
            if candidate in users:
                return candidate
        penalties = getattr(self, "roast_state", {}).get("eaten_penalties", {})
        for candidate in candidates:
            if isinstance(penalties, dict) and candidate in penalties:
                return candidate
        return candidates[0]

    def _storage_group_key(self, group_id: str) -> str:
        candidates = self._identity_candidates(str(group_id))
        daily = getattr(self, "history", {}).get("daily", {})
        for day in daily.values() if isinstance(daily, dict) else ():
            groups = day.get("groups", {}) if isinstance(day, dict) else {}
            for candidate in candidates:
                if isinstance(groups, dict) and candidate in groups:
                    return candidate
        return candidates[0]
'''
new_storage = '''    def _claim_legacy_identity(
        self,
        namespaced: str,
        legacy: str,
        *,
        kind: str,
        legacy_exists: bool,
    ) -> str:
        """Let one platform claim ambiguous legacy data; other platforms stay isolated."""
        if namespaced == legacy or not legacy_exists:
            return namespaced
        with self._data_lock:
            claims_root = self.history.setdefault("identity_claims", {})
            claims = claims_root.setdefault(kind, {})
            claimed_by = str(claims.get(legacy) or "")
            if not claimed_by:
                claims[legacy] = namespaced
                self.save_json(self.history_path, self.history)
                return legacy
            return legacy if claimed_by == namespaced else namespaced

    def _storage_user_key(self, user_id: str) -> str:
        candidates = self._identity_candidates(str(user_id))
        namespaced = candidates[0]
        legacy = candidates[-1]
        if namespaced == legacy:
            return namespaced
        users = getattr(self, "history", {}).get("users", {})
        penalties = getattr(self, "roast_state", {}).get("eaten_penalties", {})
        legacy_exists = (
            legacy in users
            or (isinstance(penalties, dict) and legacy in penalties)
            or self._identity_exists(legacy)
        )
        if namespaced in users or (
            isinstance(penalties, dict) and namespaced in penalties
        ):
            return namespaced
        return self._claim_legacy_identity(
            namespaced,
            legacy,
            kind="users",
            legacy_exists=legacy_exists,
        )

    def _storage_group_key(self, group_id: str) -> str:
        candidates = self._identity_candidates(str(group_id))
        namespaced = candidates[0]
        legacy = candidates[-1]
        if namespaced == legacy:
            return namespaced
        daily = getattr(self, "history", {}).get("daily", {})
        namespaced_exists = False
        legacy_exists = False
        for day in daily.values() if isinstance(daily, dict) else ():
            groups = day.get("groups", {}) if isinstance(day, dict) else {}
            if not isinstance(groups, dict):
                continue
            namespaced_exists = namespaced_exists or namespaced in groups
            legacy_exists = legacy_exists or legacy in groups
        if namespaced_exists:
            return namespaced
        return self._claim_legacy_identity(
            namespaced,
            legacy,
            kind="groups",
            legacy_exists=legacy_exists,
        )
'''
main = replace_once(main, old_storage, new_storage, "legacy identity claims")

main = replace_once(
    main,
    '''                if self._identity_exists(legacy_digits) and not self._identity_exists(canonical):
                    return legacy_digits
''',
    '''                if self._identity_exists(legacy_digits) and not self._identity_exists(canonical):
                    return self._namespace_identity(event, legacy_digits, "user")
''',
    "WhatsApp legacy namespace",
)

old_roll = '''    async def roll_pig(self, event: AstrMessageEvent):
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

        async with self._daily_draw_lock:
            today_cache = self.load_json(
                self.today_path, {"date": "", "records": {}}
            )
            if today_cache.get("date") != today_str:
                today_cache = {"date": today_str, "records": {}}
            user_records = today_cache.setdefault("records", {})
            existing = next(
                (
                    user_records[candidate]
                    for candidate in self._identity_candidates(target_id)
                    if candidate in user_records
                ),
                None,
            )
            if viewing_other:
                if not existing:
                    await event.send(
                        event.plain_result("对方今天还没有抽取小猪；查看不会替对方抽取。")
                    )
                    return
                await self.send_rendered_pig(event, existing, target_id)
                return

            if self._consume_eaten_penalty(str(actor_id), today_str):
                await event.send(
                    event.plain_result(
                        "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                    )
                )
                return
            if existing:
                await self.send_rendered_pig(event, existing, actor_id)
                return
            if not self.pig_list:
                await event.send(event.plain_result("小猪信息加载失败，请检查后台报错！"))
                return

            storage_id = self._storage_user_key(actor_id)
            pig = self._choose_daily_pig(storage_id)
            user_records[storage_id] = pig
            self._record_unlock(
                storage_id,
                pig,
                today_str,
                group_id=self._event_group_id(event),
                save=False,
            )
            self.save_json_batch(
                {self.today_path: today_cache, self.history_path: self.history}
            )
        await self.send_rendered_pig(event, pig, actor_id)
'''
new_roll = '''    async def roll_pig(self, event: AstrMessageEvent):
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
                    for candidate in self._identity_candidates(target_id)
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
                # Repair historical state left by an older interrupted write.
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
main = replace_once(main, old_roll, new_roll, "draw lock scope and history repair")

old_overview = '''    async def page_overview(self):
        """管理面板：总体指标、趋势与热门小猪。"""
        try:
            await asyncio.sleep(0)
            today = self._today()
            users = self.history.get("users", {})
            catalog_ids = {str(pig.get("id")) for pig in self.pig_list}
            total_users = len(users)
            total_draws = sum(int(u.get("total_draws", 0)) for u in users.values())
            unlocked_counts = [
                len(set(u.get("pigs", {})).intersection(catalog_ids))
                for u in users.values()
            ]
            average_unlocked = (
                sum(unlocked_counts) / total_users if total_users else 0
            )
            average_rate = (
                average_unlocked / len(catalog_ids) * 100 if catalog_ids else 0
            )
            daily = self.history.get("daily", {})
            trend = []
            for offset in range(13, -1, -1):
                day = today - datetime.timedelta(days=offset)
                item = daily.get(day.isoformat(), {})
                trend.append(
                    {
                        "date": f"{day.month}/{day.day}",
                        "users": len(item.get("users", [])),
                        "draws": int(item.get("draws", 0)),
                        "new_unlocks": int(item.get("new_unlocks", 0)),
                    }
                )
            draws, collectors = self._catalog_aggregates()
            names = {
                str(pig.get("id")): str(pig.get("name") or pig.get("id"))
                for pig in self.pig_list
            }
            top_pigs = [
                {
                    "id": pig_id,
                    "name": names.get(pig_id, pig_id),
                    "draws": count,
                    "collectors": collectors[pig_id],
                }
                for pig_id, count in draws.most_common(10)
                if pig_id in names
            ]
            today_item = daily.get(today.isoformat(), {})
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "metrics": {
                            "total_users": total_users,
                            "total_draws": total_draws,
                            "catalog_count": len(catalog_ids),
                            "today_users": len(today_item.get("users", [])),
                            "average_unlocked": round(average_unlocked, 2),
                            "average_unlock_rate": round(average_rate, 2),
                        },
                        "trend": trend,
                        "top_pigs": top_pigs,
                        "csrf_token": self._csrf_token,
                    },
                }
            )
        except Exception as exc:
            logger.error(f"今日小猪管理页总览失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "获取统计数据失败"})
'''
new_overview = '''    def _build_overview_data(self) -> dict:
        """Build the dashboard snapshot off the event-loop thread."""
        with self._data_lock:
            today = self._today()
            users = self.history.get("users", {})
            catalog_ids = {str(pig.get("id")) for pig in self.pig_list}
            total_users = len(users)
            total_draws = sum(int(u.get("total_draws", 0)) for u in users.values())
            unlocked_counts = [
                len(set(u.get("pigs", {})).intersection(catalog_ids))
                for u in users.values()
            ]
            average_unlocked = (
                sum(unlocked_counts) / total_users if total_users else 0
            )
            average_rate = (
                average_unlocked / len(catalog_ids) * 100 if catalog_ids else 0
            )
            daily = self.history.get("daily", {})
            trend = []
            for offset in range(13, -1, -1):
                day = today - datetime.timedelta(days=offset)
                item = daily.get(day.isoformat(), {})
                trend.append(
                    {
                        "date": f"{day.month}/{day.day}",
                        "users": len(item.get("users", [])),
                        "draws": int(item.get("draws", 0)),
                        "new_unlocks": int(item.get("new_unlocks", 0)),
                    }
                )
            draws, collectors = self._catalog_aggregates()
            names = {
                str(pig.get("id")): str(pig.get("name") or pig.get("id"))
                for pig in self.pig_list
            }
            top_pigs = [
                {
                    "id": pig_id,
                    "name": names.get(pig_id, pig_id),
                    "draws": count,
                    "collectors": collectors[pig_id],
                }
                for pig_id, count in draws.most_common(10)
                if pig_id in names
            ]
            today_item = daily.get(today.isoformat(), {})
            return {
                "metrics": {
                    "total_users": total_users,
                    "total_draws": total_draws,
                    "catalog_count": len(catalog_ids),
                    "today_users": len(today_item.get("users", [])),
                    "average_unlocked": round(average_unlocked, 2),
                    "average_unlock_rate": round(average_rate, 2),
                },
                "trend": trend,
                "top_pigs": top_pigs,
            }

    async def page_overview(self):
        """管理面板：总体指标、趋势与热门小猪。"""
        try:
            data = await asyncio.to_thread(self._build_overview_data)
            data["csrf_token"] = self._csrf_token
            return self._jsonify({"status": "ok", "data": data})
        except Exception as exc:
            logger.error(f"今日小猪管理页总览失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "获取统计数据失败"})
'''
main = replace_once(main, old_overview, new_overview, "overview background aggregation")

main = replace_once(
    main,
    "            draws, collectors = self._catalog_aggregates()\n            payload = []\n",
    "            draws, collectors = await asyncio.to_thread(self._catalog_aggregates)\n            payload = []\n",
    "catalog aggregate background thread",
)

ast.parse(main)
MAIN.write_text(main, encoding="utf-8")

page = PAGE.read_text(encoding="utf-8")
page = replace_once(
    page,
    "try{paintRgbaCanvas($('imagePreview'),p.thumbnail||await get('pighub/preview',{url:p.image_url}));toast('已带回 PigHub 图片，请继续填写描述与文案')}",
    "try{await paintRgbaCanvas($('imagePreview'),p.thumbnail||await get('pighub/preview',{url:p.image_url}));toast('已带回 PigHub 图片，请继续填写描述与文案')}",
    "PigHub preview await",
)
PAGE.write_text(page, encoding="utf-8")

# Restore the complete historical changelog and prepend this release.
original = subprocess.run(
    ["git", "show", "origin/main:CHANGELOG.md"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    check=True,
).stdout
history = original
if history.startswith("# 更新\n"):
    history = history[len("# 更新\n") :]
entry = '''# 更新
## v2.4.0 (2026-08-03)
### 稳定性与安全
- 修复并发抽取可能令当日缓存与永久图鉴不一致的问题；相关 JSON 采用预写、备份与失败回滚的批量提交。
- `@他人` 现在只读取对方已有结果，不再替对方抽取，也不能借此绕过次日惩罚。
- 新增平台命名空间与旧 ID 认领记录：既有数据由首次使用的平台继续继承，其他平台的同号用户保持隔离。
- JSON 损坏时保留 `.corrupt-*` 副本并优先从 `.bak` 恢复，避免静默覆盖原始数据。
- AI 文案按小猪分片加锁并加入可配置超时，避免单个模型请求阻塞全部生成。
- 管理页写接口增加同源与 CSRF 校验；统计计算和缩略图处理移出事件循环，缩略图改为压缩 PNG。
- 云同步限制重定向主机、拒绝私网解析、限制图片尺寸，并在任务完成时立即落盘以降低峰值内存。
- 新增 IANA 时区配置，修复图片句柄、裁剪、长文案溢出及管理员 ID 比较不一致。

### 工程
- 版本更新至 2.4.0，文档最低 AstrBot 版本与元数据统一为 4.24.2。
- 移除未使用的 Jinja2 依赖，新增身份/IP 辅助模块、回归测试与 GitHub Actions CI。

'''
CHANGELOG.write_text(entry + history.lstrip(), encoding="utf-8")

(TESTS / "test_source_regressions.py").write_text(
    '''from __future__ import annotations\n\nimport ast\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nSOURCE = (ROOT / "main.py").read_text(encoding="utf-8")\n\n\ndef _method(name: str):\n    tree = ast.parse(SOURCE)\n    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin")\n    return next(node for node in plugin.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)\n\n\ndef test_timezone_does_not_use_uninitialized_self_timezone():\n    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""\n    assert "self._now().tzinfo" not in init\n    assert "datetime.datetime.now().astimezone().tzinfo" in init\n\n\ndef test_daily_draw_lock_contains_no_network_awaits():\n    method = _method("roll_pig")\n    draw_locks = [node for node in ast.walk(method) if isinstance(node, ast.AsyncWith)]\n    assert draw_locks\n    for block in draw_locks:\n        assert not any(isinstance(node, ast.Await) for statement in block.body for node in ast.walk(statement))\n\n\ndef test_dashboard_aggregation_is_offloaded():\n    method = ast.get_source_segment(SOURCE, _method("page_overview")) or ""\n    assert "asyncio.to_thread(self._build_overview_data)" in method\n\n\ndef test_pighub_preview_awaits_canvas_decode():\n    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")\n    assert "try{await paintRgbaCanvas($('imagePreview')" in page\n''',
    encoding="utf-8",
)

print("post-review fixes applied")
