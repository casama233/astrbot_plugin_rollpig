import datetime
from collections import Counter
from zoneinfo import ZoneInfo

from daily_report_core import (
    aggregate_daily_report,
    due_datetime,
    parse_report_time,
    prune_state,
    top_tied,
)


def test_parse_report_time_and_fallback():
    assert parse_report_time("23:45") == (23, 45)
    assert parse_report_time("00:03") == (0, 3)
    assert parse_report_time("25:99") == (23, 50)
    assert parse_report_time("not-a-time") == (23, 50)


def test_due_datetime_keeps_locked_report_date_across_midnight():
    timezone = ZoneInfo("Asia/Shanghai")
    report_date = datetime.date(2026, 8, 14)
    due = due_datetime(report_date, 23, 58, timezone, 6 * 60)
    assert due.isoformat() == "2026-08-15T00:04:00+08:00"
    assert report_date.isoformat() == "2026-08-14"


def test_top_tied_preserves_real_ties_deterministically():
    result = top_tied(Counter({"u2": 3, "u1": 3, "u3": 1}))
    assert result == {"value": 3, "winners": ["u1", "u2"]}


def test_daily_report_aggregates_all_awards_and_popular_pig():
    members = [
        {"user_id": "a", "pig_id": "pink", "pig_name": "粉猪"},
        {"user_id": "b", "pig_id": "pink", "pig_name": "粉猪"},
        {"user_id": "c", "pig_id": "blue", "pig_name": "蓝猪"},
        {"user_id": "d", "pig_id": "blue", "pig_name": "蓝猪", "was_eaten": True},
    ]
    events = [
        {"kind": "roast_success", "actor_id": "a", "target_id": "b", "victim_id": "b"},
        {"kind": "roast_success", "actor_id": "a", "target_id": "d", "victim_id": "d"},
        {"kind": "roast_escape", "actor_id": "b", "target_id": "c"},
        {"kind": "roast_backlash", "actor_id": "b", "target_id": "c", "victim_id": "b"},
        {"kind": "roast_backlash", "actor_id": "d", "target_id": "c", "victim_id": ""},
    ]
    report = aggregate_daily_report(members, events, ["d"], roast_total=3)
    assert report["active_users"] == 4
    assert report["draws"] == 4
    assert report["roasts"] == 3
    assert report["eats"] == 1
    assert report["escapes"] == 1
    assert report["backlashes"] == 2
    assert {item["id"] for item in report["popular_pigs"]} == {"pink", "blue"}
    assert report["awards"]["roast_maniac"] == {"value": 2, "winners": ["a"]}
    assert report["awards"]["miserable_ingredient"] == {"value": 2, "winners": ["b"]}
    assert report["awards"]["escape_master"] == {"value": 1, "winners": ["c"]}
    assert report["awards"]["backlash_king"] == {"value": 2, "winners": ["c"]}


def test_prune_state_keeps_group_routing_but_drops_old_daily_data():
    state = {
        "groups": {"g": {"umo": "platform:GroupMessage:g"}},
        "events": {
            "2026-07-01": {"g": [{"kind": "roast_success"}]},
            "2026-08-14": {"g": []},
        },
        "jobs": {
            "2026-07-01": {"g": {"status": "sent"}},
            "2026-08-14": {"g": {"status": "pending"}},
        },
    }
    changed = prune_state(state, datetime.date(2026, 8, 14), keep_days=14)
    assert changed
    assert state["groups"]["g"]["umo"] == "platform:GroupMessage:g"
    assert "2026-07-01" not in state["events"]
    assert "2026-07-01" not in state["jobs"]
    assert "2026-08-14" in state["events"]


def test_entrypoint_layers_focused_features_over_existing_plugin():
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    entry = (root / "main.py").read_text(encoding="utf-8")
    assert (
        "class RollPigPlugin(DailyReportMixin, ExVariantMixin, _BaseRollPigPlugin)"
        in entry
    )
    assert "from .daily_report_feature import DailyReportMixin" in entry
    assert "from .ex_variant_feature import ExVariantMixin" in entry
    assert "legacy_main" in entry


def test_daily_report_contract_keeps_sacrifice_opt_in():
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    import json

    config = json.loads((root / "_conf_schema.json").read_text(encoding="utf-8"))
    assert config["daily_report_random_eat_enabled"]["default"] is False
    feature = (root / "daily_report_feature.py").read_text(encoding="utf-8")
    assert 'config.get("daily_report_random_eat_enabled", False)' in feature
    assert "manual views never sacrifice" in feature
    assert "unified_msg_origin" in feature
    assert "self.context.send_message(umo, chain)" in feature
    assert "daily_report_sacrifice" in feature
