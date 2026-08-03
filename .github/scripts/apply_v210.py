from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


index_path = ROOT / "pages" / "pig-manager" / "index.html"
index = index_path.read_text(encoding="utf-8")
if '<script src="./ui-feedback.js"></script>' not in index:
    index = replace_once(
        index,
        '<script src="/api/plugin/page/bridge-sdk.js"></script>\n',
        '<script src="/api/plugin/page/bridge-sdk.js"></script>\n'
        '<script src="./ui-feedback.js"></script>\n',
        "dashboard feedback script",
    )
index_path.write_text(index, encoding="utf-8")

changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
if "## v2.9.3 (2026-08-04)" not in changelog:
    anchor = "## v2.9.2 (2026-08-04)\n"
    section = (
        "## v2.9.3 (2026-08-04)\n"
        "### 管理面板操作反馈与待重启保护\n"
        "- 修复安全更新后页面文件已替换、但 AstrBot 尚未重启时，新页面请求旧后端路由并只显示“未找到该路由”的问题；现在会明确提示页面／运行时版本不一致并要求重启。\n"
        "- 新增醒目的“等待重启”横幅；待重启期间禁用迁移、验证、重建、导出、回滚、同步与更新按钮。\n"
        "- 管理操作显示独立按钮状态、执行阶段、已等待时间与耗时；v2.10 新增的投影重建也纳入同一反馈和互斥机制。\n\n"
    )
    changelog = replace_once(changelog, anchor, section + anchor, "v2.9.3 changelog")
changelog_path.write_text(changelog, encoding="utf-8")

tests_path = ROOT / "tests" / "test_source_regressions.py"
tests = tests_path.read_text(encoding="utf-8")
marker = "def test_dashboard_feedback_covers_restart_and_projection_rebuild"
if marker not in tests:
    tests += '''


def test_dashboard_feedback_covers_restart_and_projection_rebuild():
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    feedback = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(
        encoding="utf-8"
    )
    assert '<script src="./ui-feedback.js"></script>' in page
    assert "storageRebuildBtn" in feedback
    assert "'storage/rebuild'" in feedback
    assert "restartRequired" in feedback
    assert "已有管理任务正在执行" in feedback
'''
tests_path.write_text(tests, encoding="utf-8")

print("v2.10 final synchronization applied")
