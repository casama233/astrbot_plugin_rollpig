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
