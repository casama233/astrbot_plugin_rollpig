from __future__ import annotations

from pathlib import Path

from storage import SQLiteStorage, StorageManager


def _pig(pig_id: str) -> dict:
    return {
        "id": pig_id,
        "name": pig_id,
        "description": "test",
        "analysis": "test",
    }


def test_claimed_identity_fragments_do_not_double_count_dashboard(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    canonical = "v2|qq@one|user|1"
    legacy = "1"
    storage.create_daily_draw(
        draw_date="2026-08-01", user_id=canonical, pig=_pig("pig-a")
    )
    storage.create_daily_draw(
        draw_date="2026-08-01", user_id=legacy, pig=_pig("pig-a")
    )
    with storage.transaction() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO identity_claims(claim_kind, legacy_id, namespaced_id) "
            "VALUES ('users', ?, ?)",
            (legacy, canonical),
        )

    overview = storage.get_dashboard_overview(
        start_date="2026-08-01",
        end_date="2026-08-14",
        catalog_ids=("pig-a", "pig-b"),
    )
    assert overview["total_users"] == 1
    assert overview["total_draws"] == 1
    assert overview["average_unlocked"] == 1
    assert overview["average_unlock_rate"] == 50
    assert overview["top_pigs"] == [
        {"id": "pig-a", "draws": 1, "collectors": 1}
    ]
    assert overview["trend"] == [
        {
            "date": "2026-08-01",
            "users": 1,
            "draws": 1,
            "new_unlocks": 1,
        }
    ]
    assert overview["observability"]["identity_scope"] == (
        "claim-aware-logical-users"
    )


def test_claimed_identity_fragments_do_not_distort_deep_analytics(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    canonical = "v2|qq@one|user|1"
    legacy = "1"
    for user_id in (canonical, legacy):
        storage.create_daily_draw(
            draw_date="2026-08-01", user_id=user_id, pig=_pig("pig-a")
        )
    with storage.transaction() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO identity_claims(claim_kind, legacy_id, namespaced_id) "
            "VALUES ('users', ?, ?)",
            (legacy, canonical),
        )

    insights = storage.get_dashboard_insights(
        current_start="2026-08-01",
        current_end="2026-08-07",
        previous_start="2026-07-25",
        previous_end="2026-07-31",
        activity_start="2026-07-11",
        catalog_ids=("pig-a", "pig-b"),
    )
    assert insights["periods"]["current"]["active_users"] == 1
    assert insights["periods"]["current"]["draws"] == 1
    assert insights["catalog"]["median_unlocked"] == 1
    assert insights["catalog"]["zero_collector_count"] == 1
    assert insights["observability"]["identity_scope"] == (
        "claim-aware-logical-users"
    )


def test_core_dashboard_no_longer_fabricates_metric_sparklines():
    page = Path("pages/pig-manager/index.html").read_text(encoding="utf-8")
    forbidden = (
        "catalog-unlocks.slice",
        "v+(users[i]||0)",
        "unlocks.map(v=>v/catalog*100)",
        "数据正在实时生长",
    )
    for token in forbidden:
        assert token not in page
    assert "chart-draw-bar" in page
    assert "本地事实快照" in page


def test_deep_analytics_success_rate_excludes_in_progress_attempts():
    source = Path("pages/pig-manager/ui-analytics.js").read_text(encoding="utf-8")
    assert "const completed = ready + failed" in source
    assert "success: ready / completed * 100" in source
    assert "生成中" in source
    assert "不计入成功率分母" in source
    assert "上期→本期回访率" in source
    assert "本期独有活跃" in source
