from __future__ import annotations

import datetime
import importlib.util
import sys
import threading
import types
from pathlib import Path

from roast_reservations import create_or_join_reservation, resolve_reservation
from services.oven_refill_service import OvenRefillService


ROOT = Path(__file__).resolve().parents[1]


class _TestLogger:
    @staticmethod
    def warning(*_args, **_kwargs):
        return None

    @staticmethod
    def info(*_args, **_kwargs):
        return None


def _load_oven_refill_mixin():
    """Load the mixin without requiring AstrBot in the unit-test environment."""

    module_name = "_oven_refill_feature_regression"
    sys.modules.pop(module_name, None)
    astrbot_module = types.ModuleType("astrbot")
    api_module = types.ModuleType("astrbot.api")
    api_module.logger = _TestLogger()
    astrbot_module.api = api_module

    previous_astrbot = sys.modules.get("astrbot")
    previous_api = sys.modules.get("astrbot.api")
    sys.modules["astrbot"] = astrbot_module
    sys.modules["astrbot.api"] = api_module
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, ROOT / "oven_refill_feature.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module.OvenRefillMixin
    finally:
        sys.modules.pop(module_name, None)
        if previous_astrbot is None:
            sys.modules.pop("astrbot", None)
        else:
            sys.modules["astrbot"] = previous_astrbot
        if previous_api is None:
            sys.modules.pop("astrbot.api", None)
        else:
            sys.modules["astrbot.api"] = previous_api


def _oven_harness():
    mixin = _load_oven_refill_mixin()
    target = object.__new__(mixin)
    target._data_lock = threading.RLock()
    target.oven_refill_state = {"version": 1, "dates": {}}
    target.oven_refill_daily_limit = 2
    target.oven_refill_round_timeout_seconds = 60
    target.oven_refill_service = OvenRefillService()
    target.oven_refill_support_ratio_percent = 30
    target.oven_refill_min_supporters = 3
    target.oven_refill_max_base_supporters = 8
    target.oven_refill_extra_supporters_per_success = 2
    target._today = lambda: datetime.date(2026, 8, 15)
    target._save_oven_refill_state_locked = lambda: None
    return target


def test_refill_round_timeout_closes_zombie_campaign():
    target = _oven_harness()
    started = target._start_refill_round(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="a",
        active_count=3,
        now=100,
    )
    assert started["state"] == "started"
    assert started["required"] == 3

    expired = target._add_refill_support(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="b",
        now=161,
    )
    assert expired == {"state": "expired"}
    row = target._refill_bucket_locked("2026-08-15", "g1")
    assert row["active"] is False
    assert row["completing"] is False
    assert row["failed_reason"] == "expired"


def test_refill_threshold_is_intentionally_frozen_at_round_start():
    target = _oven_harness()
    started = target._start_refill_round(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="a",
        active_count=2,
        now=100,
    )
    assert started["required"] == 2

    # Later population growth is deliberately a gameplay mechanic: this round
    # keeps the requirement announced when it started.
    row = target._refill_bucket_locked("2026-08-15", "g1")
    assert row["active_count"] == 2
    assert row["required"] == 2
    complete = target._add_refill_support(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="b",
        now=101,
    )
    assert complete["state"] == "complete"
    assert complete["required"] == 2


def test_interrupted_settlement_is_closed_and_counted_once():
    target = _oven_harness()
    target._start_refill_round(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="a",
        active_count=2,
        now=100,
    )
    target._add_refill_support(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="b",
        now=101,
    )
    row = target._refill_bucket_locked("2026-08-15", "g1")
    assert row["completing"] is True
    assert row["successes"] == 0

    assert target._recover_interrupted_refills_locked() is True
    assert row["completing"] is False
    assert row["active"] is False
    assert row["successes"] == 1
    assert row["settlement_state"] == "interrupted"
    assert row["failed_reason"] == "interrupted_counted"

    assert target._recover_interrupted_refills_locked() is False
    assert row["successes"] == 1


def test_storage_error_degrades_and_consumes_round_instead_of_replaying():
    target = _oven_harness()
    target._start_refill_round(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="a",
        active_count=2,
        now=100,
    )
    completed = target._add_refill_support(
        draw_date="2026-08-15",
        group_id="g1",
        actor_id="b",
        now=101,
    )
    assert completed["state"] == "complete"

    finish = target._finish_refill_round(
        draw_date="2026-08-15",
        group_id="g1",
        round_no=completed["round"],
        restored_users=1,
        active_users=4,
        now=102,
        settlement_error="sqlite busy",
    )
    assert finish == {"state": "degraded", "successes": 1}
    row = target._refill_bucket_locked("2026-08-15", "g1")
    assert row["completing"] is False
    assert row["failed_reason"] == "grant_error"
    assert row["restored_users"] == 1


def test_refill_requires_parent_group_roast_feature():
    target = _oven_harness()
    target.enable_oven_refill = True
    target.enable_roast = True
    target.enable_group_roast = True
    assert target._oven_refill_available() is True

    target.enable_group_roast = False
    assert target._oven_refill_available() is False
    target.enable_group_roast = True
    target.enable_roast = False
    assert target._oven_refill_available() is False


def test_resolved_reservation_cannot_be_reopened():
    state: dict = {}
    created = create_or_join_reservation(
        state,
        draw_date="2026-08-15",
        group_id="g1",
        target_id="target",
        actor_id="chef",
        now=1,
    )
    resolved = resolve_reservation(
        state,
        draw_date="2026-08-15",
        group_id="g1",
        target_id="target",
        outcome="success",
        now=2,
    )
    assert resolved is not None

    reopened = create_or_join_reservation(
        state,
        draw_date="2026-08-15",
        group_id="g1",
        target_id="target",
        actor_id="friend",
        now=3,
    )
    assert reopened["status"] == "resolved"
    assert reopened["reservation"]["id"] == created["reservation"]["id"]
    assert reopened["reservation"]["participants"] == ["chef"]


def test_reservation_draw_check_and_trigger_share_lock_order():
    source = (ROOT / "roast_reservation_feature.py").read_text(encoding="utf-8")
    create = source[
        source.index("async def _create_or_join_roast_reservation") : source.index(
            "async def _roast_group_target"
        )
    ]
    create_lock = create.index("async with self._roast_reservation_lock")
    assert create.index("self._get_daily_pig(target_id", create_lock) > create_lock
    assert 'existing_status == "resolved"' in create

    trigger = source[
        source.index("async def _trigger_roast_reservation_after_draw") : source.index(
            "async def send_rendered_pig"
        )
    ]
    trigger_lock = trigger.index("async with self._roast_reservation_lock")
    pending_check = trigger.index("pending = self._pending_roast_reservation")
    assert trigger_lock < pending_check


def test_wood_is_the_only_player_facing_refill_term():
    # Old spellings are permitted only as hidden compatibility aliases in main.py.
    for relative in (
        "player_copy.py",
        "oven_refill_feature.py",
        "roast_reservation_feature.py",
        "help_system.py",
        "_conf_schema.json",
        "docs/ROAST-RESERVATIONS.md",
        "docs/CONFIGURATION.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "添煤" not in text, relative
        assert "添柴" in text, relative

    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "@filter.command('添柴'" in main
    assert "'添煤'" in main  # compatibility only
    assert "'烤箱添煤'" in main  # compatibility only

    help_source = (ROOT / "help_system.py").read_text(encoding="utf-8")
    assert 'HelpEntry("/添柴"' in help_source
    assert 'HelpEntry("/添煤"' not in help_source


def test_reservation_copy_explains_how_its_wood_action_is_performed():
    for relative in (
        "player_copy.py",
        "roast_reservation_feature.py",
        "docs/ROAST-RESERVATIONS.md",
        "docs/CONFIGURATION.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "添柴" in text, relative
        assert "/烤群友" in text, relative
