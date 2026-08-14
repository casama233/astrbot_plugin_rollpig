from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "legacy_main.py").read_text(encoding="utf-8")


def _method_source(name: str) -> str:
    tree = ast.parse(SOURCE)
    plugin = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )
    method = next(
        node
        for node in plugin.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )
    return ast.get_source_segment(SOURCE, method) or ""


def test_ai_roast_copy_uses_exact_seven_natural_day_window():
    method = _method_source("_get_ai_roast_copy")
    assert "today_value - datetime.timedelta(days=6)" in method
    assert "cutoff_date=cutoff" in method
    assert "through_date=today" in method


def test_first_successful_copy_is_returned_directly_before_random_reuse():
    method = _method_source("_get_ai_roast_copy")
    direct_return = 'return str(completed.get("content") or generated)'
    random_return = "return random.choice(list(recent.values())) if recent else None"
    assert direct_return in method
    assert random_return in method
    assert method.index(direct_return) < method.index(random_return, method.index(direct_return))


def test_same_day_ready_copy_randomizes_across_the_rolling_pool():
    method = _method_source("_get_ai_roast_copy")
    assert 'str(claimed.get("status")) == "ready" and today in recent' in method
    assert "return random.choice(list(recent.values()))" in method


def test_non_owner_never_calls_the_model_again_that_day():
    method = _method_source("_get_ai_roast_copy")
    claim_guard = 'if not claimed.get("claimed"):'
    generator_call = "generated = await self._generate_ai_roast_copy(event, pig)"
    assert claim_guard in method
    assert generator_call in method
    guard_position = method.index(claim_guard)
    generator_position = method.index(generator_call, guard_position)
    guarded_block = method[guard_position:generator_position]
    assert "return random.choice(list(recent.values())) if recent else None" in guarded_block
