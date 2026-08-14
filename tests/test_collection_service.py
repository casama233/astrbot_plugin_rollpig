from services.collection_service import CollectionService
from services.draw_service import DrawService


def test_claimed_read_candidates_only_include_owned_fragments():
    current = "v2|aiocqhttp@default|user|10001"
    pre_instance = "v2|aiocqhttp|user|10001"
    raw = "10001"
    other_platform = "v2|telegram@default|user|10001"

    selected = CollectionService.claimed_read_candidates(
        (current, pre_instance, raw),
        {
            pre_instance: current,
            raw: other_platform,
        },
    )

    assert selected == (current, pre_instance)
    assert raw not in selected


def test_preferred_storage_key_is_kept_after_a_safe_claim():
    current = "v2|aiocqhttp@default|user|10001"
    pre_instance = "v2|aiocqhttp|user|10001"

    selected = CollectionService.claimed_read_candidates(
        (current, pre_instance, "10001"),
        {},
        preferred_storage_key=pre_instance,
    )

    assert selected == (current, pre_instance)


def test_merge_ownership_preserves_authoritative_gameplay_state():
    primary = {
        "total_draws": 3,
        "active_days": 3,
        "duplicate_streak": 0,
        "pigs": {
            "pink-pig": {
                "first_unlocked": "2026-08-12",
                "last_drawn": "2026-08-14",
                "count": 2,
            }
        },
    }
    legacy = {
        "total_draws": 100,
        "active_days": 90,
        "duplicate_streak": 8,
        "pigs": {
            "pink-pig": {
                "first_unlocked": "2026-07-01",
                "last_drawn": "2026-08-13",
                "count": 2,
            },
            "blue-pig": {
                "first_unlocked": "2026-07-02",
                "last_drawn": "2026-07-02",
                "count": 4,
            },
        },
    }

    merged = CollectionService.merge_ownership((primary, legacy))

    assert merged["total_draws"] == 3
    assert merged["active_days"] == 3
    assert merged["duplicate_streak"] == 0
    assert set(merged["pigs"]) == {"pink-pig", "blue-pig"}
    assert merged["pigs"]["pink-pig"] == {
        "first_unlocked": "2026-07-01",
        "last_drawn": "2026-08-14",
        "count": 2,
    }
    assert merged["pigs"]["blue-pig"]["count"] == 4


def test_stale_fragment_cannot_raise_current_pity():
    current = {
        "duplicate_streak": 0,
        "pigs": {"pink-pig": {"count": 1}},
    }
    stale = {
        "duplicate_streak": 8,
        "pigs": {"pink-pig": {"count": 1}},
    }

    merged = CollectionService.merge_ownership((current, stale))
    service = DrawService(
        enable_new_pig_pity=True,
        pity_step_percent=15,
        enable_daily_duplicate_pity=False,
    )

    assert merged["duplicate_streak"] == 0
    assert service.pity_chance(merged) == 0.0


def test_merge_ownership_uses_max_count_instead_of_sum_for_overlap():
    first = {
        "duplicate_streak": 1,
        "pigs": {
            "same-pig": {
                "first_unlocked": "2026-08-01",
                "last_drawn": "2026-08-10",
                "count": 5,
            }
        },
    }
    migration_copy = {
        "duplicate_streak": 9,
        "pigs": {
            "same-pig": {
                "first_unlocked": "2026-08-01",
                "last_drawn": "2026-08-10",
                "count": 5,
            }
        },
    }

    merged = CollectionService.merge_ownership((first, migration_copy))

    assert merged["pigs"]["same-pig"]["count"] == 5
    assert merged["duplicate_streak"] == 1


def test_sibling_instance_is_not_discovered_outside_candidate_pool():
    current = "v2|aiocqhttp@default|user|10001"
    pre_instance = "v2|aiocqhttp|user|10001"
    sibling = "v2|aiocqhttp@other-bot|user|10001"

    selected = CollectionService.claimed_read_candidates(
        (current, pre_instance, "10001"),
        {sibling: current},
    )

    assert sibling not in selected
    assert selected == (current,)
