from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CatalogService:
    """Pure catalog composition and read policies.

    The service owns ordering/search/sampling semantics only. File IO, validation,
    persistence, rendering and AstrBot events stay outside this boundary.
    """

    page_size: int = 12

    @staticmethod
    def merge_layers(
        base: Sequence[Mapping[str, Any]],
        overrides: Sequence[Mapping[str, Any]],
        tombstones: set[str] | frozenset[str],
    ) -> list[dict[str, Any]]:
        """Apply local overrides and tombstones without disturbing base order."""
        blocked = {str(item) for item in tombstones}
        override_map = {
            str(item.get("id") or ""): item
            for item in overrides
            if str(item.get("id") or "")
        }
        merged: list[dict[str, Any]] = []
        used: set[str] = set()

        for source in base:
            pig_id = str(source.get("id") or "")
            if not pig_id or pig_id in blocked:
                continue
            merged.append(dict(override_map.get(pig_id, source)))
            used.add(pig_id)

        for source in overrides:
            pig_id = str(source.get("id") or "")
            if not pig_id or pig_id in used or pig_id in blocked:
                continue
            merged.append(dict(source))
            used.add(pig_id)

        return merged

    @staticmethod
    def find(
        catalog: Sequence[Mapping[str, Any]], pig_id: str
    ) -> Mapping[str, Any] | None:
        wanted = str(pig_id)
        return next(
            (pig for pig in catalog if str(pig.get("id") or "") == wanted),
            None,
        )

    @staticmethod
    def ordered_for_collection(
        catalog: Sequence[Mapping[str, Any]], unlocked: Mapping[str, Any] | None
    ) -> list[Mapping[str, Any]]:
        """Put unlocked active pigs first while preserving active catalog order."""
        unlocked_ids = set(unlocked) if isinstance(unlocked, Mapping) else set()
        return [
            pig for pig in catalog if str(pig.get("id") or "") in unlocked_ids
        ] + [
            pig for pig in catalog if str(pig.get("id") or "") not in unlocked_ids
        ]

    @staticmethod
    def collection_display_catalog(
        catalog: Sequence[Mapping[str, Any]],
        unlocked: Mapping[str, Any] | None,
        snapshots: Mapping[str, Any] | None = None,
        *,
        hidden_ids: set[str] | frozenset[str] = frozenset(),
    ) -> list[dict[str, Any]]:
        """Build the permanent collection view without mutating the draw catalog.

        The active catalog is the authority for what may currently be drawn, not
        for what a player permanently owns.  An unlocked pig that disappeared
        from a later resource source remains visible from its historical snapshot.
        Explicit local tombstones stay hidden so an administrator can still remove
        content intentionally.
        """
        unlocked_map = unlocked if isinstance(unlocked, Mapping) else {}
        snapshot_map = snapshots if isinstance(snapshots, Mapping) else {}
        blocked = {str(item) for item in hidden_ids if str(item)}

        active = [
            dict(pig)
            for pig in catalog
            if isinstance(pig, Mapping) and str(pig.get("id") or "")
        ]
        active_ids = {str(pig.get("id") or "") for pig in active}
        unlocked_ids = {str(item) for item in unlocked_map if str(item)}

        active_unlocked = [
            pig for pig in active if str(pig.get("id") or "") in unlocked_ids
        ]
        active_locked = [
            pig for pig in active if str(pig.get("id") or "") not in unlocked_ids
        ]

        retired_ids = [
            pig_id
            for pig_id in unlocked_ids
            if pig_id not in active_ids and pig_id not in blocked
        ]

        def retired_sort_key(pig_id: str) -> tuple[str, str]:
            record = unlocked_map.get(pig_id, {})
            first_unlocked = (
                str(record.get("first_unlocked") or "")
                if isinstance(record, Mapping)
                else ""
            )
            return (first_unlocked or "9999-99-99", pig_id)

        retired: list[dict[str, Any]] = []
        for pig_id in sorted(retired_ids, key=retired_sort_key):
            snapshot = snapshot_map.get(pig_id)
            if isinstance(snapshot, Mapping):
                pig = dict(snapshot)
            else:
                pig = {
                    "id": pig_id,
                    "name": pig_id,
                    "description": "歷史收藏",
                    "analysis": "這隻小豬仍在你的永久收藏記錄中，但目前資源源已不再提供它。",
                }
            pig["id"] = pig_id
            pig["name"] = str(pig.get("name") or pig_id)
            pig["description"] = str(pig.get("description") or "歷史收藏")
            pig["analysis"] = str(
                pig.get("analysis")
                or "這隻小豬仍在你的永久收藏記錄中，但目前資源源已不再提供它。"
            )
            pig["_collection_retired"] = True
            retired.append(pig)

        return active_unlocked + retired + active_locked

    def page_count(self, catalog: Sequence[Mapping[str, Any]]) -> int:
        size = max(1, int(self.page_size))
        return max(1, (len(catalog) + size - 1) // size)

    @staticmethod
    def sample(
        catalog: Sequence[Mapping[str, Any]],
        amount: int,
        *,
        rng: Any = random,
    ) -> list[Mapping[str, Any]]:
        count = min(max(0, int(amount)), len(catalog))
        return list(rng.sample(list(catalog), count)) if count else []

    @staticmethod
    def search(
        catalog: Sequence[Mapping[str, Any]], keyword: str
    ) -> list[Mapping[str, Any]]:
        query = str(keyword or "").strip().lower()
        if not query:
            return []
        fields = ("id", "name", "description", "analysis")
        return [
            pig
            for pig in catalog
            if query
            in " ".join(str(pig.get(key, "")) for key in fields).lower()
        ]
