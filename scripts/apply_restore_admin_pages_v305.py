from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.5"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one occurrence of {old!r}, found {count}")
    write(path, text.replace(old, new, 1))


replace_once("metadata.yaml", 'version: "3.0.4"', f'version: "{VERSION}"')
replace_once("main.py", "AstrBot-RollPig/3.0.4", f"AstrBot-RollPig/{VERSION}")

updater = read("updater.py")
updater, count = re.subn(
    r"AstrBot-RollPig-Safe-Updater/\d+\.\d+\.\d+",
    f"AstrBot-RollPig-Safe-Updater/{VERSION}",
    updater,
    count=1,
)
if count != 1:
    raise SystemExit("updater.py: updater User-Agent not found")
write("updater.py", updater)

page_path = "pages/pig-manager/index.html"
page = read(page_path)
if "rollpig-inline-assets:start" in page or "data-rollpig-analytics-ui" in page:
    raise SystemExit("index.html: v3.0.4 inline bundle still present")
page, count = re.subn(
    r'<script src="\./ui-feedback\.js\?v=[^"]+"></script>',
    f'<script src="./ui-feedback.js?v={VERSION}"></script>',
    page,
    count=1,
)
if count != 1:
    raise SystemExit("index.html: external feedback loader anchor not found")
write(page_path, page)

loader_path = "pages/pig-manager/ui-feedback.js"
loader = read(loader_path)
loader, count = re.subn(
    r"const ASSET_VERSION = '[^']+'",
    f"const ASSET_VERSION = '{VERSION}'",
    loader,
    count=1,
)
if count != 1:
    raise SystemExit("ui-feedback.js: ASSET_VERSION not found")
loader = re.sub(r"\?v=\d+\.\d+\.\d+", f"?v={VERSION}", loader)
write(loader_path, loader)

analytics_path = "pages/pig-manager/ui-analytics.js"
analytics = read(analytics_path)
analytics, count = re.subn(
    r"const BOOTSTRAP_VERSION = '[^']+'",
    f"const BOOTSTRAP_VERSION = '{VERSION}'",
    analytics,
    count=1,
)
if count != 1:
    raise SystemExit("ui-analytics.js: BOOTSTRAP_VERSION not found")
write(analytics_path, analytics)

changelog = read("CHANGELOG.md")
entry = (
    f"## v{VERSION} (2026-08-04)\n"
    "### 管理页可用性紧急恢复\n"
    "- 回退 v3.0.4 将企业主题与 Analytics 整体内联到主 HTML 的方案；该方案会导致今日小猪插件内部视图只剩顶部导航、主体无法激活。\n"
    "- 恢复 v3.0.3 已验证可用的轻量页面骨架，优先保证数据总览、猪猪图鉴、同步、存储和安全更新页面可打开。\n"
    "- 深度 Analytics 暂时降级，不再以牺牲管理页面可用性为代价加载。\n"
    "- 新增页面体积、视图锚点、主模块语法和禁止整页内联的回归检查。\n\n"
)
if entry not in changelog:
    if not changelog.startswith("# 更新\n"):
        raise SystemExit("CHANGELOG.md: heading missing")
    changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
write("CHANGELOG.md", changelog)

write(
    "tests/test_ui_cache_busting.py",
    '''from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.5"
PAGE = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(encoding="utf-8")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.scripts: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "script":
            self.scripts.append(values)


def test_admin_page_stays_lightweight_and_keeps_all_internal_views():
    assert len(PAGE.encode("utf-8")) < 300_000
    assert "rollpig-inline-assets:start" not in PAGE
    assert "data-rollpig-analytics-ui" not in PAGE
    parser = PageParser()
    parser.feed(PAGE)
    for element_id in (
        "view-overview",
        "view-catalog",
        "refreshBtn",
        "storageStatus",
        "updateStatus",
        "pigGrid",
    ):
        assert element_id in parser.ids


def test_external_enhancement_loader_cannot_block_the_main_module():
    loader = f'<script src="./ui-feedback.js?v={VERSION}"></script>'
    assert loader in PAGE
    assert PAGE.index(loader) < PAGE.index('<script type="module">')
    assert "const bridge=window.AstrBotPluginPage" in PAGE
    assert "loadOverview" in PAGE
    assert "loadPigs" in PAGE


def test_loader_versions_maintenance_assets():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
    for asset in (
        "enterprise-theme.css",
        "analytics-theme.css",
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert asset in LOADER


def test_main_module_is_extractable_for_node_syntax_validation():
    match = re.search(r'<script type="module">(.*?)</script>', PAGE, re.S)
    assert match and match.group(1).strip()
''',
)

dashboard_path = ROOT / "tests/test_dashboard_feedback.py"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = re.sub(
    r"def test_feedback_layer_loads_before_inline_module\(\):\n.*?\n\ndef test_feedback_layer_explains_stale_runtime_routes",
    '''def test_feedback_layer_loads_before_inline_module():
    external = '<script src="./ui-feedback.js?v=3.0.5"></script>'
    assert external in PAGE
    assert PAGE.index(external) < PAGE.index('<script type="module">')
    assert "./ui-feedback-core.js" in LOADER
    assert "./ui-enterprise.js" in LOADER
    assert "./ui-analytics.js" in LOADER
    assert "rollpig-inline-assets:start" not in PAGE


def test_feedback_layer_explains_stale_runtime_routes''',
    dashboard,
    count=1,
    flags=re.S,
)
if "3.0.5" not in dashboard:
    raise SystemExit("test_dashboard_feedback.py: loader contract replacement failed")
dashboard_path.write_text(dashboard, encoding="utf-8")

source_path = ROOT / "tests/test_source_regressions.py"
source = source_path.read_text(encoding="utf-8")
source = re.sub(
    r"def test_dashboard_feedback_covers_restart_and_projection_rebuild\(\):\n.*?\n\ndef test_main_delegates_sql_primary_hot_writes",
    '''def test_dashboard_feedback_covers_restart_and_projection_rebuild():
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


def test_main_delegates_sql_primary_hot_writes''',
    source,
    count=1,
    flags=re.S,
)
if "3.0.5" not in source:
    raise SystemExit("test_source_regressions.py: page contract replacement failed")
source_path.write_text(source, encoding="utf-8")

old_contract = ROOT / "tests/test_v304_release_contract.py"
old_contract.unlink(missing_ok=True)
write(
    "tests/test_v305_release_contract.py",
    '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v305_release_contract_restores_admin_page_availability():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
    loader = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(encoding="utf-8")
    assert 'version: "3.0.5"' in metadata
    assert 'AstrBot-RollPig/3.0.5' in main
    assert 'AstrBot-RollPig-Safe-Updater/3.0.5' in updater
    assert '/analytics/insights' in main
    assert '<script src="./ui-feedback.js?v=3.0.5"></script>' in page
    assert '<script type="module">' in page
    assert 'id="view-overview"' in page
    assert 'id="view-catalog"' in page
    assert "rollpig-inline-assets:start" not in page
    assert "const ASSET_VERSION = '3.0.5'" in loader
''',
)

spa_path = ROOT / "tests/test_analytics_spa_remount.py"
if spa_path.exists():
    spa = spa_path.read_text(encoding="utf-8")
    spa = re.sub(r"3\.0\.[0-9]+", VERSION, spa)
    spa_path.write_text(spa, encoding="utf-8")

for temporary in (
    ROOT / "scripts/apply_restore_admin_pages_v305.py",
    ROOT / ".github/workflows/apply-restore-admin-pages-v305.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.0.5 admin page recovery applied")
