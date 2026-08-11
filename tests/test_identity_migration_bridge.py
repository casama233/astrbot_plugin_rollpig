import json
from pathlib import Path

from storage import StorageManager


def test_bridge_marker_still_identifies_the_legacy_enhanced_namespace(tmp_path: Path):
    legacy = tmp_path / "astrbot_plugin_rollpig"
    StorageManager(legacy, mode="json")
    marker = legacy / ".rollpig-enhanced-origin.json"
    assert marker.is_file()
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["source_repository"] == "casama233/astrbot_plugin_rollpig"
    assert payload["source_plugin_name"] == "astrbot_plugin_rollpig"
    assert payload["bridge_version"] == "3.1.4"
    assert payload["migration_target"] == "casama233/astrbot_plugin_rollpig_plus"


def test_bridge_marker_is_never_written_to_plus_namespace(tmp_path: Path):
    future = tmp_path / "astrbot_plugin_rollpig_plus"
    StorageManager(future, mode="json")
    assert not (future / ".rollpig-enhanced-origin.json").exists()
