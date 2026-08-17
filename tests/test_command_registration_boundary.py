from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPERS = [
    "legacy_main.py",
    "daily_report_feature.py",
    "ex_variant_feature.py",
    "roast_reservation_feature.py",
    "reservation_firewood_feature.py",
    "random_roast_feature.py",
]
REPORT_ADAPTERS = {
    "pigsty_daily_report_status": "狀態",
    "pigsty_daily_report_enable": "開啟",
    "pigsty_daily_report_disable": "關閉",
}
COMPAT_ADAPTERS = {"oven_refill_support_compat": "oven_refill_support"}
EXPECTED = {
    "eat_group_member",
    "eat_random_group_member",
    "find_pigs",
    "firewood_support",
    "force_roast_group_member",
    "my_pigsty",
    "oven_refill",
    *COMPAT_ADAPTERS,
    "pigsty_daily_report",
    *REPORT_ADAPTERS,
    "random_pigs",
    "roast_group_member",
    "roast_random_group_member",
    "roast_today_pig",
    "roll_pig",
    "rollpig_help",
    "tomorrow_pig",
    "weekly_pigs",
    "yesterday_pig",
}


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _dotted(node.func)
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return f"{head}.{node.attr}" if head else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _commands(path: Path) -> dict[str, ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[str, ast.AsyncFunctionDef] = {}
    for item in tree.body:
        if not isinstance(item, ast.ClassDef):
            continue
        for fn in item.body:
            if not isinstance(fn, ast.AsyncFunctionDef):
                continue
            if any(_dotted(dec) in {"filter.command", "filter.command_group"} for dec in fn.decorator_list):
                found[fn.name] = fn
    return found


def test_helper_modules_do_not_register_commands():
    leaked = {path: sorted(_commands(ROOT / path)) for path in HELPERS if _commands(ROOT / path)}
    assert not leaked, f"helper modules still own AstrBot commands: {leaked}"


def test_main_owns_complete_command_surface_with_explicit_priority():
    commands = _commands(ROOT / "main.py")
    assert set(commands) == EXPECTED
    for name, fn in commands.items():
        command_decorators = [dec for dec in fn.decorator_list if _dotted(dec) == "filter.command"]
        assert command_decorators, f"{name} lost filter.command"
        for dec in command_decorators:
            assert isinstance(dec, ast.Call)
            priorities = [kw.value for kw in dec.keywords if kw.arg == "priority"]
            assert len(priorities) == 1, f"{name} must declare priority exactly once"
            assert isinstance(priorities[0], ast.Constant) and priorities[0].value == 1000


def test_main_command_wrappers_delegate_to_inherited_implementation():
    commands = _commands(ROOT / "main.py")
    adapters = set(REPORT_ADAPTERS) | set(COMPAT_ADAPTERS)
    for name, fn in commands.items():
        if name in adapters:
            continue
        calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call)]
        delegated = False
        for call in calls:
            func = call.func
            if not isinstance(func, ast.Attribute) or func.attr != name:
                continue
            value = func.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "super":
                delegated = True
                break
        assert delegated, f"{name} wrapper no longer delegates to super().{name}"


def test_compact_report_adapters_delegate_to_one_existing_report_handler():
    commands = _commands(ROOT / "main.py")
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    for name, action in REPORT_ADAPTERS.items():
        fn = commands[name]
        segment = ast.get_source_segment(source, fn) or ""
        assert "super().pigsty_daily_report(event" in segment
        assert repr(action) in segment or f"'{action}'" in segment or f'"{action}"' in segment
        assert "event.send" not in segment
        assert "_set_daily_report_group_auto" not in segment


def test_refill_compat_adapter_delegates_to_claimed_refill_handler():
    commands = _commands(ROOT / "main.py")
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    fn = commands["oven_refill_support_compat"]
    segment = ast.get_source_segment(source, fn) or ""
    assert "super().oven_refill_support(event)" in segment
    assert "event.send" not in segment
    assert "_claim_command_event" not in segment


def test_runtime_rebind_workaround_is_removed():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "_rebind_rollpig_handlers_to_entrypoint" not in source
    assert "star_handlers_registry" not in source
