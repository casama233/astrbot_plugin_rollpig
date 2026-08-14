from __future__ import annotations

import pytest

from services.draw_service import DrawService


class StubRng:
    def __init__(self, first_choice, random_value: float):
        self.first_choice = first_choice
        self.random_value = random_value
        self.choice_calls = 0

    def choice(self, items):
        self.choice_calls += 1
        if self.choice_calls == 1:
            return self.first_choice
        return items[0]

    def random(self):
        return self.random_value


def test_legacy_pity_is_unchanged_when_daily_bonus_is_disabled():
    service = DrawService(
        enable_new_pig_pity=True,
        pity_step_percent=15,
        enable_daily_duplicate_pity=False,
    )
    assert service.pity_chance({"duplicate_streak": 0}) == pytest.approx(0.0)
    assert service.pity_chance({"duplicate_streak": 1}) == pytest.approx(0.15)
    assert service.pity_chance({"duplicate_streak": 2}) == pytest.approx(0.30)


def test_daily_bonus_starts_on_second_consecutive_duplicate_day():
    service = DrawService()
    assert service.pity_chance({"duplicate_streak": 0}) == pytest.approx(0.0)
    assert service.pity_chance({"duplicate_streak": 1}) == pytest.approx(0.20)
    assert service.pity_chance({"duplicate_streak": 2}) == pytest.approx(0.40)
    assert service.pity_chance({"duplicate_streak": 3}) == pytest.approx(0.60)
    assert service.pity_chance({"duplicate_streak": 4}) == pytest.approx(0.75)


def test_daily_bonus_has_independent_switch_and_can_work_without_legacy_pity():
    service = DrawService(
        enable_new_pig_pity=False,
        enable_daily_duplicate_pity=True,
        daily_duplicate_pity_start_day=2,
        daily_duplicate_pity_step_percent=5,
        daily_duplicate_pity_max_percent=15,
    )
    assert service.pity_chance({"duplicate_streak": 0}) == pytest.approx(0.0)
    assert service.pity_chance({"duplicate_streak": 1}) == pytest.approx(0.05)
    assert service.pity_chance({"duplicate_streak": 3}) == pytest.approx(0.15)
    assert service.pity_chance({"duplicate_streak": 20}) == pytest.approx(0.15)


def test_combined_pity_never_exceeds_eighty_percent():
    service = DrawService()
    assert service.pity_chance({"duplicate_streak": 20}) == pytest.approx(0.80)


def test_choose_rerolls_duplicate_to_unseen_when_combined_pity_hits():
    duplicate = {"id": "owned", "name": "Owned"}
    unseen = {"id": "new", "name": "New"}
    service = DrawService()
    rng = StubRng(duplicate, random_value=0.19)

    chosen = service.choose(
        [duplicate, unseen],
        {"pigs": {"owned": {"count": 1}}, "duplicate_streak": 1},
        rng=rng,
    )

    assert chosen["id"] == "new"


def test_choose_keeps_duplicate_when_roll_misses_combined_pity():
    duplicate = {"id": "owned", "name": "Owned"}
    unseen = {"id": "new", "name": "New"}
    service = DrawService()
    rng = StubRng(duplicate, random_value=0.20)

    chosen = service.choose(
        [duplicate, unseen],
        {"pigs": {"owned": {"count": 1}}, "duplicate_streak": 1},
        rng=rng,
    )

    assert chosen["id"] == "owned"
