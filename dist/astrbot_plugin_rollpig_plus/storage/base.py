from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any


class StorageBackend(ABC):
    """Persistence contract used by RollPig business services.

    The first implementation remains JSON-compatible.  SQLite can implement
    the same contract later without making commands and dashboard handlers
    depend on a concrete file format.
    """

    backend_name = "unknown"
    supports_domain_reads = False
    supports_domain_writes = False
    supports_runtime_snapshot = False
    supports_dashboard_analytics = False

    @abstractmethod
    def load_json(self, path: Path, default: Any) -> Any:
        """Load one logical document, returning a detached default on absence."""

    @abstractmethod
    def save_json(self, path: Path, data: Any) -> None:
        """Persist one logical document."""

    @abstractmethod
    def save_json_batch(self, updates: dict[Path, Any]) -> None:
        """Persist related documents with rollback on replacement failure."""

    @abstractmethod
    def transaction(self) -> AbstractContextManager[None]:
        """Return a backend transaction/critical-section context manager."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return a small dashboard-safe backend status snapshot."""

    # SQL-primary domain write API. JSONStorage deliberately does not implement
    # these methods; callers retain the legacy JSON path when capability is false.
    def create_daily_draw(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def replace_daily_pig_with_eaten(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def claim_legacy_identity(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def remember_identity_alias(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def consume_roast_cooldown(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def increment_roast_count(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def consume_daily_backdoor(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def get_ai_roast_copies(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def store_ai_roast_copy(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def upsert_catalog_override(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def delete_catalog_entry(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def restore_catalog_entry(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def claim_ai_roast_generation(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def complete_ai_roast_generation(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def load_runtime_snapshot(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_dashboard_overview(self, **kwargs: Any) -> dict[str, Any] | None:
        return None

    def get_dashboard_insights(self, **kwargs: Any) -> dict[str, Any] | None:
        return None

    # Transitional domain read API. JSONStorage keeps using the in-memory
    # compatibility documents; SQLite overrides these methods with indexed SQL.
    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:
        return None

    def get_daily_draw(
        self, draw_date: str, user_candidates: tuple[str, ...]
    ) -> dict[str, Any] | None:
        return None

    def get_group_members(self, draw_date: str, group_id: str) -> list[str] | None:
        return None

    def get_eaten_victims(self, event_date: str, group_id: str) -> list[str] | None:
        return None

    def get_roast_count(
        self, draw_date: str, group_id: str, user_candidates: tuple[str, ...]
    ) -> int | None:
        return None
