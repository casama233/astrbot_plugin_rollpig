from services import DrawService, RoastService


class FakeRng:
    def __init__(self, choices, roll):
        self.choices = list(choices)
        self.roll = roll

    def choice(self, values):
        wanted = self.choices.pop(0)
        return next(value for value in values if value["id"] == wanted)

    def random(self):
        return self.roll


def test_draw_service_applies_duplicate_pity_without_storage_dependency():
    pigs = [{"id": "seen"}, {"id": "new"}]
    service = DrawService(enable_new_pig_pity=True, pity_step_percent=20)
    chosen = service.choose(
        pigs,
        {"duplicate_streak": 4, "pigs": {"seen": {}}},
        rng=FakeRng(["seen", "new"], 0.1),
    )
    assert chosen["id"] == "new"


def test_roast_service_keeps_actor_and_target_rules_separate():
    service = RoastService()
    pork = {"id": "mc_porkchop", "name": "猪排"}
    machine = {"id": "mechanical-pig", "name": "机械猪"}
    assert service.eat_actor_block_reason(pork).startswith("你今天是")
    assert service.eat_target_block_reason(pork) is None
    assert service.eat_target_block_reason(machine) is None
    assert "开袋即食成功" in service.eat_success_message(pork)
