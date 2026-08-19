from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from fontTools.ttLib import TTFont
from opencc import OpenCC

ROOT = Path(__file__).resolve().parents[1]
T2S = OpenCC("t2s")
CJK = re.compile(r"[\u3400-\u9fff]")

# Authored EX JSON is intentionally optional. During provenance quarantine the
# explicit bundled EX files may be absent; runtime then uses the deterministic
# baseline, which has its own behavior/content tests. If authored files are
# reintroduced later, this gate automatically resumes checking their copy.
JSON_TARGETS = [
    ROOT / "resource" / "pig.json",
    ROOT / "resource" / "pig_ex_variants.json",
    ROOT / "resource" / "roast_copy.json",
    *sorted((ROOT / "resource" / "ex_curated").glob("*.json")),
    ROOT / "_conf_schema.json",
    ROOT / ".astrbot-plugin" / "i18n" / "zh-CN.json",
]
DISPLAY_PYTHON = [
    ROOT / "animated_image_feature.py",
    ROOT / "ex_admin_feature.py",
    ROOT / "ex_public_source_feature.py",
    ROOT / "help_system.py",
    ROOT / "player_copy.py",
    ROOT / "roast_copy.py",
    ROOT / "services" / "catalog_service.py",
    *sorted((ROOT / "renderers").glob("*.py")),
]
LEGACY_ALLOWED_TRADITIONAL = {"強行點火"}


def strings(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, str):
        yield value


def python_strings(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield getattr(node, "lineno", 0), node.value


def assert_simplified(label: str, value: str, failures: list[str]) -> None:
    if CJK.search(value) and T2S.convert(value) != value:
        failures.append(f"{label}: contains Traditional display copy: {value!r}")


def main() -> int:
    failures: list[str] = []
    rendered: list[tuple[str, str]] = []

    for path in JSON_TARGETS:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for value in strings(payload):
            assert_simplified(str(path.relative_to(ROOT)), value, failures)
            if str(path).startswith(str(ROOT / "resource")):
                rendered.append((str(path.relative_to(ROOT)), value))

    for path in DISPLAY_PYTHON:
        for line, value in python_strings(path):
            assert_simplified(f"{path.relative_to(ROOT)}:{line}", value, failures)
            if (
                path.name in {"help_system.py", "player_copy.py"}
                or path.parent.name == "renderers"
            ):
                rendered.append((f"{path.relative_to(ROOT)}:{line}", value))

    legacy = ROOT / "legacy_main.py"
    for line, value in python_strings(legacy):
        if value in LEGACY_ALLOWED_TRADITIONAL:
            continue
        assert_simplified(f"legacy_main.py:{line}", value, failures)

    for path in sorted((ROOT / "pages").rglob("*")):
        if not path.is_file() or path.suffix not in {".html", ".js"}:
            continue
        for line_no, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if "ERROR_PATTERN" in line:
                continue
            assert_simplified(f"{path.relative_to(ROOT)}:{line_no}", line, failures)

    font = TTFont(ROOT / "resource" / "font" / "荆南麦圆体.otf")
    cmap: set[int] = set()
    for table in font["cmap"].tables:
        cmap.update(table.cmap.keys())

    for source, value in rendered:
        for ch in value:
            code = ord(ch)
            if 0x3400 <= code <= 0x9FFF and code not in cmap:
                failures.append(f"{source}: primary font missing {ch} U+{code:04X}")

    if failures:
        print("Display copy contract failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Display copy contract: Simplified Chinese + bundled font coverage OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
