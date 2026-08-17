import ast
import random
from pathlib import Path

from services import RoastService


ROOT = Path(__file__).resolve().parents[1]
MAIN_SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")
SERVICE_SOURCE = (ROOT / "services" / "roast_service.py").read_text(encoding="utf-8")


class FakeChoices:
    def __init__(self, result: str):
        self.result = result
        self.calls = []

    def choices(self, population, *, weights, k):
        self.calls.append((tuple(population), tuple(weights), k))
        return [self.result]


class FakeRoastRng(FakeChoices):
    def __init__(self, result: str, target: str):
        super().__init__(result)
        self.target = target
        self.choice_calls = []

    def choice(self, population):
        self.choice_calls.append(tuple(population))
        return self.target


def _main_method(name: str):
    tree = ast.parse(MAIN_SOURCE)
    plugin = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )
    return next(
        node
        for node in plugin.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


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


def test_default_roast_rng_is_process_global_seed_isolated():
    service = RoastService()
    assert isinstance(service._rng, random.SystemRandom)


def test_injected_roast_rng_drives_target_and_outcome_from_one_private_source():
    rng = FakeRoastRng("escape", "user-b")
    service = RoastService(rng=rng)

    assert service.choose_group_roast_target(["user-a", "user-b"]) == "user-b"
    assert service.choose_group_roast_outcome() == "escape"
    assert rng.choice_calls == [("user-a", "user-b")]
    assert rng.calls == [
        (
            ("success", "escape", "backlash"),
            (60, 30, 10),
            1,
        )
    ]


def test_empty_random_roast_target_pool_is_rejected():
    service = RoastService(rng=FakeRoastRng("success", "unused"))
    try:
        service.choose_group_roast_target([])
    except ValueError as exc:
        assert "must not be empty" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("empty target pool must fail")


def test_random_roast_filters_protection_before_target_selection():
    method = ast.get_source_segment(
        MAIN_SOURCE, _main_method("roast_random_group_member")
    ) or ""
    assert "self._roast_protection_status" in method
    assert "if not protected" in method
    assert "self.roast_service.choose_group_roast_target" in method
    assert "random.choice" not in method


def test_random_roast_spends_charge_before_mentioning_target():
    method = ast.get_source_segment(
        MAIN_SOURCE, _main_method("roast_random_group_member")
    ) or ""
    assert method.index("self._consume_group_roast_charge") < method.index(
        "self._send_with_mention"
    )
    assert "if not charge_status.get(\"consumed\")" in method


def test_random_roast_keeps_shared_outcome_and_event_pipeline():
    method = ast.get_source_segment(
        MAIN_SOURCE, _main_method("roast_random_group_member")
    ) or ""
    assert "self.roast_service.choose_group_roast_outcome" in method
    assert '"roast_escape"' in method
    assert '"roast_backlash"' in method
    assert '"roast_success"' in method
    assert "self._record_group_roast" in method


def test_roast_service_source_never_falls_back_to_process_global_rng():
    assert "random.SystemRandom()" in SERVICE_SOURCE
    assert "chooser = rng or self._rng" in SERVICE_SOURCE
    assert "chooser = rng or random" not in SERVICE_SOURCE


def test_roast_copy_helpers_preserve_policy_and_piggy_protection_copy():
    service = RoastService()
    assert service.format_cooldown(1) == "1 分钟"
    assert service.format_cooldown(3600) == "1 小时 0 分"
    assert service.format_cooldown(3661) == "1 小时 2 分"
    assert service.roast_protection_message(3) == (
        "🛡️ 对方昨天被成功烤了 3 次，今天领到『猪身安全险』。"
        "普通烤／吃会被猪圈保安拦下；后门强制模式仍然不讲武德。"
    )
