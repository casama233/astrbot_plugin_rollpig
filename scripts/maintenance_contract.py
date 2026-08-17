from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_BULLETS = {
    "- 暫無。",
    "- 暂无。",
    "- 無。",
    "- 无。",
    "* 暫無。",
    "* 暂无。",
}
USER_FACING_PREFIXES = (
    "pages/",
    "renderers/",
    "services/",
    "resource/",
)
USER_FACING_FILES = {
    "main.py",
    "legacy_main.py",
    "help_feature.py",
    "help_system.py",
    "daily_report_core.py",
    "daily_report_feature.py",
    "gameplay_events.py",
    "oven_refill_feature.py",
    "reservation_firewood_feature.py",
    "roast_reservation_feature.py",
    "permanent_collection_feature.py",
    "ex_admin_feature.py",
    "ex_public_source_feature.py",
    "ex_variant_feature.py",
    "ex_variants.py",
    "rollpig_core.py",
    "roast_charges.py",
    "roast_reservations.py",
    "updater.py",
    "_conf_schema.json",
    "README.md",
}


def _git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def _git_show(ref: str, path: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


def _changed_files(base: str, head: str) -> set[str]:
    output = _git("diff", "--name-only", "--diff-filter=ACMR", f"{base}...{head}")
    return {line.strip() for line in output.splitlines() if line.strip()}


def _markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _substantive_bullets(section: str) -> set[str]:
    bullets = {
        line.strip()
        for line in section.splitlines()
        if line.lstrip().startswith(("- ", "* "))
    }
    return {line for line in bullets if line not in PLACEHOLDER_BULLETS}


def _metadata_version(text: str) -> str:
    match = re.search(r"(?m)^version:\s*[\"']?([^\"'\n]+)", text)
    return match.group(1).strip() if match else ""


def _extract_commands(source: str) -> set[str]:
    if not source.strip():
        return set()
    tree = ast.parse(source)
    commands: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            func = decorator.func
            is_command = (
                isinstance(func, ast.Attribute)
                and func.attr == "command"
                and isinstance(func.value, ast.Name)
                and func.value.id == "filter"
            )
            if not is_command:
                continue
            first = decorator.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                commands.add(first.value)
    return commands


def _config_keys(text: str) -> set[str]:
    if not text.strip():
        return set()
    payload = json.loads(text)
    return set(payload) if isinstance(payload, dict) else set()


def _wiki_corpus(root: Path = ROOT) -> str:
    docs_root = root / "docs"
    parts: list[str] = []
    if docs_root.is_dir():
        for path in sorted(docs_root.rglob("*.md")):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _coverage_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    main_source = (root / "main.py").read_text(encoding="utf-8")
    commands = _extract_commands(main_source)
    wiki = _wiki_corpus(root)
    missing_commands = sorted(cmd for cmd in commands if f"/{cmd}" not in wiki)
    if missing_commands:
        errors.append(
            "Wiki 未覆盖这些 canonical 指令：" + ", ".join(f"/{item}" for item in missing_commands)
        )

    schema_text = (root / "_conf_schema.json").read_text(encoding="utf-8")
    config_keys = _config_keys(schema_text)
    config_doc = (root / "docs" / "CONFIGURATION.md").read_text(encoding="utf-8")
    missing_keys = sorted(key for key in config_keys if key not in config_doc)
    if missing_keys:
        errors.append(
            "docs/CONFIGURATION.md 未覆盖这些配置键：" + ", ".join(missing_keys)
        )
    return errors


def _is_user_facing(path: str) -> bool:
    if path in USER_FACING_FILES:
        return True
    if path.startswith(USER_FACING_PREFIXES):
        return True
    if path.endswith(".py") and "/" not in path:
        return True
    return False


def _wiki_declaration(body: str) -> tuple[str, str]:
    match = re.search(r"(?im)^\s*Wiki-Impact\s*:\s*(.+?)\s*$", body or "")
    if not match:
        return "", ""
    value = match.group(1).strip()
    lowered = value.lower()
    if lowered.startswith("updated") or value.startswith("已更新"):
        return "updated", value
    if lowered.startswith("none") or value.startswith(("无需", "無需")):
        reason = re.sub(r"^(?:none|无需|無需)\s*[:：—–-]?\s*", "", value, flags=re.I)
        return "none", reason.strip()
    return "invalid", value


def _check_changelog(base: str, head: str, changed: set[str]) -> list[str]:
    errors: list[str] = []
    if "CHANGELOG.md" not in changed:
        return ["每个 PR 都必须维护 CHANGELOG.md。"]

    base_changelog = _git_show(base, "CHANGELOG.md")
    head_changelog = _git_show(head, "CHANGELOG.md")
    base_version = _metadata_version(_git_show(base, "metadata.yaml"))
    head_version = _metadata_version(_git_show(head, "metadata.yaml"))

    if base_version and head_version and base_version != head_version:
        release_section = _markdown_section(head_changelog, f"v{head_version}")
        if not release_section:
            errors.append(f"Release PR 必须在 CHANGELOG.md 中新增 ## v{head_version}。")
        notes_path = f".github/release-v{head_version}.md"
        if not _git_show(head, notes_path):
            errors.append(f"Release PR 缺少 {notes_path}。")
        if notes_path not in changed:
            errors.append(f"Release PR 必须在本 PR 中维护 {notes_path}，不能复用旧文件。")
        return errors

    base_unreleased = _substantive_bullets(_markdown_section(base_changelog, "未發佈"))
    head_unreleased = _substantive_bullets(_markdown_section(head_changelog, "未發佈"))
    added = head_unreleased - base_unreleased
    if not added:
        errors.append(
            "非 Release PR 必须在 CHANGELOG.md 的「## 未發佈」下新增至少一条非占位记录。"
        )
    return errors


def _check_wiki_impact(base: str, head: str, changed: set[str], body: str) -> list[str]:
    errors: list[str] = []
    docs_changed = sorted(
        path for path in changed if path.startswith("docs/") and path.endswith(".md")
    )
    user_facing = sorted(path for path in changed if _is_user_facing(path))
    mode, detail = _wiki_declaration(body)

    if mode == "":
        errors.append(
            "PR 描述必须声明 `Wiki-Impact: updated` 或 `Wiki-Impact: none — <原因>`。"
        )
    elif mode == "invalid":
        errors.append("Wiki-Impact 声明格式无效。")
    elif mode == "updated" and not docs_changed:
        errors.append("Wiki-Impact 标记为 updated，但本 PR 没有修改任何 docs/**/*.md。")
    elif mode == "none" and len(detail) < 12:
        errors.append("Wiki-Impact: none 必须给出具体原因，不能只写 none。")

    base_commands = _extract_commands(_git_show(base, "main.py"))
    head_commands = _extract_commands(_git_show(head, "main.py"))
    command_delta = base_commands ^ head_commands
    if command_delta:
        if "docs/COMMANDS.md" not in changed:
            errors.append(
                "canonical 指令集合发生变化，必须同步修改 docs/COMMANDS.md。"
            )
        command_doc = _git_show(head, "docs/COMMANDS.md")
        missing_added = sorted(
            cmd for cmd in (head_commands - base_commands) if f"/{cmd}" not in command_doc
        )
        if missing_added:
            errors.append(
                "新增 canonical 指令未写入 docs/COMMANDS.md："
                + ", ".join(f"/{item}" for item in missing_added)
            )
        if mode == "none":
            errors.append("指令集合变化不能使用 Wiki-Impact: none。")

    base_config = _config_keys(_git_show(base, "_conf_schema.json"))
    head_config = _config_keys(_git_show(head, "_conf_schema.json"))
    config_delta = base_config ^ head_config
    if config_delta:
        if "docs/CONFIGURATION.md" not in changed:
            errors.append("配置 schema 发生变化，必须同步修改 docs/CONFIGURATION.md。")
        config_doc = _git_show(head, "docs/CONFIGURATION.md")
        missing_added = sorted(key for key in (head_config - base_config) if key not in config_doc)
        if missing_added:
            errors.append(
                "新增配置键未写入 docs/CONFIGURATION.md：" + ", ".join(missing_added)
            )
        if mode == "none":
            errors.append("配置 schema 变化不能使用 Wiki-Impact: none。")

    if user_facing and mode == "updated" and not docs_changed:
        errors.append("用户可见代码发生变化时，Wiki-Impact: updated 必须伴随 Wiki 修改。")

    return errors


def check_pr(base: str, head: str, event_path: str) -> list[str]:
    changed = _changed_files(base, head)
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except Exception:
        event = {}
    body = str((event.get("pull_request") or {}).get("body") or "")

    errors = []
    errors.extend(_check_changelog(base, head, changed))
    errors.extend(_check_wiki_impact(base, head, changed, body))
    return errors


def check_release(root: Path = ROOT) -> list[str]:
    errors = _coverage_errors(root)
    metadata = (root / "metadata.yaml").read_text(encoding="utf-8")
    version = _metadata_version(metadata)
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append("metadata.yaml 的 version 必须是稳定 x.y.z。")
        return errors

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    release_section = _markdown_section(changelog, f"v{version}")
    if not release_section:
        errors.append(f"CHANGELOG.md 缺少当前版本 ## v{version}。")
    notes_path = root / ".github" / f"release-v{version}.md"
    if not notes_path.is_file() or not notes_path.read_text(encoding="utf-8").strip():
        errors.append(f"缺少非空 Release Notes：.github/release-v{version}.md")
    if not re.search(r"(?m)^##\s+未發佈\s*$", changelog):
        errors.append("CHANGELOG.md 必须保留 ## 未發佈 区。")
    return errors


def _print_result(errors: list[str]) -> int:
    if not errors:
        print("Maintenance contract: OK")
        return 0
    print("Maintenance contract failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("pr")
    pr.add_argument("--base", required=True)
    pr.add_argument("--head", required=True)
    pr.add_argument("--event", required=True)

    sub.add_parser("coverage")
    sub.add_parser("release")
    args = parser.parse_args()

    if args.command == "pr":
        return _print_result(check_pr(args.base, args.head, args.event))
    if args.command == "coverage":
        return _print_result(_coverage_errors())
    return _print_result(check_release())


if __name__ == "__main__":
    raise SystemExit(main())
