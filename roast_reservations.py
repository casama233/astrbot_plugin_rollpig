from __future__ import annotations

import datetime
import time
import uuid
from collections.abc import Mapping
from typing import Any

RESERVATION_STATE_VERSION = 1
RESERVATION_PENDING = "pending"
RESERVATION_RESOLVED = "resolved"


def ensure_reservation_state(state: Any) -> dict[str, Any]:
    """Normalize the small auxiliary reservation document in-place when possible."""
    if not isinstance(state, dict):
        state = {}
    state["version"] = RESERVATION_STATE_VERSION
    if not isinstance(state.get("reservations"), dict):
        state["reservations"] = {}
    return state


def get_reservation(
    state: Mapping[str, Any], draw_date: str, group_id: str, target_id: str
) -> dict[str, Any] | None:
    dates = state.get("reservations", {}) if isinstance(state, Mapping) else {}
    groups = dates.get(str(draw_date), {}) if isinstance(dates, Mapping) else {}
    targets = groups.get(str(group_id), {}) if isinstance(groups, Mapping) else {}
    row = targets.get(str(target_id)) if isinstance(targets, Mapping) else None
    return dict(row) if isinstance(row, Mapping) else None


def list_pending_reservations(
    state: Mapping[str, Any], draw_date: str, group_id: str
) -> list[dict[str, Any]]:
    """Return stable copies of this group's pending reservations for one day."""
    dates = state.get("reservations", {}) if isinstance(state, Mapping) else {}
    groups = dates.get(str(draw_date), {}) if isinstance(dates, Mapping) else {}
    targets = groups.get(str(group_id), {}) if isinstance(groups, Mapping) else {}
    if not isinstance(targets, Mapping):
        return []
    rows: list[dict[str, Any]] = []
    for raw_target, raw_row in targets.items():
        if not isinstance(raw_row, Mapping):
            continue
        if str(raw_row.get("status") or "") != RESERVATION_PENDING:
            continue
        row = dict(raw_row)
        row.setdefault("target_id", str(raw_target))
        rows.append(row)
    rows.sort(key=lambda item: (int(item.get("created_at", 0) or 0), str(item.get("target_id") or "")))
    return rows


def create_or_join_reservation(
    state: dict[str, Any],
    *,
    draw_date: str,
    group_id: str,
    target_id: str,
    actor_id: str,
    max_participants: int = 12,
    now: int | None = None,
) -> dict[str, Any]:
    """Create one reservation or join its free support list.

    The caller decides whether a newly-created reservation consumes gameplay
    resources. Existing participants are idempotent and never consume again. A
    resolved reservation is terminal for its date/group/target key and cannot be
    reopened by a racing request.
    """
    ensure_reservation_state(state)
    date_key = str(draw_date or "").strip()
    group_key = str(group_id or "").strip()
    target_key = str(target_id or "").strip()
    actor_key = str(actor_id or "").strip()
    if not all((date_key, group_key, target_key, actor_key)):
        return {"status": "invalid"}
    if actor_key == target_key:
        return {"status": "self"}
    limit = min(20, max(2, int(max_participants)))
    dates = state["reservations"]
    groups = dates.setdefault(date_key, {})
    if not isinstance(groups, dict):
        groups = {}
        dates[date_key] = groups
    targets = groups.setdefault(group_key, {})
    if not isinstance(targets, dict):
        targets = {}
        groups[group_key] = targets
    row = targets.get(target_key)
    timestamp = int(time.time() if now is None else now)

    if isinstance(row, dict):
        status = str(row.get("status") or "")
        if status == RESERVATION_RESOLVED:
            return {"status": "resolved", "reservation": dict(row)}
        if status not in {"", RESERVATION_PENDING}:
            return {"status": "closed", "reservation": dict(row)}

    if not isinstance(row, dict) or str(row.get("status") or "") != RESERVATION_PENDING:
        row = {
            "id": uuid.uuid4().hex,
            "status": RESERVATION_PENDING,
            "chef_id": actor_key,
            "target_id": target_key,
            "participants": [actor_key],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        targets[target_key] = row
        return {"status": "created", "reservation": dict(row)}
    participants = row.setdefault("participants", [])
    if not isinstance(participants, list):
        participants = []
        row["participants"] = participants
    participants = [str(item) for item in participants if str(item)]
    row["participants"] = participants
    if actor_key in participants:
        return {"status": "existing", "reservation": dict(row)}
    if len(participants) >= limit:
        return {"status": "full", "reservation": dict(row)}
    participants.append(actor_key)
    row["updated_at"] = timestamp
    return {"status": "joined", "reservation": dict(row)}


def remove_reservation(
    state: dict[str, Any], draw_date: str, group_id: str, target_id: str
) -> bool:
    dates = state.get("reservations", {})
    if not isinstance(dates, dict):
        return False
    groups = dates.get(str(draw_date))
    if not isinstance(groups, dict):
        return False
    targets = groups.get(str(group_id))
    if not isinstance(targets, dict) or str(target_id) not in targets:
        return False
    targets.pop(str(target_id), None)
    if not targets:
        groups.pop(str(group_id), None)
    if not groups:
        dates.pop(str(draw_date), None)
    return True


def resolve_reservation(
    state: dict[str, Any],
    *,
    draw_date: str,
    group_id: str,
    target_id: str,
    outcome: str,
    now: int | None = None,
) -> dict[str, Any] | None:
    """Atomically mark a pending reservation resolved before message delivery."""
    ensure_reservation_state(state)
    dates = state["reservations"]
    groups = dates.get(str(draw_date), {})
    targets = groups.get(str(group_id), {}) if isinstance(groups, dict) else {}
    row = targets.get(str(target_id)) if isinstance(targets, dict) else None
    if not isinstance(row, dict) or str(row.get("status") or "") != RESERVATION_PENDING:
        return None
    row["status"] = RESERVATION_RESOLVED
    row["outcome"] = str(outcome)
    row["resolved_at"] = int(time.time() if now is None else now)
    row["updated_at"] = row["resolved_at"]
    return dict(row)


def prune_reservations(
    state: dict[str, Any], today: datetime.date, keep_days: int = 2
) -> bool:
    """Drop old natural-day buckets; reservations never carry across a day."""
    ensure_reservation_state(state)
    cutoff = (today - datetime.timedelta(days=max(1, int(keep_days)))).isoformat()
    dates = state["reservations"]
    changed = False
    for date_key in list(dates):
        if str(date_key) < cutoff:
            dates.pop(date_key, None)
            changed = True
    return changed
