from __future__ import annotations

import ast
from pathlib import Path

from source_service.app import _duplicate_hints, _image_dhash, _name_key

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
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RollPigPlugin")
    fn = next(node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "pigsty_daily_report")
    assert [arg.arg for arg in fn.args.args][-1] == "args"
    source = (ROOT / "daily_report_feature.py").read_text(encoding="utf-8")
    for word in ("开启", "关闭", "状态", "群主、群管理员或 AstrBot 管理员"):
        assert word in source


def test_review_image_uses_astrbot_query_and_sensitive_get_csrf():
    source = (ROOT / "legacy_main.py").read_text(encoding="utf-8")
    assert 'submission_id = str(request.query.get("id") or "").strip()' in source
    assert 'request.args.get("id")' not in source
    assert 'query.get("__rollpig_csrf"' in source
    html = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    assert "source/reviews/image',{id:submissionId,__rollpig_csrf:csrfToken}" in html
    assert "source/reviews',{__rollpig_csrf:csrfToken}" in html


def test_duplicate_hints_find_name_and_visual_similarity():
    from PIL import Image
    import io

    image = Image.new("RGB", (32, 32), "white")
    for x in range(16):
        for y in range(32):
            image.putpixel((x, y), (0, 0, 0))
    buf = io.BytesIO()
    image.save(buf, "PNG")
    raw = buf.getvalue()
    index = [{"id": "old-pig", "name": "测试猪", "name_key": _name_key("测试猪"), "image_dhash": _image_dhash(raw)}]
    hints = _duplicate_hints({"name": "测试豬"}, raw, index)
    assert hints and hints[0]["id"] == "old-pig"
    assert "名称相同" in hints[0]["reasons"]
    assert any("图片相似" in reason for reason in hints[0]["reasons"])


def test_review_service_has_global_pending_ceiling_and_hardened_unit():
    source = (ROOT / "source_service/app.py").read_text(encoding="utf-8")
    assert "MAX_PENDING_TOTAL = 200" in source
    assert "待审核队列已满" in source
    unit = (ROOT / "deploy/rollpig-source-review.service").read_text(encoding="utf-8")
    for directive in ("PrivateDevices=true", "ProtectHome=true", "ProtectKernelTunables=true", "MemoryDenyWriteExecute=true"):
        assert directive in unit


def test_review_duplicate_index_is_cached_by_catalog_revision():
    source = (ROOT / "source_service/app.py").read_text(encoding="utf-8")
    assert "_duplicate_index_cache_key" in source
    assert "stat.st_mtime_ns" in source
    assert "get_flattened_data" in source
