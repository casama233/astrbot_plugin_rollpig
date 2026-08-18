from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping

from opencc import OpenCC


_T2S = OpenCC("t2s")


@lru_cache(maxsize=8192)
def simplify_display_text(value: object) -> str:
    """Normalize user-visible Chinese copy to Simplified Chinese.

    IDs, command aliases, config keys and protocol values must not pass through
    this helper. It is intentionally for names/descriptions/analysis/copy only.
    """
    return _T2S.convert(str(value or ""))


def simplify_pig_display_copy(pig: Mapping[str, Any]) -> dict[str, Any]:
    """Copy one pig record and normalize only fields that can be displayed."""
    result = dict(pig)
    for key in ("name", "description", "analysis"):
        if key in result:
  result[key] = simplify_display_text(result.get(key))
    return result
