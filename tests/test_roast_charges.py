from roast_charges import (
    bootstrap_legacy_cooldown,
    consume_roast_charge_state,
    refresh_roast_charge_state,
)


HOUR = 3600
INTERVAL = 8 * HOUR


def test_two_immediate_roasts_consume_two_charges_without_resetting_refill():
    first = consume_roast_charge_state(
        None, now=1000, max_charges=2, recovery_seconds=INTERVAL
    )
    second = consume_roast_charge_state(
        first, now=1010, max_charges=2, recovery_seconds=INTERVAL
    )
    blocked = consume_roast_charge_state(
        second, now=1020, max_charges=2, recovery_seconds=INTERVAL
    )

    assert first["consumed"] is True and first["charges"] == 1
    assert second["consumed"] is True and second["charges"] == 0
    assert second["refill_anchor"] == first["refill_anchor"] == 1000
    assert blocked["consumed"] is False and blocked["charges"] == 0
    assert blocked["next_refill_seconds"] == INTERVAL - 20


def test_missing_charges_refill_one_by_one():
    state = {"charges": 0, "refill_anchor": 1000}
    one = refresh_roast_charge_state(
        state, now=1000 + INTERVAL, max_charges=2, recovery_seconds=INTERVAL
    )
    full = refresh_roast_charge_state(
        one, now=1000 + 2 * INTERVAL, max_charges=2, recovery_seconds=INTERVAL
    )

    assert one["charges"] == 1
    assert one["refill_anchor"] == 1000 + INTERVAL
    assert full["charges"] == 2
    assert full["next_refill_seconds"] == 0


def test_spending_recovered_charge_keeps_queue_running():
    empty = {"charges": 0, "refill_anchor": 1000}
    spent = consume_roast_charge_state(
        empty,
        now=1000 + INTERVAL,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    assert spent["consumed"] is True
    assert spent["charges"] == 0
    assert spent["refill_anchor"] == 1000 + INTERVAL
    assert spent["next_refill_seconds"] == INTERVAL


def test_active_legacy_cooldown_becomes_one_spent_charge():
    migrated = bootstrap_legacy_cooldown(
        1000,
        now=1000 + HOUR,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )
    consumed = consume_roast_charge_state(
        migrated,
        now=1000 + HOUR,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    assert migrated["charges"] == 1
    assert consumed["consumed"] is True
    assert consumed["charges"] == 0
    assert consumed["refill_anchor"] == 1000


def test_expired_legacy_cooldown_starts_full():
    migrated = bootstrap_legacy_cooldown(
        1000,
        now=1000 + INTERVAL,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    assert migrated["charges"] == 2
    assert migrated["next_refill_seconds"] == 0


def test_capacity_one_preserves_legacy_cooldown_behavior():
    migrated = bootstrap_legacy_cooldown(
        1000,
        now=1000 + HOUR,
        max_charges=1,
        recovery_seconds=INTERVAL,
    )
    blocked = consume_roast_charge_state(
        migrated,
        now=1000 + HOUR,
        max_charges=1,
        recovery_seconds=INTERVAL,
    )

    assert migrated["charges"] == 0
    assert blocked["consumed"] is False
    assert blocked["next_refill_seconds"] == 7 * HOUR
