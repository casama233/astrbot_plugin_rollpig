from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
CONFIG = ROOT / "_conf_schema.json"
METADATA = ROOT / "metadata.yaml"
README = ROOT / "README.md"
REQUIREMENTS = ROOT / "requirements.txt"
PAGE = ROOT / "pages" / "pig-manager" / "index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_regex(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, got {count}")
    return text


def replace_dates_in_self_methods(source: str) -> str:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    ranges: list[tuple[int, int]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "RollPigPlugin":
            continue
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = child.args.posonlyargs + child.args.args
                if args and args[0].arg == "self":
                    ranges.append((child.lineno - 1, child.end_lineno or child.lineno))
    for start, end in ranges:
        block = "".join(lines[start:end])
        block = block.replace("datetime.date.today()", "self._today()")
        block = block.replace("datetime.datetime.now().astimezone()", "self._now()")
        lines[start:end] = [block] + [""] * (end - start - 1)
    return "".join(lines)


main = MAIN.read_text(encoding="utf-8")

main = replace_once(
    main,
    "import hashlib\nimport io\nimport json\n",
    "import hashlib\nimport importlib\nimport io\nimport ipaddress\nimport json\nimport os\nimport secrets\nimport shutil\nimport socket\n",
    "imports",
)
# The original file already imports shutil later; remove the duplicate introduced by the guarded import patch.
main = main.replace("import re\nimport shutil\nimport tempfile", "import re\nimport tempfile", 1)
main = replace_once(
    main,
    "from pathlib import Path\nfrom urllib.parse import quote, urljoin, urlsplit, urlunsplit\n",
    "from pathlib import Path\nfrom urllib.parse import quote, urljoin, urlsplit, urlunsplit\nfrom zoneinfo import ZoneInfo, ZoneInfoNotFoundError\n",
    "zoneinfo import",
)

main = replace_once(
    main,
    "        self.admins_id: list[str] = context.get_config().get(\"admins_id\", [])\n        self.at_view_pig: bool = self.config.get(\"at_view_pig\", False)\n",
    "        self.admins_id: set[str] = {\n            str(item).strip()\n            for item in context.get_config().get(\"admins_id\", [])\n            if str(item).strip()\n        }\n        timezone_name = str(self.config.get(\"timezone\", \"local\") or \"local\").strip()\n        self.timezone_name = timezone_name\n        try:\n            self.timezone = (\n                datetime.datetime.now().astimezone().tzinfo\n                if timezone_name.lower() in {\"\", \"local\", \"system\"}\n                else ZoneInfo(timezone_name)\n            )\n        except ZoneInfoNotFoundError:\n            logger.warning(f\"未知时区 {timezone_name}，已回退系统时区\")\n            self.timezone = datetime.datetime.now().astimezone().tzinfo\n            self.timezone_name = \"local\"\n        try:\n            ai_timeout = float(self.config.get(\"ai_generation_timeout_seconds\", 45))\n        except (TypeError, ValueError):\n            ai_timeout = 45\n        self.ai_generation_timeout = min(120.0, max(5.0, ai_timeout))\n        self.at_view_pig: bool = self.config.get(\"at_view_pig\", False)\n",
    "normalized admins and time config",
)

main = replace_once(
    main,
    "        self._resource_sync_lock = asyncio.Lock()\n        self._pighub_lock = asyncio.Lock()\n        self._ai_roast_copy_lock = asyncio.Lock()\n",
    "        self._resource_sync_lock = asyncio.Lock()\n        self._pighub_lock = asyncio.Lock()\n        self._daily_draw_lock = asyncio.Lock()\n        self._page_write_lock = asyncio.Lock()\n        self._ai_roast_copy_locks: dict[str, asyncio.Lock] = {}\n        self._csrf_token = secrets.token_urlsafe(32)\n",
    "locks",
)

helper_methods = r'''
    def _now(self) -> datetime.datetime:
        """Return timezone-aware plugin time."""
        return datetime.datetime.now(self.timezone)

    def _today(self) -> datetime.date:
        return self._now().date()

    def _platform_namespace(self, event: AstrMessageEvent) -> str:
        if self._is_whatsapp_event(event):
            return "whatsapp"
        platform_meta = getattr(event, "platform_meta", None)
        candidates = (
            getattr(event, "platform_name", None),
            getattr(platform_meta, "name", None),
            getattr(platform_meta, "id", None),
            platform_meta,
            getattr(getattr(event, "message_obj", None), "type", None),
        )
        for value in candidates:
            text = str(value or "").strip().lower()
            if text and text not in {"none", "unknown"}:
                return re.sub(r"[^a-z0-9_.-]+", "-", text).strip("-") or "unknown"
        return "unknown"

    @staticmethod
    def _legacy_identity(value: str) -> str:
        text = str(value or "")
        match = re.fullmatch(r"v2\|[^|]+\|(?:user|group)\|(.*)", text)
        return match.group(1) if match else text

    def _namespace_identity(self, event: AstrMessageEvent, value: str, kind: str) -> str:
        raw = str(value or "").strip()
        if not raw or raw.startswith("v2|"):
            return raw
        return f"v2|{self._platform_namespace(event)}|{kind}|{raw}"

    def _identity_candidates(self, value: str) -> tuple[str, ...]:
        value = str(value or "").strip()
        legacy = self._legacy_identity(value)
        return (value,) if legacy == value else (value, legacy)

    def _is_admin_id(self, event: AstrMessageEvent, user_id: str) -> bool:
        candidates = set(self._identity_candidates(user_id))
        candidates.add(self._namespace_identity(event, self._legacy_identity(user_id), "user"))
        return bool(candidates.intersection(self.admins_id))

    def _ai_roast_lock(self, pig_id: str) -> asyncio.Lock:
        key = str(pig_id or "__unknown__")
        lock = self._ai_roast_copy_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._ai_roast_copy_locks[key] = lock
        return lock

    def _request_csrf_token(self) -> str:
        try:
            return str(request.headers.get("X-RollPig-CSRF", "") or "")
        except Exception:
            return ""

    def _is_authorized_write_request(self, request_obj) -> bool:
        return self._is_same_origin_request(request_obj) and secrets.compare_digest(
            self._request_csrf_token(), self._csrf_token
        )

    @staticmethod
    def _is_public_ip(address: str) -> bool:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )

    async def _validate_remote_target(self, url: str, allowed_hosts: set[str] | None = None) -> None:
        parsed = urlsplit(url)
        host = str(parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            raise ValueError("远程地址必须是无凭据的 HTTPS URL")
        if allowed_hosts is not None and host not in allowed_hosts:
            raise ValueError(f"远程跳转到未授权主机：{host}")
        try:
            infos = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError(f"无法解析远程主机：{host}") from exc
        addresses = {str(item[4][0]).split("%", 1)[0] for item in infos}
        if not addresses or any(not self._is_public_ip(item) for item in addresses):
            raise ValueError(f"远程主机解析到非公网地址：{host}")

    @staticmethod
    def _validate_image_dimensions(raw: bytes, label: str = "图片") -> None:
        try:
            with PILImage.open(io.BytesIO(raw)) as image:
                width, height = image.size
                if width < 1 or height < 1:
                    raise ValueError(f"{label}尺寸无效")
                if width > 8192 or height > 8192 or width * height > 25_000_000:
                    raise ValueError(f"{label}尺寸过大，最高支持 8192×8192 / 2500 万像素")
                image.verify()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"{label}内容无效") from exc

'''
main = replace_once(
    main,
    "    def _load_font(\n",
    helper_methods + "    def _load_font(\n",
    "helper methods",
)

old_json = '''    def load_json(self, path: Path, default):
        """
        加载JSON文件\\n
        :param path: 文件路径
        :param default: 默认值（文件不存在或解析失败时使用）
        :return: 解析后的数据对象
        """
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return default
        try:
            return json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError:
            logger.error(f"JSON文件解析失败，重置为默认值：{path}")
            path.write_text(
                json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return default

    def save_json(self, path: Path, data):
        """
        保存JSON数据\\n
        :param path: 文件路径
        :param data: 数据对象
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        with self._data_lock:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(payload)
                tmp_path = Path(tmp.name)
            tmp_path.replace(path)
'''
new_json = '''    def load_json(self, path: Path, default):
        """Load JSON without destroying malformed user data."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self.save_json(path, default)
            return json.loads(json.dumps(default, ensure_ascii=False))
        try:
            return json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            stamp = self._now().strftime("%Y%m%d-%H%M%S")
            corrupt = path.with_name(f"{path.name}.corrupt-{stamp}")
            try:
                shutil.copy2(path, corrupt)
            except OSError as backup_exc:
                logger.error(f"JSON 损坏且备份失败：{path} ({backup_exc})")
            backup = path.with_name(f"{path.name}.bak")
            if backup.exists():
                try:
                    restored = json.loads(backup.read_text("utf-8"))
                    logger.error(f"JSON 解析失败，已从备份恢复：{path}；损坏副本：{corrupt}")
                    self.save_json(path, restored)
                    return restored
                except Exception:
                    pass
            logger.error(f"JSON 解析失败，已保留损坏副本并重建默认值：{path} ({exc})")
            self.save_json(path, default)
            return json.loads(json.dumps(default, ensure_ascii=False))

    def save_json(self, path: Path, data):
        self.save_json_batch({path: data})

    def save_json_batch(self, updates: dict[Path, object]) -> None:
        """Atomically stage a related set of JSON files and roll back on replacement failure."""
        staged: dict[Path, Path] = {}
        backups: dict[Path, Path] = {}
        replaced: list[Path] = []
        with self._data_lock:
            try:
                for raw_path, data in updates.items():
                    path = Path(raw_path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    payload = json.dumps(data, ensure_ascii=False, indent=2)
                    with tempfile.NamedTemporaryFile(
                        "w", encoding="utf-8", dir=path.parent,
                        prefix=f".{path.name}.", suffix=".tmp", delete=False,
                    ) as tmp:
                        tmp.write(payload)
                        tmp.flush()
                        os.fsync(tmp.fileno())
                        staged[path] = Path(tmp.name)
                    backup = path.with_name(f"{path.name}.bak")
                    if path.exists():
                        shutil.copy2(path, backup)
                        backups[path] = backup
                for path, tmp_path in staged.items():
                    os.replace(tmp_path, path)
                    replaced.append(path)
            except Exception:
                for path in reversed(replaced):
                    backup = backups.get(path)
                    if backup and backup.exists():
                        shutil.copy2(backup, path)
                raise
            finally:
                for tmp_path in staged.values():
                    tmp_path.unlink(missing_ok=True)
'''
main = replace_once(main, old_json, new_json, "safe JSON storage")

old_group = '''    @staticmethod
    def _event_group_id(event: AstrMessageEvent) -> str:
        """返回群 ID；私聊或适配器未提供时返回空字符串。"""
        try:
            group_id = str(event.get_group_id() or "")
        except (AttributeError, TypeError):
            group_id = ""
        if not group_id:
            message_obj = getattr(event, "message_obj", None)
            raw_message = getattr(message_obj, "raw_message", None)
            if isinstance(raw_message, dict):
                chat_jid = str(raw_message.get("chatJid") or "")
                if chat_jid.endswith("@g.us"):
                    group_id = chat_jid
        if group_id.endswith("@g.us") and RollPigPlugin._is_whatsapp_event(event):
            return group_id.split("@", 1)[0]
        return group_id
'''
new_group = '''    def _event_group_id(self, event: AstrMessageEvent) -> str:
        """Return a platform-namespaced group ID; private chats return an empty string."""
        try:
            group_id = str(event.get_group_id() or "")
        except (AttributeError, TypeError):
            group_id = ""
        if not group_id:
            message_obj = getattr(event, "message_obj", None)
            raw_message = getattr(message_obj, "raw_message", None)
            if isinstance(raw_message, dict):
                chat_jid = str(raw_message.get("chatJid") or "")
                if chat_jid.endswith("@g.us"):
                    group_id = chat_jid
        if group_id.endswith("@g.us") and self._is_whatsapp_event(event):
            group_id = group_id.split("@", 1)[0]
        return self._namespace_identity(event, group_id, "group") if group_id else ""
'''
main = replace_once(main, old_group, new_group, "group namespace")

old_wa = '''    @staticmethod
    def _whatsapp_lid_to_pn(value: str) -> str:
        """从 WhatsApp 适配器的运行时映射解析 LID；适配器未安装时安全返回原值。"""
        raw = str(value or "").strip()
        if not raw.lower().endswith("@lid"):
            return raw
        try:
            from astrbot_plugin_whatsapp_adapter.whatsapp_adapter import _LID_PN_CACHE

            mapped = _LID_PN_CACHE.get(raw) or _LID_PN_CACHE.get(raw.lower())
            return str(mapped or raw)
        except Exception:
            return raw
'''
new_wa = '''    @staticmethod
    def _whatsapp_lid_to_pn(value: str) -> str:
        """Resolve WhatsApp LID through a public adapter hook when available."""
        raw = str(value or "").strip()
        if not raw.lower().endswith("@lid"):
            return raw
        try:
            module = importlib.import_module(
                "astrbot_plugin_whatsapp_adapter.whatsapp_adapter"
            )
            for name in ("resolve_lid_to_pn", "get_phone_number_for_lid"):
                resolver = getattr(module, name, None)
                if callable(resolver):
                    mapped = resolver(raw)
                    if mapped:
                        return str(mapped)
            # Compatibility only: old adapter releases expose no public resolver.
            cache = getattr(module, "_LID_PN_CACHE", None)
            if isinstance(cache, dict):
                mapped = cache.get(raw) or cache.get(raw.lower())
                if mapped:
                    return str(mapped)
        except Exception:
            pass
        return raw
'''
main = replace_once(main, old_wa, new_wa, "WhatsApp compatibility wrapper")

# Namespace the final canonical user identity while preserving WhatsApp normalization logic.
main = replace_once(
    main,
    "        if not result or not self._is_whatsapp_event(event):\n            return result\n",
    "        if not result:\n            return result\n        if not self._is_whatsapp_event(event):\n            return self._namespace_identity(event, result, \"user\")\n",
    "non-whatsapp namespace",
)
main = replace_once(
    main,
    "            return canonical\n        return resolved\n\n    def _event_sender_id",
    "            return self._namespace_identity(event, canonical, \"user\")\n        return self._namespace_identity(event, resolved, \"user\")\n\n    def _event_sender_id",
    "whatsapp namespace",
)

# Legacy reads remain available after the namespace migration.
main = replace_once(
    main,
    '''    def _get_user_collection(self, user_id: str) -> dict:
        user = self.history.get("users", {}).get(str(user_id), {})
        return user if isinstance(user, dict) else {}
''',
    '''    def _get_user_collection(self, user_id: str) -> dict:
        users = self.history.get("users", {})
        for candidate in self._identity_candidates(str(user_id)):
            user = users.get(candidate, {})
            if isinstance(user, dict) and user:
                return user
        return {}
''',
    "legacy collection lookup",
)
main = replace_once(
    main,
    '''        pig_id = str(day.get("records", {}).get(str(user_id), ""))
        if not pig_id:
            return None
''',
    '''        records = day.get("records", {})
        pig_id = ""
        for candidate in self._identity_candidates(str(user_id)):
            pig_id = str(records.get(candidate, ""))
            if pig_id:
                break
        if not pig_id:
            return None
''',
    "legacy daily lookup",
)

old_roll = '''    @filter.command(
        "今日小猪",
        alias={
            "今日小豬",
            "今天是什么小猪",
            "今天是什麼小豬",
            "抽小猪",
            "抽小豬",
            "我的小猪",
            "我的小豬",
            "rollpig",
        },
    )
    async def roll_pig(self, event: AstrMessageEvent):
        """抽取今日小猪／今日小豬"""
        today_str = datetime.date.today().isoformat()
        user_id = self._event_sender_id(event)
        is_self_draw = True
        if self.at_view_pig:
            at_ids = self.get_at_ids(event)
            if len(at_ids) > 1:
                await event.send(event.plain_result("一次只能抽取一个小猪哦！"))
                return
            if at_ids:
                if at_ids[0] not in self.admins_id:
                    user_id = at_ids[0]
                    is_self_draw = False
                else:
                    await event.send(event.plain_result("你这只小猪，不许对主人不敬！"))
                    return
        if is_self_draw and self._consume_eaten_penalty(str(user_id), today_str):
            await event.send(
                event.plain_result(
                    "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                )
            )
            return
        today_cache = self.load_json(self.today_path, {"date": "", "records": {}})
        if today_cache.get("date") != today_str:
            today_cache = {"date": today_str, "records": {}}
        user_records = today_cache["records"]

        if user_id in user_records:
            pig = user_records[user_id]
            self._record_unlock(
                user_id, pig, today_str, group_id=self._event_group_id(event)
            )
            await self.send_rendered_pig(event, pig, user_id)
            return

        if not self.pig_list:
            await event.send(event.plain_result("小猪信息加载失败，请检查后台报错！"))
            return

        pig = self._choose_daily_pig(user_id)
        user_records[user_id] = pig
        self.save_json(self.today_path, today_cache)
        self._record_unlock(
            user_id, pig, today_str, group_id=self._event_group_id(event)
        )

        await self.send_rendered_pig(event, pig, user_id)
'''
new_roll = '''    @filter.command(
        "今日小猪",
        alias={
            "今日小豬",
            "今天是什么小猪",
            "今天是什麼小豬",
            "抽小猪",
            "抽小豬",
            "我的小猪",
            "我的小豬",
            "rollpig",
        },
    )
    async def roll_pig(self, event: AstrMessageEvent):
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

            pig = self._choose_daily_pig(actor_id)
            user_records[actor_id] = pig
            self._record_unlock(
                actor_id,
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
main = replace_once(main, old_roll, new_roll, "daily draw transaction and view-only mention")

# Make eaten replacement use one staged transaction for all related state.
main = replace_once(
    main,
    "            self.save_json(self.today_path, today_cache)\n\n            daily = self.history.setdefault(\"daily\", {})",
    "\n            daily = self.history.setdefault(\"daily\", {})",
    "remove early eaten today write",
)
main = replace_once(
    main,
    "            self.save_json(self.history_path, self.history)\n\n            penalties = self.roast_state.setdefault",
    "\n            penalties = self.roast_state.setdefault",
    "remove early eaten history write",
)
main = replace_once(
    main,
    "            self._save_roast_state()\n        return dict(eaten)\n",
    "            self.save_json_batch(\n                {\n                    self.today_path: today_cache,\n                    self.history_path: self.history,\n                    self.roast_state_path: self.roast_state,\n                }\n            )\n        return dict(eaten)\n",
    "atomic eaten state",
)

# AI: per-pig lock and bounded provider calls.
main = main.replace("async with self._ai_roast_copy_lock:", "async with self._ai_roast_lock(pig_id):", 1)
main = replace_once(
    main,
    "                    response = await llm_generate(\n                        chat_provider_id=provider_id, prompt=prompt\n                    )\n",
    "                    response = await asyncio.wait_for(\n                        llm_generate(chat_provider_id=provider_id, prompt=prompt),\n                        timeout=self.ai_generation_timeout,\n                    )\n",
    "AI context timeout",
)
main = replace_once(
    main,
    '''                response = await provider.text_chat(
                    prompt=prompt,
                    session_id=None,
                    contexts=[],
                    image_urls=[],
                    func_tool=None,
                    system_prompt="",
                )
''',
    '''                response = await asyncio.wait_for(
                    provider.text_chat(
                        prompt=prompt,
                        session_id=None,
                        contexts=[],
                        image_urls=[],
                        func_tool=None,
                        system_prompt="",
                    ),
                    timeout=self.ai_generation_timeout,
                )
''',
    "AI provider timeout",
)
main = main.replace("            timeout=60,", "            timeout=self.ai_generation_timeout,", 1)

# Harden origin/CSRF semantics: missing browser provenance is denied, and all writes require token.
old_origin = '''    def _is_same_origin_request(self, request) -> bool:
        host = request.headers.get("Host", "") if request else ""
        origin = request.headers.get("Origin", "") if request else ""
        referer = request.headers.get("Referer", "") if request else ""
        sec_fetch_site = request.headers.get("Sec-Fetch-Site", "") if request else ""
        if sec_fetch_site and sec_fetch_site not in {
            "same-origin",
            "same-site",
            "none",
        }:
            return False
        if origin:
            return host and origin.split("://", 1)[-1].split("/", 1)[0] == host
        if referer:
            return host and referer.split("://", 1)[-1].split("/", 1)[0] == host
        return sec_fetch_site == "none"
'''
new_origin = '''    def _is_same_origin_request(self, request) -> bool:
        if not request:
            return False
        host = str(request.headers.get("Host", "") or "").lower()
        origin = str(request.headers.get("Origin", "") or "")
        referer = str(request.headers.get("Referer", "") or "")
        sec_fetch_site = str(request.headers.get("Sec-Fetch-Site", "") or "").lower()
        if not host or sec_fetch_site not in {"same-origin", "same-site"}:
            return False
        source = origin or referer
        if not source:
            return False
        parsed = urlsplit(source)
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host
'''
main = replace_once(main, old_origin, new_origin, "same-origin hardening")
main = main.replace("if not self._is_same_origin_request(request):", "if not self._is_authorized_write_request(request):")

# Include the CSRF token in the authenticated overview response.
main = replace_once(
    main,
    '                        "top_pigs": top_pigs,\n',
    '                        "top_pigs": top_pigs,\n                        "csrf_token": self._csrf_token,\n',
    "overview csrf token",
)

# Offload read-heavy dashboard aggregation and thumbnail work.
main = replace_once(
    main,
    "    async def page_overview(self):\n        \"\"\"管理面板：总体指标、趋势与热门小猪。\"\"\"\n        try:\n",
    "    async def page_overview(self):\n        \"\"\"管理面板：总体指标、趋势与热门小猪。\"\"\"\n        try:\n            await asyncio.sleep(0)\n",
    "overview yield",
)
main = main.replace(
    '                        "thumbnail": self._thumbnail_pixels(pig_id),',
    '                        "thumbnail": await asyncio.to_thread(self._thumbnail_pixels, pig_id),',
    1,
)

# Compress dashboard thumbnails as PNG instead of raw RGBA payloads.
old_pixels = '''    @staticmethod
    def _rgba_pixel_payload(image: PILImage.Image, size: int) -> dict:
        """返回保留透明通道的 Canvas 像素，绕过沙箱中的图片 URL。"""
        method = getattr(PILImage, "Resampling", PILImage).LANCZOS
        fitted = ImageOps.fit(image.convert("RGBA"), (size, size), method)
        return {
            "width": size,
            "height": size,
            "rgba": base64.b64encode(fitted.tobytes()).decode("ascii"),
        }
'''
new_pixels = '''    @staticmethod
    def _rgba_pixel_payload(image: PILImage.Image, size: int) -> dict:
        """Return a compressed PNG data URL for dashboard canvases."""
        method = getattr(PILImage, "Resampling", PILImage).LANCZOS
        fitted = ImageOps.fit(image.convert("RGBA"), (size, size), method)
        output = io.BytesIO()
        fitted.save(output, "PNG", optimize=True)
        return {
            "width": size,
            "height": size,
            "png": base64.b64encode(output.getvalue()).decode("ascii"),
        }
'''
main = replace_once(main, old_pixels, new_pixels, "compressed thumbnails")

# Validate every remote image before it reaches disk or thumbnail decoding.
main = replace_once(
    main,
    "                        try:\n                            with PILImage.open(io.BytesIO(data)) as image:\n                                image.verify()\n                        except Exception as exc:\n                            raise ValueError(f\"图片内容无效：{filename}\") from exc\n                        (staging_images / filename).write_bytes(data)\n",
    "                        self._validate_image_dimensions(data, filename)\n                        (staging_images / filename).write_bytes(data)\n",
    "cloud image dimension validation",
)
main = replace_once(
    main,
    "        with PILImage.open(io.BytesIO(raw)) as source:\n            source.verify()\n        with PILImage.open(io.BytesIO(raw)) as source:\n",
    "        RollPigPlugin._validate_image_dimensions(raw, \"PigHub 图片\")\n        with PILImage.open(io.BytesIO(raw)) as source:\n",
    "pighub dimension validation",
)

# Stream cloud image writes as tasks complete instead of retaining the full package in memory.
old_downloads = '''                    downloads = await asyncio.gather(
                        *(fetch_image(meta) for meta in image_metas)
                    )
                    filenames = [filename for filename, _ in downloads]
                    if len(filenames) != len(set(filenames)):
                        raise ValueError("云资源 manifest 存在重复图片文件名")
                    for filename, data in downloads:
                        try:
                            with PILImage.open(io.BytesIO(data)) as image:
                                image.verify()
                        except Exception as exc:
                            raise ValueError(f"图片内容无效：{filename}") from exc
                        (staging_images / filename).write_bytes(data)
                    pig_ids = {item["id"] for item in pigs}
                    image_ids = {Path(name).stem for name, _ in downloads}
'''
new_downloads = '''                    async def fetch_and_store(meta):
                        filename, data = await fetch_image(meta)
                        self._validate_image_dimensions(data, filename)
                        await asyncio.to_thread(
                            (staging_images / filename).write_bytes, data
                        )
                        return filename

                    tasks = [
                        asyncio.create_task(fetch_and_store(meta))
                        for meta in image_metas
                    ]
                    filenames: list[str] = []
                    try:
                        for task in asyncio.as_completed(tasks):
                            filenames.append(await task)
                    except Exception:
                        for task in tasks:
                            task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                        raise
                    if len(filenames) != len(set(filenames)):
                        raise ValueError("云资源 manifest 存在重复图片文件名")
                    pig_ids = {item["id"] for item in pigs}
                    image_ids = {Path(name).stem for name in filenames}
'''
main = replace_once(main, old_downloads, new_downloads, "stream cloud package")

# Manual, host-pinned redirects and DNS/IP validation.
old_limited_once = '''    async def _download_limited_once(
        self, client: httpx.AsyncClient, url: str, max_size: int
    ) -> bytes:
        total = 0
        chunks: list[bytes] = []
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            if response.url.scheme != "https":
                raise ValueError(f"远程地址发生了非 HTTPS 跳转：{url}")
            length = response.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > max_size:
                raise ValueError(f"远程文件超过大小上限：{url}")
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > max_size:
                    raise ValueError(f"远程文件超过大小上限：{url}")
                chunks.append(chunk)
        return b"".join(chunks)
'''
new_limited_once = '''    async def _download_limited_once(
        self, client: httpx.AsyncClient, url: str, max_size: int
    ) -> bytes:
        current = url
        original_host = str(urlsplit(url).hostname or "").lower()
        allowed_hosts = {original_host, "pighub.top"}
        for _ in range(4):
            await self._validate_remote_target(current, allowed_hosts)
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = str(response.headers.get("Location", "") or "")
                    if not location:
                        raise ValueError("远程跳转缺少 Location")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                length = response.headers.get("Content-Length")
                if length and length.isdigit() and int(length) > max_size:
                    raise ValueError(f"远程文件超过大小上限：{current}")
                total = 0
                chunks: list[bytes] = []
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_size:
                        raise ValueError(f"远程文件超过大小上限：{current}")
                    chunks.append(chunk)
                return b"".join(chunks)
        raise ValueError("远程地址跳转次数过多")
'''
main = replace_once(main, old_limited_once, new_limited_once, "safe redirects")
main = main.replace('"follow_redirects": follow_redirects,', '"follow_redirects": False,', 1)

# Render source images with context managers and a guaranteed fit crop.
old_avatar = '''        if avatar_path:
            try:
                avatar = PILImage.open(avatar_path)
                avatar.thumbnail((avatar_w, avatar_h))
                # 居中裁剪（保证正方形，适配新尺寸：280/2=140）
                if avatar.size != (avatar_w, avatar_h):
                    center_x = avatar.width // 2
                    center_y = avatar.height // 2
                    half = self.AVATAR_SIZE // 2
                    crop_box = (
                        center_x - half,
                        center_y - half,
                        center_x + half,
                        center_y + half,
                    )
                    avatar = avatar.crop(crop_box)
            except Exception as e:
'''
new_avatar = '''        if avatar_path:
            try:
                with PILImage.open(avatar_path) as source:
                    method = getattr(PILImage, "Resampling", PILImage).LANCZOS
                    avatar = ImageOps.fit(
                        ImageOps.exif_transpose(source).convert("RGBA"),
                        (avatar_w, avatar_h),
                        method,
                    )
            except Exception as e:
'''
main = replace_once(main, old_avatar, new_avatar, "safe avatar rendering")

# Serialize page save/delete operations and persist related catalog files in one batch.
main = replace_once(
    main,
    "            with self._data_lock:\n                overrides = self._validate_pig_records(\n",
    "            async with self._page_write_lock:\n                with self._data_lock:\n                    overrides = self._validate_pig_records(\n",
    "page save lock",
)
# Re-indent the known save block introduced above.
save_start = main.index("            async with self._page_write_lock:\n                with self._data_lock:\n                    overrides =", main.index("async def page_pig_save"))
save_end = main.index("            logger.info", save_start)
block = main[save_start:save_end]
lines = block.splitlines()
for i in range(2, len(lines)):
    if lines[i].startswith("                "):
        lines[i] = "    " + lines[i]
block = "\n".join(lines) + "\n"
main = main[:save_start] + block + main[save_end:]
main = replace_once(
    main,
    "                    self.save_json(self.local_overrides_path, overrides)\n                    self.save_json(self.tombstones_path, sorted(tombstones))\n                    self._reload_catalog_layers()\n",
    "                    self.save_json_batch(\n                        {\n                            self.local_overrides_path: overrides,\n                            self.tombstones_path: sorted(tombstones),\n                        }\n                    )\n                    self._reload_catalog_layers()\n",
    "page save batch",
)
# Delete is smaller: keep the existing data lock and batch the metadata files.
main = replace_once(
    main,
    "                self.save_json(self.local_overrides_path, overrides)\n                self.save_json(self.tombstones_path, sorted(tombstones))\n",
    "                self.save_json_batch(\n                    {\n                        self.local_overrides_path: overrides,\n                        self.tombstones_path: sorted(tombstones),\n                    }\n                )\n",
    "page delete batch",
)

# Normalize the remaining admin check.
main = main.replace(
    "if actor_id not in {str(item) for item in self.admins_id}:",
    "if not self._is_admin_id(event, actor_id):",
    1,
)

main = replace_dates_in_self_methods(main)

# Ensure the patched source remains syntactically valid before writing it.
ast.parse(main)
MAIN.write_text(main, encoding="utf-8")

# Configuration additions.
config = json.loads(CONFIG.read_text(encoding="utf-8"))
config["timezone"] = {
    "description": "每日边界时区",
    "hint": "填写 IANA 时区（例如 Asia/Shanghai、America/Los_Angeles）；local 使用服务器系统时区",
    "type": "string",
    "default": "local",
}
config["ai_generation_timeout_seconds"] = {
    "description": "AI 文案调用超时（秒）",
    "hint": "范围 5-120，默认 45；超时自动回退本地文案",
    "type": "float",
    "default": 45,
}
CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

# Frontend: compressed PNG thumbnails and CSRF header propagation.
page = PAGE.read_text(encoding="utf-8")
page = replace_once(
    page,
    "async function post(path,payload){return unwrap(await bridge.apiPost(path,payload||{}))}",
    "let csrfToken='';\nasync function post(path,payload){const body={...(payload||{}),__rollpig_csrf:csrfToken};return unwrap(await bridge.apiPost(path,body,{headers:{'X-RollPig-CSRF':csrfToken}}))}",
    "frontend post csrf",
)
# Some bridge versions do not accept explicit headers. The backend also accepts the body fallback below.
page = page.replace(
    "function paintRgbaCanvas(canvas,thumbnail){const w=Number(thumbnail?.width),h=Number(thumbnail?.height),binary=atob(String(thumbnail?.rgba||''));if(!w||!h||w>512||h>512||binary.length!==w*h*4)throw new Error('缩略图像素数据无效');canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d');const frame=ctx.createImageData(w,h);for(let i=0;i<binary.length;i++)frame.data[i]=binary.charCodeAt(i);ctx.putImageData(frame,0,0)}",
    "async function paintRgbaCanvas(canvas,thumbnail){const w=Number(thumbnail?.width),h=Number(thumbnail?.height),png=String(thumbnail?.png||'');if(!w||!h||w>512||h>512||!png)throw new Error('缩略图数据无效');const image=new Image();image.src='data:image/png;base64,'+png;await image.decode();canvas.width=w;canvas.height=h;canvas.getContext('2d').drawImage(image,0,0,w,h)}",
    1,
)
page = page.replace("if(canvas)paintRgbaCanvas(canvas,thumbnail)", "if(canvas)await paintRgbaCanvas(canvas,thumbnail)")
page = page.replace("Boolean(p.thumbnail?.rgba)", "Boolean(p.thumbnail?.png)")
page = page.replace("if(p.thumbnail?.rgba)paintRgbaCanvas($('imagePreview'),p.thumbnail)", "if(p.thumbnail?.png)paintRgbaCanvas($('imagePreview'),p.thumbnail)")
page = replace_once(
    page,
    "async function loadOverview(){const d=await get('overview'),m=d.metrics;",
    "async function loadOverview(){const d=await get('overview'),m=d.metrics;csrfToken=String(d.csrf_token||csrfToken);",
    "frontend csrf capture",
)
PAGE.write_text(page, encoding="utf-8")

# Backend body fallback for bridge implementations that cannot set custom headers.
main = MAIN.read_text(encoding="utf-8")
main = replace_once(
    main,
    '''    def _request_csrf_token(self) -> str:
        try:
            return str(request.headers.get("X-RollPig-CSRF", "") or "")
        except Exception:
            return ""
''',
    '''    def _request_csrf_token(self) -> str:
        try:
            header = str(request.headers.get("X-RollPig-CSRF", "") or "")
            if header:
                return header
            cached = getattr(request, "_rollpig_payload", None)
            return str(cached.get("__rollpig_csrf", "")) if isinstance(cached, dict) else ""
        except Exception:
            return ""
''',
    "csrf body fallback helper",
)
# For each mutating endpoint, parse payload before authorization and cache it.
for signature in ("page_pig_suggest", "page_pig_save", "page_pig_delete"):
    pattern = rf'(    async def {signature}\(self\):\n        """[^\n]+"""\n        try:\n)(            if not self\._is_authorized_write_request\(request\):\n                return self\._jsonify\(\{{"status": "error", "message": "请求来源无效"\}}\)\n            payload = await request\.json\(default=\{{\}}\)\n)'
    replacement = r'\1            payload = await request.json(default={})\n            setattr(request, "_rollpig_payload", payload if isinstance(payload, dict) else {})\n            if not self._is_authorized_write_request(request):\n                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})\n'
    main, count = re.subn(pattern, replacement, main, count=1)
    if count != 1:
        raise RuntimeError(f"csrf endpoint patch failed: {signature}")
# Resource sync has no JSON payload; accept a query/body token is not viable through all bridges, so frontend sends body.
pattern = r'(    async def page_resource_sync\(self\):\n        """[^\n]+"""\n        try:\n)(            if not self\._is_authorized_write_request\(request\):\n                return self\._jsonify\(\{"status": "error", "message": "请求来源无效"\}\)\n)'
replacement = r'\1            payload = await request.json(default={})\n            setattr(request, "_rollpig_payload", payload if isinstance(payload, dict) else {})\n            if not self._is_authorized_write_request(request):\n                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})\n'
main, count = re.subn(pattern, replacement, main, count=1)
if count != 1:
    raise RuntimeError("csrf endpoint patch failed: page_resource_sync")
ast.parse(main)
MAIN.write_text(main, encoding="utf-8")

# Metadata, dependency cleanup, changelog and tests.
metadata = METADATA.read_text(encoding="utf-8")
metadata = re.sub(r"(?m)^version:\s*.*$", "version: 2.4.0", metadata, count=1)
METADATA.write_text(metadata, encoding="utf-8")

requirements = [line for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines() if not line.lower().startswith("jinja2")]
REQUIREMENTS.write_text("\n".join(requirements).rstrip() + "\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = readme.replace("AstrBot-3.4%2B", "AstrBot-4.24.2%2B")
readme += """

## 2.4.0 稳定性与安全更新

- 今日抽取改为单事务写入，避免并发造成今日结果与永久图鉴不一致。
- `@他人` 仅查看已有结果，不再替对方抽取，也不能绕过被吃惩罚。
- 用户与群组 ID 加入平台命名空间；旧数据在读取时保持兼容。
- JSON 损坏时保留 `.corrupt-*` 副本，并优先尝试 `.bak` 恢复。
- AI 文案增加可配置超时并按小猪分片加锁，避免单次模型卡住全部请求。
- 云资源限制重定向主机、拒绝私网解析、限制图片像素，并边下载边落盘。
- 管理页写操作增加同源与 CSRF 校验；缩略图改用压缩 PNG，降低响应体积。
- 新增每日边界时区配置，并修正图片句柄与裁剪行为。
"""
README.write_text(readme, encoding="utf-8")

(ROOT / "CHANGELOG.md").write_text("""# Changelog

## 2.4.0 - 2026-08-03

### Fixed
- Atomic daily draw/history persistence and eaten-state persistence.
- Read-only mention lookup and penalty bypass prevention.
- Platform-namespaced identities with legacy lookup compatibility.
- Non-destructive JSON recovery with backups.
- Bounded, per-pig AI generation locks.
- Redirect, SSRF, image-dimension and cloud-package memory hardening.
- Dashboard CSRF checks and compressed thumbnails.
- Configurable timezone and safer image rendering.

### Changed
- Minimum AstrBot version documentation now matches metadata (4.24.2).
- Removed the unused Jinja2 dependency.
""", encoding="utf-8")

(ROOT / "rollpig_core.py").write_text('''"""Small dependency-free helpers used by tests and future refactors."""\nfrom __future__ import annotations\n\nimport ipaddress\nimport re\n\n\ndef legacy_identity(value: str) -> str:\n    match = re.fullmatch(r"v2\\|[^|]+\\|(?:user|group)\\|(.*)", str(value or ""))\n    return match.group(1) if match else str(value or "")\n\ndef namespace_identity(platform: str, kind: str, value: str) -> str:\n    raw = str(value or "").strip()\n    if not raw or raw.startswith("v2|"):\n        return raw\n    safe_platform = re.sub(r"[^a-z0-9_.-]+", "-", str(platform or "unknown").lower()).strip("-") or "unknown"\n    if kind not in {"user", "group"}:\n        raise ValueError("kind must be user or group")\n    return f"v2|{safe_platform}|{kind}|{raw}"\n\ndef is_public_ip(value: str) -> bool:\n    ip = ipaddress.ip_address(value)\n    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)\n''', encoding="utf-8")

(ROOT / "tests").mkdir(exist_ok=True)
(ROOT / "tests" / "test_rollpig_core.py").write_text('''from rollpig_core import is_public_ip, legacy_identity, namespace_identity\n\n\ndef test_namespace_round_trip():\n    key = namespace_identity("Discord", "user", "123")\n    assert key == "v2|discord|user|123"\n    assert legacy_identity(key) == "123"\n\ndef test_namespace_is_idempotent():\n    key = "v2|qq|group|456"\n    assert namespace_identity("qq", "group", key) == key\n\ndef test_public_ip_filter():\n    assert is_public_ip("8.8.8.8")\n    assert not is_public_ip("127.0.0.1")\n    assert not is_public_ip("10.0.0.1")\n    assert not is_public_ip("169.254.169.254")\n''', encoding="utf-8")

(ROOT / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
(ROOT / ".github" / "workflows" / "ci.yml").write_text('''name: CI\n\non:\n  push:\n    branches: [main]\n  pull_request:\n\npermissions:\n  contents: read\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n      - run: python -m pip install --upgrade pip pytest pillow httpx\n      - run: python -m compileall -q main.py rollpig_core.py\n      - run: pytest -q\n''', encoding="utf-8")

print("audit fixes applied")
