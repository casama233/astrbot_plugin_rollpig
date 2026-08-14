from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .base import StorageBackend


class JSONStorage(StorageBackend):
    """Backward-compatible JSON persistence with staged writes and rollback."""

    backend_name = "json"

    def __init__(self, lock: threading.RLock | None = None):
        self._lock = lock or threading.RLock()
        self._last_error = ""
        self._last_write_at = 0

    @staticmethod
    def _clone(value: Any) -> Any:
        return copy.deepcopy(value)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            yield

    def load_json(self, path: Path, default: Any) -> Any:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            self.save_json(path, default)
            return self._clone(default)

        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self._last_error = f"{path.name}: {exc}"
            corrupt = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
            try:
                shutil.copy2(path, corrupt)
            except OSError:
                pass

            backup = path.with_name(f"{path.name}.bak")
            if backup.exists():
                try:
                    with backup.open("r", encoding="utf-8") as handle:
                        recovered = json.load(handle)
                    self.save_json(path, recovered)
                    return recovered
                except (OSError, UnicodeError, json.JSONDecodeError):
                    pass

            self.save_json(path, default)
            return self._clone(default)

    def save_json(self, path: Path, data: Any) -> None:
        self.save_json_batch({Path(path): data})

    def save_json_batch(self, updates: dict[Path, Any]) -> None:
        normalized = {Path(path): value for path, value in updates.items()}
        if not normalized:
            return

        staged: dict[Path, Path] = {}
        backups: dict[Path, Path] = {}
        existed: dict[Path, bool] = {}
        replaced: list[Path] = []

        with self._lock:
            try:
                for target, value in normalized.items():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    existed[target] = target.exists()
                    descriptor, temporary_name = tempfile.mkstemp(
                        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
                    )
                    temporary = Path(temporary_name)
                    staged[target] = temporary
                    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                        json.dump(value, handle, ensure_ascii=False, indent=2)
                        handle.write("\n")
                        handle.flush()
                        os.fsync(handle.fileno())

                for target in normalized:
                    backup = target.with_name(f"{target.name}.bak")
                    backups[target] = backup
                    if target.exists():
                        shutil.copy2(target, backup)

                for target, temporary in staged.items():
                    os.replace(temporary, target)
                    replaced.append(target)

                for parent in {target.parent for target in normalized}:
                    self._fsync_directory(parent)
                self._last_error = ""
                self._last_write_at = int(time.time())
            except Exception as exc:
                self._last_error = str(exc)
                for target in reversed(replaced):
                    backup = backups.get(target)
                    try:
                        if existed.get(target) and backup and backup.exists():
                            shutil.copy2(backup, target)
                        elif not existed.get(target) and target.exists():
                            target.unlink()
                    except OSError:
                        pass
                raise
            finally:
                for temporary in staged.values():
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        pass

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        if os.name == "nt":
            return
        descriptor = None
        try:
            descriptor = os.open(path, os.O_RDONLY)
            os.fsync(descriptor)
        except OSError:
            pass
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def health(self) -> dict[str, Any]:
        return {
            "backend": self.backend_name,
            "transactional_batch": True,
            "last_write_at": self._last_write_at,
            "last_error": self._last_error,
        }
