from __future__ import annotations

import ast
from pathlib import Path

import pytest

from help_system import HelpFeatureState, build_help_sections
from player_copy import (
    PLAYER_COPY,
    SUPPORTED_PLAYER_LOCALES,
    copy_placeholders,
    copy_text,
    normalize_player_locale,
)


ROOT = Path(__file__).resolve().parents[1]


def _flatten_help(locale: str) -> str:
    sections = build_help_sections(
        HelpFeatureState(
            at_view_pig=True,
            enable_ai_roast_copy=True,
            daily_report_random_eat_enabled=True,
        ),
        locale=locale,
    )
    rows: list[str] = []
    for section in sections:
        rows.append(section.title)
        rows.extend(f"{entry.command} {entry.detail}" for entry in section.entries)
    return "\n".join(rows)


def test_player_copy_locales_have_identical_keys_and_placeholders():
    assert tuple(PLAYER_COPY) == SUPPORTED_PLAYER_LOCALES
    base_keys = set(PLAYER_COPY["zh-TW"])
    assert base_keys
    assert set(PLAYER_COPY["zh-CN"]) == base_keys

    for key in sorted(base_keys):
        tw = PLAYER_COPY["zh-TW"][key]
        cn = PLAYER_COPY["zh-CN"][key]
        assert tw.strip(), key
        assert cn.strip(), key
        assert copy_placeholders(tw) == copy_placeholders(cn), key


def test_player_copy_locale_aliases_and_strict_formatting():
    assert normalize_player_locale("zh_Hant") == "zh-TW"
    assert normalize_player_locale("zh-HK") == "zh-TW"
    assert normalize_player_locale("zh_Hans") == "zh-CN"
    assert normalize_player_locale("zh-SG") == "zh-CN"
    assert normalize_player_locale("unknown") == "zh-TW"

    assert "3 格" in copy_text(
        "help.mechanic.oven_energy", locale="zh-CN", capacity=3
    )
    with pytest.raises(KeyError):
        copy_text("help.mechanic.oven_energy", locale="zh-TW")
    with pytest.raises(KeyError):
        copy_text("missing.copy.key")


def test_dynamic_help_uses_same_simplified_display_copy_for_all_locale_aliases():
    tw = _flatten_help("zh-TW")
    cn = _flatten_help("zh-CN")

    for text in (tw, cn):
        assert "每天抽猪" in text
        assert "群体补货" in text
        assert "预约烤猪" in text
        assert "猪圈日报" in text
        assert "EX 成长" in text
        assert "/今日小猪" in text

    # Locale aliases remain accepted, but generated cards deliberately use
    # Simplified labels so the bundled image font does not need Traditional CJK.
    assert "/今日小豬" not in tw
    assert "/今日小豬" not in cn


def test_dynamic_help_defaults_to_simplified_chinese_for_generated_card():
    rows = []
    for section in build_help_sections(HelpFeatureState(at_view_pig=True)):
        rows.append(section.title)
        rows.extend(f"{entry.command} {entry.detail}" for entry in section.entries)
    text = "\n".join(rows)
    assert "每天抽猪" in text
    assert "/今日小猪" in text
    assert "/猪圈日报" in text
    assert "/烤箱补货" in text


def test_help_copy_cannot_regress_to_inline_player_facing_literals():
    """Migrated help descriptions/section titles must stay in player_copy."""

    source = (ROOT / "help_system.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    violations: list[tuple[int, str]] = []

    def has_cjk(value: object) -> bool:
        return isinstance(value, str) and any(
            "\u3400" <= ch <= "\u9fff" for ch in value
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ""
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr

        if name == "HelpEntry" and len(node.args) >= 2:
            detail = node.args[1]
            if isinstance(detail, ast.Constant) and has_cjk(detail.value):
                violations.append((detail.lineno, str(detail.value)))

        if name == "_section" and node.args:
            title = node.args[0]
            if isinstance(title, ast.Constant) and has_cjk(title.value):
                violations.append((title.lineno, str(title.value)))

    assert violations == []
