from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class DrawService:
    """Pure daily-draw selection policy, independent from persistence and AstrBot."""

    enable_new_pig_pity: bool = True
    pity_step_percent: int = 15

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
        if not self.enable_new_pig_pity:
            return chosen
        user = collection if isinstance(collection, Mapping) else {}
        unlocked_raw = user.get("pigs")
        unlocked = set(unlocked_raw) if isinstance(unlocked_raw, Mapping) else set()
        unseen = [pig for pig in pigs if str(pig.get("id") or "") not in unlocked]
        chosen_id = str(chosen.get("id") or "")
        if not unseen or chosen_id not in unlocked:
            return chosen
        streak = max(0, int(user.get("duplicate_streak", 0) or 0))
        chance = min(0.80, streak * max(0, self.pity_step_percent) / 100)
        return dict(rng.choice(unseen)) if rng.random() < chance else chosen
