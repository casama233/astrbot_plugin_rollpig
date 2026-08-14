from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start_index] + replacement + text[end_index:]


ROAST_SERVICE = '''from __future__ import annotations

import math
import random
from typing import Any, Mapping

try:
    from ..rollpig_core import special_pig_state
except ImportError:  # pragma: no cover - direct module loading compatibility
    from rollpig_core import special_pig_state


class RoastService:
    """Pure eligibility, outcome and copy policy for roast/eat actions."""

    GROUP_ROAST_OUTCOMES = ("success", "escape", "backlash")
    GROUP_ROAST_WEIGHTS = (60, 30, 10)

    @staticmethod
    def _name(pig: Mapping[str, Any] | None) -> str:
        value = pig or {}
        return str(value.get("name") or value.get("id") or "特殊形态").strip()

    def roast_block_reason(
        self, pig: Mapping[str, Any] | None, *, subject: str = "target"
    ) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        actor = subject == "actor"
        if state == "missing":
            return "你今天还没有抽取小猪。" if actor else "对方今天还没有抽取小猪。"
        name = self._name(pig)
        if state == "human":
            if actor:
                return "你今天是「人类」：只能围观，不能参与猪圈料理。"
            return "对方今天是「人类」：猪圈劳动合同不支持把人送上烤架。"
        if state == "eaten":
            if actor:
                return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
            return "对方今天是「吃掉了」：盘子都空了，不能继续参与烧烤流程。"
        if actor:
            return f"你今天是「{name}」：已经上桌了，不能再次参与烧烤。"
        return f"对方今天是「{name}」：已经是熟食，不能再上一次烤架。"

    def eat_actor_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        if state == "missing":
            return "你今天还没有抽取小猪，不能发动吃群友。"
        name = self._name(pig)
        if state == "human":
            return "你今天是「人类」：猪圈菜单不允许人类发动吃群友。"
        if state == "eaten":
            return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
        return f"你今天是「{name}」：已经上桌了，暂时不能去吃群友。"

    def eat_target_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state in {"normal", "cooked"}:
            return None
        if state == "missing":
            return "对方今天还没有抽取小猪。"
        if state == "human":
            return "对方今天是「人类」：吃人不在猪圈菜单里。"
        return "对方今天已经是「吃掉了」：盘子空了，不能再吃一次。"

    def eat_success_message(self, pig: Mapping[str, Any]) -> str:
        name = self._name(pig)
        action = (
            "开袋即食成功"
            if special_pig_state(dict(pig)) == "cooked"
            else "吃群友成功"
        )
        return f" 🍴 {action}，「{name}」被吃掉了；明天抽猪可能失败。"

    def choose_group_roast_outcome(self, *, bypass: bool = False, rng=None) -> str:
        """Return the existing 60/30/10 roast outcome from one policy source."""
        if bypass:
            return "success"
        chooser = rng or random
        return str(
            chooser.choices(
                self.GROUP_ROAST_OUTCOMES,
                weights=self.GROUP_ROAST_WEIGHTS,
                k=1,
            )[0]
        )

    @staticmethod
    def format_cooldown(seconds: int) -> str:
        seconds = max(1, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes = max(1, math.ceil(remainder / 60)) if remainder else 0
        return f"{hours} 小时 {minutes} 分" if hours else f"{minutes} 分钟"

    @staticmethod
    def roast_protection_message(count: int) -> str:
        return (
            f"🛡️ 对方昨天被烤了 {count} 次，今天已获得猪圈保护。"
            "普通烧烤会被拦截；后门强制模式仍可突破保护。"
        )
'''
write("services/roast_service.py", ROAST_SERVICE)


ROAST_RENDERER = '''from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Mapping

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from .common import ImageResolver, fit_card_image, get_text_size


RECIPES = (
    ("蜜汁脆皮", "外脆里嫩，甜度刚好，今日烦恼全部烤化。"),
    ("炭火蒜香", "火候拉满，蒜香扑鼻，猪圈厨神认证出品。"),
    ("椒盐黄金", "咸香酥脆，一口下去好运值直接加满。"),
    ("慢烤照烧", "低温慢烤锁住快乐，再刷上一层闪亮好运。"),
    ("香草熔岩", "表面平静，内心滚烫，是今天最有戏的小猪料理。"),
)


def render_roast_card(
    pig: Mapping[str, object],
    *,
    user_id: str,
    draw_date: str,
    ai_copy: str | None,
    palette: Mapping[str, object],
    font_bold: ImageFont.FreeTypeFont,
    body_font: ImageFont.FreeTypeFont,
    image_resolver: ImageResolver,
) -> Path:
    """Render the existing roast dish card from explicit view inputs only."""
    seed = f"{user_id}:{draw_date}:{pig.get('id')}"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    recipe, copy = RECIPES[digest[0] % len(RECIPES)]
    if ai_copy:
        recipe = "AI 私房"
        copy = ai_copy

    canvas = PILImage.new("RGB", (800, 870), palette["roast_canvas"])
    draw = ImageDraw.Draw(canvas)
    title_font = font_bold.font_variant(size=52)
    name_font = font_bold.font_variant(size=38)
    draw.rounded_rectangle(
        (34, 28, 766, 830),
        38,
        fill=palette["roast_surface"],
        outline=palette["roast_outline"],
        width=5,
    )
    source = "AI 料理" if ai_copy else "本地料理"
    draw.text(
        (64, 58),
        f"今日烤猪 · {source}",
        font=title_font,
        fill=palette["roast_title"],
    )

    pig_id = str(pig.get("id") or "")
    path = image_resolver(pig_id, None)
    if path:
        thumb = fit_card_image(path, (430, 430))
        warm = PILImage.new("RGBA", thumb.size, (232, 91, 38, 45))
        thumb = PILImage.alpha_composite(thumb, warm)
        canvas.paste(thumb.convert("RGB"), (185, 150))

    dish_name = f"{recipe}{pig.get('name', '小猪')}"
    dish_name = dish_name if len(dish_name) <= 16 else dish_name[:15] + "…"
    dish_w, _ = get_text_size(dish_name, name_font)
    draw.text(
        ((800 - dish_w) // 2, 625),
        dish_name,
        font=name_font,
        fill=palette["roast_title"],
    )

    lines: list[str] = []
    current = ""
    for char in copy:
        candidate = current + char
        if get_text_size(candidate, body_font)[0] > 640:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip("…") + "…"
    for index, line in enumerate(lines):
        line_w, _ = get_text_size(line, body_font)
        draw.text(
            ((800 - line_w) // 2, 705 + index * 42),
            line,
            font=body_font,
            fill=palette["roast_body"],
        )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output = Path(tmp.name)
    canvas.save(output, "PNG", optimize=True)
    return output
'''
write("renderers/roast.py", ROAST_RENDERER)


# Export the roast renderer.
renderers_init = read("renderers/__init__.py")
renderers_init = replace_once(
    renderers_init,
    "from .pig_card import PigCardLayout, render_pig_card\n",
    "from .pig_card import PigCardLayout, render_pig_card\nfrom .roast import render_roast_card\n",
    "renderers import",
)
renderers_init = replace_once(
    renderers_init,
    '    "render_pigsty",\n    "render_weekly_summary",\n',
    '    "render_pigsty",\n    "render_roast_card",\n    "render_weekly_summary",\n',
    "renderers __all__",
)
write("renderers/__init__.py", renderers_init)


# Route legacy roast drawing through the renderer and centralize normal roast policy.
legacy = read("legacy_main.py")
legacy = legacy.replace(
    "        render_pigsty,\n        render_weekly_summary as render_weekly_summary_image,\n",
    "        render_pigsty,\n        render_roast_card as render_roast_card_image,\n        render_weekly_summary as render_weekly_summary_image,\n",
)
if legacy.count("render_roast_card as render_roast_card_image") != 2:
    raise RuntimeError("legacy renderer import: expected package + fallback imports")

old_protection = '''    def _roast_protection_message(self, count: int) -> str:\n        return (\n            f"🛡️ 对方昨天被烤了 {count} 次，今天已获得猪圈保护。"\n            "普通烧烤会被拦截；后门强制模式仍可突破保护。"\n        )\n'''
new_protection = '''    def _roast_protection_message(self, count: int) -> str:\n        return self.roast_service.roast_protection_message(count)\n'''
legacy = replace_once(legacy, old_protection, new_protection, "protection facade")

old_cooldown = '''    @staticmethod\n    def _format_cooldown(seconds: int) -> str:\n        seconds = max(1, int(seconds))\n        hours, remainder = divmod(seconds, 3600)\n        minutes = max(1, math.ceil(remainder / 60)) if remainder else 0\n        return f"{hours} 小时 {minutes} 分" if hours else f"{minutes} 分钟"\n'''
new_cooldown = '''    @staticmethod\n    def _format_cooldown(seconds: int) -> str:\n        return RoastService.format_cooldown(seconds)\n'''
legacy = replace_once(legacy, old_cooldown, new_cooldown, "cooldown facade")

normal_roast = '''    def _record_roast_outcome_event(\n        self,\n        kind: str,\n        group_id: str,\n        *,\n        actor_id: str,\n        target_id: str,\n        victim_id: str = "",\n    ) -> None:\n        """Extension hook; report/event mixins can observe without owning the flow."""\n        del kind, group_id, actor_id, target_id, victim_id\n\n    async def _roast_group_target(\n        self,\n        event: AstrMessageEvent,\n        target_id: str,\n        *,\n        bypass: bool = False,\n    ) -> None:\n        """Execute the single normal group-roast flow; mixins observe via hooks."""\n        actor_id = self._event_sender_id(event)\n        group_id = self._event_group_id(event)\n        if not group_id:\n            await event.send(event.plain_result("烤群友只能在群聊中使用。"))\n            return\n        if not target_id:\n            await event.send(event.plain_result("请 @ 一位群友，或回复对方的消息后再使用。"))\n            return\n        if target_id == actor_id:\n            await event.send(event.plain_result("不能对自己使用烤群友；请用 /今日烤猪。"))\n            return\n        target_pig = self._get_daily_pig(target_id, self._today())\n        reason = self._roast_block_reason(target_pig)\n        if reason:\n            await event.send(event.plain_result(reason))\n            return\n        protected, roast_count = await self._roast_protection_status(\n            group_id, target_id\n        )\n        if protected and not bypass:\n            await event.send(\n                event.plain_result(self._roast_protection_message(roast_count))\n            )\n            return\n        if not bypass:\n            remaining = await self._consume_group_roast_cooldown(\n                group_id, actor_id\n            )\n            if remaining:\n                await event.send(\n                    event.plain_result(\n                        f"烤架还在降温，请 {self._format_cooldown(remaining)} 后再试。"\n                    )\n                )\n                return\n\n        result = self.roast_service.choose_group_roast_outcome(bypass=bypass)\n        if result == "escape":\n            self._record_roast_outcome_event(\n                "roast_escape",\n                group_id,\n                actor_id=actor_id,\n                target_id=target_id,\n            )\n            await event.send(\n                event.plain_result("💨 对方一溜烟逃走了，烤架上只剩一阵风。")\n            )\n            return\n        if result == "backlash":\n            actor_pig = self._get_daily_pig(actor_id, self._today())\n            actor_reason = self._roast_block_reason(actor_pig, subject="actor")\n            victim_id = "" if actor_reason else actor_id\n            self._record_roast_outcome_event(\n                "roast_backlash",\n                group_id,\n                actor_id=actor_id,\n                target_id=target_id,\n                victim_id=victim_id,\n            )\n            if actor_reason:\n                await event.send(\n                    event.plain_result(\n                        "🔥 烤架反噬了！但你今天没有可料理的小猪，侥幸躲过一劫。"\n                    )\n                )\n                return\n            await event.send(\n                event.plain_result("🔥 烤架反噬！这次轮到你的今日小猪上桌。")\n            )\n            await self._record_group_roast(group_id, actor_id)\n            await self._send_roast_card(event, actor_pig, actor_id)\n            return\n\n        self._record_roast_outcome_event(\n            "roast_success",\n            group_id,\n            actor_id=actor_id,\n            target_id=target_id,\n            victim_id=target_id,\n        )\n        prefix = "🔥 后门生效，" if bypass else "🔥 烧烤成功，"\n        await event.send(\n            event.plain_result(f"{prefix}对方今天的小猪已被端上料理台。")\n        )\n        await self._record_group_roast(group_id, target_id)\n        await self._send_roast_card(event, target_pig, target_id)\n\n'''
legacy = replace_between(
    legacy,
    "    async def _roast_group_target(\n",
    "    async def _eat_group_target(\n",
    normal_roast,
    "legacy roast flow",
)

roast_facade = '''    def render_roast_image(\n        self, pig: dict, user_id: str, ai_copy: str | None = None\n    ) -> Path:\n        copy = ai_copy or ""\n        body_font = (\n            self._ai_copy_font(copy, 26)\n            if ai_copy\n            else self.font_regular.font_variant(size=26)\n        )\n        return render_roast_card_image(\n            pig,\n            user_id=str(user_id),\n            draw_date=self._today().isoformat(),\n            ai_copy=ai_copy,\n            palette=self._image_palette(),\n            font_bold=self.font_bold,\n            body_font=body_font,\n            image_resolver=self.find_image_file,\n        )\n\n'''
legacy = replace_between(
    legacy,
    "    def render_roast_image(\n",
    "    def render_help_image(\n",
    roast_facade,
    "roast renderer facade",
)
write("legacy_main.py", legacy)


# Daily report observes normal roast outcomes instead of duplicating the whole flow.
daily = read("daily_report_feature.py")
daily_hook = '''    def _record_roast_outcome_event(\n        self,\n        kind: str,\n        group_id: str,\n        *,\n        actor_id: str,\n        target_id: str,\n        victim_id: str = "",\n    ) -> None:\n        """Observe the base roast flow while preserving report-enable semantics."""\n        self._record_daily_report_event(\n            group_id,\n            kind,\n            actor_id=actor_id,\n            target_id=target_id,\n            victim_id=victim_id,\n        )\n\n'''
daily = replace_between(
    daily,
    "    async def _roast_group_target(\n",
    "    async def pigsty_daily_report(\n",
    daily_hook,
    "daily report roast observer",
)
write("daily_report_feature.py", daily)


# Reservation settlement uses the exact same outcome policy as normal roasts.
reservation = read("roast_reservation_feature.py")
reservation = replace_once(
    reservation,
    "import random\n",
    "",
    "reservation random import",
)
reservation = replace_once(
    reservation,
    '''        outcome = random.choices(\n            ["success", "escape", "backlash"], weights=[60, 30, 10], k=1\n        )[0]\n''',
    '''        outcome = self.roast_service.choose_group_roast_outcome()\n''',
    "reservation outcome policy",
)
write("roast_reservation_feature.py", reservation)


# Renderer + roast policy contracts.
write(
    "tests/test_roast_policy.py",
    '''from services import RoastService\n\n\nclass FakeChoices:\n    def __init__(self, result: str):\n        self.result = result\n        self.calls = []\n\n    def choices(self, population, *, weights, k):\n        self.calls.append((tuple(population), tuple(weights), k))\n        return [self.result]\n\n\ndef test_group_roast_outcome_keeps_single_60_30_10_policy():\n    service = RoastService()\n    rng = FakeChoices("backlash")\n    assert service.choose_group_roast_outcome(rng=rng) == "backlash"\n    assert rng.calls == [(\n        ("success", "escape", "backlash"),\n        (60, 30, 10),\n        1,\n    )]\n\n\ndef test_bypass_forces_success_without_touching_rng():\n    service = RoastService()\n    rng = FakeChoices("escape")\n    assert service.choose_group_roast_outcome(bypass=True, rng=rng) == "success"\n    assert rng.calls == []\n\n\ndef test_roast_copy_helpers_preserve_existing_text_contract():\n    service = RoastService()\n    assert service.format_cooldown(1) == "1 分钟"\n    assert service.format_cooldown(3600) == "1 小时 0 分"\n    assert service.format_cooldown(3661) == "1 小时 2 分"\n    assert service.roast_protection_message(3) == (\n        "🛡️ 对方昨天被烤了 3 次，今天已获得猪圈保护。"\n        "普通烧烤会被拦截；后门强制模式仍可突破保护。"\n    )\n''',
)

write(
    "tests/test_roast_boundary_contract.py",
    '''import ast\nfrom pathlib import Path\n\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef _class_method(path: str, class_name: str, method_name: str):\n    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))\n    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)\n    return next(\n        node\n        for node in cls.body\n        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))\n        and node.name == method_name\n    )\n\n\ndef _defined_methods(path: str, class_name: str) -> set[str]:\n    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))\n    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)\n    return {\n        node.name\n        for node in cls.body\n        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))\n    }\n\n\ndef _call_chain(call: ast.Call) -> str:\n    node = call.func\n    parts = []\n    while isinstance(node, ast.Attribute):\n        parts.append(node.attr)\n        node = node.value\n    if isinstance(node, ast.Name):\n        parts.append(node.id)\n    return ".".join(reversed(parts))\n\n\ndef test_daily_report_observes_roasts_without_owning_the_flow():\n    methods = _defined_methods("daily_report_feature.py", "DailyReportMixin")\n    assert "_roast_group_target" not in methods\n    assert "_record_roast_outcome_event" in methods\n\n\ndef test_normal_roast_flow_uses_service_policy_and_event_hook():\n    method = _class_method("legacy_main.py", "RollPigPlugin", "_roast_group_target")\n    calls = {_call_chain(node) for node in ast.walk(method) if isinstance(node, ast.Call)}\n    assert "self.roast_service.choose_group_roast_outcome" in calls\n    assert "self._record_roast_outcome_event" in calls\n    assert "random.choices" not in calls\n\n\ndef test_reservation_uses_same_outcome_policy():\n    source = (ROOT / "roast_reservation_feature.py").read_text(encoding="utf-8")\n    assert "random.choices" not in source\n    assert "roast_service.choose_group_roast_outcome" in source\n\n\ndef test_roast_renderer_has_no_plugin_runtime_or_storage_dependency():\n    source = (ROOT / "renderers" / "roast.py").read_text(encoding="utf-8")\n    tree = ast.parse(source)\n    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}\n    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}\n    imported = {\n        alias.name.split(".")[0]\n        for node in ast.walk(tree)\n        if isinstance(node, (ast.Import, ast.ImportFrom))\n        for alias in node.names\n    }\n    forbidden = {\n        "AstrMessageEvent",\n        "astrbot",\n        "storage",\n        "load_json",\n        "save_json",\n        "_today",\n        "_get_daily_pig",\n        "roast_service",\n    }\n    assert not (forbidden & (names | attrs | imported))\n\n\ndef test_legacy_roast_renderer_is_only_a_facade():\n    method = _class_method("legacy_main.py", "RollPigPlugin", "render_roast_image")\n    calls = {_call_chain(node) for node in ast.walk(method) if isinstance(node, ast.Call)}\n    names = {node.id for node in ast.walk(method) if isinstance(node, ast.Name)}\n    assert "render_roast_card_image" in calls\n    assert not ({"PILImage", "ImageDraw", "ImageOps", "tempfile"} & names)\n''',
)

write(
    "tests/test_roast_renderer.py",
    '''from pathlib import Path\n\nfrom PIL import Image as PILImage\nfrom PIL import ImageFont\n\nfrom renderers import render_roast_card\n\n\nPALETTE = {\n    "roast_canvas": (44, 35, 34),\n    "roast_surface": (61, 47, 45),\n    "roast_outline": (134, 84, 66),\n    "roast_title": (245, 218, 195),\n    "roast_body": (231, 204, 184),\n}\n\n\ndef _no_image(_pig_id: str, _ex_level: int | None = None) -> Path | None:\n    return None\n\n\ndef test_roast_renderer_smoke_and_dimensions():\n    bold = ImageFont.truetype("DejaVuSans.ttf", 66)\n    body = ImageFont.truetype("DejaVuSans.ttf", 26)\n    output = render_roast_card(\n        {"id": "demo", "name": "Demo Pig"},\n        user_id="u1",\n        draw_date="2026-08-14",\n        ai_copy=None,\n        palette=PALETTE,\n        font_bold=bold,\n        body_font=body,\n        image_resolver=_no_image,\n    )\n    try:\n        assert output.exists()\n        with PILImage.open(output) as image:\n            assert image.format == "PNG"\n            assert image.size == (800, 870)\n    finally:\n        output.unlink(missing_ok=True)\n''',
)

# Extend the existing renderer boundary list and facade contract.
renderer_contract = read("tests/test_renderer_boundary_contract.py")
renderer_contract = replace_once(
    renderer_contract,
    '    ROOT / "renderers" / "catalog.py",\n    ROOT / "renderers" / "weekly.py",\n',
    '    ROOT / "renderers" / "catalog.py",\n    ROOT / "renderers" / "roast.py",\n    ROOT / "renderers" / "weekly.py",\n',
    "renderer contract files",
)
renderer_contract = replace_once(
    renderer_contract,
    '        "render_catalog_grid": "render_catalog_grid_image",\n        "render_weekly_summary": "render_weekly_summary_image",\n',
    '        "render_catalog_grid": "render_catalog_grid_image",\n        "render_roast_image": "render_roast_card_image",\n        "render_weekly_summary": "render_weekly_summary_image",\n',
    "renderer facade contract",
)
write("tests/test_renderer_boundary_contract.py", renderer_contract)


# Document the fourth boundary without claiming the charge/refill feature exists yet.
architecture = read("docs/ARCHITECTURE.md")
architecture = replace_once(
    architecture,
    "目前 `render_roast_image`、管理面板縮圖與其他舊圖像輸出尚在 `legacy_main.py`。後續應按同一原則逐個拆分，而不是讓 `renderers/` 取得整個 plugin instance。\n",
    "目前管理面板縮圖與其他少量舊圖像輸出尚在 `legacy_main.py`。後續應按同一原則逐個拆分，而不是讓 `renderers/` 取得整個 plugin instance。\n\n## Roast / Group Interaction Boundary\n\n第四階段把烤豬料理卡移入 `renderers/roast.py`，renderer 只接收小豬 view data、日期、字體、palette 與 image resolver；不讀 storage、不知道 AstrBot event，也不決定烤豬結果。\n\n普通 `/烤群友` 與預約烤豬的 **60/30/10** 結果選擇統一由 `RoastService.choose_group_roast_outcome()` 提供，後門仍固定成功。`DailyReportMixin` 不再複製整條 `_roast_group_target()`；它只透過 `_record_roast_outcome_event()` hook 觀察既有結算並寫入日報事件，因此資格、保護、冷卻、反噬與料理卡投遞只有一份正常流程。\n\n這個 service 仍是純規則層：SQLite／JSON 寫入、冷卻消耗、實際被烤次數、消息投遞、預約一次性 resolved 與 Gameplay Event persistence 都留在 orchestration。這一階段**不新增烤箱次數／補貨玩法**；下一階段若導入 charge/refill，應替換 orchestration 的冷卻消耗策略，而不是再次複製 roast outcome 或 settlement。\n",
    "architecture roast section",
)
write("docs/ARCHITECTURE.md", architecture)

changelog = read("CHANGELOG.md")
anchor = "- 新增 renderer 架構契約與獨立輸出 smoke；`renderers/` 禁止 AstrBot/storage/同步依賴，collection 與 weekly domain read 仍留在插件 orchestration，視覺與命令行為不變。\n"
addition = anchor + "- 完成 roast/group interaction boundary 第四階段：`render_roast_image` 移入 `renderers/roast.py`；料理卡 renderer 僅接受明確 view input，不取得 plugin instance。\n- 普通烤群友與預約烤豬共用 `RoastService` 的單一 60/30/10 outcome policy；`DailyReportMixin` 改為 outcome event hook，不再複製完整烤豬流程。現有保護、冷卻、後門、反噬、預約一次性與資料 schema 均不變。\n"
changelog = replace_once(changelog, anchor, addition, "changelog roast boundary")
write("CHANGELOG.md", changelog)

# Temporary orchestration files must never appear in the final branch diff.
(ROOT / "scripts" / "_tmp_apply_roast_boundary.py").unlink(missing_ok=True)
(ROOT / ".github" / "workflows" / "_tmp-roast-boundary.yml").unlink(missing_ok=True)
