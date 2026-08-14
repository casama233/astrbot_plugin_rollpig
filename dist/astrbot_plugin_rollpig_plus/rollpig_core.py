"""Small dependency-free helpers used by tests and future refactors."""
from __future__ import annotations

import datetime
import ipaddress
import re
from typing import Any, Mapping


def legacy_identity(value: str) -> str:
    match = re.fullmatch(r"v2\|[^|]+\|(?:user|group)\|(.*)", str(value or ""))
    return match.group(1) if match else str(value or "")


def pre_instance_identity(value: str) -> str:
    """Return the old adapter-type-only key for an instance-aware v2 key."""
    match = re.fullmatch(
        r"v2\|([^|]+)\|(user|group)\|(.*)", str(value or "")
    )
    if not match or "@" not in match.group(1):
        return ""
    platform_type = match.group(1).split("@", 1)[0]
    return f"v2|{platform_type}|{match.group(2)}|{match.group(3)}"


def identity_candidates(value: str) -> tuple[str, ...]:
    """Return instance-aware, pre-instance and raw keys in preference order."""
    text = str(value or "").strip()
    raw = legacy_identity(text)
    if raw == text:
        return (text,)
    candidates = [text]
    previous = pre_instance_identity(text)
    if previous:
        candidates.append(previous)
    if raw not in candidates:
        candidates.append(raw)
    return tuple(candidates)


def namespace_identity(platform: str, kind: str, value: str) -> str:
    raw = str(value or "").strip()
    if not raw or raw.startswith("v2|"):
        return raw
    safe_platform = re.sub(
        r"[^a-z0-9_.@-]+", "-", str(platform or "unknown").lower()
    ).strip("-") or "unknown"
    if kind not in {"user", "group"}:
        raise ValueError("kind must be user or group")
    return f"v2|{safe_platform}|{kind}|{raw}"


def is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)


_SPECIAL_HUMAN_IDS = frozenset({"human"})
_SPECIAL_EATEN_IDS = frozenset({"eaten"})
_SPECIAL_COOKED_IDS = frozenset({"mc_porkchop", "lard-pig"})
_SPECIAL_HUMAN_NAMES = frozenset({"人类", "人類"})
_SPECIAL_EATEN_NAMES = frozenset({"吃掉了"})
_SPECIAL_COOKED_NAMES = frozenset({"猪油", "豬油", "熟食形态", "熟食形態"})


def special_pig_state(pig: dict | None) -> str:
    """Classify only the special states that alter cooking/eating eligibility."""
    if not isinstance(pig, dict) or not pig:
        return "missing"
    pig_id = str(pig.get("id") or "").strip().lower()
    name = str(pig.get("name") or "").strip()
    if pig_id in _SPECIAL_HUMAN_IDS or name in _SPECIAL_HUMAN_NAMES:
        return "human"
    if pig_id in _SPECIAL_EATEN_IDS or name in _SPECIAL_EATEN_NAMES:
        return "eaten"
    if pig_id in _SPECIAL_COOKED_IDS or name in _SPECIAL_COOKED_NAMES:
        return "cooked"
    return "normal"

def consecutive_duplicate_day_streak(
    history: Mapping[str, Any] | None,
    collection: Mapping[str, Any] | None,
    storage_id: str,
    before_date: datetime.date,
) -> int:
    """Count adjacent prior calendar days whose completed draw was already unlocked.

    A missing day breaks the chain. If a day's visible record was replaced by the
    special ``eaten`` state, ``eaten_originals`` is used so the original draw still
    determines whether that day was a duplicate.
    """
    history_map = history if isinstance(history, Mapping) else {}
    daily = history_map.get("daily")
    if not isinstance(daily, Mapping):
        return 0

    user = collection if isinstance(collection, Mapping) else {}
    pigs = user.get("pigs")
    if not isinstance(pigs, Mapping):
        return 0

    key = str(storage_id or "")
    if not key:
        return 0

    streak = 0
    cursor = before_date - datetime.timedelta(days=1)
    while True:
        day = daily.get(cursor.isoformat())
        if not isinstance(day, Mapping):
            break
        records = day.get("records")
        if not isinstance(records, Mapping):
            break
        pig_id = str(records.get(key) or "")
        if pig_id == "eaten":
            originals = day.get("eaten_originals")
            pig_id = (
                str(originals.get(key) or "")
                if isinstance(originals, Mapping)
                else ""
            )
        if not pig_id:
            break

        record = pigs.get(pig_id)
        if not isinstance(record, Mapping):
            break
        first_unlocked = str(record.get("first_unlocked") or "")
        try:
            first_unlocked_date = datetime.date.fromisoformat(first_unlocked)
        except ValueError:
            break
        if first_unlocked_date >= cursor:
            break

        streak += 1
        cursor -= datetime.timedelta(days=1)

    return streak

