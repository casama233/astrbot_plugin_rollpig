from __future__ import annotations

import datetime
from collections import Counter
from typing import Any

try:
    from .gameplay_events import (
        EVENT_OVEN_REFILL_FAILED,
        EVENT_OVEN_REFILL_STARTED,
        EVENT_OVEN_REFILL_SUCCEEDED,
        EVENT_OVEN_REFILL_SUPPORTED,
        EVENT_ROAST_BACKLASH,
        EVENT_ROAST_ESCAPE,
        EVENT_ROAST_SUCCESS,
        prune_gameplay_events,
    )
except ImportError:  # pragma: no cover - direct module loading compatibility
    from gameplay_events import (
        EVENT_OVEN_REFILL_FAILED,
        EVENT_OVEN_REFILL_STARTED,
        EVENT_OVEN_REFILL_SUCCEEDED,
        EVENT_OVEN_REFILL_SUPPORTED,
        EVENT_ROAST_BACKLASH,
        EVENT_ROAST_ESCAPE,
        EVENT_ROAST_SUCCESS,
        prune_gameplay_events,
    )


def parse_report_time(value: Any, default: str = "23:50") -> tuple[int, int]:
    """Parse HH:MM safely; invalid values fall back to the provided default."""
    text = str(value or "").strip()
    try:
        hour_text, minute_text = text.split(":", 1)
        hour, minute = int(hour_text), int(minute_text)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (TypeError, ValueError):
        pass
    if text != default:
        return parse_report_time(default, "23:50")
    return 23, 50


def due_datetime(
    report_date: datetime.date,
    hour: int,
    minute: int,
    timezone: datetime.tzinfo,
    delay_seconds: int = 0,
) -> datetime.datetime:
    """Return the timezone-aware due datetime for a fixed report date."""
    base = datetime.datetime.combine(
        report_date,
        datetime.time(hour=int(hour), minute=int(minute)),
        tzinfo=timezone,
    )
    return base + datetime.timedelta(seconds=max(0, int(delay_seconds)))


def top_tied(counter: Counter[str]) -> dict[str, Any]:
    """Return a deterministic tied-top result suitable for UI rendering."""
    positive = {str(key): int(value) for key, value in counter.items() if int(value) > 0}
    if not positive:
        return {"value": 0, "winners": []}
    best = max(positive.values())
    winners = sorted(key for key, value in positive.items() if value == best)
    return {"value": best, "winners": winners}


def aggregate_daily_report(
    member_pigs: list[dict[str, Any]],
    events: list[dict[str, Any]],
    eaten_victims: list[str] | tuple[str, ...] | set[str],
    *,
    roast_total: int | None = None,
) -> dict[str, Any]:
    """Aggregate one group's daily RollPig activity into report-ready statistics.

    Event semantics:
    - roast_success: actor successfully roasted target; victim_id is target.
    - roast_escape: target escaped.
    - roast_backlash: target triggered backlash; victim_id is the actor only when
      the actor actually had a roastable pig and was roasted.
    - daily_sacrifice: optional report-time sacrifice (not a roast award event).
    """
    unique_members: dict[str, dict[str, Any]] = {}
    pig_counts: Counter[str] = Counter()
    pig_names: dict[str, str] = {}
    for item in member_pigs:
        if not isinstance(item, dict):
            continue
        user_id = str(item.get("user_id") or "")
        pig_id = str(item.get("pig_id") or "")
        if not user_id:
            continue
        unique_members[user_id] = item
        if pig_id and pig_id != "eaten":
            pig_counts[pig_id] += 1
            pig_names[pig_id] = str(item.get("pig_name") or pig_id)

    roast_maniac: Counter[str] = Counter()
    miserable: Counter[str] = Counter()
    escape_master: Counter[str] = Counter()
    backlash_king: Counter[str] = Counter()
    event_roasts = 0
    escapes = 0
    backlashes = 0
    oven_refill_started = 0
    oven_refill_supports = 0
    oven_refill_successes = 0
    oven_refill_failures = 0

    for raw in events:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "")
        actor = str(raw.get("actor_id") or "")
        target = str(raw.get("target_id") or "")
        victim = str(raw.get("victim_id") or "")
        if kind == EVENT_ROAST_SUCCESS:
            if actor:
                roast_maniac[actor] += 1
            if victim:
                miserable[victim] += 1
                event_roasts += 1
        elif kind == EVENT_ROAST_ESCAPE:
            escapes += 1
            if target:
                escape_master[target] += 1
        elif kind == EVENT_ROAST_BACKLASH:
            backlashes += 1
            if target:
                backlash_king[target] += 1
            if victim:
                miserable[victim] += 1
                event_roasts += 1
        elif kind == EVENT_OVEN_REFILL_STARTED:
            oven_refill_started += 1
            # 发起者会自动贡献本轮第 1 份煤。
            oven_refill_supports += 1
        elif kind == EVENT_OVEN_REFILL_SUPPORTED:
            oven_refill_supports += 1
        elif kind == EVENT_OVEN_REFILL_SUCCEEDED:
            oven_refill_successes += 1
        elif kind == EVENT_OVEN_REFILL_FAILED:
            oven_refill_failures += 1

    popular = top_tied(pig_counts)
    popular_has_trend = int(popular["value"] or 0) > 1
    popular_items = (
        [
            {"id": pig_id, "name": pig_names.get(pig_id, pig_id), "count": popular["value"]}
            for pig_id in popular["winners"]
        ]
        if popular_has_trend
        else []
    )
    victims = sorted({str(value) for value in eaten_victims if str(value)})
    total_roasts = event_roasts if roast_total is None else max(event_roasts, int(roast_total))
    roast_detail_missing = max(0, total_roasts - event_roasts)

    return {
        "active_users": len(unique_members),
        "draws": len(unique_members),
        "roasts": total_roasts,
        "eats": len(victims),
        "escapes": escapes,
        "backlashes": backlashes,
        "oven_refill_started": oven_refill_started,
        "oven_refill_supports": oven_refill_supports,
        "oven_refill_successes": oven_refill_successes,
        "oven_refill_failures": oven_refill_failures,
        "popular_pigs": popular_items,
        "pig_variety": len(pig_counts),
        "popular_peak": int(popular["value"] or 0),
        "popular_has_trend": popular_has_trend,
        "roast_detail_missing": roast_detail_missing,
        "roast_detail_complete": roast_detail_missing == 0,
        "awards": {
            "roast_maniac": top_tied(roast_maniac),
            "miserable_ingredient": top_tied(miserable),
            "escape_master": top_tied(escape_master),
            "backlash_king": top_tied(backlash_king),
        },
        "eaten_victims": victims,
    }


def prune_state(state: dict[str, Any], today: datetime.date, keep_days: int = 14) -> bool:
    """Prune dated report events/jobs while keeping group routing metadata."""
    changed = False
    events = state.get("events")
    if not isinstance(events, dict):
        events = {}
        state["events"] = events
        changed = True
    changed = prune_gameplay_events(events, today, keep_days) or changed

    jobs = state.get("jobs")
    if not isinstance(jobs, dict):
        jobs = {}
        state["jobs"] = jobs
        changed = True
    cutoff = (today - datetime.timedelta(days=max(2, int(keep_days)))).isoformat()
    for date_key in list(jobs):
        if str(date_key) < cutoff:
            jobs.pop(date_key, None)
            changed = True
    return changed
