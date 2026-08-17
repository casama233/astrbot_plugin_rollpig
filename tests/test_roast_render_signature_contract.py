from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _method(path: str, class_name: str, method_name: str) -> ast.FunctionDef:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return next(
        node for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    )


def _positional_args(fn: ast.FunctionDef) -> list[str]:
    return [arg.arg for arg in fn.args.args]


def test_roast_render_chain_accepts_local_copy():
    main_fn = _method("main.py", "RollPigPlugin", "render_roast_image")
    ex_fn = _method("ex_variant_feature.py", "ExVariantMixin", "render_roast_image")

    expected = ["self", "pig", "user_id", "ai_copy", "local_copy"]
    assert _positional_args(main_fn)[:5] == expected
    assert _positional_args(ex_fn)[:5] == expected


def test_ex_variant_forwards_local_copy_to_next_renderer():
    source = (ROOT / "ex_variant_feature.py").read_text(encoding="utf-8")
    fn = _method("ex_variant_feature.py", "ExVariantMixin", "render_roast_image")
    method_source = ast.get_source_segment(source, fn) or ""
    assert "super().render_roast_image(display, user_id, ai_copy, local_copy)" in method_source


def test_roast_sender_supplies_local_copy():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    assert "self.render_roast_image, pig, user_id, ai_copy, local_copy" in source
