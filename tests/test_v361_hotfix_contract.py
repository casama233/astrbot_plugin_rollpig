from __future__ import annotations

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
