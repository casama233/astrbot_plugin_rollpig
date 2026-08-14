from services.oven_charge_service import OvenChargeService


def test_full_account_spends_one_and_starts_recovery_clock():
    result = OvenChargeService.consume(
        None,
        now=1000,
        max_charges=2,
        recovery_seconds=800,
    )
    assert result["consumed"] is True
    assert result["charges"] == 1
    assert result["entry"] == {"charges": 1, "anchor_at": 1000.0}


def test_second_spend_preserves_partial_recovery_progress():
    result = OvenChargeService.consume(
        {"charges": 1, "anchor_at": 1000},
        now=1200,
        max_charges=2,
        recovery_seconds=800,
    )
    assert result["consumed"] is True
    assert result["charges"] == 0
    assert result["entry"] == {"charges": 0, "anchor_at": 1000.0}


def test_empty_account_reports_time_to_next_cell():
    result = OvenChargeService.consume(
        {"charges": 0, "anchor_at": 1000},
        now=1200,
        max_charges=2,
        recovery_seconds=800,
    )
    assert result["consumed"] is False
    assert result["remaining"] == 600


def test_lazy_recovery_adds_one_per_interval_without_overbanking():
    status = OvenChargeService.status(
        {"charges": 0, "anchor_at": 1000},
        now=1900,
        max_charges=2,
        recovery_seconds=800,
    )
    assert status["charges"] == 1
    assert status["remaining"] == 700
    assert status["entry"] == {"charges": 1, "anchor_at": 1800.0}

    full = OvenChargeService.status(
        status["entry"],
        now=2700,
        max_charges=2,
        recovery_seconds=800,
    )
    assert full["charges"] == 2
    assert full["remaining"] == 0
    assert full["entry"]["anchor_at"] == 2700.0


def test_group_refill_adds_one_only_and_caps_at_maximum():
    one = OvenChargeService.add_one(
        {"charges": 0, "anchor_at": 1000},
        now=1200,
        max_charges=2,
        recovery_seconds=800,
    )
    assert one == {"charges": 1, "anchor_at": 1000.0}

    full = OvenChargeService.add_one(
        {"charges": 2, "anchor_at": 1000},
        now=1200,
        max_charges=2,
        recovery_seconds=800,
    )
    assert full == {"charges": 2, "anchor_at": 1200.0}


def test_refill_threshold_scales_and_second_round_is_harder():
    assert OvenChargeService.refill_requirement(1, 0) == 0
    assert OvenChargeService.refill_requirement(2, 0) == 2
    assert OvenChargeService.refill_requirement(5, 0) == 3
    assert OvenChargeService.refill_requirement(16, 0) == 5
    assert OvenChargeService.refill_requirement(16, 1) == 7
    assert OvenChargeService.refill_requirement(100, 0) == 8
    assert OvenChargeService.refill_requirement(100, 1) == 10
