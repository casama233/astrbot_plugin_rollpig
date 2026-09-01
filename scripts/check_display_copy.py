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
    *sorted((ROOT / "resource").glob("bundled_ex_copy*.json")),
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

    font_path = ROOT / "resource" / "font" / "荆南麦圆体.otf"
    if not font_path.is_file():
        failures.append(f"missing bundled image font: {font_path.relative_to(ROOT)}")
    else:
        font = TTFont(font_path)
        cmap = set()
        for table in font["cmap"].tables:
            cmap.update(table.cmap)
        missing: dict[str, set[str]] = {}
        for label, value in rendered:
            chars = {ch for ch in value if CJK.fullmatch(ch)} - LEGACY_ALLOWED_TRADITIONAL
            absent = {ch for ch in chars if ord(ch) not in cmap}
            if absent:
                missing.setdefault(label, set()).update(absent)
        for label, chars in sorted(missing.items()):
            failures.append(
                f"{label}: bundled font misses CJK glyphs: {''.join(sorted(chars))}"
            )

    if failures:
        print("Display-copy/font coverage check failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("Display-copy/font coverage check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
