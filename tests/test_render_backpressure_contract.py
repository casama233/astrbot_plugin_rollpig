from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"


def _class_node() -> ast.ClassDef:
    tree = ast.parse(MAIN.read_text(encoding="utf-8"), filename=str(MAIN))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )


def _method(name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    cls = _class_node()
    return next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return f"{head}.{node.attr}" if head else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def test_image_rendering_has_bounded_thread_backpressure():
    source = MAIN.read_text(encoding="utf-8")
    assert "threading.BoundedSemaphore" in source
    assert 'config_view.get("image_render_concurrency", 2)' in source
    assert "min(8, max(1, render_concurrency))" in source

    renderers = {
        "render_pig_image",
        "render_pigsty_image",
        "render_catalog_grid",
        "render_weekly_summary",
        "render_roast_image",
        "render_daily_report_image",
    }
    for name in renderers:
        fn = _method(name)
        calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call)]
        assert any(
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "_run_with_render_slot"
            for call in calls
        ), f"{name} bypasses the shared render gate"


def test_help_cache_miss_is_prepared_off_event_loop_before_delegation():
    fn = _method("rollpig_help")
    calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call)]

    assert any(
        _dotted(call.func) == "asyncio.to_thread"
        and call.args
        and isinstance(call.args[0], ast.Attribute)
        and call.args[0].attr == "_ensure_help_image_cache"
        for call in calls
    )
    assert any(
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "rollpig_help"
        and isinstance(call.func.value, ast.Call)
        and isinstance(call.func.value.func, ast.Name)
        and call.func.value.func.id == "super"
        for call in calls
    )


def test_help_render_uses_stable_master_and_expendable_send_copy():
    source = MAIN.read_text(encoding="utf-8")
    assert 'self.plugin_data_dir / "render_cache" / "help"' in source
    assert "os.link(cache_path, output)" in source
    assert "shutil.copyfile(cache_path, output)" in source
    assert "HELP_RENDER_CACHE_VERSION = 1" in source
