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


def test_batch_rollback_removes_newly_created_files():
    method = ast.get_source_segment(SOURCE, _method("save_json_batch")) or ""
    assert "path.unlink(missing_ok=True)" in method


def test_outbound_mentions_strip_storage_namespace():
    method = ast.get_source_segment(SOURCE, _method("_send_with_mention")) or ""
    assert "mention_id = self._legacy_identity(canonical_id)" in method
    assert "Comp.At(qq=mention_id)" in method
    assert "f\"@{mention_id}{text}\"" in method
