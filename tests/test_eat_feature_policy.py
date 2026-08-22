import ast
import datetime
import random
from pathlib import Path

from eat_feature import EatFeatureMixin
from services import EatService


ROOT = Path(__file__).resolve().parents[1]
FEATURE_SOURCE = (ROOT / "eat_feature.py").read_text(encoding="utf-8")
MAIN_SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


class FakeRng:
    def __init__(self, *, outcome="escape", target="user-b"):
        self.outcome = outcome
        self.target = target
        self.choice_calls = []
        self.choices_calls = []

    def choice(self, population):
        self.choice_calls.append(tuple(population))
        return self.target

    def choices(self, population, *, weights, k):
        self.choices_calls.append((tuple(population), tuple(weights), k))
        return [self.outcome]


def _feature_method(name: str):
    tree = ast.parse(FEATURE_SOURCE)
    feature = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "EatFeatureMixin"
    )
    return next(
        node
        for node in feature.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def test_default_eat_rng_is_process_global_seed_isolated():
    assert isinstance(EatService()._rng, random.SystemRandom)


def test_default_eat_weights_preserve_15_percent_success_and_add_escape():
    assert EatService.outcome_weights(15, 20) == (15, 20, 65)


def test_cooked_bonus_steals_probability_from_backlash():
    assert EatService.outcome_weights(
        15, 20, success_bonus_percent=10
    ) == (25, 20, 55)


def test_extreme_admin_tuning_remains_bounded():
    assert EatService.outcome_weights(
        80, 80, success_bonus_percent=40
    ) == (90, 10, 0)


def test_injected_rng_drives_target_and_outcome_from_one_private_source():
    rng = FakeRng(outcome="backlash", target="user-b")
    service = EatService(rng=rng)

    assert service.choose_group_eat_target(["user-a", "user-b"]) == "user-b"
    assert (
        service.choose_eat_outcome(success_percent=15, escape_percent=20)
        == "backlash"
    )
    assert rng.choice_calls == [("user-a", "user-b")]
    assert rng.choices_calls == [
        (("success", "escape", "backlash"), (15, 20, 65), 1)
    ]


def test_empty_random_eat_target_pool_is_rejected():
    try:
        EatService().choose_group_eat_target([])
    except ValueError as exc:
        assert "must not be empty" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("empty target pool must fail")


def test_eat_feature_never_uses_process_global_random_module():
    assert "import random" not in FEATURE_SOURCE
    assert "random.choice" not in FEATURE_SOURCE
    assert "random.randrange" not in FEATURE_SOURCE
    assert "self.eat_service.choose_group_eat_target" in FEATURE_SOURCE
    assert "self.eat_service.choose_eat_outcome" in FEATURE_SOURCE


def test_direct_eat_claims_appetite_before_rolling_outcome():
    method = ast.get_source_segment(
        FEATURE_SOURCE, _feature_method("_eat_group_target")
    ) or ""
    assert method.index("self._claim_eat_attempt") < method.index(
        "self.eat_service.choose_eat_outcome"
    )
    assert "async with self._eat_action_lock" in method
    assert "self._eat_limit_reason" in method
    assert "self._eat_protection_status" in method
    assert '"eat_success"' in method
    assert '"eat_failure"' in method


def test_random_eat_filters_both_protection_layers_before_private_selection():
    method = ast.get_source_segment(
        FEATURE_SOURCE, _feature_method("eat_random_group_member")
    ) or ""
    assert "self._roast_protection_status" in method
    assert "self._eat_protection_status" in method
    assert "self.eat_service.choose_group_eat_target" in method
    assert "random.choice" not in method


def test_success_limit_blocks_lucky_serial_eater():
    feature = object.__new__(EatFeatureMixin)
    feature.eat_daily_attempt_limit = 2
    feature.eat_daily_success_limit = 1
    feature._eat_actor_stats = lambda group_id, actor_id: (1, 1)

    reason = feature._eat_limit_reason("group-a", "user-a")
    assert reason is not None
    assert "已经吃饱" in reason


def test_yesterday_success_grants_digestive_protection():
    feature = object.__new__(EatFeatureMixin)
    feature.enable_eat_protection = True
    feature.eat_protection_threshold = 1
    today = datetime.date(2026, 8, 23)
    feature._today = lambda: today
    feature._eat_day_events = lambda group_id, day: [
        {
            "kind": feature.EVENT_EAT_SUCCESS,
            "victim_id": "target-a",
            "actor_id": "hunter-a",
        }
    ] if day == today - datetime.timedelta(days=1) else []

    assert feature._eat_protection_status("group-a", "target-a") == (True, 1)
    assert feature._eat_protection_status("group-a", "target-b") == (False, 0)


def test_main_entrypoint_wires_eat_mixin_and_appetite_command():
    assert "from .eat_feature import EatFeatureMixin" in MAIN_SOURCE
    assert "EatFeatureMixin," in MAIN_SOURCE
    assert "@filter.command('胃口'" in MAIN_SOURCE
    assert "return await super().eat_appetite_status(event)" in MAIN_SOURCE
