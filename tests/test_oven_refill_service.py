from services.oven_refill_service import OvenRefillService


def test_refill_threshold_scales_with_active_population():
    assert OvenRefillService.refill_requirement(1, 0) == 0
    assert OvenRefillService.refill_requirement(2, 0) == 2
    assert OvenRefillService.refill_requirement(5, 0) == 3
    assert OvenRefillService.refill_requirement(16, 0) == 5
    assert OvenRefillService.refill_requirement(100, 0) == 8


def test_later_successful_rounds_are_harder_but_capped_by_population():
    assert OvenRefillService.refill_requirement(16, 1) == 7
    assert OvenRefillService.refill_requirement(100, 1) == 10
    assert OvenRefillService.refill_requirement(5, 1) == 5


def test_threshold_policy_is_configurable_and_bounded():
    assert OvenRefillService.refill_requirement(
        20,
        0,
        ratio_percent=50,
        minimum_supporters=4,
        maximum_base_supporters=6,
    ) == 6
    assert OvenRefillService.refill_requirement(
        3,
        4,
        ratio_percent=100,
        minimum_supporters=2,
        maximum_base_supporters=8,
        extra_per_success=10,
    ) == 3
