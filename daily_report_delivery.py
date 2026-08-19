from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


def _path_identity(value: Path | str) -> Path:
    path = Path(value).expanduser()
    try:
        return path.resolve()
    except (OSError, RuntimeError):
        return path.absolute()


def cancel_stale_daily_report_tasks(plugin_data_dir: Path | str) -> int:
    """Cancel leaked daily-report schedulers for the same plugin data namespace.

    AstrBot hot reloads can leave an older plugin object's background task alive
    if its unload lifecycle is interrupted. A newly loaded RollPig instance calls
    this helper before creating its own scheduler, so suspended legacy
    ``_background_daily_report`` tasks lose the ability to send future reports.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return 0

    target = _path_identity(plugin_data_dir)
    current = asyncio.current_task()
    cancelled = 0
    for task in asyncio.all_tasks():
        if task is current or task.done():
            continue
        coro = task.get_coro()
        code = getattr(coro, "cr_code", None)
        if getattr(code, "co_name", "") != "_background_daily_report":
            continue
        frame = getattr(coro, "cr_frame", None)
        owner = frame.f_locals.get("self") if frame is not None else None
        owner_dir = getattr(owner, "plugin_data_dir", None)
        if owner_dir is None or _path_identity(owner_dir) != target:
            continue
        task.cancel()
        cancelled += 1
    return cancelled


class DailyReportDeliveryClaims:
    """Filesystem-backed at-most-once claim store for scheduled daily reports.

    Exclusive file creation arbitrates delivery across plugin reloads/instances.
    Claims remain for the report retention window so a stale job snapshot cannot
    resurrect an already-attempted group/date delivery.
    """

    def __init__(
        self, root: Path | str, *, keep_days: int, owner: str | None = None
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        # This constructor runs before DailyReportMixin creates the new scheduler.
        # Sweep leaked legacy schedulers from the same data namespace first; the
        # durable delivery claim below remains the final at-most-once boundary.
        self.cancelled_stale_schedulers = cancel_stale_daily_report_tasks(
            self.root.parent
        )
        self.keep_days = max(1, int(keep_days))
        self.owner = str(owner or uuid.uuid4().hex)

    def path_for(self, group_id: str, draw_date: str) -> Path:
        digest = hashlib.sha256(
            f"{draw_date}\0{group_id}".encode("utf-8")
        ).hexdigest()[:32]
        return self.root / f"{draw_date}-{digest}.json"

    @staticmethod
    def read(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {"status": "unknown"}
        return payload if isinstance(payload, dict) else {"status": "unknown"}

    def try_acquire(
        self, group_id: str, draw_date: str
    ) -> tuple[Path | None, dict[str, Any]]:
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
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
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
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)

    def finalize(
        self, path: Path, *, status: str, error: str = ""
    ) -> dict[str, Any]:
        payload = self.read(path)
        payload.update(
            status=str(status),
            finalized_at=int(time.time()),
            error=str(error or "")[:300],
        )
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
