from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "command_actor_feature.py"
MAIN = ROOT / "main.py"


def _method(source: str, class_name: str, method_name: str):
    tree = ast.parse(source)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
    )


def test_main_installs_actor_mention_mixin_before_gameplay_mixins():
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )
    bases = [ast.unparse(base) for base in cls.bases]

    assert "CommandActorMentionMixin" in bases
    assert bases.index("CommandActorMentionMixin") < bases.index("ReservationFirewoodMixin")
    assert "from .command_actor_feature import CommandActorMentionMixin" in source
    assert "from command_actor_feature import CommandActorMentionMixin" in source


def test_claim_hook_installs_actor_header_after_stopping_command_fallthrough():
    source = FEATURE.read_text(encoding="utf-8")
    method = _method(source, "CommandActorMentionMixin", "_claim_command_event")
    method_source = ast.get_source_segment(source, method) or ""

    assert "super()._claim_command_event(event)" in method_source
    assert "self._install_command_actor_header(event)" in method_source


def test_actor_header_wraps_first_group_reply_and_preserves_original_chain():
    source = FEATURE.read_text(encoding="utf-8")

    assert "if not self._event_group_id(event):" in source
    assert "_rollpig_actor_header_installed" in source
    assert "actor_id = self._event_sender_id(event)" in source
    assert "original_send = event.send" in source
    assert "event.send = send_with_actor_header" in source
    assert "result.chain = [*prefix, *chain]" in source
    assert "header_sent = True" in source


def test_existing_actor_mention_is_not_duplicated_and_target_mentions_survive():
    source = FEATURE.read_text(encoding="utf-8")

    assert "_result_starts_with_same_mention" in source
    assert "isinstance(current, Comp.At)" in source
    assert "isinstance(current, Comp.Plain)" in source
    assert "if not self._result_starts_with_same_mention(result, prefix):" in source


def test_actor_header_uses_native_mentions_with_cross_platform_fallbacks():
    source = FEATURE.read_text(encoding="utf-8")

    assert 'platform_type in {"discord", "slack", "qq_official"}' in source
    assert 'platform_type == "telegram"' in source
    assert "Comp.At(qq=mention_id, name=telegram_name)" in source
    assert 'Comp.Plain("\\n")' in source
