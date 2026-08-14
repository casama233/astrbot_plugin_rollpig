from __future__ import annotations

import ast
from pathlib import Path

from help_system import HelpFeatureState, build_help_sections, help_sections_fingerprint


ROOT = Path(__file__).resolve().parents[1]
REPORT_ADAPTERS = {
    "pigsty_daily_report_status": "/豬圈日報狀態",
    "pigsty_daily_report_enable": "/豬圈日報開啟／關閉",
    "pigsty_daily_report_disable": "/豬圈日報開啟／關閉",
}


def _commands(state: HelpFeatureState) -> set[str]:
    return {
        entry.command
        for section in build_help_sections(state)
        for entry in section.entries
    }


def _registered_command_surfaces() -> dict[str, set[str]]:
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    commands: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            func = decorator.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "filter"
                and func.attr == "command"
            ):
                continue
            surfaces: set[str] = set()
            first = decorator.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                surfaces.add(first.value)
            for keyword in decorator.keywords:
                if keyword.arg != "alias" or not isinstance(keyword.value, ast.Set):
                    continue
                for item in keyword.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        surfaces.add(item.value)
            commands[node.name] = surfaces
    return commands


def test_disabled_features_are_omitted_instead_of_advertised():
    state = HelpFeatureState(
        at_view_pig=False,
        enable_new_pig_pity=False,
        enable_daily_duplicate_pity=False,
        enable_roast=False,
        enable_group_roast=False,
        enable_roast_reservation=False,
        enable_group_eat=False,
        enable_roast_protection=False,
        enable_ai_roast_copy=False,
        enable_daily_report=False,
        daily_report_random_eat_enabled=False,
    )
    commands = _commands(state)

    assert "/今日小豬 @某人" not in commands
    assert "/今日烤豬" not in commands
    assert "/烤群友 @某人" not in commands
    assert "/隨機烤群友" not in commands
    assert "/打點後廚 @某人" not in commands
    assert "/吃群友 @某人" not in commands
    assert "/隨機吃群友" not in commands
    assert not any(command.startswith("/豬圈日報") for command in commands)
    assert "新豬保底" not in commands
    assert "跨日疲勞保底" not in commands
    assert "預約烤豬" not in commands


def test_enabled_features_expose_new_report_and_reservation_capabilities():
    state = HelpFeatureState(
        at_view_pig=True,
        enable_roast=True,
        enable_group_roast=True,
        enable_roast_reservation=True,
        enable_group_eat=True,
        enable_roast_protection=True,
        enable_ai_roast_copy=True,
        enable_daily_report=True,
        daily_report_auto_send=False,
        daily_report_random_eat_enabled=True,
    )
    commands = _commands(state)

    assert "/今日小豬 @某人" in commands
    assert "/豬圈日報狀態" in commands
    assert "/烤箱補貨" in commands
    assert "/添煤" in commands
    assert "/豬圈日報開啟／關閉" in commands
    assert "自動日報總開關" in commands
    assert "預約烤豬" in commands
    assert "次日保護" in commands
    assert "AI 烤豬文案" in commands
    assert "日報隨機祭品" in commands


def test_all_registered_commands_have_script_aware_help_coverage_when_enabled():
    commands = _commands(
        HelpFeatureState(
            at_view_pig=True,
            enable_ai_roast_copy=True,
            daily_report_random_eat_enabled=True,
        )
    )
    registered = _registered_command_surfaces()

    uncovered = set()
    for handler, surfaces in registered.items():
        if handler == "rollpig_help":
            continue
        if handler in REPORT_ADAPTERS:
            if REPORT_ADAPTERS[handler] not in commands:
                uncovered.add(handler)
            continue
        if not any(
            any(entry.startswith(f"/{surface}") for entry in commands)
            for surface in surfaces
        ):
            uncovered.add(handler)
    assert uncovered == set(), f"commands missing from dynamic help: {sorted(uncovered)}"


def test_help_fingerprint_tracks_visible_content_and_theme():
    base = build_help_sections(HelpFeatureState(at_view_pig=False))
    with_at = build_help_sections(HelpFeatureState(at_view_pig=True))

    assert help_sections_fingerprint(base, theme="light") != help_sections_fingerprint(
        with_at, theme="light"
    )
    assert help_sections_fingerprint(base, theme="light") != help_sections_fingerprint(
        base, theme="night"
    )
