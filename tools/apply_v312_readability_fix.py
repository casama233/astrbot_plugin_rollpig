from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "3.1.1"
NEW_VERSION = "3.1.2"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {count}: {old!r}")
    return text.replace(old, new, 1)


css_path = "pages/pig-manager/analytics-theme.css"
css = read(css_path)
replacements = [
    (
        "  --analytics-grid: color-mix(in srgb, var(--line) 72%, transparent);\n  margin: 0 0 14px;\n  padding: 19px;",
        "  --analytics-grid: color-mix(in srgb, var(--line) 72%, transparent);\n  font-size: 14px;\n  line-height: 1.5;\n  margin: 0 0 14px;\n  padding: 22px;",
    ),
    ("  margin-bottom: 15px;\n}\n\n.analytics-suite__head h2", "  margin-bottom: 18px;\n}\n\n.analytics-suite__head h2"),
    ("  font-size: 17px;\n  font-weight: 740;", "  font-size: 18px;\n  line-height: 1.3;\n  font-weight: 740;"),
    ("  font-size: 10.5px;\n  line-height: 1.6;", "  font-size: 13px;\n  line-height: 1.6;"),
    ("  min-height: 27px;\n  color: var(--muted);\n  font: 600 9.5px/1 ui-monospace", "  min-height: 32px;\n  color: var(--muted);\n  font: 600 12px/1.2 ui-monospace"),
    ("  min-height: 25px;\n  display: inline-flex;", "  min-height: 30px;\n  display: inline-flex;"),
    ("  padding: 0 8px;\n  border: 1px solid var(--line);", "  padding: 0 10px;\n  border: 1px solid var(--line);"),
    ("  gap: 9px;\n  margin-bottom: 9px;\n}\n\n.analytics-kpi", "  gap: 12px;\n  margin-bottom: 12px;\n}\n\n.analytics-kpi"),
    ("  min-height: 112px;\n  padding: 14px;", "  min-height: 124px;\n  padding: 16px;"),
    ("  font-size: 9.5px;\n  font-weight: 650;", "  font-size: 12px;\n  line-height: 1.35;\n  font-weight: 650;"),
    ("  margin-top: 8px;\n}\n\n.analytics-kpi__row strong", "  margin-top: 10px;\n}\n\n.analytics-kpi__row strong"),
    ("  font-size: clamp(23px, 2.6vw, 31px);", "  font-size: clamp(24px, 2.6vw, 32px);"),
    ("  min-height: 21px;\n  padding: 3px 7px;\n  border-radius: 999px;\n  font: 700 9px/1 ui-monospace", "  min-height: 25px;\n  padding: 4px 8px;\n  border-radius: 999px;\n  font: 700 11.5px/1.1 ui-monospace"),
    ("  color: var(--muted);\n  font-size: 9.5px;\n}\n\n.analytics-grid", "  color: var(--muted);\n  font-size: 12px;\n  line-height: 1.45;\n}\n\n.analytics-grid"),
    ("  gap: 9px;\n}\n\n.analytics-card", "  gap: 12px;\n}\n\n.analytics-card"),
    ("  min-height: 260px;\n  padding: 15px;", "  min-height: 288px;\n  padding: 18px;"),
    ("  gap: 12px;\n  margin-bottom: 14px;", "  gap: 14px;\n  margin-bottom: 16px;"),
    ("  font-size: 8.5px;\n  font-weight: 700;\n  letter-spacing: .1em;", "  font-size: 11.5px;\n  line-height: 1.35;\n  font-weight: 700;\n  letter-spacing: .08em;"),
    ("  font-size: 13px;\n  font-weight: 720;", "  font-size: 16px;\n  line-height: 1.35;\n  font-weight: 720;"),
    ("  font-size: 9px;\n  font-weight: 550;\n  text-align: right;", "  max-width: 48%;\n  font-size: 12px;\n  line-height: 1.4;\n  font-weight: 550;\n  overflow-wrap: anywhere;\n  text-align: right;"),
    ("  gap: 4px;\n  margin: -7px 0 8px;\n  color: var(--muted);\n  font-size: 8px;", "  gap: 5px;\n  margin: -4px 0 10px;\n  color: var(--muted);\n  font-size: 11px;"),
    ("  gap: 5px;\n  min-height: 112px;\n  align-content: center;\n  padding: 11px;", "  gap: 6px;\n  min-height: 144px;\n  align-content: center;\n  padding: 13px;"),
    ("  font: 500 7px/1 ui-monospace", "  font: 550 10.5px/1.2 ui-monospace"),
    ("  gap: 8px;\n  margin-top: 11px;\n}\n\n.activity-summary span", "  gap: 10px;\n  margin-top: 14px;\n}\n\n.activity-summary span"),
    ("  padding-left: 9px;\n  border-left: 2px solid", "  padding-left: 10px;\n  border-left: 2px solid"),
    ("  color: var(--muted);\n  font-size: 8.5px;\n}\n\n.activity-summary b", "  color: var(--muted);\n  font-size: 12px;\n  line-height: 1.4;\n}\n\n.activity-summary b"),
    ("  font-size: 13px;\n  font-variant-numeric: tabular-nums;\n}\n\n.compare-list", "  font-size: 17px;\n  font-variant-numeric: tabular-nums;\n}\n\n.compare-list"),
    ("  gap: 14px;\n  margin-top: 19px;", "  gap: 16px;\n  margin-top: 20px;"),
    ("  margin-bottom: 6px;\n  color: var(--muted);\n  font-size: 9.5px;", "  margin-bottom: 8px;\n  color: var(--muted);\n  font-size: 12.5px;"),
    ("  font-size: 11px;\n  font-variant-numeric: tabular-nums;", "  font-size: 13.5px;\n  font-variant-numeric: tabular-nums;"),
    ("  height: 5px;\n  min-width: 2px;", "  height: 6px;\n  min-width: 2px;"),
    ("  margin-top: 16px;\n  color: var(--muted);\n  font-size: 8.5px;", "  margin-top: 18px;\n  color: var(--muted);\n  font-size: 11.5px;"),
    ("  grid-template-columns: 116px 1fr;", "  grid-template-columns: 124px 1fr;"),
    ("  min-height: 172px;", "  min-height: 190px;"),
    ("  width: 108px;\n  height: 108px;", "  width: 112px;\n  height: 112px;"),
    ("  width: 84px;\n  height: 84px;", "  width: 86px;\n  height: 86px;"),
    ("  font-size: 21px;", "  font-size: 24px;"),
    ("  font-size: 8px;\n}\n\n.analytics-dl", "  font-size: 11px;\n}\n\n.analytics-dl"),
    ("  gap: 8px;\n  margin: 0;", "  gap: 10px;\n  margin: 0;"),
    ("  padding-bottom: 7px;\n  border-bottom", "  padding-bottom: 9px;\n  border-bottom"),
    ("  font-size: 8.5px;\n}\n\n.analytics-dl dd", "  font-size: 12px;\n}\n\n.analytics-dl dd"),
    ("  margin: 0;\n  font-weight: 720;", "  margin: 0;\n  font-size: 14px;\n  font-weight: 720;"),
    ("  gap: 7px;\n}\n\n.coverage-list div", "  gap: 9px;\n}\n\n.coverage-list div"),
    ("  gap: 8px;\n  font-size: 9px;", "  gap: 10px;\n  font-size: 12px;"),
    ("  font-size: 10px;\n  font-variant-numeric: tabular-nums;", "  font-size: 13px;\n  font-variant-numeric: tabular-nums;"),
    ("  margin-top: 13px;\n  padding-top: 10px;", "  margin-top: 15px;\n  padding-top: 12px;"),
    ("  color: var(--muted);\n  font-size: 8.5px;\n}\n\n.platform-list", "  color: var(--muted);\n  font-size: 11.5px;\n  line-height: 1.4;\n}\n\n.platform-list"),
    ("  gap: 11px;\n  margin-top: 18px;", "  gap: 14px;\n  margin-top: 20px;"),
    ("  margin-bottom: 5px;\n  font-size: 9px;", "  margin-bottom: 7px;\n  font-size: 12.5px;"),
    ("  height: 5px;\n  border-radius: 999px;\n  background: var(--line);", "  height: 6px;\n  border-radius: 999px;\n  background: var(--line);"),
    ("  gap: 10px;\n  padding: 8px 10px;", "  gap: 12px;\n  padding: 10px 12px;"),
    ("  font-size: 8px;\n  font-weight: 700;", "  font-size: 11px;\n  line-height: 1.3;\n  font-weight: 700;"),
    ("  min-height: 39px;\n  border-top: 1px solid var(--line);\n  font-size: 9.5px;", "  min-height: 48px;\n  border-top: 1px solid var(--line);\n  font-size: 13px;"),
    ("  grid-template-columns: 20px minmax(0, 1fr);", "  grid-template-columns: 24px minmax(0, 1fr);"),
    ("  width: 20px;\n  height: 20px;", "  width: 24px;\n  height: 24px;"),
    ("  font-size: 8px;\n}\n\n.rising-table__row b,", "  font-size: 10.5px;\n}\n\n.rising-table__row b,"),
    ("  font-size: 9.5px;\n}\n\n.rising-table__row small", "  font-size: 13px;\n}\n\n.rising-table__row small"),
    ("  font: 500 7.5px/1.2 ui-monospace", "  font: 500 11px/1.35 ui-monospace"),
    ("  gap: 7px;\n  margin: 18px 0 15px;", "  gap: 10px;\n  margin: 20px 0 16px;"),
    ("  min-height: 64px;\n  padding: 10px;", "  min-height: 78px;\n  padding: 13px;"),
    ("  font-size: 8px;\n}\n\n.operations-grid strong", "  font-size: 12px;\n  line-height: 1.4;\n}\n\n.operations-grid strong"),
    ("  font-size: 18px;\n  font-variant-numeric", "  font-size: 22px;\n  font-variant-numeric"),
    ("  margin-bottom: 6px;\n  color: var(--muted);\n  font-size: 8.5px;", "  margin-bottom: 8px;\n  color: var(--muted);\n  font-size: 12px;"),
    ("  font-size: 10px;\n}\n\n.ai-health em", "  font-size: 13px;\n}\n\n.ai-health em"),
    ("  font-size: 9.5px;\n  text-align: center;", "  font-size: 13px;\n  line-height: 1.5;\n  text-align: center;"),
    ("  font-size: 13px;\n}\n\n.analytics-error .btn", "  font-size: 16px;\n}\n\n.analytics-error .btn"),
    ("  .analytics-suite { padding: 16px; }", "  .analytics-suite { padding: 18px; }"),
    ("  .analytics-kpi { min-height: 100px; }", "  .analytics-kpi { min-height: 116px; }"),
    ("  .retention-ring strong { font-size: 18px; }", "  .retention-ring strong { font-size: 22px; }"),
    ("  .rising-table__row { grid-template-columns: minmax(130px, 1fr) repeat(3, 44px); gap: 6px; padding-inline: 8px; }", "  .rising-table__row { grid-template-columns: minmax(150px, 1fr) repeat(3, 52px); gap: 7px; padding-inline: 9px; }"),
    ("  .analytics-suite { margin-inline: 0; padding: 13px; }", "  .analytics-suite { margin-inline: 0; padding: 14px; }"),
    ("  .activity-cell span { font-size: 6.5px; }", "  .activity-cell span { font-size: 10px; }"),
    ("  .rising-table__row { grid-template-columns: minmax(125px, 1fr) 46px 48px; }", "  .rising-table__row { grid-template-columns: minmax(140px, 1fr) 52px 54px; }"),
]
for old, new in replacements:
    css = replace_once(css, old, new, css_path)
write(css_path, css)

active_version_files = [
    "metadata.yaml",
    "main.py",
    "updater.py",
    "pages/pig-manager/index.html",
    "pages/pig-manager/ui-bootstrap.js",
    "pages/pig-manager/ui-analytics.js",
    "tests/test_ui_cache_busting.py",
    "tests/test_ui_asset_delivery.py",
    "tests/test_analytics_spa_remount.py",
    "tests/test_source_regressions.py",
    "tests/browser/admin-ui.test.mjs",
    "tests/browser/performance-browser.mjs",
]
for path in active_version_files:
    content = read(path)
    if OLD_VERSION not in content:
        raise RuntimeError(f"{path}: missing active version {OLD_VERSION}")
    write(path, content.replace(OLD_VERSION, NEW_VERSION))

changelog = read("CHANGELOG.md")
entry = """## v3.1.2 (2026-08-05)
### Analytics 字体与可读性修复
- 将 Analytics 基础正文提高到 14px，卡片标题提高到 16px，辅助文字、图例、平台名称和表格内容统一提高到可读范围。
- 日期热力图、收藏覆盖、双周期对比、回访用户、平台构成、上升最快猪猪和运行健康等全部区块同步调整，不再出现 7–9px 的微型文字。
- 提高表格行高、卡片内边距和正文行高，并保留桌面信息密度。
- 新增 1366px 桌面与 430px 窄屏 Chromium 布局测试，验证文字尺寸与横向溢出。

"""
changelog = replace_once(changelog, "# 更新\n", "# 更新\n" + entry, "CHANGELOG.md")
write("CHANGELOG.md", changelog)

old_contract = ROOT / "tests/test_v311_release_contract.py"
if old_contract.exists():
    old_contract.unlink()
write(
    "tests/test_v312_release_contract.py",
    '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v312_release_contract_is_readable_lazy_and_versioned():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    updater = (ROOT / "updater.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "pages/pig-manager/ui-bootstrap.js").read_text(encoding="utf-8")
    page = (ROOT / "pages/pig-manager/index.html").read_text(encoding="utf-8")
    css = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")
    assert 'version: "3.1.2"' in metadata
    assert "AstrBot-RollPig/3.1.2" in main
    assert "AstrBot-RollPig-Safe-Updater/3.1.2" in updater
    assert "analyticsLoadBtn" in bootstrap
    assert "sessionStorage" not in bootstrap
    assert "font-size: 14px" in css
    assert "font-size: 16px" in css
    assert "min-height: 48px" in css
    assert "同步任务已启动；已关闭自动轮询" in page
''',
)

write(
    "tests/test_analytics_readability.py",
    '''from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")


def block(selector: str) -> str:
    match = re.search(re.escape(selector) + r"\\s*\\{([^}]*)\\}", CSS, re.S)
    assert match, selector
    return match.group(1)


def px(selector: str, property_name: str) -> float:
    match = re.search(rf"{re.escape(property_name)}\\s*:\\s*([0-9.]+)px", block(selector))
    assert match, (selector, property_name)
    return float(match.group(1))


def test_analytics_text_hierarchy_has_readable_minimums():
    assert px(".analytics-suite", "font-size") >= 14
    assert px(".analytics-card__head h3", "font-size") >= 16
    assert px(".analytics-card__head small", "font-size") >= 12
    assert px(".activity-cell span", "font-size") >= 10.5
    assert px(".platform-row > div", "font-size") >= 12
    assert px(".rising-table__row", "font-size") >= 13
    assert px(".rising-table__row", "min-height") >= 48
    assert px(".rising-table__row small", "font-size") >= 11
    assert px(".operations-grid span", "font-size") >= 12


def test_no_legacy_micro_type_remains():
    explicit = [float(value) for value in re.findall(r"font-size\\s*:\\s*([0-9.]+)px", CSS)]
    shorthand = [float(value) for value in re.findall(r"font\\s*:[^;]*?\\s([0-9.]+)px/", CSS)]
    assert explicit and min(explicit) >= 10
    assert shorthand and min(shorthand) >= 10.5
    assert "font-size: 6.5px" not in CSS
    assert "font: 500 7px" not in CSS
    assert "font: 500 7.5px" not in CSS
''',
)

write(
    "tests/browser/analytics-readability.test.mjs",
    '''import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {JSDOM} from 'jsdom';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const CSS = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/analytics-theme.css'), 'utf8');

function computed(selector, width = 1366) {
  const dom = new JSDOM(`<!doctype html><style>:root{--line:#444;--surface:#222;--surface-strong:#282228;--bg:#181318;--pink:#e973a4;--pink-2:#ef9aba;--pink-soft:#321d27;--violet:#8b83f5;--muted:#b8abb3;--ink:#fff;--green:#67d9a6;--danger:#f77;--orange:#fa5;--ease:ease;--shadow-soft:none}${CSS}</style><section class="analytics-suite"><header class="analytics-card__head"><div><span>Audience</span><h3>平台用户构成</h3></div><small>最近 7 日</small></header><div class="activity-cell"><i></i><span>08-05</span></div><div class="platform-row"><div><span>aiocqhttp@default</span><b>18</b></div><i><em></em></i></div><div class="rising-table__row"><span><i>1</i><b>测试猪猪</b><small>sample-pig</small></span><span>3</span><span>0</span><span>+3</span></div><div class="operations-grid"><div><span>烧烤次数</span><strong>15</strong></div></div></section>`, {pretendToBeVisual: true});
  Object.defineProperty(dom.window, 'innerWidth', {value: width});
  return {dom, style: dom.window.getComputedStyle(dom.window.document.querySelector(selector))};
}

test('representative analytics text uses readable computed sizes', () => {
  const expectations = [
    ['.analytics-suite', 14],
    ['.analytics-card__head h3', 16],
    ['.analytics-card__head small', 12],
    ['.activity-cell span', 10.5],
    ['.platform-row > div', 12],
    ['.rising-table__row', 13],
    ['.rising-table__row small', 11],
    ['.operations-grid span', 12],
  ];
  for (const [selector, minimum] of expectations) {
    const {dom, style} = computed(selector);
    assert.ok(parseFloat(style.fontSize) >= minimum, `${selector}: ${style.fontSize}`);
    dom.window.close();
  }
});
''',
)

write(
    "tests/browser/readability-browser.mjs",
    '''import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright-core';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const CSS = fs.readFileSync(path.join(ROOT, 'pages/pig-manager/analytics-theme.css'), 'utf8');
const executablePath = process.env.CHROME_PATH;
assert.ok(executablePath, 'CHROME_PATH is required');

const browser = await chromium.launch({executablePath, headless: true, args: ['--no-sandbox']});
const page = await browser.newPage({viewport: {width: 1366, height: 900}});
const cells = Array.from({length: 28}, (_, index) => `<div class="activity-cell"><i style="--intensity:.6"></i><span>08-${String(index + 1).padStart(2, '0')}</span></div>`).join('');
const html = `<!doctype html><meta charset="utf-8"><style>:root{--line:#493941;--surface:#261e23;--surface-strong:#2c2228;--bg:#191317;--pink:#e873a4;--pink-2:#ef9aba;--pink-soft:#321d27;--violet:#8b83f5;--muted:#b9abb3;--ink:#fff;--green:#67d9a6;--danger:#f77;--orange:#fa5;--ease:ease;--shadow-soft:none;--radius-md:12px}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Arial,sans-serif}${CSS}</style><section class="analytics-suite"><header class="analytics-suite__head"><div><h2>猪圈深度分析</h2><p>用于观察活跃趋势、收藏覆盖与运行健康。</p></div><div class="analytics-suite__meta"><span>最近 28 日</span></div></header><div class="analytics-grid"><article class="analytics-card analytics-card--wide"><header class="analytics-card__head"><div><span>28 Day Activity</span><h3>活跃热力与玩法脉冲</h3></div><small>8.6 日均活跃</small></header><div class="activity-legend">低<i></i><i></i><i></i><i></i>高</div><div class="activity-heatmap">${cells}</div><div class="activity-summary"><span><b>60</b>抽取</span><span><b>60</b>新解锁</span><span><b>15</b>烧烤</span><span><b>3</b>被吃事件</span></div></article><article class="analytics-card"><header class="analytics-card__head"><div><span>Audience Mix</span><h3>平台用户构成</h3></div><small>32 个身份</small></header><div class="platform-list"><div class="platform-row"><div><span>aiocqhttp@default</span><b>18</b></div><i><em style="width:80%"></em></i></div></div></article><article class="analytics-card analytics-card--wide"><header class="analytics-card__head"><div><span>Momentum</span><h3>上升最快的猪猪</h3></div><small>当前 7 日与上一周期绝对差值</small></header><div class="rising-table"><div class="rising-table__head"><span>猪猪</span><span>本期</span><span>上期</span><span>变化</span></div><div class="rising-table__row"><span><i>1</i><b>三叉泰克司</b><small>sailor-sushi-pig</small></span><span>3</span><span>0</span><span>+3</span></div></div></article><article class="analytics-card"><header class="analytics-card__head"><div><span>Runtime Signals</span><h3>玩法运行健康</h3></div><small>最近 7 日</small></header><div class="operations-grid"><div><span>烧烤次数</span><strong>15</strong></div><div><span>被吃事件</span><strong>3</strong></div></div></article></div></section>`;
await page.setContent(html);

async function metrics() {
  return page.evaluate(() => {
    const size = selector => parseFloat(getComputedStyle(document.querySelector(selector)).fontSize);
    const height = selector => parseFloat(getComputedStyle(document.querySelector(selector)).minHeight);
    return {
      viewport: innerWidth,
      suite: size('.analytics-suite'),
      title: size('.analytics-card__head h3'),
      helper: size('.analytics-card__head small'),
      date: size('.activity-cell span'),
      platform: size('.platform-row > div'),
      row: size('.rising-table__row'),
      rowHeight: height('.rising-table__row'),
      alias: size('.rising-table__row small'),
      operationLabel: size('.operations-grid span'),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    };
  });
}

const desktop = await metrics();
assert.ok(desktop.suite >= 14, desktop);
assert.ok(desktop.title >= 16, desktop);
assert.ok(desktop.helper >= 12, desktop);
assert.ok(desktop.date >= 10.5, desktop);
assert.ok(desktop.platform >= 12, desktop);
assert.ok(desktop.row >= 13, desktop);
assert.ok(desktop.rowHeight >= 48, desktop);
assert.ok(desktop.alias >= 11, desktop);
assert.ok(desktop.operationLabel >= 12, desktop);
assert.ok(desktop.scrollWidth <= desktop.clientWidth, desktop);

await page.setViewportSize({width: 430, height: 1000});
const mobile = await metrics();
assert.ok(mobile.date >= 10, mobile);
assert.ok(mobile.scrollWidth <= mobile.clientWidth, mobile);

const report = {desktop, mobile};
fs.mkdirSync(path.join(ROOT, 'docs'), {recursive: true});
fs.writeFileSync(path.join(ROOT, 'docs/readability-v3.1.2.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report, null, 2));
await browser.close();
''',
)

write(
    ".github/release-v3.1.2.md",
    """## Analytics 可读性修复

- 将 Analytics 基础正文提升至 14px，卡片标题提升至 16px。
- 放大日期刻度、辅助说明、平台名称、覆盖分布和表格文字。
- 提高表格行高、卡片内距与正文行高，避免高 DPI 屏幕难以辨认。
- 保持桌面信息密度，并通过 430px 窄屏横向溢出测试。
- 通过完整 pytest、jsdom 与真实 Chromium 可读性和性能测试。
""",
)

write(
    ".github/workflows/release-v3.1.2.yml",
    """name: Release v3.1.2

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  release:
    if: ${{ github.repository == 'casama233/astrbot_plugin_rollpig' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
      - name: Check target version
        id: version
        shell: bash
        run: |
          if ! grep -q 'version: "3.1.2"' metadata.yaml; then
            echo "release=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          if git ls-remote --exit-code --tags origin refs/tags/v3.1.2 >/dev/null 2>&1; then
            echo "release=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi
          echo "release=true" >> "$GITHUB_OUTPUT"
      - name: Install and test
        if: steps.version.outputs.release == 'true'
        run: |
          npm ci
          python -m pip install -r requirements.txt pytest
          npm test
          python -m pytest -q
          python -m compileall -q main.py updater.py services storage
          CHROME_PATH="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser)"
          CHROME_PATH="$CHROME_PATH" npm run test:browser-perf
          CHROME_PATH="$CHROME_PATH" node tests/browser/readability-browser.mjs
      - name: Publish GitHub Release
        if: steps.version.outputs.release == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create v3.1.2 \
            --target "$GITHUB_SHA" \
            --title "v3.1.2 · Analytics 可读性修复" \
            --notes-file .github/release-v3.1.2.md
""",
)

remaining = []
for path in active_version_files:
    if OLD_VERSION in read(path):
        remaining.append(path)
if remaining:
    raise RuntimeError(f"active version references were not updated: {remaining}")
