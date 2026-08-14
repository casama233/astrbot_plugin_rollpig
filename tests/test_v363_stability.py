from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_daily_report_handler_uses_live_instance_sender_dispatch():
    tree = ast.parse((ROOT / "daily_report_feature.py").read_text(encoding="utf-8"))
    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "pigsty_daily_report":
            target = node
            break
    assert target is not None
    calls = [node for node in ast.walk(target) if isinstance(node, ast.Call)]
    dotted = []
    for call in calls:
        func = call.func
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                dotted.append(f"{func.value.id}.{func.attr}")
            elif isinstance(func.value, ast.Call) and isinstance(func.value.func, ast.Name):
                dotted.append(f"{func.value.func.id}().{func.attr}")
    assert "self._event_sender_id" in dotted
    assert "super()._event_sender_id" not in dotted
    # _event_sender_id already records the report context; a second explicit write
    # would duplicate work and preserve the reload-sensitive call path.
    assert "self._remember_daily_report_context" not in dotted


def test_v363_keeps_permanent_collection_read_model_in_entry_mro():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "from .permanent_collection_feature import PermanentCollectionMixin" in source
    assert "PermanentCollectionMixin," in source
    permanent = (ROOT / "permanent_collection_feature.py").read_text(encoding="utf-8")
    assert "active draw/search catalog" in permanent
    assert "unlocked historical snapshots" in permanent


def test_v363_does_not_ship_unreviewed_identity_fragment_merge():
    # PR #68 is intentionally not part of this emergency patch. Identity-fragment
    # recovery needs claim-aware end-to-end tests before it can affect pity/EX state.
    core = (ROOT / "rollpig_core.py").read_text(encoding="utf-8")
    assert "merge_user_collection_fragments" not in core
    assert "claimed_identity_candidates" not in core
