from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "rollpig_release_metadata",
    ROOT / "scripts/release_metadata.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_stable_metadata_outputs_are_deterministic():
    fields = MODULE.parse_metadata(
        """name: astrbot_plugin_rollpig
display_name: 豬豬源
version: "3.12.0"
"""
    )
    assert MODULE.build_outputs(fields) == {
        "version": "3.12.0",
        "tag": "v3.12.0",
        "plugin_name": "astrbot_plugin_rollpig",
        "display_name": "豬豬源",
        "archive": "astrbot_plugin_rollpig-v3.12.0.zip",
    }


@pytest.mark.parametrize("version", ["3.12", "v3.12.0", "3.12.0-rc1"])
def test_non_stable_versions_are_rejected(version):
    with pytest.raises(ValueError, match="stable x.y.z"):
        MODULE.parse_metadata(
            f"""name: astrbot_plugin_rollpig
display_name: 豬豬源
version: "{version}"
"""
        )


def test_empty_version_is_rejected_as_missing():
    with pytest.raises(ValueError, match="missing required fields: version"):
        MODULE.parse_metadata(
            """name: astrbot_plugin_rollpig
display_name: 豬豬源
version: ""
"""
        )


def test_unsafe_plugin_name_is_rejected():
    with pytest.raises(ValueError, match="unsafe plugin name"):
        MODULE.parse_metadata(
            """name: ../rollpig
display_name: 豬豬源
version: 3.12.0
"""
        )
