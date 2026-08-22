from __future__ import annotations

import ast
from pathlib import Path

from help_system import HelpFeatureState, build_help_sections, help_sections_fingerprint


ROOT = Path(__file__).resolve().parents[1]
REPORT_ADAPTERS = {
    "pigsty_daily_report_status": "/猪圈日报状态",
    "pigsty_daily_report_enable": "/猪圈日报开启／关闭",
    "pigsty_daily_report_disable": "/猪圈日报开启／关闭",
}
COMPAT_ADAPTERS = {"oven_refill_support_compat": "/添柴"}


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
        enable_oven_refill=False,
        enable_group_eat=False,
        enable_roast_protection=False,
        enable_eat_protection=False,
        enable_ai_roast_copy=False,
        enable_daily_report=False,
        daily_report_random_eat_enabled=False,
    )
    commands = _commands(state)

    assert "/今日小猪 @某人" not in commands
    assert "/今日烤猪" not in commands
    assert "/烤群友 @某人" not in commands
    assert "/随机烤群友" not in commands
    assert "/打点后厨 @某人" not in commands
    assert "/添柴" not in commands
    assert "/吃群友 @某人" not in commands
    assert "/随机吃群友" not in commands
    assert "/胃口" not in commands
    assert not any(command.startswith("/猪圈日报") for command in commands)
    assert not any("新豬保底" in command for command in commands)
    assert not any("跨日疲勞" in command for command in commands)
    assert not any("预约烤猪" in command for command in commands)
    assert not any("群友胃口" in command for command in commands)
    assert not any("餐后观察期" in command for command in commands)


def test_enabled_features_expose_new_report_reservation_and_appetite_capabilities():
    state = HelpFeatureState(
        at_view_pig=True,
        enable_roast=True,
        enable_group_roast=True,
        enable_roast_reservation=True,
        enable_oven_refill=True,
        enable_group_eat=True,
        enable_roast_protection=True,
        enable_eat_protection=True,
        enable_ai_roast_copy=True,
        enable_daily_report=True,
        daily_report_auto_send=False,
        daily_report_random_eat_enabled=True,
    )
    commands = _commands(state)

    assert "/今日小猪 @某人" in commands
    assert "/猪圈日报状态" in commands
    assert "/烤箱补货" in commands
    assert "/添柴" in commands
    assert "/添煤" not in commands
    assert "/胃口" in commands
    assert "/猪圈日报开启／关闭" in commands
    assert any("自动日报" in command for command in commands)
    assert any("预约烤猪" in command for command in commands)
    assert any("群友胃口" in command for command in commands)
    assert any("次日保护" in command for command in commands)
    assert any("餐后观察期" in command for command in commands)
    assert any("AI 料理文案" in command for command in commands)
    assert any("日报祭品" in command for command in commands)


def test_reservation_only_configuration_still_exposes_contextual_firewood():
    commands = _commands(
        HelpFeatureState(
            enable_roast=True,
            enable_group_roast=True,
            enable_roast_reservation=True,
            enable_oven_refill=False,
        )
    )
    assert "/添柴" in commands
    assert "/烤箱补货" not in commands


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
        if handler in COMPAT_ADAPTERS:
            if COMPAT_ADAPTERS[handler] not in commands:
                uncovered.add(handler)
            continue
        if not any(
            any(entry.startswith(f"/{surface}") for entry in commands)
            for surface in surfaces
        ):
            uncovered.add(handler)
    assert uncovered == set(), f"commands missing from dynamic help: {sorted(uncovered)}"


def test_help_fingerprint_tracks_visible_content_theme_and_appetite_values():
    base = build_help_sections(HelpFeatureState(at_view_pig=False))
    with_at = build_help_sections(HelpFeatureState(at_view_pig=True))
    more_appetite = build_help_sections(HelpFeatureState(eat_daily_attempt_limit=3))

    assert help_sections_fingerprint(base, theme="light") != help_sections_fingerprint(
        with_at, theme="light"
    )
    assert help_sections_fingerprint(base, theme="light") != help_sections_fingerprint(
        more_appetite, theme="light"
    )
    assert help_sections_fingerprint(base, theme="light") != help_sections_fingerprint(
        base, theme="night"
    )
