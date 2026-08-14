from pathlib import Path


def test_refill_feature_has_no_astrbot_decorators_and_claims_events():
    source = Path("oven_refill_feature.py").read_text(encoding="utf-8")
    assert "@filter.command" not in source
    assert "async def oven_refill(" in source
    assert "async def oven_refill_support(" in source
    assert source.count("self._claim_command_event(event)") >= 2


def test_refill_campaign_is_auxiliary_and_charge_state_stays_in_authority():
    source = Path("oven_refill_feature.py").read_text(encoding="utf-8")
    assert 'self.plugin_data_dir / "oven_refill_state.json"' in source
    assert "self.storage.grant_roast_charge" in source
    assert "add_roast_charge_state" in source
    assert "start_oven_refill" not in source
    assert "support_oven_refill" not in source


def test_main_registers_refill_commands_on_real_star_entry():
    source = Path("main.py").read_text(encoding="utf-8")
    assert "OvenRefillMixin" in source
    assert "@filter.command('烤箱补货'" in source
    assert "@filter.command('添煤'" in source
    assert "return await super().oven_refill(event)" in source
    assert "return await super().oven_refill_support(event)" in source


def test_refill_events_use_shared_gameplay_event_namespace():
    source = Path("oven_refill_feature.py").read_text(encoding="utf-8")
    for name in (
        "EVENT_OVEN_REFILL_STARTED",
        "EVENT_OVEN_REFILL_SUPPORTED",
        "EVENT_OVEN_REFILL_SUCCEEDED",
        "EVENT_OVEN_REFILL_FAILED",
    ):
        assert name in source
    assert "_record_gameplay_event" in source
    assert "daily_report_state" not in source
