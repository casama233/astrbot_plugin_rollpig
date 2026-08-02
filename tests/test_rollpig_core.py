from rollpig_core import is_public_ip, legacy_identity, namespace_identity


def test_namespace_round_trip():
    key = namespace_identity("Discord", "user", "123")
    assert key == "v2|discord|user|123"
    assert legacy_identity(key) == "123"

def test_namespace_is_idempotent():
    key = "v2|qq|group|456"
    assert namespace_identity("qq", "group", key) == key

def test_public_ip_filter():
    assert is_public_ip("8.8.8.8")
    assert not is_public_ip("127.0.0.1")
    assert not is_public_ip("10.0.0.1")
    assert not is_public_ip("169.254.169.254")
