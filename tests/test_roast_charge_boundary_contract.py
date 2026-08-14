from pathlib import Path


def test_group_roast_and_reservation_use_charge_api():
    legacy = Path("legacy_main.py").read_text(encoding="utf-8")
    reservation = Path("roast_reservation_feature.py").read_text(encoding="utf-8")

    assert "async def _consume_group_roast_charge(" in legacy
    assert legacy.count("await self._consume_group_roast_charge(") >= 1
    assert "await self._consume_group_roast_charge(group_id, actor_id)" in reservation
    assert "creator pays one charge" in reservation


def test_legacy_cooldown_api_is_only_a_compatibility_facade():
    legacy = Path("legacy_main.py").read_text(encoding="utf-8")
    reservation = Path("roast_reservation_feature.py").read_text(encoding="utf-8")

    assert legacy.count("async def _consume_group_roast_cooldown(") == 1
    assert "Deprecated compatibility facade over the charge system" in legacy
    assert "_consume_group_roast_cooldown(" not in reservation


def test_charge_state_roundtrips_through_roast_projection():
    sqlite = Path("storage/sqlite_storage.py").read_text(encoding="utf-8")

    assert '"roast_charges": {}' in sqlite
    assert 'state.get("roast_charges")' in sqlite
    assert 'roast["roast_charges"] = {' in sqlite
    assert "charges INTEGER NOT NULL DEFAULT -1" in sqlite
    assert "refill_anchor REAL NOT NULL DEFAULT 0" in sqlite


def test_existing_cooldown_config_is_reused_as_recovery_interval():
    schema = Path("_conf_schema.json").read_text(encoding="utf-8")
    legacy = Path("legacy_main.py").read_text(encoding="utf-8")

    assert '"group_roast_max_charges"' in schema
    assert "烤箱每格能量恢复时间" in schema
    assert 'self.config.get("group_roast_max_charges", 2)' in legacy
    assert "self.group_roast_cooldown_seconds" in legacy
