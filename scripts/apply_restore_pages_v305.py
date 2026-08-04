from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.5"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_required(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one {old!r}, found {count}")
    write(path, text.replace(old, new, 1))


# Restore the last known lightweight, working page. The external enhancement loader
# is intentionally removed because AstrBot's authenticated page transport does not
# attach authorization headers to browser subresource requests.
page = subprocess.check_output(
    ["git", "show", "v3.0.3:pages/pig-manager/index.html"],
    cwd=ROOT,
    text=True,
    encoding="utf-8",
)
page, removed = re.subn(
    r'\n?<script\s+src="\./ui-feedback\.js\?v=3\.0\.3"></script>\n?',
    "\n",
    page,
    count=1,
)
if removed != 1:
    raise SystemExit("v3.0.3 page loader anchor was not found")
if "rollpig-inline-assets:start" in page:
    raise SystemExit("restored page unexpectedly contains v3.0.4 inline bundle")
write("pages/pig-manager/index.html", page)

replace_required("metadata.yaml", 'version: "3.0.4"', f'version: "{VERSION}"')
replace_required("main.py", "AstrBot-RollPig/3.0.4", f"AstrBot-RollPig/{VERSION}")
replace_required(
    "updater.py",
    "AstrBot-RollPig-Safe-Updater/3.0.4",
    f"AstrBot-RollPig-Safe-Updater/{VERSION}",
)

feedback_loader = read("pages/pig-manager/ui-feedback.js").replace(
    "const ASSET_VERSION = '3.0.4'", f"const ASSET_VERSION = '{VERSION}'"
)
feedback_loader = feedback_loader.replace("?v=3.0.4", f"?v={VERSION}")
write("pages/pig-manager/ui-feedback.js", feedback_loader)

analytics = read("pages/pig-manager/ui-analytics.js").replace(
    "const BOOTSTRAP_VERSION = '3.0.4'", f"const BOOTSTRAP_VERSION = '{VERSION}'"
)
write("pages/pig-manager/ui-analytics.js", analytics)

changelog = read("CHANGELOG.md")
entry = (
    f"## v{VERSION} (2026-08-04)\n"
    "### 紧急恢复附属页面可用性\n"
    "- 撤回 v3.0.4 将数千行 CSS/JavaScript 内联进管理页的高风险方案，恢复最后已知可正常加载的轻量页面。\n"
    "- 移除会返回 401 的相对增强资源请求；基础总览、图鉴、同步、SQLite 管理与安全更新继续可用。\n"
    "- 企业增强主题与深度 Analytics 暂时停用，待通过真实 AstrBot 浏览器集成验证后再恢复。\n"
    "- 不修改 SQLite 数据、API 数据结构、抽猪规则或其他业务流程。\n\n"
)
if entry not in changelog:
    if not changelog.startswith("# 更新\n"):
        raise SystemExit("CHANGELOG.md heading missing")
    changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
write("CHANGELOG.md", changelog)

# Keep version contracts consistent.
for path in ROOT.glob("tests/*"):
    if not path.is_file() or path.suffix not in {".py", ".js", ".cjs"}:
        continue
    text = path.read_text(encoding="utf-8").replace("3.0.4", VERSION)
    path.write_text(text, encoding="utf-8")

old_contract = ROOT / "tests/test_v304_release_contract.py"
new_contract = ROOT / "tests/test_v305_release_contract.py"
if old_contract.exists():
    old_contract.rename(new_contract)
if new_contract.exists():
    text = new_contract.read_text(encoding="utf-8")
    text = text.replace("test_v304_", "test_v305_")
    text = re.sub(
        r'\n\s*assert "data-rollpig-feedback-core" in page\n'
        r'\s*assert "data-rollpig-enterprise-ui" in page\n'
        r'\s*assert "data-rollpig-analytics-ui" in page\n'
        r'\s*assert \'src="\./ui-feedback\.js\' not in page',
        '\n    assert "rollpig-inline-assets:start" not in page\n'
        '    assert \'src="./ui-feedback.js\' not in page',
        text,
        count=1,
    )
    new_contract.write_text(text, encoding="utf-8")

write(
    "tests/test_ui_cache_busting.py",
    '''from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.5"
PAGE = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "pages/pig-manager/ui-feedback.js").read_text(encoding="utf-8")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.ids: set[str] = set()
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts += 1
        for key, value in attrs:
            if key == "id" and value:
                self.ids.add(value)


def test_admin_page_is_lightweight_parseable_and_keeps_core_views():
    parser = PageParser()
    parser.feed(PAGE)
    parser.close()
    assert len(PAGE.encode("utf-8")) < 500_000
    assert {"view-overview", "view-catalog", "refreshBtn", "storageStatus", "updateStatus"} <= parser.ids
    assert parser.scripts >= 2


def test_page_does_not_load_protected_relative_enhancement_assets():
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', PAGE)
    assert scripts == ["/api/plugin/page/bridge-sdk.js"]
    assert "rollpig-inline-assets:start" not in PAGE
    assert 'src="./ui-feedback.js' not in PAGE
    for asset in (
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
        "enterprise-theme.css",
        "analytics-theme.css",
    ):
        assert f'src="./{asset}' not in PAGE
        assert f'href="./{asset}' not in PAGE


def test_modular_enhancement_sources_remain_versioned_but_are_not_bootstrapped():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
''',
)

dashboard_path = ROOT / "tests/test_dashboard_feedback.py"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = re.sub(
    r"def test_feedback_layer_loads_before_inline_module\(\):\n.*?\n\ndef test_feedback_layer_explains_stale_runtime_routes",
    '''def test_feedback_layer_is_kept_as_a_maintenance_source_only():
    bridge = '<script src="/api/plugin/page/bridge-sdk.js"></script>'
    assert bridge in PAGE
    assert 'src="./ui-feedback.js' not in PAGE
    assert "rollpig-inline-assets:start" not in PAGE
    assert "./ui-feedback-core.js" in LOADER
    assert "./ui-enterprise.js" in LOADER
    assert "./ui-analytics.js" in LOADER


def test_feedback_layer_explains_stale_runtime_routes''',
    dashboard,
    count=1,
    flags=re.S,
)
dashboard_path.write_text(dashboard, encoding="utf-8")

source_path = ROOT / "tests/test_source_regressions.py"
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    '    assert "data-rollpig-feedback-core" in page\n'
    '    assert "data-rollpig-analytics-ui" in page\n'
    '    assert \'src="./ui-feedback.js\' not in page\n',
    '    assert "rollpig-inline-assets:start" not in page\n'
    '    assert \'src="./ui-feedback.js\' not in page\n',
    1,
)
source_path.write_text(source, encoding="utf-8")

for temporary in (
    ROOT / "scripts/apply_restore_pages_v305.py",
    ROOT / ".github/workflows/apply-restore-pages-v305.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.0.5 emergency page restore applied")
