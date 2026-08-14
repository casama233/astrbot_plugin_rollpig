from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class OvenChargeService:
    """Pure charge/refill policy for group roasting.

    Persistence, identities and AstrBot events deliberately stay outside this
    service.  ``anchor_at`` marks the start of recovery progress while the
    account is below the configured maximum.
    """

    @staticmethod
    def normalize_entry(
        entry: Mapping[str, Any] | None,
        *,
        now: float,
        max_charges: int,
        recovery_seconds: int,
    ) -> dict[str, float | int]:
        maximum = max(1, int(max_charges))
        interval = max(1, int(recovery_seconds))
        current = entry if isinstance(entry, Mapping) else {}
        try:
            charges = int(current.get("charges", maximum))
        except (TypeError, ValueError):
            charges = maximum
        charges = min(maximum, max(0, charges))
        try:
            anchor = float(current.get("anchor_at", now) or now)
        except (TypeError, ValueError):
            anchor = float(now)
        anchor = min(float(now), max(0.0, anchor))

        if charges >= maximum:
            return {"charges": maximum, "anchor_at": float(now)}

        elapsed = max(0.0, float(now) - anchor)
        recovered = int(elapsed // interval)
        if recovered <= 0:
            return {"charges": charges, "anchor_at": anchor}

        charges = min(maximum, charges + recovered)
        if charges >= maximum:
            return {"charges": maximum, "anchor_at": float(now)}
        return {
            "charges": charges,
            "anchor_at": anchor + recovered * interval,
        }

    @classmethod
    def consume(
        cls,
        entry: Mapping[str, Any] | None,
        *,
        now: float,
        max_charges: int,
        recovery_seconds: int,
    ) -> dict[str, Any]:
        maximum = max(1, int(max_charges))
        interval = max(1, int(recovery_seconds))
        normalized = cls.normalize_entry(
            entry,
            now=now,
            max_charges=maximum,
            recovery_seconds=interval,
        )
        charges = int(normalized["charges"])
        anchor = float(normalized["anchor_at"])
        if charges <= 0:
            remaining = max(1, int(math.ceil(anchor + interval - float(now))))
            return {
                "consumed": False,
                "remaining": remaining,
                "charges": 0,
                "entry": normalized,
            }

        before = charges
        charges -= 1
        # Spending from full starts a fresh recovery interval. Spending while
        # already below full preserves any partial progress toward the next cell.
        if before >= maximum:
            anchor = float(now)
        updated = {"charges": charges, "anchor_at": anchor}
        return {
            "consumed": True,
            "remaining": 0,
            "charges": charges,
            "entry": updated,
        }

    @classmethod
    def add_one(
        cls,
        entry: Mapping[str, Any] | None,
        *,
        now: float,
        max_charges: int,
        recovery_seconds: int,
    ) -> dict[str, float | int]:
        maximum = max(1, int(max_charges))
        normalized = cls.normalize_entry(
            entry,
            now=now,
            max_charges=maximum,
            recovery_seconds=recovery_seconds,
        )
        charges = min(maximum, int(normalized["charges"]) + 1)
        return {
            "charges": charges,
            "anchor_at": float(now) if charges >= maximum else float(normalized["anchor_at"]),
        }

    @classmethod
    def status(
        cls,
        entry: Mapping[str, Any] | None,
        *,
        now: float,
        max_charges: int,
        recovery_seconds: int,
    ) -> dict[str, Any]:
        maximum = max(1, int(max_charges))
        interval = max(1, int(recovery_seconds))
        normalized = cls.normalize_entry(
            entry,
            now=now,
            max_charges=maximum,
            recovery_seconds=interval,
        )
        charges = int(normalized["charges"])
        remaining = 0
        if charges < maximum:
            remaining = max(
                1,
                int(math.ceil(float(normalized["anchor_at"]) + interval - float(now))),
            )
        return {
            "charges": charges,
            "max_charges": maximum,
            "remaining": remaining,
            "entry": normalized,
        }

    @staticmethod
    def refill_requirement(active_count: int, successes_today: int) -> int:
        active = max(0, int(active_count))
        if active < 2:
            return 0
        base = min(8, max(3, int(math.ceil(active * 0.30))))
        if active == 2:
            base = 2
        return min(active, base + max(0, int(successes_today)) * 2)
