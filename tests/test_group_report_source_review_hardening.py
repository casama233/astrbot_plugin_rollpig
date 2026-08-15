from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_daily_report_scheduler_is_per_group_opt_in():
    source = (ROOT / "daily_report_feature.py").read_text(encoding="utf-8")
    assert 'group.setdefault("auto_enabled", False)' in source
    assert 'and bool(value.get("auto_enabled", False))' in source
    assert 'auto_enabled_since' in source
    assert 'date_key < enabled_since' in source
    assert 'day_end = datetime.datetime.combine' in source


def test_daily_report_command_exposes_group_controls_from_main_entrypoint():
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin"
    )
    fn = next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "pigsty_daily_report"
    )
    assert [arg.arg for arg in fn.args.args][-1] == "args"
    source = (ROOT / "daily_report_feature.py").read_text(encoding="utf-8")
    for word in ("开启", "关闭", "状态", "只有 AstrBot 管理员"):
        assert word in source
    manager_start = source.index("    def _daily_report_group_manager")
    manager_end = source.index("    def _daily_report_group_auto_enabled", manager_start)
    manager = source[manager_start:manager_end]
    assert "self._is_admin_id(event, actor_id)" in manager
    assert "sender.role" not in manager
    assert "raw_message" not in manager
    assert "owner" not in manager


def test_review_image_uses_astrbot_query_and_sensitive_get_csrf():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    assert 'submission_id = str(request.query.get("id") or "").strip()' in source
    assert 'request.args.get("id")' not in source
    assert 'query.get("__rollpig_csrf"' in source
    html = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    assert "source/reviews/image',{id:submissionId,__rollpig_csrf:csrfToken}" in html
    assert "source/reviews',{__rollpig_csrf:csrfToken}" in html
