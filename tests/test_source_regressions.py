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



def test_dashboard_feedback_covers_restart_and_projection_rebuild():
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    feedback = (ROOT / "pages" / "pig-manager" / "ui-feedback-core.js").read_text(
        encoding="utf-8"
    )
    assert '<script src="./ui-feedback.js?v=3.0.5"></script>' in page
    assert "rollpig-inline-assets:start" not in page
    assert "storageRebuildBtn" in feedback
    assert "'storage/rebuild'" in feedback
    assert "restartRequired" in feedback
    assert "已有管理任务正在执行" in feedback


def test_main_delegates_sql_primary_hot_writes():
    assert 'supports_domain_writes' in SOURCE
    assert 'self.storage.create_daily_draw' in SOURCE
    assert 'self.storage.replace_daily_pig_with_eaten' in SOURCE
    assert 'await self._replace_today_with_eaten_persisted' in SOURCE



def test_identity_metadata_uses_sql_merge_in_sqlite_mode():
    claim = ast.get_source_segment(SOURCE, _method("_claim_legacy_identity")) or ""
    alias = ast.get_source_segment(SOURCE, _method("_remember_sender_alias")) or ""
    assert "self.storage.claim_legacy_identity" in claim
    assert "self.storage.remember_identity_alias" in alias



def test_main_delegates_v212_sql_hot_writes():
    cooldown = ast.get_source_segment(SOURCE, _method("_consume_group_roast_cooldown")) or ""
    counts = ast.get_source_segment(SOURCE, _method("_record_group_roast")) or ""
    protection = ast.get_source_segment(SOURCE, _method("_roast_protection_status")) or ""
    backdoor = ast.get_source_segment(SOURCE, _method("_consume_daily_backdoor")) or ""
    ai = ast.get_source_segment(SOURCE, _method("_get_ai_roast_copy")) or ""
    save = ast.get_source_segment(SOURCE, _method("_persist_catalog_override")) or ""
    delete = ast.get_source_segment(SOURCE, _method("_persist_catalog_delete")) or ""
    assert "asyncio.to_thread" in cooldown and "consume_roast_cooldown" in cooldown
    assert "asyncio.to_thread" in counts and "increment_roast_count" in counts
    assert "get_roast_count" in protection
    assert "consume_daily_backdoor" in backdoor
    assert "claim_ai_roast_generation" in ai and "complete_ai_roast_generation" in ai
    assert "upsert_catalog_override" in save
    assert "delete_catalog_entry" in delete


def test_catalog_image_changes_are_compensated_on_metadata_failure():
    save = ast.get_source_segment(SOURCE, _method("_persist_catalog_override")) or ""
    delete = ast.get_source_segment(SOURCE, _method("_persist_catalog_delete")) or ""
    assert save.index("_write_custom_image") < save.index("upsert_catalog_override")
    assert "except Exception:" in save
    assert "_restore_custom_images" in save
    assert delete.index("unlink") < delete.index("delete_catalog_entry")
    assert "_restore_custom_images" in delete



def test_v213_runtime_uses_sql_snapshot_and_unique_ai_generation_claim():
    init = ast.get_source_segment(SOURCE, _method("__init__")) or ""
    ai = ast.get_source_segment(SOURCE, _method("_get_ai_roast_copy")) or ""
    assert "self.storage.load_runtime_snapshot()" in init
    assert "self._runtime_document" in init
    assert "claim_ai_roast_generation" in ai
    assert "complete_ai_roast_generation" in ai
    assert "uuid.uuid4().hex" in ai
    assert "random.choice(list(recent.values()))" in ai



def test_v213_sql_authority_repairs_documents_in_the_safe_direction():
    storage_source = (ROOT / "storage" / "sqlite_storage.py").read_text(
        encoding="utf-8"
    )
    assert 'authority.startswith("sql-primary-")' in storage_source
    assert "_repair_compatibility_documents_tx" in storage_source
    assert 'action = "repaired-compatibility-documents-from-sql"' in storage_source
    assert "history = self._history_document_from_sql(connection)" in storage_source
    assert "roast = self._roast_document_from_sql(connection)" in storage_source
    assert "today_doc = self._today_document_from_sql(connection, draw_date)" in storage_source



def test_v214_dashboard_uses_sql_analytics_and_exposes_repair_status():
    overview = ast.get_source_segment(SOURCE, _method("_build_overview_data")) or ""
    storage_source = (ROOT / "storage" / "sqlite_storage.py").read_text(
        encoding="utf-8"
    )
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "supports_dashboard_analytics" in overview
    assert "get_dashboard_overview" in overview
    assert "COUNT(DISTINCT user_id)" in storage_source
    assert "idx_daily_draws_date_pig" in storage_source
    assert "last_repair_reason" in storage_source
    assert "sql-primary-v2.14" in storage_source
    assert "统计 SQL" in page
    assert "写入权威" in page
    assert "最近修复" in page


def test_v3_release_contract_uses_sql_single_authority_and_on_demand_json():
    primary = (ROOT / "storage" / "sqlite_primary.py").read_text(encoding="utf-8")
    manager = (ROOT / "storage" / "primary_manager.py").read_text(encoding="utf-8")
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    config = (ROOT / "_conf_schema.json").read_text(encoding="utf-8")
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'version: "3.0.5"' in metadata
    assert "AstrBot-RollPig/3.0.5" in SOURCE
    assert "sql-primary-v3.0" in primary
    assert '"compatibility_mode": "on-demand"' in primary
    assert 'connection.execute("DELETE FROM documents")' in primary
    assert "RUNTIME_MANAGED_PATHS" in manager
    assert "新安装直接建立 SQLite" in config
    assert "兼容 JSON" in page
    assert "按需生成" in page

