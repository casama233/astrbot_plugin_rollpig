from pathlib import Path

import pytest

from storage.sqlite_primary import SQLitePrimaryStorage
from storage.sqlite_storage import SQLiteStorage


INTERVAL = 8 * 3600
MANAGED = {"roast_state.json"}


def _storage(storage_cls, root: Path):
    return storage_cls(root / "rollpig.db", root, MANAGED)


@pytest.mark.parametrize("storage_cls", [SQLiteStorage, SQLitePrimaryStorage])
def test_sqlite_charge_consumption_is_user_group_scoped(storage_cls, tmp_path):
    storage = _storage(storage_cls, tmp_path)

    first = storage.consume_roast_charge(
        group_id="group-a",
        actor_id="v2|aiocqhttp@default|user|10001",
        now=1000,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )
    second = storage.consume_roast_charge(
        group_id="group-a",
        actor_id="v2|aiocqhttp@default|user|10001",
        now=1010,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )
    blocked = storage.consume_roast_charge(
        group_id="group-a",
        actor_id="v2|aiocqhttp@default|user|10001",
        now=1020,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )
    other_group = storage.consume_roast_charge(
        group_id="group-b",
        actor_id="v2|aiocqhttp@default|user|10001",
        now=1020,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    assert first["consumed"] is True and first["charges"] == 1
    assert second["consumed"] is True and second["charges"] == 0
    assert blocked["consumed"] is False and blocked["charges"] == 0
    assert other_group["consumed"] is True and other_group["charges"] == 1


@pytest.mark.parametrize("storage_cls", [SQLiteStorage, SQLitePrimaryStorage])
def test_active_legacy_cooldown_migrates_to_one_remaining_charge(storage_cls, tmp_path):
    storage = _storage(storage_cls, tmp_path)
    actor = "v2|aiocqhttp@default|user|10001"
    legacy = storage.consume_roast_cooldown(
        group_id="group-a",
        actor_id=actor,
        now=1000,
        cooldown_seconds=INTERVAL,
    )
    migrated_use = storage.consume_roast_charge(
        group_id="group-a",
        actor_id=actor,
        now=1000 + 3600,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    assert legacy.get("remaining", 0) == 0
    assert migrated_use["consumed"] is True
    assert migrated_use["charges"] == 0
    assert migrated_use["refill_anchor"] == 1000


def test_sqlite_compatibility_document_preserves_charge_state(tmp_path):
    storage = _storage(SQLiteStorage, tmp_path)
    storage.consume_roast_charge(
        group_id="group-a",
        actor_id="v2|aiocqhttp@default|user|10001",
        now=1000,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    roast = storage.load_json(tmp_path / "roast_state.json", {})
    entry = roast["roast_charges"]["group-a:v2|aiocqhttp@default|user|10001"]
    assert entry["charges"] == 1
    assert entry["refill_anchor"] == 1000


def test_sqlite_primary_runtime_snapshot_preserves_charge_state(tmp_path):
    storage = _storage(SQLitePrimaryStorage, tmp_path)
    storage.consume_roast_charge(
        group_id="group-a",
        actor_id="v2|aiocqhttp@default|user|10001",
        now=1000,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    roast = storage.load_runtime_snapshot()["roast_state"]
    entry = roast["roast_charges"]["group-a:v2|aiocqhttp@default|user|10001"]
    assert entry["charges"] == 1
    assert entry["refill_anchor"] == 1000
