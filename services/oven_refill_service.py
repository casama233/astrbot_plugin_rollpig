from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class OvenRefillService:
    """Pure cooperative refill threshold policy.

    Persistence, identities and AstrBot events stay outside this service. The
    first refill uses a bounded percentage of today's active players; later
    successful rounds get progressively harder without ever requiring more
    supporters than the active population.
    """

    @staticmethod
    def refill_requirement(
        active_count: int,
        successes_today: int,
        *,
        ratio_percent: int = 30,
        minimum_supporters: int = 3,
        maximum_base_supporters: int = 8,
        extra_per_success: int = 2,
    ) -> int:
        active = max(0, int(active_count))
        if active < 2:
            return 0
        if active == 2:
            return 2

        ratio = min(100, max(1, int(ratio_percent))) / 100.0
        minimum = max(2, int(minimum_supporters))
        maximum = max(minimum, int(maximum_base_supporters))
        base = max(minimum, int(math.ceil(active * ratio)))
        base = min(maximum, base)
        required = base + max(0, int(successes_today)) * max(
            0, int(extra_per_success)
        )
        return min(active, required)
