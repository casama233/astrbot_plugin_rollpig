from __future__ import annotations

import asyncio
import datetime
import importlib
import logging
import sys
import threading
import types
from dataclasses import dataclass, field

import pytest

from storage import StorageManager


DAY = datetime.date(2026, 11, 25)
NEXT_DAY = DAY + datetime.timedelta(days=1)
GROUP = "discord:group:123"
CHEF = "discord:user:100"
OTHER_CHEF = "discord:user:101"
DINER = "discord:user:102"
OTHER_DINER = "discord:user:103"


@dataclass
class Event:
    sender: str = CHEF
    group: str = GROUP
    target: str = ""
    messages: list = field(default_factory=list)
    stopped: bool = False

    @staticmethod
    def plain_result(message):
        return message

    async def send(self, message):
        self.messages.append(message)


class KitchenHarness:
    def __init__(self, path, mode):
        self.plugin_data_dir = path
        self._data_lock = threading.RLock()
        self.config = {"enable_roast_feeding": True}
        self.enable_roast = True
        self.date = DAY
        self.roster = {
            (GROUP, DAY.isoformat()): [CHEF, OTHER_CHEF, DINER],
            (GROUP, (DAY - datetime.timedelta(days=1)).isoformat()): [OTHER_DINER],
        }
        self.storage = StorageManager(path, mode=mode, lock=self._data_lock).backend
        self.load_json = self.storage.load_json
        self.save_json = self.storage.save_json
        self._init_roast_feeding()

    def _today(self):
        return self.date

    def _daily_group_members(self, group, day):
        return self.roster.get((group, day), [])

    @staticmethod
    def _event_group_id(event):
        return event.group

    @staticmethod
    def _event_sender_id(event):
        return event.sender

    @staticmethod
    def _storage_user_key(user):
        return user

    @staticmethod
    def _extract_roast_target_id(event, value):
        return event.target or value

    @staticmethod
    def _claim_command_event(event):
        event.stopped = True

    @staticmethod
    async def _send_with_mention(event, target, text):
        await event.send((target, text))


@pytest.fixture
def kitchen_type(monkeypatch):
    if "astrbot.api" not in sys.modules:
        api = types.ModuleType("astrbot.api")
        api.logger = logging.getLogger(__name__)
        monkeypatch.setitem(sys.modules, "astrbot.api", api)
    mixin = importlib.import_module("roast_feeding_feature").RoastFeedingMixin
    return type("Kitchen", (KitchenHarness, mixin), {})


@pytest.mark.parametrize("mode", ["json", "auto"])
def test_feed_is_spent_once_and_mutation_survives_reload(tmp_path, mode, kitchen_type):
    kitchen = kitchen_type(tmp_path, mode)
    if mode == "auto":
        assert kitchen.storage.supports_domain_writes

    async def scenario():
        first = Event(target=DINER)
        second = Event(target=DINER)
        assert not await kitchen._feed_command(first, "")
        assert not first.stopped
        await kitchen._offer_self_roast_feed(first, {"id": "one"})
        await asyncio.gather(
            kitchen._feed_command(first, "投餵"),
            kitchen._feed_command(second, "投喂"),
        )
        assert first.stopped and second.stopped
        outcomes = (first.messages[-1], second.messages[-1])
        assert sum(isinstance(message, tuple) for message in outcomes) == 1
        assert kitchen._feeding_copy("feed_used") in outcomes
        effect = kitchen._feeding_effect(GROUP, DINER, DAY)
        assert effect in {"spicy", "rich"}
        assert kitchen._feeding_effect("qq:group:123", DINER, DAY) == ""
        assert kitchen._feeding_effect(GROUP, OTHER_DINER, NEXT_DAY) == ""
        return effect

    effect = asyncio.run(scenario())
    reopened = kitchen_type(tmp_path, mode)
    assert reopened._feeding_effect(GROUP, DINER, DAY) == effect
    same_day = Event(target=DINER)
    asyncio.run(reopened._offer_self_roast_feed(same_day, {"id": "one"}))
    assert same_day.messages == []
    asyncio.run(reopened._feed_command(same_day, "投喂"))
    assert same_day.messages == [reopened._feeding_copy("feed_used")]


def test_tomorrow_queue_keeps_existing_recipient_slot(tmp_path, kitchen_type):
    kitchen = kitchen_type(tmp_path, "json")

    async def scenario():
        first = Event(target=OTHER_DINER)
        second = Event(sender=OTHER_CHEF, target=OTHER_DINER)
        await kitchen._offer_self_roast_feed(first, {"id": "one"})
        await kitchen._offer_self_roast_feed(second, {"id": "two"})
        await kitchen._feed_command(first, "投喂")
        assert first.messages[-1] == kitchen._feeding_copy("feed_eligible")
        await kitchen._feed_command(first, "明天投喂")
        assert first.messages[-1][0] == OTHER_DINER
        assert kitchen._feeding_effect(GROUP, OTHER_DINER, DAY) == ""
        effect = kitchen._feeding_effect(GROUP, OTHER_DINER, NEXT_DAY)
        assert effect in {"spicy", "rich"}
        await kitchen._feed_command(second, "明天投喂")
        assert second.messages[-1] == kitchen._feeding_copy("feed_slot_taken")
        assert kitchen._feeding_effect(GROUP, OTHER_DINER, NEXT_DAY) == effect
        second.target = DINER
        await kitchen._feed_command(second, "明天投喂")
        assert second.messages[-1][0] == DINER
        return effect

    effect = asyncio.run(scenario())
    reopened = kitchen_type(tmp_path, "json")
    reopened.date = NEXT_DAY
    assert reopened._feeding_effect(GROUP, OTHER_DINER, reopened.date) == effect
    assert reopened._feeding_effect(GROUP, OTHER_DINER, NEXT_DAY + datetime.timedelta(days=1)) == ""


def test_save_failure_leaves_the_dish_available(tmp_path, kitchen_type):
    kitchen = kitchen_type(tmp_path, "json")
    event = Event(target=DINER)

    def fail_save(path, state):
        raise OSError("disk full")

    async def scenario():
        await kitchen._offer_self_roast_feed(event, {"id": "one"})
        kitchen.save_json = fail_save
        await kitchen._feed_command(event, "投喂")
        assert event.messages[-1] == kitchen._feeding_copy("feed_save_failed")
        assert kitchen._feeding_effect(GROUP, DINER, DAY) == ""
        kitchen.save_json = kitchen.storage.save_json
        await kitchen._feed_command(event, "投喂")
        assert event.messages[-1][0] == DINER

    asyncio.run(scenario())
