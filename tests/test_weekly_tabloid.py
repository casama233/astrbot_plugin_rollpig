from __future__ import annotations

import asyncio
import datetime
import importlib.util
import json
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from PIL import Image, ImageFont

from daily_report_delivery import DailyReportDeliveryClaims
from renderers.weekly_tabloid import WEEKLY_WIDTH


ROOT = Path(__file__).resolve().parents[1]
SUNDAY = "2026-11-22"
DISCORD_GROUP = "v2|discord@bot|group|100"
QQ_GROUP = "v2|aiocqhttp@bot|group|100"


class _Chain:
    def __init__(self):
        self.chain = []

    def message(self, text):
        self.chain.append(SimpleNamespace(type="Plain", text=text))
        return self

    def file_image(self, path):
        self.chain.append(SimpleNamespace(type="Image", path=path))
        return self


class _Button(SimpleNamespace):
    CallbackAction = SimpleNamespace


@pytest.fixture
def tabloid(monkeypatch, tmp_path):
    astrbot = ModuleType("astrbot")
    api = ModuleType("astrbot.api")
    event = ModuleType("astrbot.api.event")
    api.logger = logging.getLogger(__name__)
    api.message_components = SimpleNamespace(ActionRow=SimpleNamespace, Button=_Button)
    event.AstrMessageEvent = object
    event.MessageChain = _Chain
    event.filter = SimpleNamespace(button_action=lambda _: None)
    for module in (astrbot, api, event):
        monkeypatch.setitem(sys.modules, module.__name__, module)
    spec = importlib.util.spec_from_file_location("_weekly_tabloid_for_test", ROOT / "weekly_tabloid_feature.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Base:
        def __init__(self, context, _config):
            self.context = context
            self.plugin_data_dir = tmp_path
            self.enable_daily_report = True
            self.daily_report_skip_empty_groups = True
            self._data_lock = threading.RLock()
            self.daily_report_state = {"jobs": {}}
            self.daily_report_delivery_claims = DailyReportDeliveryClaims(tmp_path / "claims", keep_days=14)
            self.history = {"identity_claims": {"users": {"old-u1": "u1"}}}
            self.clock = datetime.datetime(2026, 11, 22, 22, 1, tzinfo=datetime.timezone.utc)
            self._run_with_render_slot = lambda renderer, *args: renderer(*args)
            self.font_regular = self.font_bold = ImageFont.truetype(
                str(ROOT / "resource" / "font" / "荆南麦圆体.otf"), 24
            )
            self.examples = {
                "day_members": {
                    (DISCORD_GROUP, "2026-11-16"): ["old-u1", "u2"],
                    (DISCORD_GROUP, "2026-11-20"): ["u1", "u3"],
                    (DISCORD_GROUP, "2026-11-21"): ["u2"],
                    (QQ_GROUP, SUNDAY): ["u4"],
                },
                "events": {
                    (DISCORD_GROUP, "2026-11-16"): [
                        {"kind": "roast_success", "actor_id": "u1", "target_id": "u2", "victim_id": "u2"},
                        {"kind": "daily_sacrifice", "victim_id": "u3"},
                    ],
                    (DISCORD_GROUP, "2026-11-21"): [
                        {"kind": "roast_success", "actor_id": "old-u1", "target_id": "u3", "victim_id": "u3"},
                        {"kind": "roast_backlash", "actor_id": "u1", "target_id": "u3", "victim_id": "u1"},
                    ],
                },
            }

        def _now(self):
            return self.clock

        def _today(self):
            return self.clock.date()

        @staticmethod
        def _daily_eaten_victims(group, date):
            return ["u3"] if group == DISCORD_GROUP and date == "2026-11-16" else []

        @staticmethod
        def _daily_group_roast_total(_group, _date):
            return 0

        def _daily_group_members(self, group, date):
            return self.examples["day_members"].get((group, date), [])

        def _report_events(self, group, date):
            return self.examples["events"].get((group, date), [])

        @staticmethod
        def _profile_for_report(_group, user):
            return {"display_name": f"猪在现场 {user}"}

        @staticmethod
        def _user_read_candidates(user):
            return ("u1", "old-u1") if user in {"u1", "old-u1"} else (user,)

        @staticmethod
        def save_json(path, state):
            path.write_text(json.dumps(state), encoding="utf-8")

        @staticmethod
        def load_json(path, default):
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    class Tabloid(module.WeeklyTabloidMixin, Base):
        def publish(self, group=DISCORD_GROUP):
            self.daily_report_state["jobs"].setdefault(SUNDAY, {})[group] = {"report_type": "weekly"}
            claim_path, _claim = self.daily_report_delivery_claims.try_acquire(group, SUNDAY)
            self.daily_report_delivery_claims.finalize(claim_path, status="sent")

    return Tabloid(SimpleNamespace(), {"enable_weekly_tabloid": True}), module


def test_silent_sunday_uses_week_and_opens_only_with_receipt(tabloid):
    plugin, module = tabloid
    chain, output = asyncio.run(plugin._prepare_scheduled_weekly_tabloid(DISCORD_GROUP, SUNDAY, "origin"))
    poll = plugin._weekly_poll(DISCORD_GROUP, SUNDAY)
    try:
        with Image.open(output) as image:
            assert image.size[0] == WEEKLY_WIDTH
            assert 650 < image.size[1] < 1600
        image_part, vote_text, button_row = chain.chain
        assert image_part.type == "Image" and image_part.path == str(output.absolute())
        assert vote_text.type == "Plain"
        buttons = button_row.buttons
        assert [item.action.data["number"] for item in buttons] == [1, 2, 3]
        assert all(item.action.data["date"] == SUNDAY for item in buttons)
        assert all(item.id == module.WEEKLY_VOTE_ACTION for item in buttons)
        names = poll["report"]["names"]
        choices = [
            module._weekly_copy("poll_item", number=number, name=names[user_id])
            for number, user_id in enumerate(poll["report"]["candidates"], start=1)
        ]
        assert vote_text.text.splitlines() == [module._weekly_copy("poll_hint"), *choices]
        assert [item.label for item in buttons] == choices
    finally:
        output.unlink()

    assert poll["report"]["totals"] == {
        "active_users": 3, "draws": 5, "roasts": 3, "eats": 1, "escapes": 0, "backlashes": 1,
    }
    assert poll["report"]["awards"]["roast_maniac"] == {"count": 2, "players": ["u1"]}
    assert poll["report"]["awards"]["backlash_king"] == {"count": 1, "players": ["u1"]}
    assert plugin._weekly_vote(DISCORD_GROUP, "u1", SUNDAY, 1) == module._weekly_copy("poll_closed")
    assert plugin._weekly_vote(QQ_GROUP, "u1", SUNDAY, 1) == module._weekly_copy("poll_closed")
    plugin.publish()
    assert plugin._weekly_vote(DISCORD_GROUP, "stranger", SUNDAY, 1) == module._weekly_copy("not_eligible")

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda user: plugin._weekly_vote(DISCORD_GROUP, user, SUNDAY, 1), ["old-u1", "u1"]))
    name = poll["report"]["names"][poll["report"]["candidates"][0]]
    assert set(replies) == {
        module._weekly_copy("vote_ok", number=1, name=name),
        module._weekly_copy("vote_duplicate", number=1, name=name),
    }
    plugin._weekly_vote(DISCORD_GROUP, "u2", SUNDAY, 2)
    plugin.weekly_tabloid_state = plugin.load_json(plugin.weekly_tabloid_state_path, {})
    plugin.clock += datetime.timedelta(days=1)
    first, second, _third = poll["report"]["candidates"]
    assert plugin._weekly_aura(DISCORD_GROUP, first, plugin._today())
    assert not plugin._weekly_aura(DISCORD_GROUP, second, plugin._today())
    assert not plugin._weekly_aura(QQ_GROUP, first, plugin._today())
    assert plugin._weekly_vote(DISCORD_GROUP, "u3", SUNDAY, 1) == module._weekly_copy("poll_closed")
    assert asyncio.run(plugin._prepare_scheduled_weekly_tabloid(DISCORD_GROUP, SUNDAY, "origin")) is None


def test_weekly_story_uses_anonymous_counts_and_cache(tabloid):
    plugin, module = tabloid
    plugin.weekly_tabloid_ai = True
    prompts = []

    async def provider_id(*, umo):
        assert umo == "origin"
        return "fixture-provider"

    async def generate(*, chat_provider_id, prompt):
        assert chat_provider_id == "fixture-provider"
        assert "u1" not in prompt
        assert "猪在现场" not in prompt
        assert DISCORD_GROUP not in prompt
        assert '"player": "P' in prompt
        prompts.append(prompt)
        return SimpleNamespace(completion_text="P1 督阵，炉口连续营业。")

    provider = SimpleNamespace(get_model=lambda: "gemini-fixture")
    plugin.context = SimpleNamespace(
        get_current_chat_provider_id=provider_id,
        get_provider_by_id=lambda _provider_id: provider,
        llm_generate=generate,
    )
    published = [
        asyncio.run(plugin._prepare_scheduled_weekly_tabloid(DISCORD_GROUP, SUNDAY, "origin"))
        for _ in range(2)
    ]
    try:
        assert len(prompts) == 1
        report = plugin._weekly_poll(DISCORD_GROUP, SUNDAY)["report"]
        assert report["story"].startswith("猪在现场 ")
        assert report["story"].endswith(" 督阵，炉口连续营业。")
        provider.get_model = lambda: "fixture-other"
        assert asyncio.run(plugin._weekly_llm_story(DISCORD_GROUP, "origin", report)) == report["story"]
        assert len(prompts) == 1
        # An unavailable renderer still sends a complete election and story.
        def fail(*_):
            raise OSError("fixture")

        plugin._run_with_render_slot = fail
        chain, output = asyncio.run(plugin._weekly_message(QQ_GROUP, report))
        assert output is None
        assert len(chain.chain) == 1
        assert chain.chain[0].type == "Plain"
        fallback = chain.chain[0].text.splitlines()
        assert fallback[:4] == [
            module._weekly_copy("title"),
            "2026-11-16  →  2026-11-22",
            report["story"],
            module._weekly_copy("stats", **report["totals"]),
        ]
        assert f'{module._weekly_copy("award_roast_maniac")} · 猪在现场 u1 (2)' in fallback
        poll_lines = plugin._weekly_poll_text(report)
        assert fallback[-len(poll_lines):] == poll_lines
    finally:
        for _chain, output in published:
            output.unlink()


@pytest.mark.parametrize("activity_group", [DISCORD_GROUP, QQ_GROUP])
def test_qq_weekly_image_keeps_numbered_vote_text_or_empty_notice(tabloid, activity_group):
    plugin, module = tabloid
    report, _ = plugin._weekly_activity(activity_group, plugin._today())
    report["names"] = plugin._weekly_report_names(activity_group, report)
    chain, output = asyncio.run(plugin._weekly_message(QQ_GROUP, report))
    try:
        image_part, vote_text = chain.chain
        assert image_part.type == "Image" and image_part.path == str(output.absolute())
        assert vote_text.type == "Plain"
        if activity_group == DISCORD_GROUP:
            assert vote_text.text.splitlines() == [
                module._weekly_copy("poll_hint"),
                *[
                    module._weekly_copy("poll_item", number=number, name=report["names"][user_id])
                    for number, user_id in enumerate(report["candidates"], start=1)
                ],
            ]
        else:
            assert vote_text.text == module._weekly_copy("poll_empty")
    finally:
        output.unlink()


def test_preview_does_not_open_poll_and_midnight_drops_stale_publication(tabloid, monkeypatch):
    plugin, module = tabloid
    sent = []

    async def send(chain):
        sent.append(chain)

    plugin._event_group_id = lambda _event: DISCORD_GROUP
    event = SimpleNamespace(send=send)
    assert asyncio.run(plugin._weekly_command(event, "八卦"))
    image_part, preview_text = sent[0].chain
    assert image_part.type == "Image"
    assert preview_text.type == "Plain" and preview_text.text == module._weekly_copy("preview_hint")
    assert not plugin.weekly_tabloid_state_path.exists()

    async def wait_past_midnight(*_):
        plugin.clock += datetime.timedelta(days=1)
        return "test"

    monkeypatch.setattr(plugin, "_weekly_llm_story", wait_past_midnight)
    assert asyncio.run(plugin._prepare_scheduled_weekly_tabloid(DISCORD_GROUP, SUNDAY, "origin")) is None
    assert not plugin.weekly_tabloid_state_path.exists()


def test_vote_save_failure_allows_retry(tabloid, monkeypatch):
    plugin, module = tabloid
    _chain, output = asyncio.run(plugin._prepare_scheduled_weekly_tabloid(DISCORD_GROUP, SUNDAY, "origin"))
    output.unlink()
    plugin.publish()
    save = plugin.save_json

    def fail(*_):
        raise OSError("fixture")

    monkeypatch.setattr(plugin, "save_json", fail)
    assert plugin._weekly_vote(DISCORD_GROUP, "u1", SUNDAY, 1) == module._weekly_copy("vote_save_failed")
    assert plugin._weekly_poll(DISCORD_GROUP, SUNDAY)["votes"] == {}
    monkeypatch.setattr(plugin, "save_json", save)
    plugin._weekly_vote(DISCORD_GROUP, "u1", SUNDAY, 1)
    assert plugin._weekly_poll(DISCORD_GROUP, SUNDAY)["votes"] == {"u1": 1}


def test_unreadable_weekly_state_does_not_prevent_plugin_startup(tabloid, monkeypatch):
    plugin, _ = tabloid
    plugin.weekly_tabloid_state_path.write_text("{}", encoding="utf-8")

    def fail(*_):
        raise OSError("fixture read failure")

    monkeypatch.setattr(type(plugin), "load_json", staticmethod(fail))
    restarted = type(plugin)(SimpleNamespace(), {"enable_weekly_tabloid": True})
    assert restarted.enable_daily_report
    assert not restarted.enable_weekly_tabloid
    assert restarted.weekly_tabloid_state_path.read_text(encoding="utf-8") == "{}"


def test_sunday_scheduler_dispatches_weekly_once_even_without_sunday_draws(tabloid):
    plugin, _ = tabloid
    spec = importlib.util.spec_from_file_location("_daily_report_for_weekly_test", ROOT / "daily_report_feature.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plugin.__class__ = type("WeeklyDispatch", (type(plugin), module.DailyReportMixin), {})
    plugin.timezone = datetime.timezone.utc
    plugin.daily_report_send_hour = 23
    plugin.daily_report_send_minute = 50
    plugin.daily_report_random_delay_minutes = 10
    plugin.daily_report_random_eat_enabled = True
    plugin._daily_report_send_lock = asyncio.Lock()
    plugin._save_daily_report_state_locked = lambda: None
    plugin._flush_daily_report_state_durable = lambda: None
    plugin.daily_report_state["groups"] = {
        DISCORD_GROUP: {"auto_enabled": True, "auto_enabled_since": SUNDAY, "umo": "discord:GroupMessage:100"}
    }

    sent = []

    async def send(umo, chain):
        assert chain.chain[-1].buttons
        assert plugin._weekly_poll(DISCORD_GROUP, SUNDAY, published=True) is None
        sent.append(umo)
        return True

    async def run():
        plugin.context.send_message = send
        await plugin._daily_report_tick()
        await plugin._daily_report_tick()

    asyncio.run(run())
    assert sent == ["discord:GroupMessage:100"]
    assert plugin._weekly_poll(DISCORD_GROUP, SUNDAY, published=True)
    job = plugin.daily_report_state["jobs"][SUNDAY][DISCORD_GROUP]
    assert job["status"] == "sent" and job["report_type"] == "weekly"
    assert "sacrifice_id" not in job
