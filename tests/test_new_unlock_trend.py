from __future__ import annotations

import sqlite3

from storage import SQLiteStorage, StorageManager


def test_json_projection_derives_new_unlock_from_first_unlocked(tmp_path):
    user_id = "v2|qq|user|1"
    history = {
        "version": 1,
        "users": {
            user_id: {
                "total_draws": 2,
                "active_days": 2,
                "duplicate_streak": 1,
                "pigs": {
                    "pink-pig": {
                        "first_unlocked": "2026-08-01",
                        "last_drawn": "2026-08-02",
                        "count": 2,
                    }
                },
            }
        },
        "daily": {
            "2026-08-01": {
                "draws": 1,
                "new_unlocks": 0,
                "users": [user_id],
                "records": {user_id: "eaten"},
                "eaten_originals": {user_id: "pink-pig"},
            },
            "2026-08-02": {
                "draws": 1,
                "new_unlocks": 0,
                "users": [user_id],
                "records": {user_id: "pink-pig"},
            },
        },
        "pig_snapshots": {
            "pink-pig": {"id": "pink-pig", "name": "粉红猪"},
            "eaten": {"id": "eaten", "name": "吃掉了"},
        },
    }
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    storage.save_json(tmp_path / "pig_history.json", history)

    with storage._connection() as connection:
        rows = connection.execute(
            "SELECT draw_date, was_new_unlock FROM daily_draws ORDER BY draw_date"
        ).fetchall()
    assert [(row["draw_date"], row["was_new_unlock"]) for row in rows] == [
        ("2026-08-01", 1),
        ("2026-08-02", 0),
    ]

    snapshot = storage.load_runtime_snapshot()["history"]
    assert snapshot["daily"]["2026-08-01"]["new_unlocks"] == 1
    assert snapshot["daily"]["2026-08-02"]["new_unlocks"] == 0


def test_schema_v4_backfills_existing_zero_unlock_flags(tmp_path):
    database = tmp_path / "rollpig.db"
    user_id = "v2|qq|user|1"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations(
                version INTEGER PRIMARY KEY,
                applied_at INTEGER NOT NULL
            );
            INSERT INTO schema_migrations VALUES (1, 1), (2, 1), (3, 1);

            CREATE TABLE identities(
                identity_key TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                identity_type TEXT NOT NULL,
                raw_id TEXT NOT NULL,
                legacy_id TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE daily_draws(
                draw_date TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES identities(identity_key),
                pig_id TEXT NOT NULL,
                original_pig_id TEXT NOT NULL DEFAULT '',
                group_ids_json TEXT NOT NULL DEFAULT '[]',
                created_at INTEGER NOT NULL DEFAULT 0,
                was_new_unlock INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(draw_date, user_id)
            );
            CREATE TABLE user_pigs(
                user_id TEXT NOT NULL REFERENCES identities(identity_key),
                pig_id TEXT NOT NULL,
                first_unlocked TEXT NOT NULL,
                last_drawn TEXT NOT NULL,
                draw_count INTEGER NOT NULL,
                PRIMARY KEY(user_id, pig_id)
            );
            """
        )
        connection.execute(
            "INSERT INTO identities VALUES (?, 'qq', 'user', '1', '1', 1)",
            (user_id,),
        )
        connection.execute(
            "INSERT INTO user_pigs VALUES (?, 'pink-pig', '2026-08-01', '2026-08-02', 2)",
            (user_id,),
        )
        connection.execute(
            "INSERT INTO daily_draws VALUES ('2026-08-01', ?, 'eaten', 'pink-pig', '[]', 1, 0)",
            (user_id,),
        )
        connection.execute(
            "INSERT INTO daily_draws VALUES ('2026-08-02', ?, 'pink-pig', '', '[]', 2, 0)",
            (user_id,),
        )

    storage = SQLiteStorage(database, tmp_path, StorageManager.MANAGED_PATHS)
    with storage._connection() as connection:
        flags = connection.execute(
            "SELECT draw_date, was_new_unlock FROM daily_draws ORDER BY draw_date"
        ).fetchall()
        version = connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0]

    assert [(row["draw_date"], row["was_new_unlock"]) for row in flags] == [
        ("2026-08-01", 1),
        ("2026-08-02", 0),
    ]
    assert version == 5
