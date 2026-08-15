from __future__ import annotations

import asyncio
import datetime
import threading

from reservation_firewood_feature import ReservationFirewoodMixin
from roast_reservations import create_or_join_reservation, get_reservation, resolve_reservation


DRAW_DATE = datetime.date(2026, 8, 15)


class FakeEvent:
    def __init__(self) -> None:
        self.sent: list[str] = []

    @staticmethod
    def plain_result(text: str) -> str:
        return text

    async def send(self, message: str) -> None:
        self.sent.append(str(message))


class FirewoodHarness(ReservationFirewoodMixin):
    def __init__(self, *, actor_id: str = "friend", requested_target: str = "") -> None:
        self.enable_roast = True
        self.enable_group_roast = True
        self.enable_roast_reservation = True
        self.roast_reservation_max_participants = 12
        self.roast_reservation_state: dict = {}
        self.oven_refill_state: dict = {"version": 1, "dates": {}}
        self._roast_reservation_lock = asyncio.Lock()
        self._data_lock = threading.RLock()
        self.actor_id = actor_id
        self.requested_target = requested_target
        self.claimed = False
        self.saved = 0
        self.mentions: list[tuple[str, str]] = []
        self.events: list[dict] = []
        self.actor_has_pig = True
        self.refill_calls = 0

    def _today(self) -> datetime.date:
        return DRAW_DATE

    def _claim_command_event(self, event) -> None:
        self.claimed = True

    def _event_group_id(self, event) -> str:
        return "g1"

    def _event_sender_id(self, event) -> str:
        return self.actor_id

    def _extract_roast_target_id(self, event, args: str = "") -> str:
        return self.requested_target

    def _get_daily_pig(self, user_id: str, day: datetime.date):
        if user_id == self.actor_id and self.actor_has_pig:
            return {"id": "pig", "name": "test pig"}
        return None

    @staticmethod
    def _roast_block_reason(pig, subject: str = "actor") -> str:
        return "" if pig else "今天没有可料理的小猪。"

    def _save_roast_reservations_locked(self) -> None:
        self.saved += 1

    def _record_gameplay_event(self, group_id: str, event_type: str, **payload) -> None:
        self.events.append({"group_id": group_id, "type": event_type, **payload})

    async def _send_with_mention(self, event, target_id: str, text: str) -> None:
        self.mentions.append((str(target_id), str(text)))

    async def oven_refill_support(self, event) -> None:
        self.refill_calls += 1


def _reserve(harness: FirewoodHarness, target: str = "target", chef: str = "chef") -> None:
    result = create_or_join_reservation(
        harness.roast_reservation_state,
        draw_date=DRAW_DATE.isoformat(),
        group_id="g1",
        target_id=target,
        actor_id=chef,
        max_participants=harness.roast_reservation_max_participants,
        now=1,
    )
    assert result["status"] == "created"


def _activate_refill(harness: FirewoodHarness) -> None:
    harness.oven_refill_state = {
        "version": 1,
        "dates": {
            DRAW_DATE.isoformat(): {
                "g1": {"active": True, "completing": False}
            }
        },
    }


def test_chef_bare_firewood_is_terminal_reservation_denial_when_no_refill():
    harness = FirewoodHarness(actor_id="chef")
    _reserve(harness)
    event = FakeEvent()

    asyncio.run(harness.firewood_support(event))

    assert harness.claimed is True
    assert harness.refill_calls == 0
    assert event.sent
    assert "主厨" in event.sent[-1]
    assert "开局已经算 1 人" in event.sent[-1]
    row = get_reservation(
        harness.roast_reservation_state, DRAW_DATE.isoformat(), "g1", "target"
    )
    assert row is not None and row["participants"] == ["chef"]


def test_single_pending_reservation_allows_bare_firewood_to_join():
    harness = FirewoodHarness(actor_id="friend")
    _reserve(harness)
    event = FakeEvent()

    asyncio.run(harness.firewood_support(event))

    assert harness.claimed is True
    assert harness.refill_calls == 0
    assert event.sent == []
    assert harness.mentions == [("target", " 🪵 又一根柴悄悄塞进来；现在共有 2 人蹲锅。")]
    row = get_reservation(
        harness.roast_reservation_state, DRAW_DATE.isoformat(), "g1", "target"
    )
    assert row is not None and row["participants"] == ["chef", "friend"]
    assert harness.events[0]["metadata"]["via"] == "firewood-command"


def test_active_refill_owns_bare_firewood_even_when_reservation_exists():
    harness = FirewoodHarness(actor_id="friend")
    _reserve(harness)
    _activate_refill(harness)
    event = FakeEvent()

    asyncio.run(harness.firewood_support(event))

    assert harness.claimed is True
    assert harness.refill_calls == 1
    row = get_reservation(
        harness.roast_reservation_state, DRAW_DATE.isoformat(), "g1", "target"
    )
    assert row is not None and row["participants"] == ["chef"]


def test_explicit_target_chooses_reservation_even_during_active_refill():
    harness = FirewoodHarness(actor_id="friend", requested_target="target")
    _reserve(harness)
    _activate_refill(harness)
    event = FakeEvent()

    asyncio.run(harness.firewood_support(event, "@target"))

    assert harness.claimed is True
    assert harness.refill_calls == 0
    row = get_reservation(
        harness.roast_reservation_state, DRAW_DATE.isoformat(), "g1", "target"
    )
    assert row is not None and row["participants"] == ["chef", "friend"]


def test_multiple_pending_reservations_require_target_when_no_refill():
    harness = FirewoodHarness(actor_id="friend")
    _reserve(harness, target="target-a", chef="chef-a")
    _reserve(harness, target="target-b", chef="chef-b")
    event = FakeEvent()

    asyncio.run(harness.firewood_support(event))

    assert harness.claimed is True
    assert event.sent
    assert "2 口预约锅" in event.sent[-1]
    assert "/添柴 @目标" in event.sent[-1]


def test_no_refill_and_no_reservation_is_claimed_and_explained():
    harness = FirewoodHarness(actor_id="friend")
    event = FakeEvent()

    asyncio.run(harness.firewood_support(event))

    assert harness.claimed is True
    assert harness.refill_calls == 0
    assert event.sent
    assert "既没有补货轮次" in event.sent[-1]
    assert "/烤箱补货" in event.sent[-1]


def test_resolved_reservation_is_not_routed_as_pending_firewood():
    harness = FirewoodHarness(actor_id="friend")
    _reserve(harness)
    resolve_reservation(
        harness.roast_reservation_state,
        draw_date=DRAW_DATE.isoformat(),
        group_id="g1",
        target_id="target",
        outcome="escape",
        now=2,
    )
    event = FakeEvent()

    asyncio.run(harness.firewood_support(event))

    assert harness.claimed is True
    assert event.sent
    assert "既没有补货轮次" in event.sent[-1]
