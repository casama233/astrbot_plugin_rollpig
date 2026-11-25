import json
from pathlib import Path


def test_group_roast_and_reservation_use_charge_api():
    legacy = Path("legacy_main.py").read_text(encoding="utf-8")
    reservation = Path("roast_reservation_feature.py").read_text(encoding="utf-8")

    assert "async def _consume_group_roast_charge(" in legacy
    assert legacy.count("await self._consume_group_roast_charge(") >= 1
    assert "await self._consume_group_roast_charge(group_id, actor_id)" in reservation
    assert "creator pays one charge" in reservation


def test_charge_state_roundtrips_through_roast_projection():
    sqlite = Path("storage/sqlite_storage.py").read_text(encoding="utf-8")

    assert '"roast_charges": {}' in sqlite
    assert 'state.get("roast_charges")' in sqlite
    assert 'roast["roast_charges"] = {' in sqlite
    assert "charges INTEGER NOT NULL DEFAULT -1" in sqlite
    assert "refill_anchor REAL NOT NULL DEFAULT 0" in sqlite


def test_existing_cooldown_config_is_reused_as_recovery_interval():
    schema = json.loads(Path("_conf_schema.json").read_text(encoding="utf-8"))
    legacy = Path("legacy_main.py").read_text(encoding="utf-8")

    assert "group_roast_max_charges" in schema
    cooldown = schema["group_roast_cooldown_hours"]
    assert cooldown["type"] == "float"
    assert "每格能量" in cooldown["hint"] and "逐格" in cooldown["hint"]
    assert '"group_roast_cooldown_hours"' in legacy
    assert 'self.config.get("group_roast_max_charges", 2)' in legacy
    assert "self.group_roast_cooldown_seconds" in legacy
