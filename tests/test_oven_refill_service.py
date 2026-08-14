from roast_charges import add_roast_charge_state
from services.oven_refill_service import OvenRefillService


INTERVAL = 8 * 3600


def test_refill_requirement_matches_group_activity_and_escalates():
    service = OvenRefillService()

    assert service.refill_requirement(1, 0) == 0
    assert service.refill_requirement(2, 0) == 2
    assert service.refill_requirement(16, 0) == 5
    assert service.refill_requirement(16, 1) == 7
    assert service.refill_requirement(16, 2) == 9


def test_refill_requirement_never_exceeds_active_players():
    service = OvenRefillService()

    assert (
        service.refill_requirement(
            4,
            5,
            ratio_percent=80,
            minimum_supporters=4,
            extra_per_success=10,
        )
        == 4
    )


def test_add_one_charge_does_not_overfill_and_preserves_recovery_queue():
    missing_two = {"charges": 0, "refill_anchor": 1000}
    first = add_roast_charge_state(
        missing_two,
        now=2000,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )
    full = add_roast_charge_state(
        first,
        now=2010,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )
    overfill = add_roast_charge_state(
        full,
        now=2020,
        max_charges=2,
        recovery_seconds=INTERVAL,
    )

    assert first["charges"] == 1 and first["increased"] is True
    assert first["refill_anchor"] == 1000
    assert full["charges"] == 2 and full["increased"] is True
    assert full["refill_anchor"] == 2010
    assert overfill["charges"] == 2 and overfill["increased"] is False
