from __future__ import annotations

import datetime

from roast_reservations import (
    create_or_join_reservation,
    get_reservation,
    prune_reservations,
    resolve_reservation,
)


def test_create_join_duplicate_and_capacity_are_deterministic():
    state: dict = {}
    created = create_or_join_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="target",
        actor_id="chef",
        max_participants=3,
        now=1,
    )
    assert created["status"] == "created"
    row = created["reservation"]
    assert row["chef_id"] == "chef"
    assert row["participants"] == ["chef"]

    duplicate = create_or_join_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="target",
        actor_id="chef",
        max_participants=3,
        now=2,
    )
    assert duplicate["status"] == "existing"

    joined = create_or_join_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="target",
        actor_id="friend",
        max_participants=3,
        now=3,
    )
    assert joined["status"] == "joined"
    assert joined["reservation"]["participants"] == ["chef", "friend"]

    create_or_join_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="target",
        actor_id="third",
        max_participants=3,
        now=4,
    )
    full = create_or_join_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="target",
        actor_id="fourth",
        max_participants=3,
        now=5,
    )
    assert full["status"] == "full"
    assert full["reservation"]["participants"] == ["chef", "friend", "third"]


def test_resolution_is_one_shot_and_keeps_original_chef():
    state: dict = {}
    create_or_join_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="target",
        actor_id="chef",
        now=1,
    )
    resolved = resolve_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="target",
        outcome="backlash",
        now=10,
    )
    assert resolved is not None
    assert resolved["status"] == "resolved"
    assert resolved["chef_id"] == "chef"
    assert resolved["outcome"] == "backlash"
    assert (
        resolve_reservation(
            state,
            draw_date="2026-08-14",
            group_id="g1",
            target_id="target",
            outcome="success",
            now=11,
        )
        is None
    )


def test_reservations_are_scoped_by_date_group_and_target():
    state: dict = {}
    for group_id in ("g1", "g2"):
        create_or_join_reservation(
            state,
            draw_date="2026-08-14",
            group_id=group_id,
            target_id="target",
            actor_id=f"chef-{group_id}",
        )
    assert get_reservation(state, "2026-08-14", "g1", "target")["chef_id"] == "chef-g1"
    assert get_reservation(state, "2026-08-14", "g2", "target")["chef_id"] == "chef-g2"
    assert get_reservation(state, "2026-08-15", "g1", "target") is None


def test_old_reservations_are_pruned_without_carrying_to_new_day():
    state: dict = {}
    create_or_join_reservation(
        state,
        draw_date="2026-08-10",
        group_id="g1",
        target_id="old",
        actor_id="chef",
    )
    create_or_join_reservation(
        state,
        draw_date="2026-08-14",
        group_id="g1",
        target_id="today",
        actor_id="chef",
    )
    assert prune_reservations(state, datetime.date(2026, 8, 14), keep_days=2)
    assert get_reservation(state, "2026-08-10", "g1", "old") is None
    assert get_reservation(state, "2026-08-14", "g1", "today") is not None
