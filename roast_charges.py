from __future__ import annotations

import math
from typing import Any, Mapping


def _limits(max_charges: int, recovery_seconds: int) -> tuple[int, int]:
    return max(1, int(max_charges)), max(1, int(recovery_seconds))


def refresh_roast_charge_state(
    state: Mapping[str, Any] | None,
    *,
    now: float,
    max_charges: int,
    recovery_seconds: int,
) -> dict[str, Any]:
    """Apply queued time-based refills without consuming a charge.

    ``refill_anchor`` marks when the oldest missing charge started recovering.
    Spending another charge while recovery is already running does not reset that
    timer; missing charges therefore refill one-by-one every configured interval.
    """
    capacity, interval = _limits(max_charges, recovery_seconds)
    current = state if isinstance(state, Mapping) else {}
    try:
        charges = int(current.get("charges", capacity))
    except (TypeError, ValueError):
        charges = capacity
    charges = min(capacity, max(0, charges))
    now_value = float(now)
    try:
        anchor = float(current.get("refill_anchor", now_value) or now_value)
    except (TypeError, ValueError):
        anchor = now_value

    if charges >= capacity:
        return {
            "charges": capacity,
            "max_charges": capacity,
            "refill_anchor": now_value,
            "next_refill_seconds": 0,
        }

    if anchor <= 0 or anchor > now_value:
        anchor = now_value
    elapsed = max(0.0, now_value - anchor)
    recovered = min(capacity - charges, int(elapsed // interval))
    if recovered:
        charges += recovered
        anchor += recovered * interval
        if charges >= capacity:
            anchor = now_value

    next_refill = (
        0
        if charges >= capacity
        else max(1, int(math.ceil(anchor + interval - now_value)))
    )
    return {
        "charges": charges,
        "max_charges": capacity,
        "refill_anchor": anchor,
        "next_refill_seconds": next_refill,
    }


def bootstrap_legacy_cooldown(
    last_used_at: float | int | None,
    *,
    now: float,
    max_charges: int,
    recovery_seconds: int,
) -> dict[str, Any]:
    """Translate the pre-charge cooldown into a fair initial token state.

    An active legacy cooldown represents one previously spent token. With the
    default capacity of two, upgrading therefore grants the still-unused second
    token while preserving the old refill timer. An expired or absent cooldown
    starts full.
    """
    capacity, interval = _limits(max_charges, recovery_seconds)
    now_value = float(now)
    try:
        used_at = float(last_used_at or 0)
    except (TypeError, ValueError):
        used_at = 0.0
    if used_at > 0 and now_value < used_at + interval:
        return refresh_roast_charge_state(
            {
                "charges": max(0, capacity - 1),
                "refill_anchor": used_at,
            },
            now=now_value,
            max_charges=capacity,
            recovery_seconds=interval,
        )
    return refresh_roast_charge_state(
        {"charges": capacity, "refill_anchor": now_value},
        now=now_value,
        max_charges=capacity,
        recovery_seconds=interval,
    )


def consume_roast_charge_state(
    state: Mapping[str, Any] | None,
    *,
    now: float,
    max_charges: int,
    recovery_seconds: int,
) -> dict[str, Any]:
    """Refresh and atomically describe one attempted token consumption."""
    refreshed = refresh_roast_charge_state(
        state,
        now=now,
        max_charges=max_charges,
        recovery_seconds=recovery_seconds,
    )
    charges = int(refreshed["charges"])
    capacity = int(refreshed["max_charges"])
    anchor = float(refreshed["refill_anchor"])
    now_value = float(now)
    interval = max(1, int(recovery_seconds))
    if charges <= 0:
        refreshed["consumed"] = False
        return refreshed

    if charges >= capacity:
        # The first missing charge starts its recovery window now.
        anchor = now_value
    charges -= 1
    next_refill = max(1, int(math.ceil(anchor + interval - now_value)))
    return {
        "charges": charges,
        "max_charges": capacity,
        "refill_anchor": anchor,
        "next_refill_seconds": next_refill,
        "consumed": True,
    }


def add_roast_charge_state(
    state: Mapping[str, Any] | None,
    *,
    now: float,
    max_charges: int,
    recovery_seconds: int,
) -> dict[str, Any]:
    """Refresh first, then grant at most one charge without exceeding capacity."""
    refreshed = refresh_roast_charge_state(
        state,
        now=now,
        max_charges=max_charges,
        recovery_seconds=recovery_seconds,
    )
    before = int(refreshed["charges"])
    capacity = int(refreshed["max_charges"])
    after = min(capacity, before + 1)
    anchor = float(refreshed["refill_anchor"])
    now_value = float(now)
    if after >= capacity:
        anchor = now_value
        next_refill = 0
    else:
        next_refill = int(refreshed.get("next_refill_seconds", 0) or 0)
    return {
        "charges": after,
        "max_charges": capacity,
        "refill_anchor": anchor,
        "next_refill_seconds": next_refill,
        "increased": after > before,
    }
