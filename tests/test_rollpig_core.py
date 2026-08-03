from rollpig_core import (
    identity_candidates,
    is_public_ip,
    legacy_identity,
    namespace_identity,
    pre_instance_identity,
    special_pig_state,
)


def test_namespace_round_trip():
    key = namespace_identity("Discord", "user", "123")
    assert key == "v2|discord|user|123"
    assert legacy_identity(key) == "123"

def test_namespace_is_idempotent():
    key = "v2|qq|group|456"
    assert namespace_identity("qq", "group", key) == key


def test_instance_namespace_reads_pre_instance_and_raw_keys():
    key = namespace_identity("aiocqhttp@default", "user", "123")
    assert key == "v2|aiocqhttp@default|user|123"
    assert pre_instance_identity(key) == "v2|aiocqhttp|user|123"
    assert identity_candidates(key) == (
        "v2|aiocqhttp@default|user|123",
        "v2|aiocqhttp|user|123",
        "123",
    )


def test_public_ip_filter():
    assert is_public_ip("8.8.8.8")
    assert not is_public_ip("127.0.0.1")
    assert not is_public_ip("10.0.0.1")
    assert not is_public_ip("169.254.169.254")



def test_special_pig_state_keeps_cooking_roles_distinct():
    assert special_pig_state(None) == "missing"
    assert special_pig_state({"id": "human", "name": "人类"}) == "human"
    assert special_pig_state({"id": "eaten", "name": "吃掉了"}) == "eaten"
    assert special_pig_state({"id": "mc_porkchop", "name": "猪排"}) == "cooked"
    assert special_pig_state({"id": "lard-pig", "name": "猪油"}) == "cooked"
    assert special_pig_state({"id": "mechanical-pig", "name": "机械猪"}) == "normal"
