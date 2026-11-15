import pytest

from rollpig_core import parse_config_bool


@pytest.mark.parametrize("default", [True, False])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        (" YES ", True),
        ("ON", True),
        ("false", False),
        (" NO ", False),
        ("OFF", False),
        (None, None),
        ("unknown", None),
        ("", None),
    ],
)
def test_parse_config_bool_preserves_supported_values_and_fallback(value, expected, default):
    assert parse_config_bool(value, default) is (default if expected is None else expected)
