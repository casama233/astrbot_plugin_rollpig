from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path.cwd()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor in {path}: {old!r}; got {count}")
    write(path, text.replace(old, new, 1))


# 1) Legacy command ownership: keep only the rich DailyReportMixin registration.
legacy = read("legacy_main.py")
legacy_daily = (
    '    @filter.command("猪圈日报", alias={"豬圈日報", "今日猪圈日报", "今日豬圈日報"})\n'
    '    async def pigsty_daily_report(self, event: AstrMessageEvent):\n'
)
if legacy.count(legacy_daily) != 1:
    raise RuntimeError("legacy daily-report command anchor changed")
legacy = legacy.replace(
    legacy_daily,
    '    async def _legacy_pigsty_daily_report(self, event: AstrMessageEvent):\n',
    1,
)
legacy = legacy.replace(
    '("/猪圈日报", "显示今日抽猪、被吃人数与随机「可怜被吃」"),',
    '("/猪圈日报", "显示完整统计海报与今日群聊称号"),',
    1,
)

# 2) Add a compatibility-safe command claim helper.
claim_marker = '    def get_at_ids(self, event: AstrMessageEvent) -> list[str]:\n'
claim_helper = '''    @staticmethod
    def _claim_command_event(event: AstrMessageEvent) -> None:
        """Claim a matched RollPig command so it cannot fall through to other plugins/LLM."""
        stopper = getattr(event, "stop_event", None)
        if callable(stopper):
            stopper()

'''
if claim_helper not in legacy:
    if legacy.count(claim_marker) != 1:
        raise RuntimeError("get_at_ids anchor changed")
    legacy = legacy.replace(claim_marker, claim_helper + claim_marker, 1)

# Insert claim calls into every command still registered by the legacy class.
def command_names(source: str) -> list[str]:
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            call = decorator if isinstance(decorator, ast.Call) else None
            func = call.func if call else decorator
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "command"
                and isinstance(func.value, ast.Name)
                and func.value.id == "filter"
            ):
                names.append(node.name)
                break
    return names


def add_claims(source: str) -> str:
    tree = ast.parse(source)
    insertions: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef) or node.name not in command_names(source):
            continue
        if not node.args.args or all(arg.arg != "event" for arg in node.args.args):
            raise RuntimeError(f"command handler {node.name} has no event argument")
        if not node.body:
            raise RuntimeError(f"empty command handler: {node.name}")
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            insert_after = first.end_lineno
        else:
            insert_after = node.lineno
        segment = ast.get_source_segment(source, node) or ""
        if "self._claim_command_event(event)" in segment:
            continue
        insertions.append((insert_after, "        self._claim_command_event(event)\n"))
    lines = source.splitlines(keepends=True)
    for line_no, addition in sorted(insertions, reverse=True):
        lines.insert(line_no, addition)
    return "".join(lines)

legacy = add_claims(legacy)

# 3) Repair historical/local PigHub records whose metadata survived but image bytes disappeared.
lock_anchor = '        self._ai_roast_copy_locks: dict[str, asyncio.Lock] = {}\n'
if '_pig_image_repair_locks' not in legacy:
    if legacy.count(lock_anchor) != 1:
        raise RuntimeError("AI roast lock anchor changed")
    legacy = legacy.replace(
        lock_anchor,
        lock_anchor + '        self._pig_image_repair_locks: dict[str, asyncio.Lock] = {}\n',
        1,
    )

send_anchor = '''    async def send_rendered_pig(
        self,
        event: AstrMessageEvent,
        pig_data: dict,
        user_id: str,
        intro: str = ". 这是你的今日小猪：",
        fallback_title: str = "今日小猪",
    ):
        """合成并发送小猪图片"""
'''
repair_method = '''    async def _repair_missing_pig_image(self, pig_data: dict) -> bool:
        """Best-effort restore of a missing local PigHub image from its trusted source URL."""
        pig_id = str(pig_data.get("id") or "").strip()
        source_url = str(pig_data.get("source_url") or "").strip()
        if not pig_id or not source_url:
            return False
        try:
            self._validate_pighub_image_url(source_url)
        except ValueError:
            return False

        # Avoid warning-only find_image_file calls while merely probing for repair.
        for ext in self.IMAGE_EXTENSIONS:
            if (self.custom_image_dir / f"{pig_id}.{ext}").exists():
                return False
        for directory in (self.resource_active_dir / "images", self.image_dir):
            for ext in self.IMAGE_EXTENSIONS:
                if (directory / f"{pig_id}.{ext}").exists():
                    return False

        lock = self._pig_image_repair_locks.setdefault(pig_id, asyncio.Lock())
        async with lock:
            for ext in self.IMAGE_EXTENSIONS:
                if (self.custom_image_dir / f"{pig_id}.{ext}").exists():
                    return False
            try:
                raw = await self._download_pighub_image(source_url)
                normalized = await asyncio.to_thread(self._normalise_image_bytes, raw)
                await asyncio.to_thread(self._write_custom_image, pig_id, normalized)
                logger.info(f"已从 PigHub 自动恢复缺失的小猪图片：{pig_id}")
                return True
            except Exception as exc:
                logger.warning(
                    f"PigHub 小猪图片自动恢复失败，继续使用无图降级：{pig_id} "
                    f"({self._describe_sync_error(exc)})"
                )
                return False

'''
if repair_method not in legacy:
    if legacy.count(send_anchor) != 1:
        raise RuntimeError("send_rendered_pig anchor changed")
    legacy = legacy.replace(send_anchor, repair_method + send_anchor, 1)

send_doc = '        """合成并发送小猪图片"""\n'
if '        await self._repair_missing_pig_image(pig_data)\n' not in legacy:
    pos = legacy.find(send_anchor)
    if pos < 0:
        raise RuntimeError("send_rendered_pig missing after repair insertion")
    body_pos = legacy.find(send_doc, pos)
    if body_pos < 0:
        raise RuntimeError("send_rendered_pig docstring missing")
    insert_at = body_pos + len(send_doc)
    legacy = (
        legacy[:insert_at]
        + '        await self._repair_missing_pig_image(pig_data)\n'
        + legacy[insert_at:]
    )

# 4) If an already-versioned cloud cache is corrupt, repair promptly after restart
# instead of waiting for the normal sync interval.
background_pattern = re.compile(
    r'    async def _background_resource_sync\(self\):\n.*?(?=    def _normalise_pighub_item\(self, raw\))',
    re.S,
)
background_replacement = '''    def _cloud_cache_needs_repair(self) -> bool:
        state = self._cloud_state()
        return bool(str(state.get("resource_version") or "")) and self._load_cloud_pigs() is None

    async def _background_resource_sync(self):
        try:
            damaged_cache = self._cloud_cache_needs_repair()
            await asyncio.sleep(5 if damaged_cache else random.randint(30, 120))
            while True:
                try:
                    state = self._cloud_state()
                    due = time.time() - float(state.get("synced_at") or 0)
                    if self._cloud_cache_needs_repair():
                        logger.warning("检测到云资源缓存不完整，立即尝试原子重新同步")
                        await self.sync_cloud_resources(force=True)
                    elif due >= self.resource_sync_interval_hours * 3600:
                        await self.sync_cloud_resources()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(f"今日小猪云资源后台同步失败，继续使用现有资源：{exc}")
                await asyncio.sleep(
                    min(3600, self.resource_sync_interval_hours * 3600)
                )
        except asyncio.CancelledError:
            pass

'''
legacy, count = background_pattern.subn(background_replacement, legacy, count=1)
if count != 1:
    raise RuntimeError("background resource sync block not found")
write("legacy_main.py", legacy)

# 5) The new rich daily-report command must claim its event as well.
daily = read("daily_report_feature.py")
daily_anchor = (
    '    async def pigsty_daily_report(self, event: AstrMessageEvent):\n'
    '        """Render the current group\'s rich report; manual views never sacrifice."""\n'
)
if daily.count(daily_anchor) != 1:
    raise RuntimeError("rich daily-report handler anchor changed")
if 'self._claim_command_event(event)' not in daily[daily.find(daily_anchor):daily.find(daily_anchor) + 500]:
    daily = daily.replace(
        daily_anchor,
        daily_anchor + '        self._claim_command_event(event)\n',
        1,
    )
write("daily_report_feature.py", daily)

# 6) Packaged CJK font is also the traditional/AI-copy fallback in v3.6.1.
main = read("main.py")
if 'def _init_traditional_font(self):' not in main:
    main = main.rstrip() + '''

    def _init_traditional_font(self):
        """Use the packaged full CJK face for traditional/AI copy before system fallbacks."""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "HanyiYongZiXiaoXiongMaoFan.ttf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "繁体兜底")
''' + "\n"
write("main.py", main)

# 7) Changelog the hotfix without versioning it yet; release step will roll this into v3.6.1.
changelog = read("CHANGELOG.md")
old_unreleased = "## 未發佈\n\n- 暫無。\n"
new_unreleased = '''## 未發佈

### 修復

- 修復 `豬圈日報` 同時由 `daily_report_feature` 與 `legacy_main` 註冊造成 AstrBot 指令衝突；僅保留完整統計海報實作。
- RollPig 聊天指令在匹配後主動停止事件繼續傳播，避免 `/今日小豬` 等指令完成後仍落入其他插件或 LLM。
- AI 料理／繁體文案優先使用發行包內 `荆南麦圆体.otf`，不再因缺少舊的獨立繁體字體而誤用 Pillow 預設字體。
- 當歷史／本地 PigHub 小豬仍保有可信 `source_url` 但圖片檔遺失時，發送前會安全地重新下載、校驗並恢復本地圖片；失敗仍維持既有無圖降級。
- 已有版本狀態但本地 cloud cache 圖片不完整時，插件重啟後會提前嘗試完整原子重同步，不必等待正常同步週期。
'''
if old_unreleased not in changelog:
    raise RuntimeError("CHANGELOG unreleased anchor changed")
changelog = changelog.replace(old_unreleased, new_unreleased, 1)
write("CHANGELOG.md", changelog)

# 8) Add source/AST contract tests for the regression bundle.
test = '''from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _command_functions(source: str) -> list[ast.AsyncFunctionDef]:
    tree = ast.parse(source)
    result: list[ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            func = decorator.func if isinstance(decorator, ast.Call) else decorator
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "command"
                and isinstance(func.value, ast.Name)
                and func.value.id == "filter"
            ):
                result.append(node)
                break
    return result


def test_only_rich_daily_report_is_registered():
    legacy = _source("legacy_main.py")
    rich = _source("daily_report_feature.py")
    assert '@filter.command("猪圈日报"' not in legacy
    assert "async def _legacy_pigsty_daily_report" in legacy
    assert '"猪圈日报",' in rich
    assert "async def pigsty_daily_report" in rich


def test_all_rollpig_command_handlers_claim_the_event():
    legacy = _source("legacy_main.py")
    functions = _command_functions(legacy)
    assert functions
    missing = []
    for node in functions:
        segment = ast.get_source_segment(legacy, node) or ""
        if "self._claim_command_event(event)" not in segment:
            missing.append(node.name)
    assert missing == []
    rich = _source("daily_report_feature.py")
    daily = next(node for node in _command_functions(rich) if node.name == "pigsty_daily_report")
    assert "self._claim_command_event(event)" in (ast.get_source_segment(rich, daily) or "")


def test_traditional_font_prefers_packaged_cjk_face():
    main = _source("main.py")
    marker = "def _init_traditional_font(self):"
    assert marker in main
    section = main[main.index(marker):]
    assert 'self.font_dir / "荆南麦圆体.otf"' in section
    assert section.index("荆南麦圆体.otf") < section.index("HanyiYongZiXiaoXiongMaoFan.ttf")


def test_missing_pighub_image_has_safe_self_heal_path():
    legacy = _source("legacy_main.py")
    assert "async def _repair_missing_pig_image" in legacy
    assert 'pig_data.get("source_url")' in legacy
    assert "self._validate_pighub_image_url(source_url)" in legacy
    assert "await self._download_pighub_image(source_url)" in legacy
    assert "await asyncio.to_thread(self._write_custom_image, pig_id, normalized)" in legacy
    send = legacy[legacy.index("async def send_rendered_pig"):]
    assert "await self._repair_missing_pig_image(pig_data)" in send[:1000]


def test_corrupt_versioned_cloud_cache_is_repaired_early():
    legacy = _source("legacy_main.py")
    assert "def _cloud_cache_needs_repair" in legacy
    assert "self._load_cloud_pigs() is None" in legacy
    assert "await asyncio.sleep(5 if damaged_cache" in legacy
    assert "await self.sync_cloud_resources(force=True)" in legacy
'''
write("tests/test_v361_hotfix_contract.py", test)

# Final syntax and contract sanity before CI installs dependencies.
for path in ("legacy_main.py", "daily_report_feature.py", "main.py", "tests/test_v361_hotfix_contract.py"):
    ast.parse(read(path), filename=path)

legacy_final = read("legacy_main.py")
if '@filter.command("猪圈日报"' in legacy_final:
    raise RuntimeError("legacy daily report is still registered")
if "async def pigsty_daily_report" not in read("daily_report_feature.py"):
    raise RuntimeError("rich daily report registration disappeared")
