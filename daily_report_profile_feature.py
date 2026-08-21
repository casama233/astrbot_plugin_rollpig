from __future__ import annotations

import re
import time
from typing import Any


class DailyReportProfileMixin:
    """Hydrate daily-report profiles independently from command senders.

    Awards are driven by gameplay actor/target/victim ids, while the original
    daily-report profile cache was populated only when a user was the sender of
    a RollPig event.  This mixin closes that gap by remembering mentioned users
    from message components and by resolving report profiles through native-id
    aliases plus platform-specific avatar fallbacks.

    Platform integrations can extend avatar resolution without changing the
    report builder by implementing ``_daily_report_avatar_for_<platform>()``.
    The resolver is intentionally synchronous: it only derives metadata from
    already-observed events/state and never performs network I/O while holding
    the plugin data lock.
    """

    _REPORT_PROFILE_ID_KEYS = (
        "qq",
        "user_id",
        "userId",
        "uid",
        "target_id",
        "targetId",
        "id",
    )
    _REPORT_PROFILE_NAME_KEYS = (
        "card",
        "nickname",
        "display_name",
        "displayName",
        "global_name",
        "globalName",
        "name",
        "username",
    )
    _REPORT_PROFILE_AVATAR_KEYS = (
        "avatar_url",
        "avatarUrl",
        "avatar",
        "face",
        "head_img",
        "headimgurl",
        "head_image",
        "photo_url",
        "icon_url",
    )

    @staticmethod
    def _daily_report_profile_value(obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    @staticmethod
    def _daily_report_clean_name(value: Any) -> str:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        return text[:36]

    def _daily_report_native_id(self, user_id: str) -> str:
        try:
            native = str(self._legacy_identity(str(user_id)) or "").strip()
        except Exception:
            native = str(user_id or "").strip()
        return native

    def _daily_report_canonical_id(self, event: Any, user_id: Any) -> str:
        raw = str(user_id or "").strip()
        if not raw or raw.lower() in {"all", "everyone", "@all"}:
            return ""
        try:
            canonical = str(self._canonical_user_id(event, raw) or "").strip()
        except Exception:
            canonical = ""
        return canonical or raw

    @staticmethod
    def _daily_report_platform_type(
        group: dict[str, Any], profile: dict[str, Any]
    ) -> str:
        raw = str(
            profile.get("platform_type")
            or group.get("platform_type")
            or profile.get("platform")
            or group.get("platform")
            or ""
        ).strip().lower()
        if not raw:
            return ""
        if "aiocqhttp" in raw or "onebot" in raw:
            return "aiocqhttp"
        for separator in ("|", ":", "/"):
            if separator in raw:
                parts = [part for part in raw.split(separator) if part]
                if "aiocqhttp" in parts or "onebot" in parts:
                    return "aiocqhttp"
        return raw

    def _daily_report_avatar_for_aiocqhttp(
        self, native_id: str, profile: dict[str, Any]
    ) -> str:
        del profile
        if native_id.isdigit():
            return f"https://q1.qlogo.cn/g?b=qq&nk={native_id}&s=640"
        return ""

    def _daily_report_fallback_avatar_url(
        self,
        platform_type: str,
        native_id: str,
        profile: dict[str, Any],
    ) -> str:
        platform = re.sub(r"[^a-z0-9_]", "_", str(platform_type or "").lower())
        if not platform or not native_id:
            return ""
        resolver = getattr(self, f"_daily_report_avatar_for_{platform}", None)
        if not callable(resolver):
            return ""
        try:
            url = str(resolver(native_id, profile) or "").strip()
        except Exception:
            return ""
        return url[:2048] if url.startswith("https://") else ""

    def _daily_report_profile_candidate(
        self,
        event: Any,
        obj: Any,
        *,
        platform: str,
        platform_type: str,
    ) -> tuple[str, dict[str, Any]] | None:
        if obj is None:
            return None

        raw_id = ""
        for key in self._REPORT_PROFILE_ID_KEYS:
            value = self._daily_report_profile_value(obj, key)
            if value is not None and str(value).strip():
                raw_id = str(value).strip()
                break
        canonical_id = self._daily_report_canonical_id(event, raw_id)
        if not canonical_id:
            return None

        native_id = self._daily_report_native_id(canonical_id) or raw_id
        profile: dict[str, Any] = {
            "platform": platform,
            "platform_type": platform_type,
            "native_id": native_id,
        }

        for key in self._REPORT_PROFILE_NAME_KEYS:
            name = self._daily_report_clean_name(
                self._daily_report_profile_value(obj, key)
            )
            if name and name not in {raw_id, native_id, canonical_id}:
                profile["display_name"] = name
                break

        for key in self._REPORT_PROFILE_AVATAR_KEYS:
            value = self._daily_report_profile_value(obj, key)
            try:
                url = self._url_candidate(value)
            except Exception:
                url = ""
            if url:
                profile["avatar_url"] = url[:2048]
                break

        if not profile.get("avatar_url"):
            fallback = self._daily_report_fallback_avatar_url(
                platform_type, native_id, profile
            )
            if fallback:
                profile["avatar_url"] = fallback
        return canonical_id, profile

    def _daily_report_event_profile_objects(self, event: Any) -> list[Any]:
        """Return mention/member-like objects without depending on one adapter."""
        message_obj = getattr(event, "message_obj", None)
        result: list[Any] = []

        def extend_components(value: Any) -> None:
            if value is None:
                return
            chain = getattr(value, "chain", None)
            if chain is not None and chain is not value:
                extend_components(chain)
                return
            if isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, dict):
                        kind = str(item.get("type") or "").lower()
                        data = item.get("data")
                        if kind in {"at", "mention", "user_mention", "mention_user"}:
                            result.append(data if isinstance(data, dict) else item)
                    else:
                        kind = type(item).__name__.lower()
                        if "mention" in kind or kind in {"at", "atuser", "at_user"}:
                            result.append(item)

        for value in (
            getattr(message_obj, "message", None),
            getattr(message_obj, "message_chain", None),
            getattr(event, "message_chain", None),
        ):
            extend_components(value)

        getter = getattr(event, "get_messages", None)
        if callable(getter):
            try:
                extend_components(getter())
            except Exception:
                pass

        raw = getattr(message_obj, "raw_message", None)
        if isinstance(raw, dict):
            for key in ("mentions", "mention_users", "mentioned_users"):
                value = raw.get(key)
                if isinstance(value, list):
                    result.extend(value)
            extend_components(raw.get("message"))
        return result

    def _remember_daily_report_context(
        self, event: Any, user_id: str = ""
    ) -> None:
        # Preserve the original sender-driven cache first, then enrich it with
        # target/mention profiles.  Calling super keeps this mixin independent
        # from the report feature's storage implementation.
        super()._remember_daily_report_context(event, user_id)

        try:
            group_id = str(self._event_group_id(event) or "").strip()
        except Exception:
            group_id = ""
        if not group_id:
            return

        try:
            platform = str(self._platform_namespace(event) or "").strip()
        except Exception:
            platform = ""
        try:
            platform_type = str(self._platform_type(event) or "").strip().lower()
        except Exception:
            platform_type = ""
        if not platform_type:
            platform_type = self._daily_report_platform_type(
                {"platform": platform}, {}
            )

        candidates: list[tuple[str, dict[str, Any]]] = []
        for obj in self._daily_report_event_profile_objects(event):
            candidate = self._daily_report_profile_candidate(
                event,
                obj,
                platform=platform,
                platform_type=platform_type,
            )
            if candidate:
                candidates.append(candidate)
        if not candidates and not platform_type:
            return

        now = int(time.time())
        changed = False
        with self._data_lock:
            groups = self.daily_report_state.setdefault("groups", {})
            group = groups.setdefault(group_id, {})
            if platform_type and group.get("platform_type") != platform_type:
                group["platform_type"] = platform_type
                changed = True
            members = group.setdefault("members", {})
            for canonical_id, incoming in candidates:
                profile = members.setdefault(canonical_id, {})
                before = dict(profile)
                for key in ("platform", "platform_type", "native_id", "avatar_url"):
                    value = incoming.get(key)
                    if value and not profile.get(key):
                        profile[key] = value
                incoming_name = str(incoming.get("display_name") or "").strip()
                current_name = str(profile.get("display_name") or "").strip()
                native_id = str(incoming.get("native_id") or "").strip()
                if incoming_name and (
                    not current_name
                    or current_name in {canonical_id, native_id}
                ):
                    profile["display_name"] = incoming_name
                profile["last_seen_at"] = now
                if profile != before:
                    changed = True
            if changed:
                self._save_daily_report_state_locked()

    def _profile_for_report(self, group_id: str, user_id: str) -> dict[str, Any]:
        result = dict(super()._profile_for_report(group_id, user_id))
        native_id = str(
            result.get("native_id") or self._daily_report_native_id(user_id)
        ).strip()

        with self._data_lock:
            group_raw = self.daily_report_state.get("groups", {}).get(
                str(group_id), {}
            )
            group = dict(group_raw) if isinstance(group_raw, dict) else {}
            members = group_raw.get("members", {}) if isinstance(group_raw, dict) else {}
            matched: dict[str, Any] = {}
            if isinstance(members, dict):
                exact = members.get(str(user_id), {})
                if isinstance(exact, dict):
                    matched = dict(exact)
                if not matched and native_id:
                    for member_id, candidate in members.items():
                        if not isinstance(candidate, dict):
                            continue
                        candidate_native = str(candidate.get("native_id") or "").strip()
                        if not candidate_native:
                            candidate_native = self._daily_report_native_id(str(member_id))
                        if candidate_native == native_id:
                            matched = dict(candidate)
                            break

        if matched:
            for key in (
                "platform",
                "platform_type",
                "native_id",
                "avatar_url",
            ):
                if matched.get(key):
                    result[key] = matched[key]
            matched_name = str(matched.get("display_name") or "").strip()
            current_name = str(result.get("display_name") or "").strip()
            if matched_name and (
                not current_name
                or current_name in {str(user_id), native_id}
            ):
                result["display_name"] = matched_name

        result.setdefault("platform", str(group.get("platform") or ""))
        result.setdefault("platform_type", str(group.get("platform_type") or ""))
        result["native_id"] = str(result.get("native_id") or native_id)

        if not str(result.get("avatar_url") or "").strip():
            platform_type = self._daily_report_platform_type(group, result)
            fallback = self._daily_report_fallback_avatar_url(
                platform_type,
                str(result.get("native_id") or ""),
                result,
            )
            if fallback:
                result["avatar_url"] = fallback

        return result
