from __future__ import annotations

import copy
import threading
from typing import Any, Callable


class DebouncedSnapshotWriter:
    """Coalesce frequent durable snapshots behind one background timer.

    State mutation stays protected by the caller-owned re-entrant lock. The
    expensive persistence callback runs on the timer thread from an immutable
    deep-copied snapshot, so callers do not perform JSON encoding/fsync work in
    their hot path. A revision counter guarantees mutations that arrive while a
    write is in progress are scheduled for a later flush instead of being lost.
    """

    def __init__(
        self,
        *,
        state_lock: threading.RLock,
        snapshot_factory: Callable[[], Any],
        write_snapshot: Callable[[Any], None],
        delay_seconds: float = 2.0,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._state_lock = state_lock
        self._snapshot_factory = snapshot_factory
        self._write_snapshot = write_snapshot
        self._delay_seconds = min(10.0, max(0.25, float(delay_seconds)))
        self._on_error = on_error
        self._write_lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._dirty = False
        self._revision = 0
        self._closed = False

    @property
    def delay_seconds(self) -> float:
        return self._delay_seconds

    def mark_dirty(self) -> None:
        """Record one mutation and ensure a single delayed flush is scheduled."""
        with self._state_lock:
            if self._closed:
                return
            self._dirty = True
            self._revision += 1
            self._schedule_locked()

    def _schedule_locked(self) -> None:
        if self._closed:
            return
        timer = self._timer
        if timer is not None and timer.is_alive():
            return
        timer = threading.Timer(self._delay_seconds, self._timer_flush)
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _timer_flush(self) -> None:
        try:
            self.flush()
        except Exception as exc:
            with self._state_lock:
                self._timer = None
                if self._dirty and not self._closed:
                    self._schedule_locked()
            if self._on_error is not None:
                self._on_error(exc)

    def flush(self, *, force: bool = False) -> bool:
        """Persist the newest consistent snapshot, serializing concurrent writers."""
        with self._write_lock:
            with self._state_lock:
                if not self._dirty and not force:
                    self._timer = None
                    return False
                snapshot = copy.deepcopy(self._snapshot_factory())
                revision = self._revision

            self._write_snapshot(snapshot)

            with self._state_lock:
                if self._revision == revision:
                    self._dirty = False
                self._timer = None
                if self._dirty and not self._closed:
                    self._schedule_locked()
            return True

    def close_and_flush(self) -> bool:
        """Stop future timers and synchronously persist the final plugin state."""
        with self._state_lock:
            self._closed = True
            timer = self._timer
            self._timer = None
        if timer is not None and timer is not threading.current_thread():
            timer.cancel()
        return self.flush(force=True)
