import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _rollpig_method(name: str) -> ast.FunctionDef:
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )
    return next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def test_reload_catalog_persists_the_merged_pig_list():
    """Regression: phase-2 delegation must not leave a stale `merged` name."""
    method = _rollpig_method("_reload_catalog_layers")

    bare_merged = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Name)
        and node.id == "merged"
        and isinstance(node.ctx, ast.Load)
    ]
    assert not bare_merged

    save_calls = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "save_json"
    ]
    assert save_calls
    assert any(
        len(call.args) >= 2
        and isinstance(call.args[1], ast.Attribute)
        and isinstance(call.args[1].value, ast.Name)
        and call.args[1].value.id == "self"
        and call.args[1].attr == "pig_list"
        for call in save_calls
    )
