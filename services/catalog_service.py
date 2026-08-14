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
        """Put unlocked pigs first while preserving order inside both partitions."""
        unlocked_ids = set(unlocked) if isinstance(unlocked, Mapping) else set()
        return [
            pig for pig in catalog if str(pig.get("id") or "") in unlocked_ids
        ] + [
            pig for pig in catalog if str(pig.get("id") or "") not in unlocked_ids
        ]

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
