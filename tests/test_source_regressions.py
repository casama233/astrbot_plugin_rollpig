from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "main.py").read_text(encoding="utf-8")


def _method(name: str):
    tree = ast.parse(SOURCE)
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin")
    return next(node for node in plugin.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)


def test_timezone_does_not_use_uninitialized_self_timezone():
    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""
    assert "self._now().tzinfo" not in init
    assert "datetime.datetime.now().astimezone().tzinfo" in init


def test_daily_draw_lock_contains_no_network_awaits():
    method = _method("roll_pig")
    draw_locks = [node for node in ast.walk(method) if isinstance(node, ast.AsyncWith)]
    assert draw_locks
    for block in draw_locks:
        assert not any(isinstance(node, ast.Await) for statement in block.body for node in ast.walk(statement))


def test_dashboard_aggregation_is_offloaded():
    method = ast.get_source_segment(SOURCE, _method("page_overview")) or ""
    assert "asyncio.to_thread(self._build_overview_data)" in method


def test_pighub_preview_awaits_canvas_decode():
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    assert "try{await paintRgbaCanvas($('imagePreview')" in page


def test_claim_aware_reads_do_not_use_raw_candidates_directly():
    for name in ("_get_user_collection", "_get_daily_pig", "_get_weekly_pig", "roll_pig"):
        method = ast.get_source_segment(SOURCE, _method(name)) or ""
        assert "_user_read_candidates" in method


def test_main_delegates_persistence_to_storage_backend():
    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""
    load = ast.get_source_segment(SOURCE, _method("load_json")) or ""
    batch = ast.get_source_segment(SOURCE, _method("save_json_batch")) or ""
    assert "self.storage_manager = StorageManager" in init
    assert "self.storage = self.storage_manager.backend" in init
    assert "self.storage.load_json" in load
    assert "self.storage.save_json_batch" in batch


def test_panel_updater_keeps_csrf_and_explicit_unsigned_confirmation():
    check = ast.get_source_segment(SOURCE, _method("page_update_check")) or ""
    apply = ast.get_source_segment(SOURCE, _method("page_update_apply")) or ""
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    assert "_is_authorized_write_request" in check
    assert "_is_authorized_write_request" in apply
    assert "confirm_unsigned" in apply
    assert "window.confirm" in page
    assert "updates/apply" in page


def test_outbound_mentions_strip_storage_namespace():
    method = ast.get_source_segment(SOURCE, _method("_send_with_mention")) or ""
    assert "mention_id = self._legacy_identity(canonical_id)" in method
    assert "Comp.At(" in method
    assert "qq=mention_id" in method
    assert "name=telegram_name" in method
    assert 'platform_type in {"slack", "qq_official"}' in method
    assert "tg://user?id={mention_id}" in method


def test_instance_namespace_and_old_keys_are_kept_compatible():
    namespace = ast.get_source_segment(SOURCE, _method("_platform_namespace")) or ""
    candidates = ast.get_source_segment(SOURCE, _method("_identity_candidates")) or ""
    assert 'return f"{platform_type}@{instance}"' in namespace
    assert "pre_instance = self._pre_instance_identity(value)" in candidates


def test_invalid_reply_and_broadcast_targets_are_filtered():
    normalise = ast.get_source_segment(
        SOURCE, _method("_normalise_platform_user_id")
    ) or ""
    get_at_ids = ast.get_source_segment(SOURCE, _method("get_at_ids")) or ""
    assert '"0"' in normalise
    assert "self._is_broadcast_mention(raw_id)" in get_at_ids


def test_native_mentions_have_onebot_and_whatsapp_fallbacks():
    method = ast.get_source_segment(SOURCE, _method("_native_mention_ids")) or ""
    assert 'raw_message.get("mentionedJids")' in method
    assert 'raw_message.get("message")' in method


def test_telegram_aliases_bridge_username_and_numeric_id():
    sender = ast.get_source_segment(SOURCE, _method("_event_sender_id")) or ""
    target = ast.get_source_segment(SOURCE, _method("get_at_ids")) or ""
    assert "self._remember_sender_alias(event, canonical_id)" in sender
    assert "self._resolve_mention_user_id(event, raw_id)" in target


def test_cooldown_protection_and_backdoor_use_claimed_storage_ids():
    for name in (
        "_consume_group_roast_cooldown",
        "_record_group_roast",
        "_roast_protection_status",
        "_consume_daily_backdoor",
    ):
        method = ast.get_source_segment(SOURCE, _method(name)) or ""
        assert "self._storage_user_key" in method



def test_special_pig_copy_separates_actor_roast_and_eat_targets():
    eat = ast.get_source_segment(SOURCE, _method("_eat_group_target")) or ""
    random_eat = ast.get_source_segment(SOURCE, _method("eat_random_group_member")) or ""
    self_roast = ast.get_source_segment(SOURCE, _method("roast_today_pig")) or ""
    actor_rules = ast.get_source_segment(SOURCE, _method("_eat_actor_block_reason")) or ""
    target_rules = ast.get_source_segment(SOURCE, _method("_eat_target_block_reason")) or ""
    success_copy = ast.get_source_segment(SOURCE, _method("_eat_success_message")) or ""

    service_source = (ROOT / "services" / "roast_service.py").read_text(encoding="utf-8")

    assert "_eat_actor_block_reason(actor_pig)" in eat
    assert "_eat_target_block_reason(target_pig)" in eat
    assert "_eat_actor_block_reason(actor_pig)" in random_eat
    assert "_eat_target_block_reason(pig)" in random_eat
    assert '_roast_block_reason(pig, subject="actor")' in self_roast
    assert "self.roast_service.eat_actor_block_reason" in actor_rules
    assert "你今天是" in service_source
    assert "self.roast_service.eat_target_block_reason" in target_rules
    assert 'state in {"normal", "cooked"}' in service_source
    assert "self.roast_service.eat_success_message" in success_copy
    assert "开袋即食成功" in service_source



def test_main_uses_services_and_indexed_sql_read_boundaries():
    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""
    choose = ast.get_source_segment(SOURCE, _method("_choose_daily_pig")) or ""
    collection = ast.get_source_segment(SOURCE, _method("_get_user_collection")) or ""
    daily = ast.get_source_segment(SOURCE, _method("_get_daily_pig")) or ""
    members = ast.get_source_segment(SOURCE, _method("_daily_group_members")) or ""
    victims = ast.get_source_segment(SOURCE, _method("_daily_eaten_victims")) or ""
    assert "self.draw_service = DrawService" in init
    assert "self.roast_service = RoastService" in init
    assert "self.draw_service.choose" in choose
    assert "self.storage.get_user_collection" in collection
    assert "self.storage.get_daily_draw" in daily
    assert "self.storage.get_group_members" in members
    assert "self.storage.get_eaten_victims" in victims


def test_storage_rebuild_api_keeps_csrf_and_confirmation():
    method = ast.get_source_segment(SOURCE, _method("page_storage_rebuild")) or ""
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    assert "_is_authorized_write_request" in method
    assert 'payload.get("confirm")' in method
    assert "storage/rebuild" in page
    assert "storageRebuildBtn" in page
