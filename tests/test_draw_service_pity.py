from __future__ import annotations

import datetime

import pytest

from rollpig_core import consecutive_duplicate_day_streak
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


def test_daily_bonus_starts_on_second_adjacent_duplicate_day():
    service = DrawService()
    assert service.pity_chance(
        {"duplicate_streak": 0, "daily_duplicate_streak": 0}
    ) == pytest.approx(0.0)
    assert service.pity_chance(
        {"duplicate_streak": 1, "daily_duplicate_streak": 1}
    ) == pytest.approx(0.20)
    assert service.pity_chance(
        {"duplicate_streak": 2, "daily_duplicate_streak": 2}
    ) == pytest.approx(0.40)
    assert service.pity_chance(
        {"duplicate_streak": 3, "daily_duplicate_streak": 3}
    ) == pytest.approx(0.60)
    assert service.pity_chance(
        {"duplicate_streak": 4, "daily_duplicate_streak": 4}
    ) == pytest.approx(0.75)


def test_calendar_gap_resets_only_new_bonus_not_legacy_pity():
    service = DrawService()
    assert service.pity_chance(
        {"duplicate_streak": 3, "daily_duplicate_streak": 0}
    ) == pytest.approx(0.45)


def test_daily_bonus_has_independent_switch_and_can_work_without_legacy_pity():
    service = DrawService(
        enable_new_pig_pity=False,
        enable_daily_duplicate_pity=True,
        daily_duplicate_pity_start_day=2,
        daily_duplicate_pity_step_percent=5,
        daily_duplicate_pity_max_percent=15,
    )
    assert service.pity_chance({"daily_duplicate_streak": 0}) == pytest.approx(0.0)
    assert service.pity_chance({"daily_duplicate_streak": 1}) == pytest.approx(0.05)
    assert service.pity_chance({"daily_duplicate_streak": 3}) == pytest.approx(0.15)
    assert service.pity_chance({"daily_duplicate_streak": 20}) == pytest.approx(0.15)


def test_combined_pity_never_exceeds_eighty_percent():
    service = DrawService()
    assert service.pity_chance(
        {"duplicate_streak": 20, "daily_duplicate_streak": 20}
    ) == pytest.approx(0.80)


def test_calendar_streak_requires_adjacent_days_and_preexisting_unlock():
    today = datetime.date(2026, 8, 14)
    collection = {
        "pigs": {
            "owned": {"first_unlocked": "2026-08-01", "count": 5},
            "newer": {"first_unlocked": "2026-08-12", "count": 1},
        }
    }
    history = {
        "daily": {
            "2026-08-13": {"records": {"u": "owned"}},
            "2026-08-12": {"records": {"u": "owned"}},
            "2026-08-11": {"records": {"u": "owned"}},
        }
    }
    assert consecutive_duplicate_day_streak(history, collection, "u", today) == 3

    history["daily"].pop("2026-08-13")
    assert consecutive_duplicate_day_streak(history, collection, "u", today) == 0


def test_calendar_streak_stops_when_previous_day_was_a_new_unlock():
    today = datetime.date(2026, 8, 14)
    collection = {"pigs": {"new": {"first_unlocked": "2026-08-13", "count": 1}}}
    history = {"daily": {"2026-08-13": {"records": {"u": "new"}}}}
    assert consecutive_duplicate_day_streak(history, collection, "u", today) == 0


def test_eaten_visible_state_uses_original_draw_for_calendar_streak():
    today = datetime.date(2026, 8, 14)
    collection = {"pigs": {"owned": {"first_unlocked": "2026-08-01", "count": 4}}}
    history = {
        "daily": {
            "2026-08-13": {
                "records": {"u": "eaten"},
                "eaten_originals": {"u": "owned"},
            }
        }
    }
    assert consecutive_duplicate_day_streak(history, collection, "u", today) == 1


def test_choose_rerolls_duplicate_to_unseen_when_combined_pity_hits():
    duplicate = {"id": "owned", "name": "Owned"}
    unseen = {"id": "new", "name": "New"}
    service = DrawService()
    rng = StubRng(duplicate, random_value=0.19)

    chosen = service.choose(
        [duplicate, unseen],
        {
            "pigs": {"owned": {"count": 1}},
            "duplicate_streak": 1,
            "daily_duplicate_streak": 1,
        },
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
        {
            "pigs": {"owned": {"count": 1}},
            "duplicate_streak": 1,
            "daily_duplicate_streak": 1,
        },
        rng=rng,
    )

    assert chosen["id"] == "owned"


def test_choose_duplicate_only_uses_already_unlocked_active_pigs():
    owned = {"id": "owned", "name": "Owned"}
    unseen = {"id": "new", "name": "New"}
    eaten = {"id": "eaten", "name": "Eaten"}
    service = DrawService()
    rng = StubRng(owned, random_value=0.0)

    chosen = service.choose_duplicate(
        [owned, unseen, eaten],
        {"pigs": {"owned": {"count": 3}, "eaten": {"count": 1}}},
        rng=rng,
    )

    assert chosen == owned


def test_choose_duplicate_falls_back_when_player_has_no_active_unlocks():
    service = DrawService()
    assert service.choose_duplicate(
        [{"id": "new", "name": "New"}],
        {"pigs": {}},
    ) is None
