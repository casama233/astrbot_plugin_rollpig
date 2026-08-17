from __future__ import annotations

import re
from pathlib import Path

legacy = Path("legacy_main.py")
text = legacy.read_text(encoding="utf-8")

relative_anchor = "    from .roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\n"
relative_import = '''    from .roast_copy import (\n        ai_candidate_key,\n        decode_ai_candidates,\n        encode_ai_candidates,\n        load_roast_copy_catalog,\n        select_ai_candidate,\n        select_local_roast_copy,\n        validate_roast_copy_catalog,\n    )\n'''
if "from .roast_copy import" not in text:
    assert relative_anchor in text
    text = text.replace(relative_anchor, relative_anchor + relative_import)

fallback_anchor = "    from roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\n"
fallback_import = '''    from roast_copy import (\n        ai_candidate_key,\n        decode_ai_candidates,\n        encode_ai_candidates,\n        load_roast_copy_catalog,\n        select_ai_candidate,\n        select_local_roast_copy,\n        validate_roast_copy_catalog,\n    )\n'''
if "from roast_copy import (" not in text:
    assert fallback_anchor in text
    text = text.replace(fallback_anchor, fallback_anchor + fallback_import)

path_anchor = '        self.ai_roast_copies_path = self.plugin_data_dir / "ai_roast_copies.json"\n'
path_add = path_anchor + '        self.roast_copy_builtin_path = self.res_dir / "roast_copy.json"\n        self.roast_copy_usage_path = self.plugin_data_dir / "roast_copy_usage.json"\n'
if "self.roast_copy_builtin_path" not in text:
    assert path_anchor in text
    text = text.replace(path_anchor, path_add)

init_anchor = '''        self.ai_roast_copies = self._runtime_document(\n            "ai_roast_copies", self.ai_roast_copies_path, ai_default\n        )\n'''
init_add = init_anchor + '''        self.roast_copy_usage = self.load_json(\n            self.roast_copy_usage_path, {"contexts": {}}\n        )\n        if not isinstance(self.roast_copy_usage, dict):\n            self.roast_copy_usage = {"contexts": {}}\n'''
if "self.roast_copy_usage = self.load_json" not in text:
    assert init_anchor in text
    text = text.replace(init_anchor, init_add)

helper_anchor = '''    def _save_ai_roast_copies(self) -> None:\n        self.save_json(self.ai_roast_copies_path, self.ai_roast_copies)\n'''
helpers = '''    @staticmethod\n    def _roast_copy_usage_key(event, group_id: str, sender_id: str) -> str:\n        return f"group:{group_id}" if group_id else f"dm:{sender_id}"\n\n    def _recent_roast_copy_keys(self, event: AstrMessageEvent) -> list[str]:\n        context_key = self._roast_copy_usage_key(\n            event, self._event_group_id(event), self._event_sender_id(event)\n        )\n        contexts = self.roast_copy_usage.get("contexts")\n        if not isinstance(contexts, dict):\n            contexts = {}\n            self.roast_copy_usage["contexts"] = contexts\n        values = contexts.get(context_key)\n        return [str(item) for item in values[-24:]] if isinstance(values, list) else []\n\n    def _remember_roast_copy_key(self, event: AstrMessageEvent, key: str) -> None:\n        key = str(key or "").strip()\n        if not key:\n            return\n        context_key = self._roast_copy_usage_key(\n            event, self._event_group_id(event), self._event_sender_id(event)\n        )\n        with self._data_lock:\n            contexts = self.roast_copy_usage.setdefault("contexts", {})\n            if not isinstance(contexts, dict):\n                contexts = {}\n                self.roast_copy_usage["contexts"] = contexts\n            recent = contexts.get(context_key)\n            recent = [str(item) for item in recent] if isinstance(recent, list) else []\n            recent.append(key)\n            contexts[context_key] = recent[-24:]\n            self.save_json(self.roast_copy_usage_path, self.roast_copy_usage)\n\n    def _effective_roast_copy_catalog(self) -> dict[str, object]:\n        remote = self.resource_active_dir / "roast_copy.json"\n        if remote.is_file():\n            try:\n                return load_roast_copy_catalog(remote)\n            except Exception as exc:\n                logger.warning(f"远端烤猪文案包无效，回退内置猪话：{exc}")\n        return load_roast_copy_catalog(self.roast_copy_builtin_path)\n\n    def _select_local_roast_copy_for_event(\n        self, event: AstrMessageEvent, pig: dict\n    ) -> dict[str, str]:\n        return select_local_roast_copy(\n            self._effective_roast_copy_catalog(),\n            pig_name=str(pig.get("name") or "小猪"),\n            recent_keys=self._recent_roast_copy_keys(event),\n        )\n\n    def _select_ai_bundle(self, event: AstrMessageEvent, payload: object) -> str | None:\n        return select_ai_candidate(\n            decode_ai_candidates(payload),\n            recent_keys=self._recent_roast_copy_keys(event),\n        )\n\n    def _select_ai_from_recent(\n        self, event: AstrMessageEvent, recent: dict\n    ) -> str | None:\n        candidates: list[str] = []\n        for payload in recent.values() if isinstance(recent, dict) else ():\n            candidates.extend(decode_ai_candidates(payload))\n        return select_ai_candidate(\n            candidates, recent_keys=self._recent_roast_copy_keys(event)\n        )\n\n'''
if "def _effective_roast_copy_catalog" not in text:
    assert helper_anchor in text
    text = text.replace(helper_anchor, helpers + helper_anchor)

# AI selection: preserve the existing one-call-per-pig-per-day ownership model,
# but decode each day's content as up to four candidates.
text = text.replace(
    '            return await self._generate_ai_roast_copy(event, pig)\n',
    '            generated = await self._generate_ai_roast_copy(event, pig)\n            return self._select_ai_bundle(event, generated)\n',
    1,
)
text = text.replace(
    '                    return random.choice(list(recent.values()))\n',
    '                    return self._select_ai_from_recent(event, recent)\n',
)
text = text.replace(
    '                    return random.choice(list(recent.values())) if recent else None\n',
    '                    return self._select_ai_from_recent(event, recent)\n',
)
text = text.replace(
    '                    return str(completed.get("content") or generated)\n',
    '                    return self._select_ai_bundle(event, completed.get("content") or generated)\n',
)
text = text.replace(
    '                return random.choice(list(recent.values())) if recent else None\n',
    '                return self._select_ai_from_recent(event, recent)\n',
)
text = text.replace(
    '                    return random.choice(list(recent.values()))\n',
    '                    return self._select_ai_from_recent(event, recent)\n',
)
text = text.replace(
    '                    return random.choice(list(recent.values())) if recent else None\n',
    '                    return self._select_ai_from_recent(event, recent)\n',
)
text = text.replace(
    '                return generated\n            return random.choice(list(recent.values())) if recent else None\n',
    '                return self._select_ai_bundle(event, generated)\n            return self._select_ai_from_recent(event, recent)\n',
)

pattern = re.compile(
    r"    async def _generate_ai_roast_copy\(\n        self, event: AstrMessageEvent, pig: dict\n    \) -> str \| None:\n.*?\n    async def _generate_pig_draft\(",
    re.DOTALL,
)
replacement = '''    async def _generate_ai_roast_copy(\n        self, event: AstrMessageEvent, pig: dict\n    ) -> str | None:\n        """Generate one four-candidate piggish bundle; old single-line caches remain readable."""\n        if not self.enable_ai_roast_copy:\n            return None\n        prompt = (\n            "你是‘今日小猪’猪圈宇宙的后厨总编，不是普通美食博主。"\n            "一次生成4条彼此明显不同的中文烤猪卡文案，并只输出JSON字符串数组。"\n            "每条18-42个汉字，必须有猪言猪语和反差包袱，自然带入至少一个猪圈世界观元素："\n            "猪圈、猪籍、猪运、返场、EX、Charge、烤架、保底、拱、哼哼、后厨。"\n            "四条分别偏向：猪圈黑话、抽卡命运、后厨判词、哲学反转；不要只是换同义词。"\n            "禁止写成普通美食广告；除非用于反转，不要使用‘外焦里嫩、香气扑鼻、火候刚好、入口即化、肥而不腻’套话。"\n            f"小猪名：{str(pig.get('name') or '小猪')[:30]}；"\n            f"描述：{str(pig.get('description') or '')[:100]}；"\n            f"图鉴文案：{str(pig.get('analysis') or '')[:180]}。"\n            "只调侃虚构小猪、猪圈日常和抽卡命运；禁止针对真实用户或群体，禁止仇恨、性内容、自残、血腥和真实暴力细节；"\n            "不写真实烹饪步骤，不解释笑点，不加标题或Markdown。"\n            "输出示例格式：[\\\"第一条\\\",\\\"第二条\\\",\\\"第三条\\\",\\\"第四条\\\"]"\n        )\n        try:\n            response = None\n            get_provider_id = getattr(self.context, "get_current_chat_provider_id", None)\n            llm_generate = getattr(self.context, "llm_generate", None)\n            umo = getattr(event, "unified_msg_origin", None)\n            if callable(get_provider_id) and callable(llm_generate) and umo:\n                provider_id = await get_provider_id(umo=umo)\n                if provider_id:\n                    response = await asyncio.wait_for(\n                        llm_generate(chat_provider_id=provider_id, prompt=prompt),\n                        timeout=self.ai_generation_timeout,\n                    )\n            if response is None:\n                provider = self.context.get_using_provider()\n                if provider is None:\n                    return None\n                response = await asyncio.wait_for(\n                    provider.text_chat(\n                        prompt=prompt,\n                        session_id=None,\n                        contexts=[],\n                        image_urls=[],\n                        func_tool=None,\n                        system_prompt="",\n                    ),\n                    timeout=self.ai_generation_timeout,\n                )\n            raw = str(getattr(response, "completion_text", "") or "").strip()\n            raw = re.sub(\n                r"^\\s*```(?:json)?\\s*|\\s*```\\s*$", "", raw, flags=re.IGNORECASE\n            )\n            match = re.search(r"\\[[\\s\\S]*\\]", raw)\n            if not match:\n                return None\n            try:\n                parsed = json.loads(match.group(0))\n            except json.JSONDecodeError:\n                return None\n            if not isinstance(parsed, list):\n                return None\n            candidates = [\n                item\n                for item in decode_ai_candidates(\n                    json.dumps(parsed, ensure_ascii=False)\n                )\n                if 8 <= len(item) <= 64\n            ]\n            if len(candidates) < 2:\n                return None\n            return encode_ai_candidates(candidates[:4])\n        except Exception as exc:\n            logger.warning(f"AI 烤猪文案生成失败，已回退本地猪话：{exc}")\n            return None\n\n    async def _generate_pig_draft('''
text, count = pattern.subn(replacement, text, count=1)
assert count == 1, "AI roast function replacement failed"

send_pattern = re.compile(
    r"    async def _send_roast_card\(\n        self, event: AstrMessageEvent, pig: dict, user_id: str\n    \) -> bool:\n.*?\n    def _record_roast_outcome_event\(",
    re.DOTALL,
)
send_replacement = '''    async def _send_roast_card(\n        self, event: AstrMessageEvent, pig: dict, user_id: str\n    ) -> bool:\n        output = None\n        try:\n            ai_copy = await self._get_ai_roast_copy(event, pig)\n            local_copy = (\n                None if ai_copy else self._select_local_roast_copy_for_event(event, pig)\n            )\n            output = await asyncio.to_thread(\n                self.render_roast_image, pig, user_id, ai_copy, local_copy\n            )\n            await event.send(event.image_result(str(output.absolute())))\n            used_key = (\n                ai_candidate_key(ai_copy)\n                if ai_copy\n                else str((local_copy or {}).get("key") or "")\n            )\n            self._remember_roast_copy_key(event, used_key)\n            return True\n        except Exception as exc:\n            logger.error(f"生成烤猪料理卡失败：{exc}", exc_info=True)\n            await event.send(event.plain_result("🧯 菜做好了，但料理卡画师把锅掀了。图片生成失败，请稍后再试。"))\n            return False\n        finally:\n            if output:\n                output.unlink(missing_ok=True)\n\n    def _record_roast_outcome_event('''
text, count = send_pattern.subn(send_replacement, text, count=1)
assert count == 1, "send roast card replacement failed"

render_pattern = re.compile(
    r"    def render_roast_image\(\n        self, pig: dict, user_id: str, ai_copy: str \| None = None\n    \) -> Path:\n.*?\n    def render_help_image\(",
    re.DOTALL,
)
render_replacement = '''    def render_roast_image(\n        self,\n        pig: dict,\n        user_id: str,\n        ai_copy: str | None = None,\n        local_copy: dict[str, str] | None = None,\n    ) -> Path:\n        copy = ai_copy or str((local_copy or {}).get("copy") or "")\n        body_font = (\n            self._ai_copy_font(copy, 26)\n            if ai_copy\n            else self.font_regular.font_variant(size=26)\n        )\n        return render_roast_card_image(\n            pig,\n            user_id=str(user_id),\n            draw_date=self._today().isoformat(),\n            ai_copy=ai_copy,\n            local_copy=local_copy,\n            palette=self._image_palette(),\n            font_bold=self.font_bold,\n            body_font=body_font,\n            image_resolver=self.find_image_file,\n        )\n\n    def render_help_image('''
text, count = render_pattern.subn(render_replacement, text, count=1)
assert count == 1, "render roast method replacement failed"

# Resource Protocol v1 optional roast_copy member.
if 'roast_copy_meta = manifest.get("roast_copy")' not in text:
    text = text.replace(
        '                    ex_meta = manifest.get("ex_variants")\n',
        '                    ex_meta = manifest.get("ex_variants")\n                    roast_copy_meta = manifest.get("roast_copy")\n',
        1,
    )
    text = text.replace(
        '                    if ex_meta is not None and not isinstance(ex_meta, dict):\n                        raise ValueError("manifest ex_variants 必须是对象")\n',
        '                    if ex_meta is not None and not isinstance(ex_meta, dict):\n                        raise ValueError("manifest ex_variants 必须是对象")\n                    if roast_copy_meta is not None and not isinstance(roast_copy_meta, dict):\n                        raise ValueError("manifest roast_copy 必须是对象")\n',
        1,
    )
    text = text.replace(
        '                        and (\n                            not isinstance(manifest.get("ex_variants"), dict)\n                            or (\n                                self.resource_active_dir / "pig_ex_variants.json"\n                            ).is_file()\n                        )\n',
        '                        and (\n                            not isinstance(manifest.get("ex_variants"), dict)\n                            or (\n                                self.resource_active_dir / "pig_ex_variants.json"\n                            ).is_file()\n                        )\n                        and (\n                            not isinstance(manifest.get("roast_copy"), dict)\n                            or (self.resource_active_dir / "roast_copy.json").is_file()\n                        )\n',
        1,
    )
    text = text.replace(
        '                    if isinstance(ex_meta, dict):\n                        declared_total += int(ex_meta.get("size") or 0)\n',
        '                    if isinstance(roast_copy_meta, dict):\n                        declared_total += int(roast_copy_meta.get("size") or 0)\n                    if isinstance(ex_meta, dict):\n                        declared_total += int(ex_meta.get("size") or 0)\n',
        1,
    )
    pig_block = '''                    pigs = self._validate_pig_records(\n                        json.loads(pig_raw.decode("utf-8-sig"))\n                    )\n                    pig_ids = {item["id"] for item in pigs}\n'''
    roast_block = pig_block + '''                    roast_copy_raw = b""\n                    if isinstance(roast_copy_meta, dict):\n                        roast_copy_raw = await self._download_manifest_item(\n                            client,\n                            self.resource_manifest_url,\n                            roast_copy_meta,\n                            256 * 1024,\n                        )\n                        validate_roast_copy_catalog(\n                            json.loads(roast_copy_raw.decode("utf-8-sig"))\n                        )\n'''
    assert pig_block in text
    text = text.replace(pig_block, roast_block, 1)
    text = text.replace(
        '                    (staging / "pig.json").write_bytes(pig_raw)\n',
        '                    (staging / "pig.json").write_bytes(pig_raw)\n                    if roast_copy_raw:\n                        (staging / "roast_copy.json").write_bytes(roast_copy_raw)\n',
        1,
    )
    text = text.replace(
        '                    package_total = len(pig_raw) + len(ex_raw)\n',
        '                    package_total = len(pig_raw) + len(ex_raw) + len(roast_copy_raw)\n',
        1,
    )

legacy.write_text(text, encoding="utf-8")

main = Path("main.py")
text = main.read_text(encoding="utf-8")
old = '''    def render_roast_image(self, pig, user_id, ai_copy=None):\n        return self._run_with_render_slot(super().render_roast_image, pig, user_id, ai_copy)\n'''
new = '''    def render_roast_image(self, pig, user_id, ai_copy=None, local_copy=None):\n        return self._run_with_render_slot(\n            super().render_roast_image, pig, user_id, ai_copy, local_copy\n        )\n'''
assert old in text
text = text.replace(old, new, 1)
main.write_text(text, encoding="utf-8")

changelog = Path("CHANGELOG.md")
text = changelog.read_text(encoding="utf-8")
marker = "## 未發佈\n\n"
entry = (
    "- 重做烤豬文案系統：內置 32 菜名 × 79 條豬言豬語正文（2,528 組），並支持 Resource Protocol v1 可選 `roast_copy` 遠端同步；同群最近 24 次文案組合防重複。\n"
    "- AI 烤豬文案升級為豬圈世界觀 prompt：每隻豬每天仍只調用模型一次，但一次生成最多 4 條候選，七日池最多 28 條；兼容舊單條快取且加入近期防重複。\n"
)
if entry.splitlines()[0] not in text:
    assert marker in text
    text = text.replace(marker, marker + entry, 1)
    changelog.write_text(text, encoding="utf-8")

doc = Path("docs/gameplay/roast-outcomes.md")
text = doc.read_text(encoding="utf-8")
section = '''\n## 烤豬卡文案來源\n\n料理卡不再只靠少量固定菜名。插件內置一份可離線使用的「豬言豬語」文案包，菜名與正文獨立組合；同一群最近使用過的組合會暫時避開，減少短時間撞文案。\n\n官方 Resource Protocol v1 manifest 可選發布 `roast_copy` 文案包。同步成功時優先使用遠端包；遠端未提供、下載失敗或校驗不通過時，仍使用插件內置包，不影響抽豬與烤豬主流程。\n\n啟用 AI 料理文案後，每隻豬每天仍最多發起一次模型請求，但單次要求生成最多 4 條不同候選，並把最近七天候選合併使用；舊版本已保存的單條 AI 文案仍可直接讀取。AI 文案與本地文案共用近期防重複記錄。\n'''
if "## 烤豬卡文案來源" not in text:
    doc.write_text(text.rstrip() + "\n" + section, encoding="utf-8")
