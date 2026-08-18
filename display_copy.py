from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping

try:
    from opencc import OpenCC as _OpenCC
except ModuleNotFoundError:  # AstrBot smoke/bootstrap may import before plugin deps install.
    _OpenCC = None


_T2S = _OpenCC("t2s") if _OpenCC is not None else None


@lru_cache(maxsize=8192)
def simplify_display_text(value: object) -> str:
    """Normalize user-visible Chinese copy to Simplified Chinese.

    IDs, command aliases, config keys and protocol values must not pass through
    this helper. It is intentionally for names/descriptions/analysis/copy only.
    When AstrBot imports the plugin before installing plugin dependencies, keep
    the plugin load-safe; normal installed runtimes still use OpenCC from
    requirements.txt for complete Traditional-to-Simplified normalization.
    """
    text = str(value or "")
    return _T2S.convert(text) if _T2S is not None else text


def simplify_pig_display_copy(pig: Mapping[str, Any]) -> dict[str, Any]:
    """Copy one pig record and normalize only fields that can be displayed."""
    result = dict(pig)
    for key in ("name", "description", "analysis"):
        if key in result:
            result[key] = simplify_display_text(result.get(key))
    return result
