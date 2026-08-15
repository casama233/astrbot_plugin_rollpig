from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Every user-facing Chinese command whose script actually changes must keep a
# Simplified and Traditional invocation. Script-identical commands are checked
# separately below, including the hidden refill compatibility surface.
SCRIPT_PAIRS = {
    "rollpig_help": ("猪猪帮助", "豬豬幫助"),
    "roll_pig": ("今日小猪", "今日小豬"),
    "my_pigsty": ("我的猪圈", "我的豬圈"),
    "yesterday_pig": ("昨日小猪", "昨日小豬"),
    "tomorrow_pig": ("明日小猪", "明日小豬"),
    "weekly_pigs": ("本周小猪", "本週小豬"),
    "random_pigs": ("随机小猪", "隨機小豬"),
    "find_pigs": ("找猪", "找豬"),
    "roast_today_pig": ("今日烤猪", "今日烤豬"),
    "roast_random_group_member": ("随机烤群友", "隨機烤群友"),
    "eat_random_group_member": ("随机吃群友", "隨機吃群友"),
    "force_roast_group_member": ("打点后厨", "打點後廚"),
    "oven_refill": ("烤箱补货", "烤箱補貨"),
    "pigsty_daily_report": ("猪圈日报", "豬圈日報"),
    "pigsty_daily_report_status": ("猪圈日报状态", "豬圈日報狀態"),
    "pigsty_daily_report_enable": ("猪圈日报开启", "豬圈日報開啟"),
    "pigsty_daily_report_disable": ("猪圈日报关闭", "豬圈日報關閉"),
}

SCRIPT_IDENTICAL = {
    "roast_group_member": "烤群友",
    "eat_group_member": "吃群友",
    "firewood_support": "添柴",
    "oven_refill_support_compat": "添煤",
}


def _command_surfaces() -> dict[str, set[str]]:
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    result: dict[str, set[str]] = {}
    for class_node in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        for fn in class_node.body:
            if not isinstance(fn, ast.AsyncFunctionDef):
                continue
            for decorator in fn.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if not (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "filter"
                    and func.attr == "command"
                ):
                    continue
                values: set[str] = set()
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    values.add(str(decorator.args[0].value))
                for keyword in decorator.keywords:
                    if keyword.arg != "alias" or not isinstance(keyword.value, ast.Set):
                        continue
                    for element in keyword.value.elts:
                        if isinstance(element, ast.Constant):
                            values.add(str(element.value))
                result[fn.name] = values
    return result


def test_every_script_sensitive_command_keeps_simplified_and_traditional_forms():
    surfaces = _command_surfaces()
    for handler, (simplified, traditional) in SCRIPT_PAIRS.items():
        assert handler in surfaces
        assert simplified in surfaces[handler], f"{handler} lost Simplified form {simplified}"
        assert traditional in surfaces[handler], f"{handler} lost Traditional form {traditional}"


def test_script_identical_commands_remain_registered():
    surfaces = _command_surfaces()
    for handler, command in SCRIPT_IDENTICAL.items():
        assert command in surfaces[handler]


def test_daily_report_compact_controls_cover_mixed_script_inputs_too():
    surfaces = _command_surfaces()
    assert {
        "猪圈日报状态",
        "猪圈日报狀態",
        "豬圈日報状态",
        "豬圈日報狀態",
    }.issubset(surfaces["pigsty_daily_report_status"])
    assert {
        "猪圈日报开启",
        "猪圈日报開啟",
        "豬圈日報开启",
        "豬圈日報開啟",
        "猪圈日报启用",
        "豬圈日報啟用",
    }.issubset(surfaces["pigsty_daily_report_enable"])
    assert {
        "猪圈日报关闭",
        "猪圈日报關閉",
        "豬圈日報关闭",
        "豬圈日報關閉",
    }.issubset(surfaces["pigsty_daily_report_disable"])


def test_no_exact_command_or_alias_is_registered_by_two_handlers():
    owners: dict[str, list[str]] = defaultdict(list)
    for handler, commands in _command_surfaces().items():
        for command in commands:
            owners[command].append(handler)
    collisions = {command: names for command, names in owners.items() if len(names) > 1}
    assert not collisions, f"duplicate AstrBot command surfaces: {collisions}"


def test_spaced_daily_report_actions_accept_both_scripts_in_business_parser():
    source = (ROOT / "daily_report_feature.py").read_text(encoding="utf-8")
    assert '{"开启", "開啟", "启用", "啟用", "on", "enable"}' in source
    assert '{"关闭", "關閉", "停用", "off", "disable"}' in source
    assert '{"状态", "狀態", "status"}' in source
