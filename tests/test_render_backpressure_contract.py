from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
HELP_FEATURE = ROOT / "help_feature.py"


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


def test_dynamic_help_owns_off_loop_cache_and_uses_shared_render_gate():
    source = HELP_FEATURE.read_text(encoding="utf-8")
    assert "await asyncio.to_thread(self.render_help_image)" in source
    assert 'self.plugin_data_dir / "render_cache" / "help"' in source
    assert "os.link(master, output)" in source
    assert "shutil.copyfile(master, output)" in source
    assert "HELP_RENDER_CACHE_VERSION = 7" in source
    assert 'gate = getattr(self, "_run_with_render_slot", None)' in source
    assert "rendered = gate(render_help_card" in source


def test_main_help_wrapper_only_delegates_to_dynamic_feature():
    fn = _method("rollpig_help")
    calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call)]
    assert any(
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "rollpig_help"
        and isinstance(call.func.value, ast.Call)
        and isinstance(call.func.value.func, ast.Name)
        and call.func.value.func.id == "super"
        for call in calls
    )
