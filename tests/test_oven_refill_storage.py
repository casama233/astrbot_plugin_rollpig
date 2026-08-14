from pathlib import Path

import pytest

from storage.sqlite_primary import SQLitePrimaryStorage
from storage.sqlite_storage import SQLiteStorage


INTERVAL = 8 * 3600
MANAGED = {"roast_state.json"}


def _storage(storage_cls, root: Path):
    return storage_cls(root / "rollpig.db", root, MANAGED)


def _consume_once(storage, group: str, actor: str, now: float = 1000):
    return storage.consume_roast_charge(
        group_id=group,
        actor_id=actor,
        now=now,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )


@pytest.mark.parametrize("storage_cls", [SQLiteStorage, SQLitePrimaryStorage])
def test_refill_start_is_unique_and_creator_auto_supports(storage_cls, tmp_path):
    storage = _storage(storage_cls, tmp_path)
    first = storage.start_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id="v2|aiocqhttp@default|user|1",
        active_count=16,
        now=1000,
        daily_limit=2,
        ratio_percent=30,
        minimum_supporters=3,
        extra_per_success=2,
        cutoff_date="2026-08-01",
    )
    second = storage.start_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id="v2|aiocqhttp@default|user|2",
        active_count=16,
        now=1010,
        daily_limit=2,
        ratio_percent=30,
        minimum_supporters=3,
        extra_per_success=2,
        cutoff_date="2026-08-01",
    )

    assert first["state"] == "started"
    assert first["required"] == 5
    assert len(first["supporters"]) == 1
    assert second["state"] == "active"
    assert second["round"] == first["round"] == 1
    assert second["supporters"] == first["supporters"]


@pytest.mark.parametrize("storage_cls", [SQLiteStorage, SQLitePrimaryStorage])
def test_support_threshold_grants_one_charge_to_active_players_atomically(storage_cls, tmp_path):
    storage = _storage(storage_cls, tmp_path)
    actors = [f"v2|aiocqhttp@default|user|{idx}" for idx in range(1, 4)]
    for actor in actors:
        _consume_once(storage, "group-a", actor)

    start = storage.start_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actors[0],
        active_count=3,
        now=1100,
        daily_limit=2,
        ratio_percent=30,
        minimum_supporters=3,
        extra_per_success=2,
        cutoff_date="2026-08-01",
    )
    mid = storage.support_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actors[1],
        active_actor_ids=actors,
        now=1110,
        max_charges=2,
        recovery_seconds=INTERVAL,
        cutoff_date="2026-08-01",
    )
    done = storage.support_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actors[2],
        active_actor_ids=actors,
        now=1120,
        max_charges=2,
        recovery_seconds=INTERVAL,
        cutoff_date="2026-08-01",
    )

    assert start["required"] == 3
    assert mid["state"] == "supported"
    assert done["state"] == "succeeded"
    assert done["restored_users"] == 3
    if isinstance(storage, SQLitePrimaryStorage):
        roast = storage.load_runtime_snapshot()["roast_state"]
    else:
        roast = storage.load_json(tmp_path / "roast_state.json", {})
    for actor in actors:
        entry = roast["roast_charges"][f"group-a:{actor}"]
        assert entry["charges"] == 2


@pytest.mark.parametrize("storage_cls", [SQLiteStorage, SQLitePrimaryStorage])
def test_duplicate_support_does_not_advance_progress(storage_cls, tmp_path):
    storage = _storage(storage_cls, tmp_path)
    actor = "v2|aiocqhttp@default|user|1"
    storage.start_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actor,
        active_count=4,
        now=1000,
        daily_limit=2,
        ratio_percent=30,
        minimum_supporters=3,
        extra_per_success=2,
        cutoff_date="2026-08-01",
    )
    duplicate = storage.support_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actor,
        active_actor_ids=[actor],
        now=1010,
        max_charges=2,
        recovery_seconds=INTERVAL,
        cutoff_date="2026-08-01",
    )

    assert duplicate["state"] == "duplicate"
    assert len(duplicate["supporters"]) == 1


@pytest.mark.parametrize("storage_cls", [SQLiteStorage, SQLitePrimaryStorage])
def test_full_group_causes_void_round_without_consuming_daily_success(storage_cls, tmp_path):
    storage = _storage(storage_cls, tmp_path)
    actors = [f"v2|aiocqhttp@default|user|{idx}" for idx in range(1, 4)]
    storage.start_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actors[0],
        active_count=3,
        now=1000,
        daily_limit=2,
        ratio_percent=30,
        minimum_supporters=3,
        extra_per_success=2,
        cutoff_date="2026-08-01",
    )
    storage.support_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actors[1],
        active_actor_ids=actors,
        now=1010,
        max_charges=2,
        recovery_seconds=INTERVAL,
        cutoff_date="2026-08-01",
    )
    failed = storage.support_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actors[2],
        active_actor_ids=actors,
        now=1020,
        max_charges=2,
        recovery_seconds=INTERVAL,
        cutoff_date="2026-08-01",
    )
    restarted = storage.start_oven_refill(
        draw_date="2026-08-15",
        group_id="group-a",
        actor_id=actors[0],
        active_count=3,
        now=1030,
        daily_limit=2,
        ratio_percent=30,
        minimum_supporters=3,
        extra_per_success=2,
        cutoff_date="2026-08-01",
    )

    assert failed["state"] == "failed"
    assert failed["restored_users"] == 0
    assert restarted["state"] == "started"
    assert restarted["round"] == 2
    assert restarted["successes"] == 0
    assert restarted["required"] == 3
