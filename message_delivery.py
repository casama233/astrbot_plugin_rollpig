from __future__ import annotations


class MessageDeliveryMixin:
    """Share mention formatting and first-reply ownership across commands.

    Build standard AstrBot results through the event, so this layer does not
    depend on a platform SDK or on report/gameplay features.
    """

    def _mention_parts(self, event, user_id: str) -> tuple[str, tuple]:
        canonical_id = self._canonical_user_id(event, user_id)
        native_id = self._legacy_identity(canonical_id)
        if not native_id:
            native_id = self._legacy_identity(str(user_id or "").strip())
        if not native_id:
            return "", ()

        platform = self._platform_type(event)
        result = event.make_result()
        if platform == "slack":
            result.message(f"<@{native_id}>")
        elif platform == "telegram":
            name = self._telegram_mention_name(event, canonical_id, native_id)
            if name:
                result.message(f"@{name}")
            elif native_id.isdigit():
                result.message(f"[群友](tg://user?id={native_id})")
            else:
                result.message(f"@{native_id}")
        else:
            # Discord, OneBot, WhatsApp and the current QQ Official adapter
            # serialize the standard At segment into their native mention.
            result.at(name="", qq=native_id)
        return native_id, tuple(result.chain)

    def _mention_message(self, event, user_id: str, text: str, *, before: str = ""):
        result = event.make_result()
        if before:
            result.message(before)
        if self._event_group_id(event):
            _native_id, parts = self._mention_parts(event, user_id)
            result.chain.extend(parts)
        result.message(text)
        self._merge_adjacent_text(result)
        return result

    @staticmethod
    def _merge_adjacent_text(result) -> None:
        # MessageChain.squash_plain() also joins text across At/media segments.
        # Merge only neighbours so inline targets and image order stay intact.
        merged = []
        for part in result.chain:
            kind = getattr(getattr(part, "type", None), "value", getattr(part, "type", None))
            previous = getattr(merged[-1], "type", None) if merged else None
            previous = getattr(previous, "value", previous)
            if kind == previous == "Plain":
                merged[-1].text += part.text
            else:
                merged.append(part)
        result.chain = merged

    async def _send_with_mention(self, event, user_id: str, text: str) -> None:
        body = str(text or "").lstrip(" \t\r\n")
        if self._event_group_id(event) and body:
            body = "\n" + body
        # A failed send may already have arrived. Do not send a second textual
        # mention as a fallback after a network/adapter exception.
        await event.send(self._mention_message(event, user_id, body))

    @staticmethod
    def _result_starts_with_same_mention(result, native_id: str, parts: tuple) -> bool:
        for current in getattr(result, "chain", ()) or ():
            kind = getattr(current, "type", None)
            kind = getattr(kind, "value", kind)
            if kind == "Reply":
                continue
            if kind == "At":
                return str(getattr(current, "qq", "")) == native_id
            if kind != "Plain":
                return False
            text = str(getattr(current, "text", "") or "").lstrip()
            if not text:
                continue
            # Old callers may already supply a textual Discord mention while
            # the shared sender now uses At, or the other way around.
            tokens = [f"<@{native_id}>", f"<@!{native_id}>"]
            if parts and getattr(parts[0], "text", None):
                tokens.append(str(parts[0].text))
            return any(
                text.startswith(token)
                and (
                    token.endswith((">", ")"))
                    or len(text) == len(token)
                    or not (text[len(token)].isalnum() or text[len(token)] == "_")
                )
                for token in tokens
            )
        return False

    def _install_command_actor_header(self, event) -> None:
        if not self._event_group_id(event):
            return
        if getattr(event, "_rollpig_actor_header_installed", False):
            return
        actor_id = self._event_sender_id(event)
        native_id, parts = self._mention_parts(event, actor_id)
        if not parts:
            return
        prefix = (*parts, *event.plain_result("\n").chain)
        original_send = event.send
        header_sent = False

        async def send_with_actor_header(result):
            nonlocal header_sent
            if not header_sent and getattr(result, "chain", None) is not None:
                if not self._result_starts_with_same_mention(result, native_id, parts):
                    result.chain = [*prefix, *result.chain]
                    # Telegram sends each Plain segment separately. Keep the
                    # requester line and body together in one platform message.
                    self._merge_adjacent_text(result)
                # Claim before awaiting: an acknowledgement timeout or another
                # concurrent send must not add the requester a second time.
                header_sent = True
            return await original_send(result)

        event.send = send_with_actor_header
        setattr(event, "_rollpig_actor_header_installed", True)

    def _claim_command_event(self, event) -> None:
        super()._claim_command_event(event)
        self._install_command_actor_header(event)
