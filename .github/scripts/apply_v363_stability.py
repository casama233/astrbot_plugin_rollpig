from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected one marker, got {text.count(old)}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) Daily-report reload safety (#66).
replace_once(
    "daily_report_feature.py",
    "        actor_id = super()._event_sender_id(event)\n        self._remember_daily_report_context(event, actor_id)\n",
    "        actor_id = self._event_sender_id(event)\n",
)

# 2) Pure identity/read-model helpers.
replace_once(
    "rollpig_core.py",
    "from typing import Any, Mapping\n",
    "from typing import Any, Iterable, Mapping\n",
)
marker = "\ndef namespace_identity(platform: str, kind: str, value: str) -> str:\n"
helper = r'''

def claimed_identity_candidates(
    value: str,
    storage_key: str,
    claims: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Return only collection fragments proven to belong to one namespaced user.

    The current identity and the storage key already selected by the claim layer are
    always trusted. Other pre-instance/raw candidates are included only when an
    explicit users-claim points at the current namespaced identity. This preserves
    cross-platform isolation while allowing old claimed fragments to remain visible.
    """
    candidates = identity_candidates(value)
    if not candidates:
        return ()
    namespaced = candidates[0]
    selected: list[str] = [namespaced]
    storage = str(storage_key or "").strip()
    if storage and storage in candidates and storage not in selected:
        selected.append(storage)
    claim_map = claims if isinstance(claims, Mapping) else {}
    for candidate in candidates[1:]:
        if candidate in selected:
            continue
        if str(claim_map.get(candidate) or "") == namespaced:
            selected.append(candidate)
    return tuple(selected)


def merge_user_collection_fragments(
    collections: Iterable[Mapping[str, Any] | None],
) -> dict[str, Any]:
    """Merge permanent ownership without inflating gameplay counters.

    Statistics and pity state come from the first (highest-priority) collection.
    Pig ownership is unioned across proven fragments. For the same pig, dates use
    min/max while ``count`` uses the maximum observed value instead of a sum so a
    migration copy cannot grant extra EX levels.
    """
    valid = [item for item in collections if isinstance(item, Mapping) and item]
    if not valid:
        return {}
    merged: dict[str, Any] = dict(valid[0])
    merged_pigs: dict[str, dict[str, Any]] = {}
    for raw_user in valid:
        raw_pigs = raw_user.get("pigs")
        if not isinstance(raw_pigs, Mapping):
            continue
        for raw_id, raw_record in raw_pigs.items():
            if not isinstance(raw_record, Mapping):
                continue
            pig_id = str(raw_id or "").strip()
            if not pig_id:
                continue
            incoming = dict(raw_record)
            try:
                incoming_count = max(0, int(incoming.get("count", 0) or 0))
            except (TypeError, ValueError):
                incoming_count = 0
            current = merged_pigs.get(pig_id)
            if current is None:
                incoming["count"] = incoming_count
                merged_pigs[pig_id] = incoming
                continue
            first_current = str(current.get("first_unlocked") or "")
            first_incoming = str(incoming.get("first_unlocked") or "")
            if first_incoming and (not first_current or first_incoming < first_current):
                current["first_unlocked"] = first_incoming
            last_current = str(current.get("last_drawn") or "")
            last_incoming = str(incoming.get("last_drawn") or "")
            if last_incoming > last_current:
                current["last_drawn"] = last_incoming
            try:
                current_count = max(0, int(current.get("count", 0) or 0))
            except (TypeError, ValueError):
                current_count = 0
            current["count"] = max(current_count, incoming_count)
    merged["pigs"] = merged_pigs
    return merged
'''
replace_once("rollpig_core.py", marker, helper + marker)

# 3) Claim-aware plugin read candidates and JSON fallback merge.
replace_once(
    "legacy_main.py",
    "    from .rollpig_core import consecutive_duplicate_day_streak\n",
    "    from .rollpig_core import (\n        claimed_identity_candidates,\n        consecutive_duplicate_day_streak,\n        merge_user_collection_fragments,\n    )\n",
)
replace_once(
    "legacy_main.py",
    "    from rollpig_core import consecutive_duplicate_day_streak\n",
    "    from rollpig_core import (\n        claimed_identity_candidates,\n        consecutive_duplicate_day_streak,\n        merge_user_collection_fragments,\n    )\n",
)
replace_once(
    "legacy_main.py",
    '''    def _user_read_candidates(self, user_id: str) -> tuple[str, ...]:
        """Return only identity keys that belong to the current platform claim."""
        candidates = self._identity_candidates(str(user_id))
        if len(candidates) == 1:
            return candidates
        namespaced = candidates[0]
        storage_key = self._storage_user_key(namespaced)
        return tuple(dict.fromkeys((namespaced, storage_key)))
''',
    '''    def _user_read_candidates(self, user_id: str) -> tuple[str, ...]:
        """Return collection fragments proven to belong to the current claim."""
        candidates = self._identity_candidates(str(user_id))
        if len(candidates) == 1:
            return candidates
        namespaced = candidates[0]
        storage_key = self._storage_user_key(namespaced)
        claims_root = self.history.get("identity_claims", {})
        claims = (
            claims_root.get("users", {})
            if isinstance(claims_root, dict)
            else {}
        )
        return claimed_identity_candidates(namespaced, storage_key, claims)
''',
)
replace_once(
    "legacy_main.py",
    '''        users = self.history.get("users", {})
        for candidate in candidates:
            user = users.get(candidate, {})
            if isinstance(user, dict) and user:
                return user
        return {}
''',
    '''        users = self.history.get("users", {})
        merged = merge_user_collection_fragments(
            users.get(candidate) for candidate in candidates
        )
        return merged
''',
)

# 4) SQLite read projection: merge ownership only, keep primary stats/pity.
replace_once(
    "storage/sqlite_storage.py",
    "from .json_storage import JSONStorage\n",
    "from .json_storage import JSONStorage\n\ntry:\n    from ..rollpig_core import merge_user_collection_fragments\nexcept ImportError:  # pragma: no cover - direct module loading compatibility\n    from rollpig_core import merge_user_collection_fragments\n",
)
old_sql = '''    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:
        candidates = self._candidate_tuple(user_candidates)
        if not candidates:
            return None
        with self._lock, self._connection() as connection:
            for user_id in candidates:
                stats = connection.execute(
                    "SELECT total_draws, active_days, duplicate_streak "
                    "FROM user_stats WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if not stats:
                    continue
                pigs = connection.execute(
                    "SELECT pig_id, first_unlocked, last_drawn, draw_count "
                    "FROM user_pigs WHERE user_id = ? ORDER BY pig_id",
                    (user_id,),
                ).fetchall()
                return {
                    "total_draws": int(stats["total_draws"]),
                    "active_days": int(stats["active_days"]),
                    "duplicate_streak": int(stats["duplicate_streak"]),
                    "pigs": {
                        str(row["pig_id"]): {
                            "first_unlocked": str(row["first_unlocked"]),
                            "last_drawn": str(row["last_drawn"]),
                            "count": int(row["draw_count"]),
                        }
                        for row in pigs
                    },
                }
        return None
'''
new_sql = '''    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:
        candidates = self._candidate_tuple(user_candidates)
        if not candidates:
            return None
        collections: list[dict[str, Any]] = []
        with self._lock, self._connection() as connection:
            for user_id in candidates:
                stats = connection.execute(
                    "SELECT total_draws, active_days, duplicate_streak "
                    "FROM user_stats WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if not stats:
                    continue
                pigs = connection.execute(
                    "SELECT pig_id, first_unlocked, last_drawn, draw_count "
                    "FROM user_pigs WHERE user_id = ? ORDER BY pig_id",
                    (user_id,),
                ).fetchall()
                collections.append(
                    {
                        "total_draws": int(stats["total_draws"]),
                        "active_days": int(stats["active_days"]),
                        "duplicate_streak": int(stats["duplicate_streak"]),
                        "pigs": {
                            str(row["pig_id"]): {
                                "first_unlocked": str(row["first_unlocked"]),
                                "last_drawn": str(row["last_drawn"]),
                                "count": int(row["draw_count"]),
                            }
                            for row in pigs
                        },
                    }
                )
        merged = merge_user_collection_fragments(collections)
        return merged or None
'''
replace_once("storage/sqlite_storage.py", old_sql, new_sql)

print("v3.6.3 stability patch applied")
