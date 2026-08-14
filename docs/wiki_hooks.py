from __future__ import annotations

from typing import Any


_REPO_ROOT_LINKS = {
    "../CONTRIBUTING.md": "https://github.com/casama233/astrbot_plugin_rollpig/blob/main/CONTRIBUTING.md",
    "../CHANGELOG.md": "https://github.com/casama233/astrbot_plugin_rollpig/blob/main/CHANGELOG.md",
}


def on_page_markdown(markdown: str, **_: Any) -> str:
    """Adapt intentional repo-root Markdown links for the GitHub Pages build.

    Repository docs are also read directly on GitHub, where ``../`` links are
    useful. MkDocs deliberately confines documentation to ``docs/`` and warns
    about those targets. Keep the source docs natural for GitHub while mapping
    the small known repo-root surface to canonical URLs during site rendering.
    """

    for source, target in _REPO_ROOT_LINKS.items():
        markdown = markdown.replace(f"]({source})", f"]({target})")
    return markdown
