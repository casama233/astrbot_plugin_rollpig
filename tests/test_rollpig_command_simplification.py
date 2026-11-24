from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_date_lookup_commands_share_one_primary_registration():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    registrations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr != "command" or not decorator.args:
                continue
            if isinstance(decorator.args[0], ast.Constant) and decorator.args[0].value in {
                "昨日小猪", "明日小猪", "本周小猪", "查猪"
            }:
                registrations.append(decorator.args[0].value)
    assert registrations.count("查猪") == 1
    assert not ({"昨日小猪", "明日小猪", "本周小猪"} & set(registrations))
    assert "昨日小猪" in source and "明日小猪" in source and "本周小猪" in source
