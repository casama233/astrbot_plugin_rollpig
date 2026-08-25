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
    assert "self._help_sections()" in source
    assert "HELP_RENDER_CACHE_VERSION" in source
    assert "self._help_font_identity()" in source
    assert "help_sections_fingerprint" in source


def test_help_cache_uses_standard_cn_font_and_invalidates_old_bitmaps():
    cls = _class("help_feature.py", "HelpFeatureMixin")
    class_source = ast.unparse(cls)
    font_source = ast.unparse(_method(cls, "_help_font_identity"))
    ensure_source = ast.unparse(_method(cls, "_ensure_help_master"))
    sections_source = ast.unparse(_method(cls, "_help_sections"))

    assert "HELP_RENDER_CACHE_VERSION = 7" in class_source
    assert "font_bold" in font_source
    assert "font_traditional" not in font_source
    assert "font_traditional" not in ensure_source
    assert "locale='zh-CN'" in sections_source


def test_help_cache_keeps_master_and_returns_disposable_output():
    cls = _class("help_feature.py", "HelpFeatureMixin")
    ensure_source = ast.unparse(_method(cls, "_ensure_help_master"))
    render_source = ast.unparse(_method(cls, "render_help_image"))

    assert "self._valid_help_master(master)" in ensure_source
    assert "staging.replace(master)" in ensure_source
    assert "os.link(master, output)" in render_source
    assert "shutil.copyfile(master, output)" in render_source


def test_help_renderer_uses_low_cpu_png_compression():
    source = (ROOT / "renderers" / "help.py").read_text(encoding="utf-8")
    assert "PNG_COMPRESS_LEVEL = 1" in source
    assert "compress_level=PNG_COMPRESS_LEVEL" in source
