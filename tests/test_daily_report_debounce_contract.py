from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _method(name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    plugin = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )
    return next(
        node
        for node in plugin.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def test_daily_report_state_save_is_debounced_after_initialization():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "DebouncedSnapshotWriter" in source
    assert "DAILY_REPORT_STATE_FLUSH_DELAY_SECONDS = 2.0" in source

    method = _method("_save_daily_report_state_locked")
    calls = [node for node in ast.walk(method) if isinstance(node, ast.Call)]
    assert any(
        isinstance(call.func, ast.Attribute) and call.func.attr == "mark_dirty"
        for call in calls
    )
    assert any(
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "_save_daily_report_state_locked"
        and isinstance(call.func.value, ast.Call)
        and isinstance(call.func.value.func, ast.Name)
        and call.func.value.func.id == "super"
        for call in calls
    ), "startup must retain the inherited immediate save before the writer exists"


def test_plugin_shutdown_forces_final_snapshot_off_event_loop():
    method = _method("terminate")
    source = ast.unparse(method)
    assert "_daily_report_task" in source
    assert ".cancel()" in source
    assert "await asyncio.to_thread(writer.close_and_flush)" in source
    assert "await super().terminate()" in source
