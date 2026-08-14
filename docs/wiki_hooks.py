from __future__ import annotations

import re
from typing import Any


_REPO_ROOT_LINKS = {
    "../CONTRIBUTING.md": "https://github.com/casama233/astrbot_plugin_rollpig/blob/main/CONTRIBUTING.md",
    "../CHANGELOG.md": "https://github.com/casama233/astrbot_plugin_rollpig/blob/main/CHANGELOG.md",
}

# These pages intentionally mix Markdown copy with several layers of custom
# <div> containers. Python-Markdown's md_in_html extension requires every
# block-level HTML ancestor to opt in; one unmarked wrapper makes all nested
# Markdown render as literal text. Keep the source readable and normalize the
# complete div chain just before MkDocs parses each handcrafted Wiki page.
_RICH_WIKI_PAGES = {
    "index.md",
    "getting-started/index.md",
    "gameplay/index.md",
    "gameplay/collection-pity.md",
    "gameplay/ex-growth.md",
    "gameplay/roast-outcomes.md",
    "gameplay/roast-charge.md",
    "gameplay/daily-report.md",
    "creators/index.md",
    "troubleshooting/index.md",
}

_DIV_OPEN_RE = re.compile(r"<div(?P<attrs>\s[^<>]*?)?>", re.IGNORECASE)
_MARKDOWN_ATTR_RE = re.compile(
    r"\smarkdown(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?",
    re.IGNORECASE,
)


def _enable_nested_markdown(markdown: str) -> str:
    """Opt every div on rich Wiki pages into md_in_html block parsing.

    Bare ``markdown`` attributes are normalized to the documented
    ``markdown=\"1\"`` form. Unmarked divs receive the same attribute so nested
    cards/steps cannot accidentally disable Markdown parsing for descendants.
    """

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if _MARKDOWN_ATTR_RE.search(tag):
            return _MARKDOWN_ATTR_RE.sub(' markdown="1"', tag, count=1)
        return f'{tag[:-1]} markdown="1">'

    return _DIV_OPEN_RE.sub(replace, markdown)


def on_page_markdown(markdown: str, page: Any | None = None, **_: Any) -> str:
    """Adapt repository links and rich Wiki HTML before Markdown rendering."""

    for source, target in _REPO_ROOT_LINKS.items():
        markdown = markdown.replace(f"]({source})", f"]({target})")

    src_uri = getattr(getattr(page, "file", None), "src_uri", "")
    if src_uri in _RICH_WIKI_PAGES:
        markdown = _enable_nested_markdown(markdown)

    return markdown
