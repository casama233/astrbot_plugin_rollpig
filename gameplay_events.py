from __future__ import annotations

import datetime
import time
import uuid
from collections.abc import Mapping
from typing import Any

EVENT_SCHEMA_VERSION = 1

# Current event kinds consumed by the daily report.
EVENT_ROAST_SUCCESS = "roast_success"
EVENT_ROAST_ESCAPE = "roast_escape"
EVENT_ROAST_BACKLASH = "roast_backlash"
EVENT_DAILY_SACRIFICE = "daily_sacrifice"

# Reserved gameplay kinds for the next feature layers. Defining the namespace
# here prevents each feature from inventing incompatible strings later.
EVENT_DRAW_COMPLETED = "draw_completed"
EVENT_PIG_UNLOCKED = "pig_unlocked"
EVENT_EX_LEVEL_UP = "ex_level_up"
EVENT_PITY_TRIGGERED = "pity_triggered"
EVENT_ROAST_RESERVATION_CREATED = "roast_reservation_created"
EVENT_ROAST_RESERVATION_JOINED = "roast_reservation_joined"
EVENT_ROAST_RESERVATION_TRIGGERED = "roast_reservation_triggered"
EVENT_ROAST_RESERVATION_CANCELLED = "roast_reservation_cancelled"
EVENT_OVEN_REFILL_STARTED = "oven_refill_started"
EVENT_OVEN_REFILL_SUPPORTED = "oven_refill_supported"
EVENT_OVEN_REFILL_SUCCEEDED = "oven_refill_succeeded"
EVENT_OVEN_REFILL_FAILED = "oven_refill_failed"


def build_gameplay_event(
    kind: str,
    *,
    actor_id: str = "",
    target_id: str = "",
    victim_id: str = "",
    pig_id: str = "",
    metadata: Mapping[str, Any] | None = None,
    event_id: str = "",
    at: int | None = None,
) -> dict[str, Any]:
    """Build the stable JSON shape shared by RollPig gameplay features.

    The first version deliberately stays compatible with the event dictionaries
    already written by the daily-report feature. New optional fields are
    additive, so old report state can be consumed without migration.
    """
    payload: dict[str, Any] = {
        "version": EVENT_SCHEMA_VERSION,
        "id": str(event_id or uuid.uuid4().hex),
        "kind": str(kind or "").strip(),
        "actor_id": str(actor_id or ""),
        "target_id": str(target_id or ""),
        "victim_id": str(victim_id or ""),
        "at": int(time.time() if at is None else at),
    }
    if pig_id:
        payload["pig_id"] = str(pig_id)
    if isinstance(metadata, Mapping) and metadata:
        payload["metadata"] = {str(key): value for key, value in metadata.items()}
    return payload


def append_gameplay_event(
    events: dict[str, Any],
    date_key: str,
    group_id: str,
    event: Mapping[str, Any],
    *,
    max_events: int = 2000,
) -> bool:
    """Append one event idempotently to the existing date/group bucket."""
    date_key = str(date_key or "").strip()
    group_id = str(group_id or "").strip()
    if not date_key or not group_id or not isinstance(event, Mapping):
        return False

    by_date = events.setdefault(date_key, {})
    if not isinstance(by_date, dict):
        by_date = {}
        events[date_key] = by_date
    rows = by_date.setdefault(group_id, [])
    if not isinstance(rows, list):
        rows = []
        by_date[group_id] = rows

    payload = dict(event)
    event_id = str(payload.get("id") or "")
    if event_id and any(
        isinstance(item, dict) and str(item.get("id") or "") == event_id
        for item in rows
    ):
        return False

    rows.append(payload)
    limit = max(1, int(max_events))
    if len(rows) > limit:
        del rows[:-limit]
    return True


def read_gameplay_events(
    events: Mapping[str, Any], date_key: str, group_id: str
) -> list[dict[str, Any]]:
    """Return defensive copies of one group's events for a natural day."""
    by_date = events.get(str(date_key), {}) if isinstance(events, Mapping) else {}
    rows = by_date.get(str(group_id), []) if isinstance(by_date, Mapping) else []
    return [dict(item) for item in rows if isinstance(item, Mapping)]


def prune_gameplay_events(
    events: dict[str, Any], today: datetime.date, keep_days: int = 14
) -> bool:
    """Prune old date buckets while preserving the existing on-disk shape."""
    changed = False
    cutoff = (today - datetime.timedelta(days=max(2, int(keep_days)))).isoformat()
    for date_key in list(events):
        if str(date_key) < cutoff:
            events.pop(date_key, None)
            changed = True
    return changed
