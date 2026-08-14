from __future__ import annotations

import ast
from pathlib import Path

from help_system import HelpFeatureState, build_help_sections, help_sections_fingerprint


ROOT = Path(__file__).resolve().parents[1]


def _commands(state: HelpFeatureState) -> set[str]:
    return {
        entry.command
        for section in build_help_sections(state)
        for entry in section.entries
    }


def _registered_primary_commands() -> set[str]:
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    commands: set[str] = set()
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
            first = decorator.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                commands.add(first.value)
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

    assert "/今日小猪 @某人" not in commands
    assert "/今日烤猪" not in commands
    assert "/烤群友 @某人" not in commands
    assert "/随机烤群友" not in commands
    assert "/打点后厨 @某人" not in commands
    assert "/吃群友 @某人" not in commands
    assert "/随机吃群友" not in commands
    assert not any(command.startswith("/猪圈日报") for command in commands)
    assert "新猪保底" not in commands
    assert "跨日疲劳保底" not in commands
    assert "预约烤猪" not in commands


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

    assert "/今日小猪 @某人" in commands
    assert "/猪圈日报 状态" in commands
    assert "/猪圈日报 开启／关闭" in commands
    assert "自动日报总开关" in commands
    assert "预约烤猪" in commands
    assert "次日保护" in commands
    assert "AI 烤猪文案" in commands
    assert "日报随机祭品" in commands


def test_all_registered_commands_have_help_coverage_when_enabled():
    commands = _commands(
        HelpFeatureState(
            at_view_pig=True,
            enable_ai_roast_copy=True,
            daily_report_random_eat_enabled=True,
        )
    )
    registered = _registered_primary_commands() - {"猪猪帮助"}

    uncovered = {
        command
        for command in registered
        if not any(entry.startswith(f"/{command}") for entry in commands)
    }
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
