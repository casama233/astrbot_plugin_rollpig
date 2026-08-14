from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class OvenRefillService:
    """Pure cooperative refill threshold policy.

    Persistence, AstrBot events and identity resolution intentionally stay
    outside this service.  The second and later successful refills become more
    expensive through ``extra_per_success`` while never requiring more supporters
    than there are active RollPig players in the group.
    """

    @staticmethod
    def refill_requirement(
        active_count: int,
        successes_today: int,
        *,
        ratio_percent: int = 30,
        minimum_supporters: int = 3,
        extra_per_success: int = 2,
    ) -> int:
        active = max(0, int(active_count))
        if active < 2:
            return 0
        ratio = min(100, max(1, int(ratio_percent))) / 100.0
        minimum = max(2, int(minimum_supporters))
        base = max(minimum, int(math.ceil(active * ratio)))
        if active == 2:
            base = 2
        required = base + max(0, int(successes_today)) * max(
            0, int(extra_per_success)
        )
        return min(active, required)
