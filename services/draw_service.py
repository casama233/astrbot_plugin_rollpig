from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DrawService:
    """Pure daily-draw selection policy, independent from persistence and AstrBot."""

    enable_new_pig_pity: bool = True
    pity_step_percent: int = 15
    enable_daily_duplicate_pity: bool = True
    daily_duplicate_pity_start_day: int = 2
    daily_duplicate_pity_step_percent: int = 5
    daily_duplicate_pity_max_percent: int = 15
    max_pity_percent: int = 80

    @staticmethod
    def _streak(collection: Mapping[str, Any] | None, key: str) -> int:
        user = collection if isinstance(collection, Mapping) else {}
        try:
            return max(0, int(user.get(key, 0) or 0))
        except (TypeError, ValueError):
            return 0

    def pity_chance(self, collection: Mapping[str, Any] | None) -> float:
        """Return the reroll-to-unseen probability for a duplicate candidate.

        ``duplicate_streak`` keeps the legacy consecutive-draw behavior.
        ``daily_duplicate_streak`` counts only adjacent completed calendar days, so
        skipping a day resets the new fatigue bonus without changing legacy pity.
        """
        legacy_streak = self._streak(collection, "duplicate_streak")
        daily_streak = self._streak(collection, "daily_duplicate_streak")

        base_percent = 0
        if self.enable_new_pig_pity:
            base_percent = legacy_streak * max(0, int(self.pity_step_percent))

        daily_bonus_percent = 0
        if self.enable_daily_duplicate_pity:
            start_day = min(7, max(2, int(self.daily_duplicate_pity_start_day)))
            step_percent = max(0, int(self.daily_duplicate_pity_step_percent))
            bonus_cap = max(0, int(self.daily_duplicate_pity_max_percent))
            current_duplicate_day = daily_streak + 1
            if current_duplicate_day >= start_day:
                bonus_layers = current_duplicate_day - start_day + 1
                daily_bonus_percent = min(bonus_cap, bonus_layers * step_percent)

        total_percent = min(
            max(0, int(self.max_pity_percent)),
            base_percent + daily_bonus_percent,
        )
        return total_percent / 100

    def choose(
        self,
        pigs: Sequence[Mapping[str, Any]],
        collection: Mapping[str, Any] | None,
        *,
        rng: Any = random,
    ) -> dict[str, Any]:
        if not pigs:
            raise ValueError("pig catalog is empty")
        chosen = dict(rng.choice(pigs))
        if not (self.enable_new_pig_pity or self.enable_daily_duplicate_pity):
            return chosen

        user = collection if isinstance(collection, Mapping) else {}
        unlocked_raw = user.get("pigs")
        unlocked = set(unlocked_raw) if isinstance(unlocked_raw, Mapping) else set()
        unseen = [pig for pig in pigs if str(pig.get("id") or "") not in unlocked]
        chosen_id = str(chosen.get("id") or "")
        if not unseen or chosen_id not in unlocked:
            return chosen

        chance = self.pity_chance(user)
        return dict(rng.choice(unseen)) if rng.random() < chance else chosen
