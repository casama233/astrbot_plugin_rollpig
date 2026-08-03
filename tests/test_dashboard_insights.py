from __future__ import annotations

import json

from storage import SQLiteStorage, StorageManager


def _pig(pig_id: str) -> dict:
    return {"id": pig_id, "name": pig_id, "description": "test", "analysis": "test"}


def test_sql_dashboard_insights_are_aggregate_only(tmp_path):
    storage = SQLiteStorage(tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS)
    storage.create_daily_draw(draw_date="2026-07-22", user_id="v2|qq@one|user|1", pig=_pig("pig-a"))
    storage.create_daily_draw(draw_date="2026-07-23", user_id="v2|discord@one|user|2", pig=_pig("pig-b"))
    storage.create_daily_draw(draw_date="2026-07-29", user_id="v2|qq@one|user|1", pig=_pig("pig-a"))
    storage.create_daily_draw(draw_date="2026-08-01", user_id="v2|telegram@one|user|3", pig=_pig("pig-c"))
    storage.increment_roast_count(
        draw_date="2026-08-02", group_id="g", user_id="v2|qq@one|user|1", cutoff_date="2026-07-01"
    )
    storage.increment_roast_count(
        draw_date="2026-08-02", group_id="g", user_id="v2|qq@one|user|1", cutoff_date="2026-07-01"
    )
    claim = storage.claim_ai_roast_generation(
        pig_id="pig-a", generated_date="2026-08-03", owner_token="owner", attempted_at=1.0,
        cutoff_date="2026-07-29", through_date="2026-08-04",
    )
    assert claim["claimed"] is True
    storage.complete_ai_roast_generation(
        pig_id="pig-a", generated_date="2026-08-03", owner_token="owner", content="ready",
        completed_at=2.0, cutoff_date="2026-07-29", through_date="2026-08-04",
    )

    insights = storage.get_dashboard_insights(
        current_start="2026-07-29", current_end="2026-08-04",
        previous_start="2026-07-22", previous_end="2026-07-28",
        activity_start="2026-07-08", catalog_ids=("pig-a", "pig-b", "pig-c", "pig-d"),
    )
    assert insights["source"] == "normalized-sql"
    assert insights["periods"]["current"]["active_users"] == 2
    assert insights["periods"]["previous"]["active_users"] == 2
    assert insights["retention"]["returning_users"] == 1
    assert insights["retention"]["rate"] == 50
    assert insights["catalog"]["zero_collector_count"] == 1
    assert insights["operations"]["roasts"] == 2
    assert insights["operations"]["ai"]["ready"] == 1
    assert insights["rising_pigs"][0]["id"] == "pig-c"
    assert {item["platform"] for item in insights["platforms"]} == {
        "qq@one", "discord@one", "telegram@one"
    }
    encoded = json.dumps(insights, ensure_ascii=False)
    assert "v2|qq@one|user|1" not in encoded
    assert "v2|discord@one|user|2" not in encoded


def test_dashboard_insights_fill_all_twenty_eight_activity_days(tmp_path):
    storage = SQLiteStorage(tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS)
    result = storage.get_dashboard_insights(
        current_start="2026-07-29", current_end="2026-08-04",
        previous_start="2026-07-22", previous_end="2026-07-28",
        activity_start="2026-07-08", catalog_ids=("pig-a",),
    )
    assert len(result["activity"]) == 28
    assert result["activity"][0]["date"] == "2026-07-08"
    assert result["activity"][-1]["date"] == "2026-08-04"
