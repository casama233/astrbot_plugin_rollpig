from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


def _bounded_number(
    config: Mapping[str, object],
    key: str,
    default: int,
    minimum: int,
    maximum: int,
    convert: type[int] | type[float],
) -> int | float:
    try:
        value = convert(config.get(key, default))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


@dataclass(frozen=True)
class ResourceSyncSettings:
    """Normalize sync limits without owning plugin state, migration or I/O."""

    interval_hours: float
    timeout: float
    use_system_proxy: bool
    max_file_size: int

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> ResourceSyncSettings:
        proxy = config.get("resource_use_system_proxy", False)
        return cls(
            interval_hours=_bounded_number(
                config, "resource_sync_interval_hours", 6, 1, 168, float
            ),
            timeout=_bounded_number(
                config, "resource_sync_timeout", 30, 2, 120, float
            ),
            use_system_proxy=(
                proxy
                if isinstance(proxy, bool)
                else str(proxy).strip().lower() in {"1", "true", "yes", "on"}
            ),
            max_file_size=int(_bounded_number(
                config, "resource_max_file_size_mb", 10, 1, 50, int
            )) * 1024 * 1024,
        )
