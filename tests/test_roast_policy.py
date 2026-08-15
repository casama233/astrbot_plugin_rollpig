from services import RoastService


class FakeChoices:
    def __init__(self, result: str):
        self.result = result
        self.calls = []

    def choices(self, population, *, weights, k):
        self.calls.append((tuple(population), tuple(weights), k))
        return [self.result]


def test_group_roast_outcome_keeps_single_60_30_10_policy():
    service = RoastService()
    rng = FakeChoices("backlash")
    assert service.choose_group_roast_outcome(rng=rng) == "backlash"
    assert rng.calls == [
        (
            ("success", "escape", "backlash"),
            (60, 30, 10),
            1,
        )
    ]


def test_bypass_forces_success_without_touching_rng():
    service = RoastService()
    rng = FakeChoices("escape")
    assert service.choose_group_roast_outcome(bypass=True, rng=rng) == "success"
    assert rng.calls == []


def test_roast_copy_helpers_preserve_policy_and_piggy_protection_copy():
    service = RoastService()
    assert service.format_cooldown(1) == "1 分钟"
    assert service.format_cooldown(3600) == "1 小时 0 分"
    assert service.format_cooldown(3661) == "1 小时 2 分"
    assert service.roast_protection_message(3) == (
        "🛡️ 对方昨天被成功烤了 3 次，今天领到『猪身安全险』。"
        "普通烤／吃会被猪圈保安拦下；后门强制模式仍然不讲武德。"
    )
