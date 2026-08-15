from __future__ import annotations

import asyncio
import datetime
import threading
from pathlib import Path

from reservation_firewood_feature import ReservationFirewoodMixin
from roast_reservations import (
    create_or_join_reservation,
    get_reservation,
    list_pending_reservations,
    resolve_reservation,
)


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
        self._roast_reservation_lock = asyncio.Lock()
        self._data_lock = threading.RLock()
        self.actor_id = actor_id
        self.requested_target = requested_target
        self.claimed = False
        self.saved = 0
        self.mentions: list[tuple[str, str]] = []
        self.events: list[dict] = []
        self.actor_has_pig = True

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

    def _record_gameplay_event(
        self,
        group_id: str,
        event_type: str,
        **payload,
    ) -> None:
        self.events.append({"group_id": group_id, "type": event_type, **payload})

    async def _send_with_mention(self, event, target_id: str, text: str) -> None:
        self.mentions.append((str(target_id), str(text)))


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


def test_main_registers_firewood_on_real_star_and_feature_claims_every_invocation():
    main = Path("main.py").read_text(encoding="utf-8")
    feature = Path("reservation_firewood_feature.py").read_text(encoding="utf-8")

    assert "ReservationFirewoodMixin" in main
    assert "@filter.command('添柴'" in main
    assert "return await super().roast_reservation_add_firewood(event, args)" in main
    assert "@filter.command" not in feature
    assert "self._claim_command_event(event)" in feature


def test_chef_firewood_is_terminal_denial_instead_of_llm_fallthrough():
    harness = FirewoodHarness(actor_id="chef")
    _reserve(harness)
    event = FakeEvent()

    asyncio.run(harness.roast_reservation_add_firewood(event))

    assert harness.claimed is True
    assert harness.saved == 0
    assert event.sent
    assert "主厨" in event.sent[-1]
    assert "不能再给自己添柴" in event.sent[-1]
    row = get_reservation(
        harness.roast_reservation_state,
        DRAW_DATE.isoformat(),
        "g1",
        "target",
    )
    assert row is not None
    assert row["participants"] == ["chef"]


def test_single_pending_reservation_allows_plain_firewood_to_join_for_free():
    harness = FirewoodHarness(actor_id="friend")
    _reserve(harness)
    event = FakeEvent()

    asyncio.run(harness.roast_reservation_add_firewood(event))

    assert harness.claimed is True
    assert event.sent == []
    assert harness.saved == 1
    assert harness.mentions == [
        ("target", " 🪵 又有人悄悄添了一把柴；现在共有 2 人蹲守。")
    ]
    row = get_reservation(
        harness.roast_reservation_state,
        DRAW_DATE.isoformat(),
        "g1",
        "target",
    )
    assert row is not None
    assert row["participants"] == ["chef", "friend"]
    assert len(harness.events) == 1
    assert harness.events[0]["target_id"] == "target"
    assert harness.events[0]["metadata"]["via"] == "firewood-command"


def test_no_pending_reservation_is_claimed_and_explained_by_plugin():
    harness = FirewoodHarness(actor_id="friend")
    event = FakeEvent()

    asyncio.run(harness.roast_reservation_add_firewood(event))

    assert harness.claimed is True
    assert event.sent
    assert "没有待添柴的预约烤箱" in event.sent[-1]


def test_multiple_pending_reservations_require_explicit_target():
    harness = FirewoodHarness(actor_id="friend")
    _reserve(harness, target="target-a", chef="chef-a")
    _reserve(harness, target="target-b", chef="chef-b")
    event = FakeEvent()

    asyncio.run(harness.roast_reservation_add_firewood(event))

    assert harness.claimed is True
    assert event.sent
    assert "有 2 口待结算预约烤箱" in event.sent[-1]
    assert "/添柴 @目标" in event.sent[-1]


def test_explicit_target_selects_one_of_multiple_pending_reservations():
    harness = FirewoodHarness(actor_id="friend", requested_target="target-b")
    _reserve(harness, target="target-a", chef="chef-a")
    _reserve(harness, target="target-b", chef="chef-b")
    event = FakeEvent()

    asyncio.run(harness.roast_reservation_add_firewood(event, "@target-b"))

    assert harness.claimed is True
    assert harness.mentions[-1][0] == "target-b"
    row = get_reservation(
        harness.roast_reservation_state,
        DRAW_DATE.isoformat(),
        "g1",
        "target-b",
    )
    assert row is not None
    assert row["participants"] == ["chef-b", "friend"]


def test_pending_list_ignores_resolved_rows_and_keeps_target_id():
    state: dict = {}
    create_or_join_reservation(
        state,
        draw_date=DRAW_DATE.isoformat(),
        group_id="g1",
        target_id="old-target",
        actor_id="chef-a",
        now=1,
    )
    create_or_join_reservation(
        state,
        draw_date=DRAW_DATE.isoformat(),
        group_id="g1",
        target_id="live-target",
        actor_id="chef-b",
        now=2,
    )
    resolve_reservation(
        state,
        draw_date=DRAW_DATE.isoformat(),
        group_id="g1",
        target_id="old-target",
        outcome="escape",
        now=3,
    )

    pending = list_pending_reservations(state, DRAW_DATE.isoformat(), "g1")
    assert [row["target_id"] for row in pending] == ["live-target"]
