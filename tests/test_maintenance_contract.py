from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "maintenance_contract.py"
SPEC = importlib.util.spec_from_file_location("maintenance_contract", SCRIPT)
assert SPEC and SPEC.loader
maintenance_contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(maintenance_contract)


def test_markdown_section_and_unreleased_bullets_ignore_placeholder():
    text = """# 更新

## 未發佈

- 暫無。
- 修正一個問題。

## v1.0.0

- 舊版本。
"""
    section = maintenance_contract._markdown_section(text, "未發佈")
    assert maintenance_contract._substantive_bullets(section) == {"- 修正一個問題。"}


def test_extract_commands_reads_canonical_filter_commands_only():
    source = """
class Plugin:
    @filter.command('今日小猪', alias={'今日小豬'})
    async def today(self, event):
        pass

    @other.command('不属于 AstrBot filter')
    async def other(self, event):
        pass
"""
    assert maintenance_contract._extract_commands(source) == {"今日小猪"}


def test_wiki_impact_declaration_requires_reason_for_none():
    assert maintenance_contract._wiki_declaration("Wiki-Impact: updated") == (
        "updated",
        "Wiki-Impact: updated".split(": ", 1)[1],
    )
    mode, reason = maintenance_contract._wiki_declaration(
        "Wiki-Impact: none — internal CI-only refactor; runtime behavior unchanged"
    )
    assert mode == "none"
    assert "runtime behavior unchanged" in reason


def test_user_facing_paths_are_distinct_from_tests_and_ci():
    assert maintenance_contract._is_user_facing("main.py") is True
    assert maintenance_contract._is_user_facing("pages/pig-manager/index.html") is True
    assert maintenance_contract._is_user_facing("tests/test_example.py") is False
    assert maintenance_contract._is_user_facing(".github/workflows/ci.yml") is False


def test_current_tree_has_command_and_configuration_wiki_coverage():
    assert maintenance_contract._coverage_errors(ROOT) == []
