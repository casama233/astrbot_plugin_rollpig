from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CollectionService:
    """Claim-aware permanent collection read policy.

    Identity resolution stays outside persistence.  Only fragments that are
    already proven to belong to the same logical user may be passed into the
    ownership merge.  Gameplay counters and pity state remain authoritative
    from the highest-priority fragment instead of being arithmetically merged.
    """

    @staticmethod
    def claimed_read_candidates(
        identity_candidates: Sequence[str],
        claims: Mapping[str, Any] | None,
        *,
        preferred_storage_key: str = "",
    ) -> tuple[str, ...]:
        pool = tuple(dict.fromkeys(str(item) for item in identity_candidates if str(item)))
        if not pool:
            return ()

        namespaced = pool[0]
        accepted_claims = set(pool)
        claim_map = claims if isinstance(claims, Mapping) else {}
        selected = [namespaced]

        preferred = str(preferred_storage_key or "")
        if preferred and preferred in accepted_claims and preferred not in selected:
            selected.append(preferred)

        for legacy in pool[1:]:
            claimed_by = str(claim_map.get(legacy) or "")
            if claimed_by in accepted_claims and legacy not in selected:
                selected.append(legacy)

        return tuple(selected)

    @staticmethod
    def merge_ownership(
        collections: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Union ownership without manufacturing gameplay history.

        The first non-empty collection is authoritative for top-level gameplay
        state such as ``duplicate_streak``, ``total_draws`` and ``active_days``.
        Pig ownership is unioned across safe identity fragments.  Overlapping
        per-pig counts use ``max`` rather than ``sum`` so migration copies cannot
        inflate EX levels.  Exact historical counter reconciliation, if ever
        needed, must be rebuilt from a deduplicated draw timeline instead.
        """
        valid = [item for item in collections if isinstance(item, Mapping) and item]
        if not valid:
            return {}

        merged = copy.deepcopy(dict(valid[0]))
        merged_pigs: dict[str, dict[str, Any]] = {}

        for collection in valid:
            pigs = collection.get("pigs", {})
            if not isinstance(pigs, Mapping):
                continue
            for pig_id_raw, record_raw in pigs.items():
                pig_id = str(pig_id_raw or "")
                if not pig_id or not isinstance(record_raw, Mapping):
                    continue
                record = dict(record_raw)
                current = merged_pigs.get(pig_id)
                if current is None:
                    merged_pigs[pig_id] = copy.deepcopy(record)
                    continue

                first_values = [
                    str(value)
                    for value in (
                        current.get("first_unlocked"),
                        record.get("first_unlocked"),
                    )
                    if str(value or "")
                ]
                last_values = [
                    str(value)
                    for value in (
                        current.get("last_drawn"),
                        record.get("last_drawn"),
                    )
                    if str(value or "")
                ]
                if first_values:
                    current["first_unlocked"] = min(first_values)
                if last_values:
                    current["last_drawn"] = max(last_values)
                current["count"] = max(
                    int(current.get("count", 0) or 0),
                    int(record.get("count", 0) or 0),
                )

        merged["pigs"] = merged_pigs
        return merged
