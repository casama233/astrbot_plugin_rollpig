from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.4"
START = "<!-- rollpig-inline-assets:start -->"
END = "<!-- rollpig-inline-assets:end -->"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_required(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text and old not in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one occurrence of {old!r}, found {count}")
    write(path, text.replace(old, new, 1))


def safe_script(source: str) -> str:
    return source.replace("</script", "<\\/script")


replace_required("metadata.yaml", 'version: "3.0.3"', f'version: "{VERSION}"')
replace_required("main.py", "AstrBot-RollPig/3.0.3", f"AstrBot-RollPig/{VERSION}")
replace_required(
    "updater.py",
    "AstrBot-RollPig-Safe-Updater/3.0.3",
    f"AstrBot-RollPig-Safe-Updater/{VERSION}",
)

loader = read("pages/pig-manager/ui-feedback.js")
loader = loader.replace("const ASSET_VERSION = '3.0.3'", f"const ASSET_VERSION = '{VERSION}'")
loader = loader.replace("?v=3.0.3", f"?v={VERSION}")
write("pages/pig-manager/ui-feedback.js", loader)

analytics = read("pages/pig-manager/ui-analytics.js").replace(
    "const BOOTSTRAP_VERSION = '3.0.3'",
    f"const BOOTSTRAP_VERSION = '{VERSION}'",
)
write("pages/pig-manager/ui-analytics.js", analytics)

enterprise_css = read("pages/pig-manager/enterprise-theme.css")
analytics_css = read("pages/pig-manager/analytics-theme.css")
feedback_core = safe_script(read("pages/pig-manager/ui-feedback-core.js"))
enterprise_js = safe_script(read("pages/pig-manager/ui-enterprise.js"))
analytics_js = safe_script(read("pages/pig-manager/ui-analytics.js"))

bundle = "\n".join(
    [
        START,
        f'<style data-rollpig-enterprise-theme data-version="{VERSION}">',
        enterprise_css,
        "</style>",
        f'<style data-rollpig-analytics-theme data-version="{VERSION}">',
        analytics_css,
        "</style>",
        f'<script data-rollpig-feedback-core data-version="{VERSION}">',
        feedback_core,
        "</script>",
        f'<script data-rollpig-enterprise-ui data-version="{VERSION}">',
        enterprise_js,
        "</script>",
        f'<script data-rollpig-analytics-ui data-version="{VERSION}">',
        analytics_js,
        "</script>",
        END,
    ]
)

index_path = ROOT / "pages/pig-manager/index.html"
index = index_path.read_text(encoding="utf-8")
if START in index and END in index:
    index = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _match: bundle,
        index,
        count=1,
        flags=re.S,
    )
else:
    pattern = re.compile(r'<script\s+src="\./ui-feedback\.js\?v=[^"]+"></script>')
    index, count = pattern.subn(lambda _match: bundle, index, count=1)
    if count != 1:
        raise SystemExit("index.html: external ui-feedback loader anchor not found")
index_path.write_text(index, encoding="utf-8")

changelog = read("CHANGELOG.md")
entry = (
    f"## v{VERSION} (2026-08-04)\n"
    "### 管理页受保护资源加载修复\n"
    "- 修复 AstrBot 通过认证 API 注入插件页面时，相对脚本与样式子资源无法携带授权头而返回 401 的问题。\n"
    "- 企业主题、交互反馈和深度 Analytics 现在直接内联进主页面，不再请求受保护的 `page/content` 子资源。\n"
    "- 保留模块化 CSS/JS 源文件作为维护来源，并新增构建一致性测试，防止发布包重新引入外部受保护资源。\n"
    "- 不修改 Analytics API、SQLite 单一权威、数据结构或业务流程。\n\n"
)
if entry not in changelog:
    if not changelog.startswith("# 更新\n"):
        raise SystemExit("CHANGELOG.md: missing heading")
    changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
write("CHANGELOG.md", changelog)

# Update versioned contracts first.
for path in ROOT.glob("tests/*"):
    if not path.is_file() or path.suffix not in {".py", ".cjs", ".js"}:
        continue
    text = path.read_text(encoding="utf-8").replace("3.0.3", VERSION)
    path.write_text(text, encoding="utf-8")

old_contract = ROOT / "tests/test_v303_release_contract.py"
new_contract = ROOT / "tests/test_v304_release_contract.py"
if old_contract.exists() and not new_contract.exists():
    old_contract.rename(new_contract)
if new_contract.exists():
    contract = new_contract.read_text(encoding="utf-8").replace("v303", "v304")
    new_contract.write_text(contract, encoding="utf-8")

# Replace loader-specific tests with the authenticated-page-safe bundle contract.
write(
    "tests/test_ui_cache_busting.py",
    '''from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.4"
PAGE = (ROOT / "pages" / "pig-manager" / "index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(encoding="utf-8")


def test_authenticated_plugin_page_uses_no_protected_asset_subrequests():
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', PAGE)
    assert scripts == ["/api/plugin/page/bridge-sdk.js"]
    assert 'src="./ui-feedback.js' not in PAGE
    assert 'href="./enterprise-theme.css' not in PAGE
    assert 'href="./analytics-theme.css' not in PAGE
    for asset in (
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert f'src="./{asset}' not in PAGE


def test_inline_bundle_is_versioned_ordered_and_matches_sources():
    markers = (
        "data-rollpig-enterprise-theme",
        "data-rollpig-analytics-theme",
        "data-rollpig-feedback-core",
        "data-rollpig-enterprise-ui",
        "data-rollpig-analytics-ui",
    )
    for marker in markers:
        assert marker in PAGE
    assert PAGE.count(f'data-version="{VERSION}"') == len(markers)
    assert PAGE.index('/api/plugin/page/bridge-sdk.js') < PAGE.index('data-rollpig-feedback-core')
    assert PAGE.index('data-rollpig-analytics-ui') < PAGE.index('<script type="module">')

    for source in (
        "enterprise-theme.css",
        "analytics-theme.css",
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        payload = (ROOT / "pages" / "pig-manager" / source).read_text(encoding="utf-8")
        if source.endswith(".js"):
            payload = payload.replace("</script", "<\\/script")
        assert payload in PAGE, source


def test_modular_loader_remains_versioned_for_maintenance_only():
    assert f"const ASSET_VERSION = '{VERSION}'" in LOADER
''',
)

dashboard_path = ROOT / "tests/test_dashboard_feedback.py"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = re.sub(
    r"def test_feedback_layer_loads_before_inline_module\(\):\n.*?\n\ndef test_feedback_layer_explains_stale_runtime_routes",
    '''def test_feedback_layer_loads_before_inline_module():
    bridge = '<script src="/api/plugin/page/bridge-sdk.js"></script>'
    feedback = 'data-rollpig-feedback-core'
    enterprise = 'data-rollpig-enterprise-ui'
    analytics = 'data-rollpig-analytics-ui'
    assert bridge in PAGE
    assert PAGE.index(bridge) < PAGE.index(feedback)
    assert PAGE.index(feedback) < PAGE.index(enterprise) < PAGE.index(analytics)
    assert PAGE.index(analytics) < PAGE.index('<script type="module">')
    assert 'src="./ui-feedback.js' not in PAGE


def test_feedback_layer_explains_stale_runtime_routes''',
    dashboard,
    count=1,
    flags=re.S,
)
dashboard_path.write_text(dashboard, encoding="utf-8")

source_path = ROOT / "tests/test_source_regressions.py"
source = source_path.read_text(encoding="utf-8")
old = '    assert \'<script src="./ui-feedback.js?v=3.0.4"></script>\' in page\n'
new = (
    '    assert "data-rollpig-feedback-core" in page\n'
    '    assert "data-rollpig-analytics-ui" in page\n'
    '    assert \'src="./ui-feedback.js\' not in page\n'
)
if old not in source:
    raise SystemExit("tests/test_source_regressions.py: loader assertion anchor missing")
source_path.write_text(source.replace(old, new, 1), encoding="utf-8")

for temporary in (
    ROOT / "scripts/apply_inline_admin_assets_v304.py",
    ROOT / ".github/workflows/apply-inline-admin-assets-v304.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.0.4 inline admin asset bundle applied")
