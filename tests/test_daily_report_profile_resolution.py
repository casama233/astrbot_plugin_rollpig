from __future__ import annotations

import threading
from types import SimpleNamespace

from daily_report_profile_feature import DailyReportProfileMixin


class _BaseDailyReportProfile:
    def _remember_daily_report_context(self, event, user_id=""):
        return None

    def _profile_for_report(self, group_id: str, user_id: str):
        return {
            "display_name": self._legacy_identity(user_id) or "群友",
            "native_id": self._legacy_identity(user_id),
        }


class _Harness(DailyReportProfileMixin, _BaseDailyReportProfile):
    def __init__(self):
        self._data_lock = threading.RLock()
        self.daily_report_state = {"groups": {}, "events": {}, "jobs": {}}
        self.saved = 0

    def _save_daily_report_state_locked(self):
        self.saved += 1

    @staticmethod
    def _legacy_identity(user_id: str) -> str:
        text = str(user_id or "")
        return text.rsplit("|", 1)[-1] if "|" in text else text

    def _canonical_user_id(self, event, user_id: str) -> str:
        return f"v2|{event.platform_type}|user|{self._legacy_identity(user_id)}"

    @staticmethod
    def _event_group_id(event) -> str:
        return str(event.group_id)

    @staticmethod
    def _platform_namespace(event) -> str:
        return str(event.platform)

    @staticmethod
    def _platform_type(event) -> str:
        return str(event.platform_type)

    @staticmethod
    def _url_candidate(value) -> str:
        if isinstance(value, str) and value.startswith("https://"):
            return value
        nested = getattr(value, "url", None)
        return str(nested) if nested and str(nested).startswith("https://") else ""


class At:
    def __init__(self, qq: str, name: str):
        self.qq = qq
        self.name = name


class MentionUser:
    def __init__(self, user_id: str, display_name: str, avatar_url: str):
        self.user_id = user_id
        self.display_name = display_name
        self.avatar_url = avatar_url


def _event(*components, platform="aiocqhttp", platform_type="aiocqhttp"):
    return SimpleNamespace(
        group_id="g1",
        platform=platform,
        platform_type=platform_type,
        message_obj=SimpleNamespace(message=list(components), raw_message={}),
        message_chain=None,
    )


def test_target_only_qq_mention_is_hydrated_for_awards():
    plugin = _Harness()
    event = _event(At("1597696368", "目标群友"))

    plugin._remember_daily_report_context(event, "sender")

    stored = plugin.daily_report_state["groups"]["g1"]["members"]
    canonical = "v2|aiocqhttp|user|1597696368"
    assert stored[canonical]["display_name"] == "目标群友"
    assert stored[canonical]["avatar_url"] == (
        "https://q1.qlogo.cn/g?b=qq&nk=1597696368&s=640"
    )

    # Gameplay events may carry either the canonical id or the native id.  Both
    # must resolve to the same cached member instead of rendering "159..." / "1".
    native_profile = plugin._profile_for_report("g1", "1597696368")
    canonical_profile = plugin._profile_for_report("g1", canonical)
    for profile in (native_profile, canonical_profile):
        assert profile["display_name"] == "目标群友"
        assert profile["avatar_url"].endswith("nk=1597696368&s=640")


def test_target_only_qq_user_gets_avatar_even_without_cached_member():
    plugin = _Harness()
    plugin.daily_report_state["groups"]["g1"] = {
        "platform": "aiocqhttp:bot-1",
        "platform_type": "aiocqhttp",
        "members": {},
    }

    profile = plugin._profile_for_report("g1", "1597696368")

    assert profile["native_id"] == "1597696368"
    assert profile["avatar_url"] == (
        "https://q1.qlogo.cn/g?b=qq&nk=1597696368&s=640"
    )


def test_generic_mention_metadata_is_preserved_without_qq_assumptions():
    plugin = _Harness()
    avatar = "https://cdn.example.test/avatar/42.png"
    event = _event(
        MentionUser("42", "跨平台群友", avatar),
        platform="discord:bot-1",
        platform_type="discord",
    )

    plugin._remember_daily_report_context(event, "sender")
    profile = plugin._profile_for_report("g1", "42")

    assert profile["display_name"] == "跨平台群友"
    assert profile["avatar_url"] == avatar
    assert profile["platform_type"] == "discord"


def test_unknown_platform_does_not_invent_an_avatar_url():
    plugin = _Harness()
    plugin.daily_report_state["groups"]["g1"] = {
        "platform": "custom-adapter",
        "platform_type": "custom-adapter",
        "members": {},
    }

    profile = plugin._profile_for_report("g1", "user-42")

    assert "avatar_url" not in profile


def test_command_actor_mixin_wires_profile_hydration_before_daily_report():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (root / "command_actor_feature.py").read_text(encoding="utf-8")
    assert "DailyReportProfileMixin" in source
    assert "class CommandActorMentionMixin(DailyReportProfileMixin):" in source
