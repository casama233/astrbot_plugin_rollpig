from __future__ import annotations

import time

from storage import SQLiteStorage, StorageManager


def _pig(pig_id: str) -> dict:
    return {
        "id": pig_id,
        "name": pig_id,
        "description": "测试",
        "analysis": "测试",
    }


def test_sql_dashboard_overview_aggregates_normalized_tables(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.create_daily_draw(
        draw_date="2026-08-01", user_id="u1", pig=_pig("pig-a")
    )
    storage.create_daily_draw(
        draw_date="2026-08-02", user_id="u1", pig=_pig("pig-a")
    )
    storage.create_daily_draw(
        draw_date="2026-08-02", user_id="u2", pig=_pig("pig-b")
    )

    overview = storage.get_dashboard_overview(
        start_date="2026-08-01",
        end_date="2026-08-14",
        catalog_ids=("pig-a", "pig-b"),
    )
    assert overview["total_users"] == 2
    assert overview["total_draws"] == 3
    assert overview["average_unlocked"] == 1
    assert overview["average_unlock_rate"] == 50
    trend = {item["date"]: item for item in overview["trend"]}
    assert trend["2026-08-01"] == {
        "date": "2026-08-01",
        "users": 1,
        "draws": 1,
        "new_unlocks": 1,
    }
    assert trend["2026-08-02"] == {
        "date": "2026-08-02",
        "users": 2,
        "draws": 2,
        "new_unlocks": 1,
    }
    assert overview["top_pigs"][:2] == [
        {"id": "pig-a", "draws": 2, "collectors": 1},
        {"id": "pig-b", "draws": 1, "collectors": 1},
    ]
    assert overview["observability"]["analytics_source"] == "normalized-sql"
    assert overview["observability"]["schema_version"] == 5


def test_dashboard_indexes_and_repair_observability(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.rebuild_projections(reason="startup-auto")
    health = storage.health()
    assert health["analytics_source"] == "normalized-sql"
    assert health["last_repair_reason"] == "startup-auto"
    assert health["last_repair_action"]
    assert health["last_repair_at"] > 0
    with storage._connection() as connection:
        indexes = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
    assert {
        "idx_daily_draws_date_pig",
        "idx_user_pigs_pig_user",
        "idx_user_pigs_first_unlocked",
    } <= indexes


def test_sql_dashboard_analytics_scales_to_hundred_thousand_users(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    with storage.transaction() as connection:
        connection.execute(
            """
            WITH RECURSIVE seq(x) AS (
                SELECT 0 UNION ALL SELECT x + 1 FROM seq WHERE x < 99999
            )
            INSERT INTO identities(
                identity_key, namespace, identity_type, raw_id, legacy_id, created_at
            )
            SELECT printf('u%06d', x), 'load', 'user', printf('%d', x),
                   printf('%d', x), 1 FROM seq
            """
        )
        connection.execute(
            """
            INSERT INTO user_stats(
                user_id, total_draws, active_days, duplicate_streak, payload_json
            )
            SELECT identity_key, 3, 3, 2, '{}'
            FROM identities WHERE namespace = 'load'
            """
        )
        connection.execute(
            """
            INSERT INTO user_pigs(
                user_id, pig_id, first_unlocked, last_drawn, draw_count
            )
            SELECT identity_key,
                   printf('pig-%02d', CAST(raw_id AS INTEGER) % 50),
                   '2026-08-01', '2026-08-03', 3
            FROM identities WHERE namespace = 'load'
            """
        )
        connection.execute(
            """
            WITH RECURSIVE seq(x) AS (
                SELECT 0 UNION ALL SELECT x + 1 FROM seq WHERE x < 299999
            )
            INSERT INTO daily_draws(
                draw_date, user_id, pig_id, original_pig_id,
                group_ids_json, created_at, was_new_unlock
            )
            SELECT date('2026-08-01', printf('+%d day', x % 3)),
                   printf('u%06d', x % 100000),
                   printf('pig-%02d', (x % 100000) % 50),
                   '', '[]', 1, CASE WHEN x % 3 = 0 THEN 1 ELSE 0 END
            FROM seq
            """
        )

    started = time.monotonic()
    overview = storage.get_dashboard_overview(
        start_date="2026-08-01",
        end_date="2026-08-14",
        catalog_ids=tuple(f"pig-{index:02d}" for index in range(50)),
    )
    elapsed = time.monotonic() - started
    assert overview["total_users"] == 100_000
    assert overview["total_draws"] == 300_000
    assert sum(item["draws"] for item in overview["trend"]) == 300_000
    assert elapsed < 8
