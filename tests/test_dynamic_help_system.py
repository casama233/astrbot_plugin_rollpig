from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from help_system import HelpFeatureState, build_help_sections, help_sections_fingerprint
from player_copy import copy_text


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
        enable_ai_roast_copy=False,
        enable_daily_report=False,
        daily_report_random_eat_enabled=False,
    )
    commands = _commands(state)

    assert "/今日小猪 @群友" not in commands
    assert "/今日烤猪" not in commands
    assert "/烤群友 @群友" not in commands
    assert "/随机烤群友" not in commands
    assert "/打点后厨 @群友" not in commands
    assert "/添柴" not in commands
    assert "/吃群友 @群友" not in commands
    assert "/随机吃群友" not in commands
    assert not any(command.startswith("/猪圈日报") for command in commands)
    assert copy_text("help.mechanic.new_pig_pity_title") not in commands
    assert copy_text("help.mechanic.duplicate_pity_title") not in commands
    assert copy_text("help.mechanic.reservation_title") not in commands


def test_enabled_features_expose_new_report_and_reservation_capabilities():
    state = HelpFeatureState(
        at_view_pig=True,
        enable_roast=True,
        enable_group_roast=True,
        enable_roast_reservation=True,
        enable_oven_refill=True,
        enable_group_eat=True,
        enable_roast_protection=True,
        enable_ai_roast_copy=True,
        enable_daily_report=True,
        daily_report_auto_send=False,
        daily_report_random_eat_enabled=True,
    )
    commands = _commands(state)

    assert "/今日小猪 @群友" in commands
    assert "/猪圈日报状态" in commands
    assert "/烤箱补货" in commands
    assert "/添柴" in commands
    assert "/添煤" not in commands
    assert "/猪圈日报开启／关闭" in commands
    for key in (
        "help.report.auto_off_title",
        "help.mechanic.reservation_title",
        "help.mechanic.protection_title",
        "help.mechanic.ai_copy_title",
        "help.mechanic.report_random_eat_title",
    ):
        assert copy_text(key) in commands


def test_native_mention_note_follows_every_at_capable_help_command():
    sections = build_help_sections(HelpFeatureState(at_view_pig=True))
    entries = [entry for section in sections for entry in section.entries]
    from player_copy import PLAYER_COPY
    note_text = PLAYER_COPY["zh-CN"]["help.mention.native_at_note"]
    assert all(word in note_text for word in ("QQ", "@列表", "选中", "手动输入", "粘贴"))
    expected_commands = {
        "/今日小猪 @群友",
        "/烤群友 @群友",
        "/打点后厨 @群友",
        "/添柴",
        "/吃群友 @群友",
    }
    for index, entry in enumerate(entries[:-1]):
        if entry.command in expected_commands:
            note = entries[index + 1]
            assert note.kind == "mention-note"
            assert note.command == ""
            assert note.detail == note_text

    commands_with_notes = {
        entries[index - 1].command
        for index, entry in enumerate(entries)
        if entry.kind == "mention-note"
    }
    assert commands_with_notes == expected_commands


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


def test_help_fingerprint_tracks_visible_content_and_theme():
    base = build_help_sections(HelpFeatureState(at_view_pig=False))
    with_at = build_help_sections(HelpFeatureState(at_view_pig=True))

    assert help_sections_fingerprint(base, theme="light") != help_sections_fingerprint(
        with_at, theme="light"
    )
    assert help_sections_fingerprint(base, theme="light") != help_sections_fingerprint(
        base, theme="night"
    )


def test_help_explains_configured_cost_recovery_risk_and_ex_content():
    state = HelpFeatureState(
        group_roast_max_charges=3,
        group_roast_recovery_hours=1.5,
        eat_success_percent=27,
        roast_reservation_max_participants=9,
    )
    entries = {
        entry.command: entry.detail
        for section in build_help_sections(state)
        for entry in section.entries
    }
    charge = entries[copy_text("help.mechanic.oven_energy_title")]
    assert "每人每群上限3格" in charge
    assert "1.5小时恢复1格" in charge
    assert "消耗1格，溜走不退" in entries["/烤群友 @群友"]
    assert all(word in entries["/吃群友 @群友"] for word in ("27%几率得手", "失手", "吃掉自己"))
    reservation = entries[copy_text("help.mechanic.reservation_title")]
    assert "上限9人" in reservation
    assert "/烤群友加入不扣格" in reservation
    growth = entries[copy_text("help.mechanic.ex_growth_title")]
    assert all(word in growth for word in ("EX", "超", "5", "差分"))

    # A cached bitmap must change whenever a displayed rule changes.
    original = help_sections_fingerprint(build_help_sections(state))
    for field, value in (
        ("group_roast_max_charges", 5),
        ("group_roast_recovery_hours", 2.5),
        ("eat_success_percent", 33),
        ("roast_reservation_max_participants", 10),
    ):
        changed = build_help_sections(replace(state, **{field: value}))
        assert help_sections_fingerprint(changed) != original, field
