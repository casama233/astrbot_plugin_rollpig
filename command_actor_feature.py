from __future__ import annotations

import astrbot.api.message_components as Comp

try:
    from .daily_report_profile_feature import DailyReportProfileMixin
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_profile_feature import DailyReportProfileMixin


class CommandActorMentionMixin(DailyReportProfileMixin):
    """Add one requester mention header to the first reply of every group command.

    Gameplay target mentions remain part of the original response chain.  This
    wrapper only identifies who triggered the command, and it deliberately does
    nothing in private chats.

    ``DailyReportProfileMixin`` sits here deliberately because this mixin is
    already first in the plugin MRO.  That lets report profile hydration wrap
    ``DailyReportMixin`` without changing command registration or the historical
    entry-point inheritance order.
    """

    def _command_actor_mention_prefix(self, event, actor_id: str) -> tuple:
        canonical_id = self._canonical_user_id(event, actor_id)
        mention_id = self._legacy_identity(canonical_id)
        if not mention_id:
            mention_id = self._legacy_identity(str(actor_id or "").strip())
        if not mention_id:
            return ()

        platform_type = self._platform_type(event)
        telegram_name = (
            self._telegram_mention_name(event, canonical_id, mention_id)
            if platform_type == "telegram"
            else ""
        )

        if platform_type in {"discord", "slack", "qq_official"}:
            return (Comp.Plain(f"<@{mention_id}>\n"),)
        if platform_type == "telegram":
            if telegram_name:
                return (Comp.Plain(f"@{telegram_name}\n"),)
            if mention_id.isdigit():
                return (Comp.Plain(f"[群友](tg://user?id={mention_id})\n"),)
            return (Comp.Plain(f"@{mention_id}\n"),)
        return (
            Comp.At(qq=mention_id, name=telegram_name),
            Comp.Plain("\n"),
        )

    @staticmethod
    def _result_starts_with_same_mention(result, prefix: tuple) -> bool:
        chain = list(getattr(result, "chain", None) or [])
        if not chain or not prefix:
            return False

        current = chain[0]
        expected = prefix[0]
        if isinstance(current, Comp.At) and isinstance(expected, Comp.At):
            return str(getattr(current, "qq", "")) == str(
                getattr(expected, "qq", "")
            )
        if isinstance(current, Comp.Plain) and isinstance(expected, Comp.Plain):
            token = str(getattr(expected, "text", "") or "").rstrip("\r\n")
            return bool(token) and str(getattr(current, "text", "") or "").startswith(
                token
            )
        return False

    def _install_command_actor_header(self, event) -> None:
        if not self._event_group_id(event):
            return
        if getattr(event, "_rollpig_actor_header_installed", False):
            return

        actor_id = self._event_sender_id(event)
        prefix = self._command_actor_mention_prefix(event, actor_id)
        if not prefix:
            return

        original_send = event.send
        header_sent = False

        async def send_with_actor_header(result):
            nonlocal header_sent
            decorated = False
            if not header_sent:
                chain = getattr(result, "chain", None)
                if chain is not None:
                    chain = list(chain or [])
                    if not self._result_starts_with_same_mention(result, prefix):
                        result.chain = [*prefix, *chain]
                    decorated = True

            response = await original_send(result)
            if decorated:
                header_sent = True
            return response

        event.send = send_with_actor_header
        setattr(event, "_rollpig_actor_header_installed", True)

    def _claim_command_event(self, event) -> None:
        super()._claim_command_event(event)
        self._install_command_actor_header(event)
