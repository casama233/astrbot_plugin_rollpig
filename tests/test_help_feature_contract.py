from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _class(path: str, name: str) -> ast.ClassDef:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name
    )


def _method(cls: ast.ClassDef, name: str):
    return next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def test_main_routes_command_to_help_feature_mixin():
    cls = _class("main.py", "RollPigPlugin")
    bases = {ast.unparse(base) for base in cls.bases}
    assert "HelpFeatureMixin" in bases


def test_help_rendering_is_offloaded_from_event_loop():
    cls = _class("help_feature.py", "HelpFeatureMixin")
    source = ast.unparse(_method(cls, "rollpig_help"))
    assert "await asyncio.to_thread(self.render_help_image)" in source


def test_help_cache_identity_comes_from_actual_visible_sections():
    cls = _class("help_feature.py", "HelpFeatureMixin")
    source = ast.unparse(_method(cls, "_help_cache_identity"))
    assert "help_sections_fingerprint(self._help_sections(), theme=theme)" in source


def test_help_renderer_uses_low_cpu_png_compression():
    source = (ROOT / "renderers" / "help.py").read_text(encoding="utf-8")
    assert "PNG_COMPRESS_LEVEL = 1" in source
    assert "compress_level=PNG_COMPRESS_LEVEL" in source
