from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_SKIP_TAGS = {"code", "pre", "script", "style", "textarea"}
_MARKERS = (
    ("heading", re.compile(r"(?m)(?:^|\n)\s*#{2,6}\s+\S")),
    ("strong", re.compile(r"\*\*[^*\n]+\*\*")),
    ("link", re.compile(r"\[[^\]\n]+\]\([^\n)]+\)")),
    ("inline-code", re.compile(r"`[^`\n]+`")),
    ("list-item", re.compile(r"(?m)(?:^|\n)\s*[-*+]\s+\S")),
)
_REQUIRED_IDS = {
    Path("troubleshooting/admin/index.html"): ("resource-sync", "admin-ui"),
}


class PigUiMarkdownLeakParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack: list[tuple[str, bool, bool]] = []
        self.pig_depth = 0
        self.skip_depth = 0
        self.leaks: list[str] = []

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
        for key, value in attrs:
            if key == "class" and value:
                return set(value.split())
        return set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        classes = self._classes(attrs)
        is_pig = any(name.startswith("pig-") for name in classes)
        is_skip = tag in _SKIP_TAGS

        if is_pig:
            self.pig_depth += 1
        if is_skip:
            self.skip_depth += 1

        if tag not in _VOID_TAGS:
            self.stack.append((tag, is_pig, is_skip))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closing elements cannot contain leaked Markdown text.
        return

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] != tag:
                continue
            closing = self.stack[index:]
            del self.stack[index:]
            for _, is_pig, is_skip in closing:
                if is_pig:
                    self.pig_depth = max(0, self.pig_depth - 1)
                if is_skip:
                    self.skip_depth = max(0, self.skip_depth - 1)
            return

    def handle_data(self, data: str) -> None:
        if self.pig_depth <= 0 or self.skip_depth > 0:
            return
        for name, pattern in _MARKERS:
            match = pattern.search(data)
            if not match:
                continue
            excerpt = " ".join(data.strip().split())[:160]
            self.leaks.append(f"{self.path}: {name}: {excerpt}")


def scan(site_dir: Path) -> list[str]:
    leaks: list[str] = []
    for path in sorted(site_dir.rglob("*.html")):
        parser = PigUiMarkdownLeakParser(path)
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        leaks.extend(parser.leaks)
    return leaks


def missing_required_anchors(site_dir: Path) -> list[str]:
    failures: list[str] = []
    for relative_path, ids in _REQUIRED_IDS.items():
        path = site_dir / relative_path
        if not path.is_file():
            failures.append(f"missing rendered page: {relative_path}")
            continue
        html = path.read_text(encoding="utf-8")
        for anchor_id in ids:
            if f'id="{anchor_id}"' not in html:
                failures.append(f"{relative_path}: missing id=\"{anchor_id}\"")
    return failures


def main() -> int:
    site_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    if not site_dir.is_dir():
        print(f"wiki render check: site directory not found: {site_dir}", file=sys.stderr)
        return 2

    leaks = scan(site_dir)
    anchor_failures = missing_required_anchors(site_dir)
    if not leaks and not anchor_failures:
        print(
            "wiki render check: no raw Markdown leaked inside pig-* UI containers; "
            "required deep-link anchors are present"
        )
        return 0

    if leaks:
        print("wiki render check: raw Markdown leaked into rendered pig UI:", file=sys.stderr)
        for leak in leaks[:40]:
            print(f"- {leak}", file=sys.stderr)
        if len(leaks) > 40:
            print(f"... and {len(leaks) - 40} more", file=sys.stderr)

    if anchor_failures:
        print("wiki render check: required deep-link anchors are missing:", file=sys.stderr)
        for failure in anchor_failures:
            print(f"- {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
