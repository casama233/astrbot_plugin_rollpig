#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPERS = [
    "legacy_main.py",
    "daily_report_feature.py",
    "ex_variant_feature.py",
    "roast_reservation_feature.py",
]
EXPECTED_COMMAND_COUNT = 15
MAIN = ROOT / "main.py"
ARCH = ROOT / "docs" / "ARCHITECTURE.md"
CHANGELOG = ROOT / "CHANGELOG.md"
TEST = ROOT / "tests" / "test_command_registration_boundary.py"


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return dotted_name(node.func)
    if isinstance(node, ast.Attribute):
        head = dotted_name(node.value)
        return f"{head}.{node.attr}" if head else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def is_command_decorator(node: ast.AST) -> bool:
    return dotted_name(node) in {"filter.command", "filter.command_group"}


def has_yield(fn: ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(fn):
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return True
    return False


@dataclass
class CommandMethod:
    source_path: str
    class_name: str
    node: ast.AsyncFunctionDef


def remove_helper_command_decorators(path: Path) -> list[CommandMethod]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    commands: list[CommandMethod] = []
    ranges: list[tuple[int, int]] = []

    for item in tree.body:
        if not isinstance(item, ast.ClassDef):
            continue
        for fn in item.body:
            if not isinstance(fn, ast.AsyncFunctionDef):
                continue
            if not any(is_command_decorator(dec) for dec in fn.decorator_list):
                continue
            if any(dotted_name(dec) == "filter.command_group" for dec in fn.decorator_list):
                raise RuntimeError(
                    f"{path.name}:{fn.name} 使用 command_group，需人工迁移，停止自动重构"
                )
            if has_yield(fn):
                raise RuntimeError(
                    f"{path.name}:{fn.name} 是 async generator，不能用 await super() 薄包装"
                )
            positional = [*fn.args.posonlyargs, *fn.args.args]
            if not positional or positional[0].arg != "self":
                raise RuntimeError(f"{path.name}:{fn.name} 不是标准实例 handler")
            commands.append(CommandMethod(path.name, item.name, fn))
            start = min(dec.lineno for dec in fn.decorator_list) - 1
            end = fn.lineno - 1
            ranges.append((start, end))

    lines = source.splitlines(keepends=True)
    for start, end in sorted(ranges, reverse=True):
        del lines[start:end]
    rewritten = "".join(lines)
    ast.parse(rewritten, filename=str(path))
    path.write_text(rewritten, encoding="utf-8")
    return commands


def with_explicit_priority(decorators: list[ast.expr]) -> list[ast.expr]:
    result: list[ast.expr] = []
    for dec in copy.deepcopy(decorators):
        if dotted_name(dec) == "filter.command":
            if not isinstance(dec, ast.Call):
                raise RuntimeError("filter.command decorator shape unexpected")
            found = False
            for kw in dec.keywords:
                if kw.arg == "priority":
                    kw.value = ast.Constant(1000)
                    found = True
            if not found:
                dec.keywords.append(ast.keyword(arg="priority", value=ast.Constant(1000)))
        result.append(dec)
    return result


def forwarding_call(fn: ast.AsyncFunctionDef) -> ast.Call:
    positional = [*fn.args.posonlyargs, *fn.args.args]
    call_args: list[ast.expr] = []
    skipped_self = False
    for arg in positional:
        if not skipped_self and arg.arg == "self":
            skipped_self = True
            continue
        call_args.append(ast.Name(id=arg.arg, ctx=ast.Load()))
    if fn.args.vararg:
        call_args.append(
            ast.Starred(
                value=ast.Name(id=fn.args.vararg.arg, ctx=ast.Load()),
                ctx=ast.Load(),
            )
        )
    keywords = [
        ast.keyword(arg=arg.arg, value=ast.Name(id=arg.arg, ctx=ast.Load()))
        for arg in fn.args.kwonlyargs
    ]
    if fn.args.kwarg:
        keywords.append(
            ast.keyword(
                arg=None,
                value=ast.Name(id=fn.args.kwarg.arg, ctx=ast.Load()),
            )
        )
    return ast.Call(
        func=ast.Attribute(
            value=ast.Call(func=ast.Name(id="super", ctx=ast.Load()), args=[], keywords=[]),
            attr=fn.name,
            ctx=ast.Load(),
        ),
        args=call_args,
        keywords=keywords,
    )


def render_wrapper(command: CommandMethod) -> str:
    original = command.node
    body: list[ast.stmt] = []
    doc = ast.get_docstring(original, clean=False)
    if doc:
        body.append(ast.Expr(value=ast.Constant(doc)))
    body.append(ast.Return(value=ast.Await(value=forwarding_call(original))))
    wrapper = ast.AsyncFunctionDef(
        name=original.name,
        args=copy.deepcopy(original.args),
        body=body,
        decorator_list=with_explicit_priority(original.decorator_list),
        returns=copy.deepcopy(original.returns),
        type_comment=original.type_comment,
    )
    wrapper = ast.fix_missing_locations(wrapper)
    return textwrap.indent(ast.unparse(wrapper), "    ")


def rewrite_main(commands: list[CommandMethod]) -> None:
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MAIN))
    module_doc = ast.get_docstring(tree, clean=False)
    if not module_doc:
        raise RuntimeError("main.py module docstring missing")
    first = tree.body[0]
    if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
        raise RuntimeError("main.py module docstring shape unexpected")
    new_doc = '''RollPig plugin entry point.\n\nAstrBot command decorators intentionally live in this module. Business logic may\nremain in ``legacy_main`` or focused feature mixins during the gradual refactor,\nbut helper modules must not register commands themselves. Thin wrappers below\ndelegate to the inherited implementation and keep AstrBot handler ownership,\npriority and unload semantics bound to the real Star entry point.\n'''
    lines = source.splitlines(keepends=True)
    lines[: first.end_lineno] = [f'"""{new_doc}"""\n']
    source = "".join(lines)

    source = source.replace(
        "from astrbot.api import logger\nfrom astrbot.core.star.star_handler import star_handlers_registry\n",
        "from astrbot.api.event import AstrMessageEvent, filter\n",
    )
    source, count = re.subn(
        r"\n_COMMAND_HANDLER_PRIORITY = 1000\n.*?\n\nclass RollPigPlugin\(",
        "\n\nclass RollPigPlugin(",
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("failed to remove v3.6.2 runtime handler rebind block")

    marker = "    # Keep the management UI cache contract visible at the plugin entry point.\n"
    if marker not in source:
        raise RuntimeError("main.py wrapper insertion marker missing")
    if "BEGIN MAIN COMMAND REGISTRATION" in source:
        raise RuntimeError("main.py command wrapper block already exists")

    wrappers = "\n\n".join(render_wrapper(item) for item in commands)
    block = (
        "    # BEGIN MAIN COMMAND REGISTRATION\n"
        "    # Decorators stay on the real Star entry module; implementations live below.\n"
        f"{wrappers}\n"
        "    # END MAIN COMMAND REGISTRATION\n\n"
    )
    source = source.replace(marker, block + marker, 1)
    ast.parse(source, filename=str(MAIN))
    MAIN.write_text(source, encoding="utf-8")


def write_contract_test(names: list[str]) -> None:
    expected = "\n".join(f'    "{name}",' for name in names)
    TEST.write_text(
        f'''from __future__ import annotations\n\nimport ast\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nHELPERS = {HELPERS!r}\nEXPECTED = {{\n{expected}\n}}\n\n\ndef _dotted(node: ast.AST) -> str:\n    if isinstance(node, ast.Call):\n        return _dotted(node.func)\n    if isinstance(node, ast.Attribute):\n        head = _dotted(node.value)\n        return f"{{head}}.{{node.attr}}" if head else node.attr\n    if isinstance(node, ast.Name):\n        return node.id\n    return ""\n\n\ndef _commands(path: Path) -> dict[str, ast.AsyncFunctionDef]:\n    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))\n    found: dict[str, ast.AsyncFunctionDef] = {{}}\n    for item in tree.body:\n        if not isinstance(item, ast.ClassDef):\n            continue\n        for fn in item.body:\n            if not isinstance(fn, ast.AsyncFunctionDef):\n                continue\n            if any(_dotted(dec) in {{"filter.command", "filter.command_group"}} for dec in fn.decorator_list):\n                found[fn.name] = fn\n    return found\n\n\ndef test_helper_modules_do_not_register_commands():\n    leaked = {{path: sorted(_commands(ROOT / path)) for path in HELPERS if _commands(ROOT / path)}}\n    assert not leaked, f"helper modules still own AstrBot commands: {{leaked}}"\n\n\ndef test_main_owns_complete_command_surface_with_explicit_priority():\n    commands = _commands(ROOT / "main.py")\n    assert set(commands) == EXPECTED\n    for name, fn in commands.items():\n        command_decorators = [dec for dec in fn.decorator_list if _dotted(dec) == "filter.command"]\n        assert command_decorators, f"{{name}} lost filter.command"\n        for dec in command_decorators:\n            assert isinstance(dec, ast.Call)\n            priorities = [kw.value for kw in dec.keywords if kw.arg == "priority"]\n            assert len(priorities) == 1, f"{{name}} must declare priority exactly once"\n            assert isinstance(priorities[0], ast.Constant) and priorities[0].value == 1000\n\n\ndef test_main_command_wrappers_delegate_to_inherited_implementation():\n    commands = _commands(ROOT / "main.py")\n    for name, fn in commands.items():\n        calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call)]\n        delegated = False\n        for call in calls:\n            func = call.func\n            if not isinstance(func, ast.Attribute) or func.attr != name:\n                continue\n            value = func.value\n            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "super":\n                delegated = True\n                break\n        assert delegated, f"{{name}} wrapper no longer delegates to super().{{name}}"\n\n\ndef test_runtime_rebind_workaround_is_removed():\n    source = (ROOT / "main.py").read_text(encoding="utf-8")\n    assert "_rebind_rollpig_handlers_to_entrypoint" not in source\n    assert "star_handlers_registry" not in source\n''',
        encoding="utf-8",
    )


def update_docs(names: list[str]) -> None:
    text = ARCH.read_text(encoding="utf-8")
    replacement = '''## AstrBot command registration boundary\n\nv3.6.2 後不再依賴運行時修改 handler metadata。所有 `@filter.command` / `@filter.command_group` 必須直接定義在真正的 `main.py` Star 入口；`legacy_main.py` 與 feature mixin 只保留可測試的業務方法。`main.py` 的薄 wrapper 只負責 AstrBot 註冊並 `await super().<handler>(...)` 委派，不複製玩法邏輯。\n\n所有 RollPig command 在 decorator 上顯式聲明 `priority=1000`，既不依賴註冊順序，也不需要 import 後重新排序 registry。handler 內仍保留 `event.stop_event()` 作為第二層隔離。AstrBot Market Smoke 必須同時驗證 `handler.__module__ == main`、`handler_module_path == main` 與 priority；任何後續拆分都不得把 command decorator 移回 helper module。\n\n這是漸進式拆分的第一個硬邊界：**命令註冊屬於入口，玩法實作屬於 service/feature。** 後續可以安全地逐步搬走 `legacy_main.py` 內容，而不再改變 AstrBot 的 handler ownership。\n\n'''
    text, count = re.subn(
        r"## AstrBot handler 所有權契約\n.*?(?=## Gameplay Event v1)",
        replacement,
        text,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("ARCHITECTURE handler ownership section not found")
    ARCH.write_text(text, encoding="utf-8")

    changelog = CHANGELOG.read_text(encoding="utf-8")
    needle = "## 未發佈\n\n- 暫無。"
    entry = (
        "## 未發佈\n\n"
        "### 架構\n\n"
        f"- 完成 command registration boundary 第一階段：{len(names)} 個 RollPig 指令 decorator 全部收回 `main.py` 真正 Star 入口，helper/mixin 僅保留業務方法；每個 command 顯式 `priority=1000` 並由薄 wrapper 委派，移除 v3.6.2 的 runtime handler rebind / registry 重排 workaround。\n"
        "- 新增 AST 契約測試，禁止 `legacy_main.py` / feature mixin 再註冊 AstrBot command，並要求入口 wrapper 保持完整指令面與 `super()` 委派。"
    )
    if needle not in changelog:
        raise RuntimeError("CHANGELOG unreleased placeholder not found")
    CHANGELOG.write_text(changelog.replace(needle, entry, 1), encoding="utf-8")


def main() -> None:
    commands: list[CommandMethod] = []
    for relative in HELPERS:
        commands.extend(remove_helper_command_decorators(ROOT / relative))
    names = [item.node.name for item in commands]
    if len(commands) != EXPECTED_COMMAND_COUNT:
        raise RuntimeError(
            f"expected {EXPECTED_COMMAND_COUNT} command handlers, found {len(commands)}: {names}"
        )
    if len(set(names)) != len(names):
        raise RuntimeError(f"duplicate command method names cannot be wrapped safely: {names}")
    rewrite_main(commands)
    write_contract_test(sorted(names))
    update_docs(sorted(names))
    print(f"migrated {len(commands)} command decorators to main.py")
    for item in commands:
        print(f"- {item.source_path}:{item.node.name}")


if __name__ == "__main__":
    main()
