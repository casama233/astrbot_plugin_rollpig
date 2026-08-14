from pathlib import Path


def test_oven_feature_owns_no_astrbot_command_decorators():
    source = Path("oven_charge_feature.py").read_text(encoding="utf-8")
    assert "@filter.command" not in source
    assert "async def _consume_group_roast_cooldown" in source
    assert "async def oven_refill(" in source
    assert "async def oven_refill_support(" in source


def test_main_registers_oven_commands_and_mixin_at_real_star_entry():
    source = Path("main.py").read_text(encoding="utf-8")
    assert "from .oven_charge_feature import OvenChargeMixin" in source
    assert "    OvenChargeMixin," in source
    assert "@filter.command('烤箱补货'" in source
    assert "@filter.command('添煤'" in source
    assert "return await super().oven_refill(event)" in source
    assert "return await super().oven_refill_support(event)" in source


def test_charge_feature_reuses_existing_roast_hook_for_normal_and_reservation_flows():
    legacy = Path("legacy_main.py").read_text(encoding="utf-8")
    reservation = Path("roast_reservation_feature.py").read_text(encoding="utf-8")
    feature = Path("oven_charge_feature.py").read_text(encoding="utf-8")

    assert "_consume_group_roast_cooldown(" in legacy
    assert "_consume_group_roast_cooldown(group_id, actor_id)" in reservation
    assert "async def _consume_group_roast_cooldown(" in feature
    assert "choose_group_roast_outcome" not in feature


def test_refill_records_reserved_gameplay_events_without_owning_report_state():
    source = Path("oven_charge_feature.py").read_text(encoding="utf-8")
    assert "EVENT_OVEN_REFILL_STARTED" in source
    assert "EVENT_OVEN_REFILL_SUPPORTED" in source
    assert "EVENT_OVEN_REFILL_SUCCEEDED" in source
    assert "_record_gameplay_event" in source
    assert "daily_report_state" not in source


def test_oven_service_is_pure_and_storage_independent():
    source = Path("services/oven_charge_service.py").read_text(encoding="utf-8")
    for token in ("astrbot", "sqlite3", "event.send", "save_json", "load_json"):
        assert token not in source
