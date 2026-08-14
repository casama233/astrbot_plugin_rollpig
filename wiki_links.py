from __future__ import annotations

from urllib.parse import urljoin


WIKI_BASE_URL = "https://casama233.github.io/astrbot_plugin_rollpig/"


def wiki_url(path: str = "") -> str:
    """Return one canonical public Piggy Wiki URL."""

    normalized = str(path or "").strip().lstrip("/")
    return urljoin(WIKI_BASE_URL, normalized)


WIKI_HOME_URL = wiki_url()
WIKI_PLAYER_URL = wiki_url("gameplay/")
WIKI_ADMIN_URL = wiki_url("CONFIGURATION/")
WIKI_CREATOR_URL = wiki_url("creators/")
WIKI_TROUBLESHOOTING_URL = wiki_url("troubleshooting/")
WIKI_RESOURCE_SYNC_HELP_URL = wiki_url("troubleshooting/#resource-sync")
WIKI_ADMIN_UI_HELP_URL = wiki_url("troubleshooting/#admin-ui")
