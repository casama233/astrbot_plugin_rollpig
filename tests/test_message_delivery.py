from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from message_delivery import MessageDeliveryMixin
from random_roast_feature import RandomRoastMixin
from rollpig_core import legacy_identity, namespace_identity


@pytest.fixture
def result_type():
    try:
        from astrbot.core.message.message_event_result import MessageEventResult
        return MessageEventResult
    except ImportError:
        # Source-only CI does not install AstrBot. Keep the boundary double to
        # its result-building API; the running-host checks use the real class.
        class Result:
            def __init__(self):
                self.chain = []

            def message(self, text):
                self.chain.append(SimpleNamespace(type="Plain", text=text))
                return self

            def at(self, name, qq):
                self.chain.append(SimpleNamespace(type="At", name=name, qq=qq))
                return self

            def url_image(self, url):
                self.chain.append(SimpleNamespace(type="Image", file=url))
                return self

        return Result


CASES = [
    ("aiocqhttp", "10001", "20002", {}, ("At", "10001"), ("At", "20002")),
    ("discord", "10001", "20002", {}, ("At", "10001"), ("At", "20002")),
    ("slack", "U_ACTOR", "U_TARGET", {}, ("Plain", "<@U_ACTOR>"), ("Plain", "<@U_TARGET>")),
    ("qq_official", "actor_openid", "target_openid", {}, ("At", "actor_openid"), ("At", "target_openid")),
    ("telegram", "10001", "20002", {"10001": "alice", "20002": "bob"}, ("Plain", "@alice"), ("Plain", "@bob")),
    ("telegram", "10001", "20002", {}, ("Plain", "[群友](tg://user?id=10001)"), ("Plain", "[群友](tg://user?id=20002)")),
    ("whatsapp", "15550000001@s.whatsapp.net", "15550000002@s.whatsapp.net", {}, ("At", "15550000001@s.whatsapp.net"), ("At", "15550000002@s.whatsapp.net")),
]
CASE_IDS = ["qq-onebot", "discord", "slack", "qq-official", "telegram-name", "telegram-id", "whatsapp"]


class Event:
    def __init__(self, case, result_type, *, group=True):
        self.platform, self.actor, self.target, self.names, *_ = case
        self.group = group
        self.make_result = result_type
        self.sent = []
        self.stopped = False
        self.fail_next = False

    def plain_result(self, text):
        return self.make_result().message(text)

    async def send(self, result):
        self.sent.append(result)
        await asyncio.sleep(0)
        if self.fail_next:
            self.fail_next = False
            raise TimeoutError("send acknowledgement timed out")


class Base:
    def _claim_command_event(self, event):
        event.stopped = True

    def _event_group_id(self, event):
        return "test-group" if event.group else ""

    def _event_sender_id(self, event):
        return namespace_identity(event.platform + "@test", "user", event.actor)

    def _canonical_user_id(self, event, user_id):
        return namespace_identity(event.platform + "@test", "user", user_id)

    _legacy_identity = staticmethod(legacy_identity)

    def _platform_type(self, event):
        return event.platform

    def _telegram_mention_name(self, event, canonical_id, native_id):
        return event.names.get(native_id, "")


class Plugin(MessageDeliveryMixin, RandomRoastMixin, Base):
    pass


def signature(result):
    values = []
    for part in result.chain:
        kind = getattr(part.type, "value", part.type)
        value = part.qq if kind == "At" else part.text if kind == "Plain" else part.file
        values.append((kind, str(value)))
    return values


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_self_reply_mentions_once_and_leaves_following_image_untouched(case, result_type):
    async def run():
        event, plugin = Event(case, result_type), Plugin()
        plugin._claim_command_event(event)
        plugin._claim_command_event(event)
        user_id = namespace_identity(event.platform + "@test", "user", event.actor)
        await plugin._send_with_mention(event, user_id, " 这是你的今日小猪。")
        image = event.make_result().url_image("https://example.invalid/pig.png")
        await event.send(image)
        assert event.stopped
        expected = [case[4], ("Plain", "\n这是你的今日小猪。")]
        if case[4][0] == "Plain":
            expected = [("Plain", case[4][1] + "\n这是你的今日小猪。")]
        assert signature(event.sent[0]) == expected
        assert event.sent[1] is image
        assert len(image.chain) == 1
    asyncio.run(run())


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_requester_header_preserves_a_different_gameplay_target(case, result_type):
    async def run():
        event, plugin = Event(case, result_type), Plugin()
        plugin._claim_command_event(event)
        await plugin._send_with_mention(event, event.target, "正文")
        expected = [case[4], ("Plain", "\n"), case[5], ("Plain", "\n正文")]
        if case[4][0] == "Plain":
            expected = [("Plain", case[4][1] + "\n" + case[5][1] + "\n正文")]
        assert signature(event.sent[0]) == expected
    asyncio.run(run())


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_private_replies_have_no_group_mentions(case, result_type):
    async def run():
        event, plugin = Event(case, result_type, group=False), Plugin()
        plugin._claim_command_event(event)
        await plugin._send_with_mention(event, event.actor, "  正文\n第二段")
        assert signature(event.sent[0]) == [("Plain", "正文\n第二段")]
    asyncio.run(run())


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_random_target_uses_the_same_platform_mention_policy(case, result_type):
    async def run():
        event, plugin = Event(case, result_type), Plugin()
        plugin._claim_command_event(event)
        await event.send(plugin._random_roast_target_announcement(event, event.target))
        expected = [
            case[4], ("Plain", "\n🎲 随机转盘停在了 "),
            case[5], ("Plain", " 头上。后厨说：就你了。"),
        ]
        if case[4][0] == "Plain":
            expected = [("Plain", case[4][1] + "\n🎲 随机转盘停在了 " + case[5][1] + " 头上。后厨说：就你了。")]
        assert signature(event.sent[0]) == expected
    asyncio.run(run())


@pytest.mark.parametrize("kind", ["native", "plain", "nickname"])
def test_discord_deduplicates_existing_mention_representations(kind, result_type):
    async def run():
        event, plugin = Event(CASES[1], result_type), Plugin()
        plugin._claim_command_event(event)
        result = event.make_result()
        if kind == "native":
            result.at(name="", qq=event.actor).message("\n正文")
        else:
            token = "<@10001>" if kind == "plain" else "<@!10001>"
            result.message(token + "\n正文")
        before = list(result.chain)
        await event.send(result)
        assert result.chain == before
    asyncio.run(run())


def test_telegram_username_prefix_does_not_hide_a_different_user(result_type):
    async def run():
        event, plugin = Event(CASES[4], result_type), Plugin()
        plugin._claim_command_event(event)
        await event.send(event.plain_result("@alice_other\n正文"))
        assert signature(event.sent[0]) == [("Plain", "@alice\n@alice_other\n正文")]
    asyncio.run(run())


def test_acknowledgement_timeout_does_not_retry_or_repeat_the_header(result_type):
    async def run():
        event, plugin = Event(CASES[1], result_type), Plugin()
        plugin._claim_command_event(event)
        event.fail_next = True
        with pytest.raises(TimeoutError):
            await plugin._send_with_mention(event, event.actor, "正文")
        assert len(event.sent) == 1
        await event.send(event.plain_result("下一段"))
        assert signature(event.sent[1]) == [("Plain", "下一段")]
    asyncio.run(run())


def test_concurrent_replies_claim_the_header_before_awaiting(result_type):
    async def run():
        event, plugin = Event(CASES[1], result_type), Plugin()
        plugin._claim_command_event(event)
        await asyncio.gather(event.send(event.plain_result("第一段")), event.send(event.plain_result("第二段")))
        assert signature(event.sent[0]) == [("At", "10001"), ("Plain", "\n第一段")]
        assert signature(event.sent[1]) == [("Plain", "第二段")]
    asyncio.run(run())
