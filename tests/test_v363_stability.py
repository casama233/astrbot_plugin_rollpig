from __future__ import annotations

import ast
from pathlib import Path

from rollpig_core import (
    claimed_identity_candidates,
    merge_user_collection_fragments,
)
from storage import StorageManager
from storage.sqlite_storage import SQLiteStorage

ROOT = Path(__file__).resolve().parents[1]


def test_claimed_candidates_keep_cross_platform_legacy_isolated():
    current = "v2|aiocqhttp@default|user|10001"
    pre_instance = "v2|aiocqhttp|user|10001"
    raw = "10001"
    claims = {
        pre_instance: current,
        raw: "v2|telegram@default|user|10001",
    }
    assert claimed_identity_candidates(current, current, claims) == (
        current,
        pre_instance,
    )


def test_claimed_candidates_accept_storage_key_selected_by_claim_layer():
    current = "v2|aiocqhttp@default|user|10001"
    raw = "10001"
    assert claimed_identity_candidates(current, raw, {}) == (current, raw)


def test_collection_fragment_merge_unions_ownership_without_inflating_gameplay_state():
    merged = merge_user_collection_fragments(
        [
            {
                "total_draws": 2,
                "active_days": 2,
                "duplicate_streak": 0,
                "pigs": {
                    "pig-a": {
                        "first_unlocked": "2026-08-10",
                        "last_drawn": "2026-08-14",
                        "count": 2,
                    }
                },
            },
            {
                "total_draws": 80,
                "active_days": 60,
                "duplicate_streak": 8,
                "pigs": {
                    "pig-a": {
                        "first_unlocked": "2026-07-01",
                        "last_drawn": "2026-08-01",
                        "count": 2,
                    },
                    "pig-b": {
                        "first_unlocked": "2026-07-02",
                        "last_drawn": "2026-07-02",
                        "count": 1,
                    },
                },
            },
        ]
    )
    # Gameplay/pity counters belong to the highest-priority current fragment.
    assert merged["total_draws"] == 2
    assert merged["active_days"] == 2
    assert merged["duplicate_streak"] == 0
    # Permanent ownership is unioned, but duplicate migration copies do not grant EX.
    assert set(merged["pigs"]) == {"pig-a", "pig-b"}
    assert merged["pigs"]["pig-a"]["first_unlocked"] == "2026-07-01"
    assert merged["pigs"]["pig-a"]["last_drawn"] == "2026-08-14"
    assert merged["pigs"]["pig-a"]["count"] == 2


def test_sqlite_collection_merge_preserves_primary_stats_and_unions_pigs(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    current = "v2|aiocqhttp@default|user|10001"
    old = "v2|aiocqhttp|user|10001"
    history = {
        "version": 1,
        "users": {
            current: {
                "total_draws": 2,
                "active_days": 2,
                "duplicate_streak": 0,
                "pigs": {
                    "pig-a": {
                        "first_unlocked": "2026-08-10",
                        "last_drawn": "2026-08-14",
                        "count": 2,
                    }
                },
            },
            old: {
                "total_draws": 50,
                "active_days": 40,
                "duplicate_streak": 6,
                "pigs": {
                    "pig-a": {
                        "first_unlocked": "2026-07-01",
                        "last_drawn": "2026-07-05",
                        "count": 2,
                    },
                    "pig-b": {
                        "first_unlocked": "2026-07-02",
                        "last_drawn": "2026-07-02",
                        "count": 1,
                    },
                },
            },
        },
        "daily": {},
        "pig_snapshots": {},
    }
    storage.save_json_batch({tmp_path / "pig_history.json": history})
    merged = storage.get_user_collection((current, old))
    assert merged is not None
    assert merged["total_draws"] == 2
    assert merged["active_days"] == 2
    assert merged["duplicate_streak"] == 0
    assert set(merged["pigs"]) == {"pig-a", "pig-b"}
    assert merged["pigs"]["pig-a"]["count"] == 2


def test_production_collection_read_path_is_claim_aware():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    assert "claimed_identity_candidates(namespaced, storage_key, claims)" in source
    assert "merge_user_collection_fragments(" in source


def test_daily_report_handler_uses_live_instance_sender_dispatch():
    tree = ast.parse((ROOT / "daily_report_feature.py").read_text(encoding="utf-8"))
    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "pigsty_daily_report":
            target = node
            break
    assert target is not None
    calls = [node for node in ast.walk(target) if isinstance(node, ast.Call)]
    dotted = []
    for call in calls:
        func = call.func
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                dotted.append(f"{func.value.id}.{func.attr}")
            elif isinstance(func.value, ast.Call) and isinstance(func.value.func, ast.Name):
                dotted.append(f"{func.value.func.id}().{func.attr}")
    assert "self._event_sender_id" in dotted
    assert "super()._event_sender_id" not in dotted
    assert "self._remember_daily_report_context" not in dotted
