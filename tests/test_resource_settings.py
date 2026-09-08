from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.resource_settings import ResourceSyncSettings


def test_defaults_match_documented_schema_without_mutating_config():
    schema = json.loads((Path(__file__).resolve().parents[1] / "_conf_schema.json").read_text())
    keys = (
        "resource_sync_interval_hours", "resource_sync_timeout",
        "resource_use_system_proxy", "resource_max_file_size_mb",
    )
    config = {key: schema[key]["default"] for key in keys}
    original = config.copy()
    expected = ResourceSyncSettings(6, 30, False, 10 * 1024 * 1024)
    assert ResourceSyncSettings.from_config({}) == expected
    assert ResourceSyncSettings.from_config(config) == expected
    assert config == original


@pytest.mark.parametrize("invalid", [None, "invalid", [], {}])
def test_malformed_numbers_keep_established_defaults(invalid):
    config = dict.fromkeys(
        ("resource_sync_interval_hours", "resource_sync_timeout", "resource_max_file_size_mb"),
        invalid,
    )
    assert ResourceSyncSettings.from_config(config) == ResourceSyncSettings(
        6, 30, False, 10 * 1024 * 1024
    )


@pytest.mark.parametrize("value, interval, timeout, size", [
    (-999, 1, 2, 1),
    (999, 168, 120, 50),
    ("2.5", 2.5, 2.5, 10),  # Size has always required an integer.
    (2.5, 2.5, 2.5, 2),
])
def test_numeric_limits_and_fractional_timeouts_are_preserved(value, interval, timeout, size):
    settings = ResourceSyncSettings.from_config({
        "resource_sync_interval_hours": value,
        "resource_sync_timeout": value,
        "resource_max_file_size_mb": value,
    })
    assert (settings.interval_hours, settings.timeout, settings.max_file_size) == (
        interval, timeout, size * 1024 * 1024
    )


@pytest.mark.parametrize("value, expected", [
    (True, True), (False, False), ("1", True), (" TRUE ", True),
    ("yes", True), ("on", True), ("false", False), ("off", False),
    ("0", False), (None, False), ("unexpected", False),
])
def test_system_proxy_compatibility_values(value, expected):
    assert ResourceSyncSettings.from_config({
        "resource_use_system_proxy": value,
    }).use_system_proxy is expected
