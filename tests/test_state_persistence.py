from __future__ import annotations

import threading

import state_persistence
from state_persistence import DebouncedSnapshotWriter


class _FakeTimer:
    created: list["_FakeTimer"] = []

    def __init__(self, delay, callback):
        self.delay = delay
        self.callback = callback
        self.daemon = False
        self._alive = False
        self.cancelled = False
        self.__class__.created.append(self)

    def start(self):
        self._alive = True

    def is_alive(self):
        return self._alive

    def cancel(self):
        self.cancelled = True
        self._alive = False

    def fire(self):
        if not self._alive:
            return
        self._alive = False
        self.callback()


def _install_fake_timer(monkeypatch):
    _FakeTimer.created = []
    monkeypatch.setattr(state_persistence.threading, "Timer", _FakeTimer)


def test_multiple_mutations_are_coalesced_into_one_snapshot(monkeypatch):
    _install_fake_timer(monkeypatch)
    lock = threading.RLock()
    state = {"value": 0}
    writes = []
    writer = DebouncedSnapshotWriter(
        state_lock=lock,
        snapshot_factory=lambda: state,
        write_snapshot=writes.append,
        delay_seconds=2,
    )

    with lock:
        state["value"] = 1
        writer.mark_dirty()
        state["value"] = 2
        writer.mark_dirty()
        state["value"] = 3
        writer.mark_dirty()

    assert len(_FakeTimer.created) == 1
    assert _FakeTimer.created[0].delay == 2
    _FakeTimer.created[0].fire()
    assert writes == [{"value": 3}]


def test_mutation_during_write_schedules_follow_up_flush(monkeypatch):
    _install_fake_timer(monkeypatch)
    lock = threading.RLock()
    state = {"value": 1}
    writes = []
    mutated = False

    writer = None

    def persist(snapshot):
        nonlocal mutated
        writes.append(snapshot)
        if not mutated:
            mutated = True
            with lock:
                state["value"] = 2
                writer.mark_dirty()

    writer = DebouncedSnapshotWriter(
        state_lock=lock,
        snapshot_factory=lambda: state,
        write_snapshot=persist,
        delay_seconds=1,
    )
    writer.mark_dirty()

    _FakeTimer.created[0].fire()
    assert writes == [{"value": 1}]
    assert len(_FakeTimer.created) == 2

    _FakeTimer.created[1].fire()
    assert writes == [{"value": 1}, {"value": 2}]


def test_close_cancels_pending_timer_and_forces_latest_snapshot(monkeypatch):
    _install_fake_timer(monkeypatch)
    lock = threading.RLock()
    state = {"value": "latest"}
    writes = []
    writer = DebouncedSnapshotWriter(
        state_lock=lock,
        snapshot_factory=lambda: state,
        write_snapshot=writes.append,
        delay_seconds=2,
    )
    writer.mark_dirty()
    pending = _FakeTimer.created[0]

    assert writer.close_and_flush() is True
    assert pending.cancelled is True
    assert writes == [{"value": "latest"}]

    with lock:
        state["value"] = "after-close"
        writer.mark_dirty()
    assert len(_FakeTimer.created) == 1
    assert writes == [{"value": "latest"}]
