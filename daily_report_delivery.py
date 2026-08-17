from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


class DailyReportDeliveryClaims:
    """Filesystem-backed at-most-once claim store for scheduled daily reports.

    Exclusive file creation arbitrates delivery across plugin reloads/instances.
    Claims remain for the report retention window so a stale job snapshot cannot
    resurrect an already-attempted group/date delivery.
    """

    def __init__(self, root: Path | str, *, keep_days: int, owner: str | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.keep_days = max(1, int(keep_days))
        self.owner = str(owner or uuid.uuid4().hex)

    def path_for(self, group_id: str, draw_date: str) -> Path:
        digest = hashlib.sha256(f"{draw_date}\0{group_id}".encode("utf-8")).hexdigest()[:32]
        return self.root / f"{draw_date}-{digest}.json"

    @staticmethod
    def read(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {"status": "unknown"}
        return payload if isinstance(payload, dict) else {"status": "unknown"}

    def try_acquire(self, group_id: str, draw_date: str) -> tuple[Path | None, dict[str, Any]]:
        path = self.path_for(group_id, draw_date)
        payload = {
            "schema_version": 1,
            "status": "claimed",
            "draw_date": str(draw_date),
            "group_id": str(group_id),
            "delivery_id": uuid.uuid4().hex,
            "owner": self.owner,
            "pid": os.getpid(),
            "claimed_at": int(time.time()),
        }
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            return None, self.read(path)
        return path, payload

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)

    def finalize(self, path: Path, *, status: str, error: str = "") -> dict[str, Any]:
        payload = self.read(path)
        payload.update(status=str(status), finalized_at=int(time.time()), error=str(error or "")[:300])
        self._write(path, payload)
        return payload

    @staticmethod
    def release(path: Path) -> None:
        path.unlink(missing_ok=True)

    def prune(self) -> None:
        cutoff = time.time() - (self.keep_days + 2) * 86400
        for path in self.root.glob("*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue
