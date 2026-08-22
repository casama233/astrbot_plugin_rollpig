from __future__ import annotations

import random
from typing import Sequence


class EatService:
    """Pure randomness policy for group-eat actions.

    The service intentionally owns a private ``SystemRandom`` source so another
    AstrBot plugin calling ``random.seed(...)`` cannot make eat outcomes or
    random target selection predictable.
    """

    EAT_OUTCOMES = ("success", "escape", "backlash")

    def __init__(self, rng=None):
        self._rng = rng or random.SystemRandom()

    @staticmethod
    def outcome_weights(
        success_percent: int,
        escape_percent: int,
        *,
        success_bonus_percent: int = 0,
    ) -> tuple[int, int, int]:
        """Return a clamped success / escape / backlash distribution.

        Bonus success chance first steals probability from backlash. If success
        plus escape would exceed 100, escape is trimmed; effective success is
        capped at 90 so even a heavily tuned cooked target keeps some risk.
        """

        success = min(
            90,
            max(0, int(success_percent)) + max(0, int(success_bonus_percent)),
        )
        escape = min(max(0, int(escape_percent)), max(0, 100 - success))
        backlash = max(0, 100 - success - escape)
        return success, escape, backlash

    def choose_eat_outcome(
        self,
        *,
        success_percent: int,
        escape_percent: int,
        success_bonus_percent: int = 0,
        rng=None,
    ) -> str:
        chooser = rng or self._rng
        weights = self.outcome_weights(
            success_percent,
            escape_percent,
            success_bonus_percent=success_bonus_percent,
        )
        return str(chooser.choices(self.EAT_OUTCOMES, weights=weights, k=1)[0])

    def choose_group_eat_target(self, candidates: Sequence[str], *, rng=None) -> str:
        pool = tuple(str(item) for item in candidates if str(item))
        if not pool:
            raise ValueError("eat target candidates must not be empty")
        chooser = rng or self._rng
        return str(chooser.choice(pool))
