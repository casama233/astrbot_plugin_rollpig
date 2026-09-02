from __future__ import annotations

import datetime

from gameplay_events import (
    EVENT_EX_LEVEL_UP,
    EVENT_ROAST_SUCCESS,
    append_gameplay_event,
    build_gameplay_event,
    prune_gameplay_events,
    read_gameplay_events,
)


def test_build_event_keeps_legacy_shape_and_adds_optional_fields():
    event = build_gameplay_event(
        EVENT_EX_LEVEL_UP,
        actor_id="u1",
        pig_id="sleep-pig",
        metadata={"from": 2, "to": 3},
        event_id="evt-1",
        at=123,
    )
    assert event["version"] == 1
    assert event["id"] == "evt-1"
    assert event["kind"] == EVENT_EX_LEVEL_UP
    assert event["actor_id"] == "u1"
    assert event["target_id"] == ""
    assert event["victim_id"] == ""
    assert event["pig_id"] == "sleep-pig"
    assert event["metadata"] == {"from": 2, "to": 3}
    assert event["at"] == 123


def test_append_is_idempotent_and_bounded():
    state: dict[str, object] = {}
    first = build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="same", at=1)
    assert append_gameplay_event(state, "2026-08-14", "g1", first, max_events=2)
    assert not append_gameplay_event(state, "2026-08-14", "g1", first, max_events=2)
    assert append_gameplay_event(
        state,
        "2026-08-14",
        "g1",
        build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="two", at=2),
        max_events=2,
    )
    assert append_gameplay_event(
        state,
        "2026-08-14",
        "g1",
        build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="three", at=3),
        max_events=2,
    )
    assert [row["id"] for row in read_gameplay_events(state, "2026-08-14", "g1")] == [
        "two",
        "three",
    ]


def test_read_returns_defensive_copies():
    state: dict[str, object] = {}
    append_gameplay_event(
        state,
        "2026-08-14",
        "g1",
        build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="evt", at=1),
    )
    rows = read_gameplay_events(state, "2026-08-14", "g1")
    rows[0]["kind"] = "mutated"
    assert read_gameplay_events(state, "2026-08-14", "g1")[0]["kind"] == EVENT_ROAST_SUCCESS


def test_prune_uses_same_keep_window_as_daily_report():
    state = {
        "2026-07-01": {"g1": []},
        "2026-08-13": {"g1": []},
        "2026-08-14": {"g1": []},
    }
    assert prune_gameplay_events(state, datetime.date(2026, 8, 14), keep_days=14)
    assert "2026-07-01" not in state
    assert "2026-08-13" in state


def test_append_can_dedupe_event_id_across_scopes():
    event = build_gameplay_event(EVENT_EX_LEVEL_UP, event_id="global", at=1)

    default_state: dict[str, object] = {}
    assert append_gameplay_event(default_state, "2026-08-14", "g1", event)
    assert append_gameplay_event(default_state, "2026-08-14", "g2", event)

    global_state: dict[str, object] = {}
    assert append_gameplay_event(
        global_state,
        "2026-08-14",
        "g1",
        event,
        dedupe_across_scopes=True,
    )
    assert not append_gameplay_event(
        global_state,
        "2026-08-14",
        "private:u1",
        event,
        dedupe_across_scopes=True,
    )
    assert not read_gameplay_events(global_state, "2026-08-14", "private:u1")
