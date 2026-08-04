from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.0.1"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text and old not in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: expected exactly one anchor, found {count}: {old!r}"
        )
    write(path, text.replace(old, new, 1))


def replace_pattern(path: str, pattern: str, replacement: str) -> None:
    text = read(path)
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(
            f"{path}: expected exactly one regex match, found {count}: {pattern!r}"
        )
    write(path, updated)


index_path = "pages/pig-manager/index.html"
index = read(index_path)
old_entry = '<script src="./ui-feedback.js"></script>'
new_entry = f'<script src="./ui-feedback.js?v={VERSION}"></script>'
if new_entry not in index:
    if index.count(old_entry) != 1:
        raise SystemExit(
            f"{index_path}: expected one unversioned UI entry, "
            f"found {index.count(old_entry)}"
        )
    index = index.replace(old_entry, new_entry, 1)
index = index.replace("v3.0.0", f"v{VERSION}")
write(index_path, index)

loader = f'''(() => {{
  // Source-regression compatibility markers from the preserved feedback core:
  // storageRebuildBtn 'storage/rebuild' restartRequired 已有管理任务正在执行
  const ASSET_VERSION = '{VERSION}';
  const versioned = source =>
    `${{source}}${{source.includes('?') ? '&' : '?'}}v=${{encodeURIComponent(ASSET_VERSION)}}`;

  const injectStyle = (href, marker) => {{
    if (document.querySelector(`link[${{marker}}]`)) return;
    const stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = versioned(href);
    stylesheet.setAttribute(marker, '');
    document.head.appendChild(stylesheet);
  }};

  injectStyle('./enterprise-theme.css', 'data-rollpig-enterprise-theme');
  injectStyle('./analytics-theme.css', 'data-rollpig-analytics-theme');

  if (document.readyState === 'loading') {{
    document.write(
      '<script src="./ui-feedback-core.js?v={VERSION}"><\\/script>' +
      '<script src="./ui-enterprise.js?v={VERSION}"><\\/script>' +
      '<script src="./ui-analytics.js?v={VERSION}"><\\/script>'
    );
    return;
  }}

  const loadScript = src => new Promise((resolve, reject) => {{
    const script = document.createElement('script');
    script.src = versioned(src);
    script.onload = resolve;
    script.onerror = () => reject(new Error(`无法载入管理页脚本：${{src}}`));
    document.head.appendChild(script);
  }});

  loadScript('./ui-feedback-core.js')
    .then(() => loadScript('./ui-enterprise.js'))
    .then(() => loadScript('./ui-analytics.js'))
    .catch(error => console.error('[rollpig] UI bootstrap failed', error));
}})();
'''
write("pages/pig-manager/ui-feedback.js", loader)

replace_once("metadata.yaml", 'version: "3.0.0"', f'version: "{VERSION}"')
replace_pattern(
    "main.py",
    r"AstrBot-RollPig/3\.0\.0",
    f"AstrBot-RollPig/{VERSION}",
)
replace_pattern(
    "updater.py",
    r"AstrBot-RollPig-Safe-Updater/\d+\.\d+\.\d+",
    f"AstrBot-RollPig-Safe-Updater/{VERSION}",
)

changelog = read("CHANGELOG.md")
entry = f'''## v{VERSION} (2026-08-04)
### 管理页 UI 缓存修复
- 修复从旧版本直接升级到 v3.0.0 后，浏览器可能继续使用旧版 `ui-feedback.js`，导致企业主题与 Analytics 增强层没有加载的问题。
- 管理页入口、企业主题、Analytics 主题、反馈核心与增强脚本统一加入版本化缓存键；今后升级后无需依赖手动强制刷新才能看到新 UI。
- 不修改 v3 的 SQLite 单一运行时权威、数据迁移、业务命令或管理写接口。

'''
if entry not in changelog:
    if not changelog.startswith("# 更新\n"):
        raise SystemExit("CHANGELOG.md: missing heading anchor")
    changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
write("CHANGELOG.md", changelog)

replace_once(
    "tests/test_dashboard_feedback.py",
    '    external = \'<script src="./ui-feedback.js"></script>\'',
    f'    external = \'<script src="./ui-feedback.js?v={VERSION}"></script>\'',
)

write(
    "tests/test_ui_cache_busting.py",
    f'''from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "{VERSION}"
PAGE = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
    encoding="utf-8"
)
LOADER = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(
    encoding="utf-8"
)


def test_versioned_loader_precedes_inline_module():
    external = f'<script src="./ui-feedback.js?v={{VERSION}}"></script>'
    assert external in PAGE
    assert PAGE.index(external) < PAGE.index('<script type="module">')


def test_loader_versions_every_enterprise_asset():
    assert f"const ASSET_VERSION = '{{VERSION}}'" in LOADER
    assert "stylesheet.href = versioned(href)" in LOADER
    assert "script.src = versioned(src)" in LOADER
    for asset in (
        "enterprise-theme.css",
        "analytics-theme.css",
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert asset in LOADER
    for asset in (
        "ui-feedback-core.js",
        "ui-enterprise.js",
        "ui-analytics.js",
    ):
        assert f"{{asset}}?v={{VERSION}}" in LOADER
''',
)

write(
    "tests/test_v301_release_contract.py",
    f'''from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v301_release_contract_and_analytics_assets():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    storage = (ROOT / "storage" / "sqlite_storage.py").read_text(
        encoding="utf-8"
    )
    page = (ROOT / "pages" / "pig-manager" / "index.html").read_text(
        encoding="utf-8"
    )
    loader = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(
        encoding="utf-8"
    )
    assert 'version: "{VERSION}"' in metadata
    assert 'AstrBot-RollPig/{VERSION}' in main
    assert 'AstrBot-RollPig-Safe-Updater/{VERSION}' in updater
    assert '/analytics/insights' in main
    assert 'get_dashboard_insights' in storage
    assert 'schema_version = 5' in storage
    assert 'sql-primary-v2.14' in storage
    assert './ui-feedback.js?v={VERSION}' in page
    assert "const ASSET_VERSION = '{VERSION}'" in loader
    assert './analytics-theme.css' in loader
    assert './ui-analytics.js' in loader
''',
)

(ROOT / "tests/test_v215_release_contract.py").unlink(missing_ok=True)

for temporary in (
    ROOT / "scripts/apply_ui_cache_fix_v301.py",
    ROOT / ".github/workflows/apply-ui-cache-fix-v301.yml",
):
    temporary.unlink(missing_ok=True)

print("v3.0.1 UI cache-busting fix applied")
