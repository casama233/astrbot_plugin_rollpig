import json
from pathlib import Path

from storage import StorageManager


def test_bridge_marker_identifies_enhanced_legacy_namespace(tmp_path: Path):
    legacy = tmp_path / "astrbot_plugin_rollpig"
    StorageManager(legacy, mode="json")
    marker = legacy / ".rollpig-enhanced-origin.json"
    assert marker.is_file()
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["source_repository"] == "casama233/astrbot_plugin_rollpig"
    assert payload["source_plugin_name"] == "astrbot_plugin_rollpig"
    assert payload["bridge_version"] == "3.1.4"
    assert payload["migration_target"] == "casama233/astrbot_plugin_rollpig_plus"


def test_bridge_marker_is_not_written_to_future_namespace(tmp_path: Path):
    future = tmp_path / "astrbot_plugin_rollpig_plus"
    StorageManager(future, mode="json")
    assert not (future / ".rollpig-enhanced-origin.json").exists()


def test_bridge_release_keeps_legacy_identity():
    metadata = Path("metadata.yaml").read_text(encoding="utf-8")
    assert 'name: "astrbot_plugin_rollpig"' in metadata
    assert 'author: "MegSopern, casama233"' in metadata
    assert 'version: "3.1.4"' in metadata
    updater = Path("updater.py").read_text(encoding="utf-8")
    assert "self._version_tuple(latest) >= (3, 2, 0)" in updater
    assert "禁止直接覆盖安装 3.2.0+" in updater
