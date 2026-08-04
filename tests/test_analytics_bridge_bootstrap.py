from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pages" / "pig-manager" / "ui-analytics.js"
HARNESS = ROOT / "tests" / "analytics_bridge_harness.cjs"


def test_bridge_ready_flag_is_set_only_inside_initialize():
    source = SCRIPT.read_text(encoding="utf-8")
    initialize = source.index("const initialize = bridge =>")
    ready_assignment = source.index("window[READY_KEY] = true")
    bridge_lookup = source.index("const bridge = window.AstrBotPluginPage")
    assert initialize < ready_assignment < bridge_lookup
    assert "window[STATE_KEY]?.starting" in source
    assert "MAX_WAIT_MS = 8000" in source
    assert "window.setTimeout(waitForBridge, POLL_MS)" in source
    assert "analyticsBridgeRetry" in source


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_bridge_bootstrap_delay_duplicate_and_timeout():
    result = subprocess.run(
        ["node", str(HARNESS)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
