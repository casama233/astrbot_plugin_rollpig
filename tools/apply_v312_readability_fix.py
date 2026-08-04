from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "3.1.1"
NEW_VERSION = "3.1.2"
MARKER = "/* v3.1.2 readable typography override */"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


css_path = "pages/pig-manager/analytics-theme.css"
css = read(css_path)
override = r'''

/* v3.1.2 readable typography override */
.analytics-suite {
  font-size: 14px;
  line-height: 1.5;
  padding: 22px;
}

.analytics-suite__head { margin-bottom: 18px; }
.analytics-suite__head h2 { font-size: 18px; line-height: 1.3; }
.analytics-suite__head p { font-size: 13px; line-height: 1.6; }
.analytics-suite__meta { min-height: 32px; font-size: 12px; line-height: 1.2; }
.analytics-suite__meta > span { min-height: 30px; padding-inline: 10px; }

.analytics-kpis { gap: 12px; margin-bottom: 12px; }
.analytics-kpi { min-height: 124px; padding: 16px; }
.analytics-kpi__label { font-size: 12px; line-height: 1.35; }
.analytics-kpi__row { margin-top: 10px; }
.analytics-kpi__row strong { font-size: clamp(24px, 2.6vw, 32px); }
.analytics-delta { min-height: 25px; padding: 4px 8px; font-size: 11.5px; line-height: 1.1; }
.analytics-kpi__note { font-size: 12px; line-height: 1.45; }

.analytics-grid { gap: 12px; }
.analytics-card { min-height: 288px; padding: 18px; }
.analytics-card__head { gap: 14px; margin-bottom: 16px; }
.analytics-card__head span { font-size: 11.5px; line-height: 1.35; letter-spacing: .08em; }
.analytics-card__head h3 { font-size: 16px; line-height: 1.35; }
.analytics-card__head small {
  max-width: 48%;
  font-size: 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.activity-legend { gap: 5px; margin: -4px 0 10px; font-size: 11px; }
.activity-heatmap { gap: 6px; min-height: 144px; padding: 13px; }
.activity-cell span { font-size: 10.5px; line-height: 1.2; }
.activity-summary { gap: 10px; margin-top: 14px; }
.activity-summary span { padding-left: 10px; font-size: 12px; line-height: 1.4; }
.activity-summary b { font-size: 17px; }

.compare-list { gap: 16px; margin-top: 20px; }
.compare-row__top { margin-bottom: 8px; font-size: 12.5px; }
.compare-row__top b { font-size: 13.5px; }
.compare-bars i { height: 6px; }
.compare-legend { margin-top: 18px; font-size: 11.5px; }

.retention-layout { grid-template-columns: 124px 1fr; min-height: 190px; }
.retention-ring { width: 112px; height: 112px; }
.retention-ring::before { width: 86px; height: 86px; }
.retention-ring strong { font-size: 24px; }
.retention-ring span { font-size: 11px; }
.analytics-dl { gap: 10px; }
.analytics-dl div { padding-bottom: 9px; }
.analytics-dl dt { font-size: 12px; }
.analytics-dl dd { font-size: 14px; }

.coverage-list { gap: 9px; }
.coverage-list div { gap: 10px; font-size: 12px; }
.coverage-list b { font-size: 13px; }
.analytics-card__footer { margin-top: 15px; padding-top: 12px; font-size: 11.5px; line-height: 1.4; }

.platform-list { gap: 14px; margin-top: 20px; }
.platform-row > div { margin-bottom: 7px; font-size: 12.5px; }
.platform-row > i,
.ai-health > i { height: 6px; }

.rising-table__head,
.rising-table__row { gap: 12px; padding: 10px 12px; }
.rising-table__head { font-size: 11px; line-height: 1.3; }
.rising-table__row { min-height: 48px; font-size: 13px; }
.rising-table__row > span:first-child { grid-template-columns: 24px minmax(0, 1fr); }
.rising-table__row > span:first-child i { width: 24px; height: 24px; font-size: 10.5px; }
.rising-table__row b { font-size: 13px; }
.rising-table__row small { font-size: 11px; line-height: 1.35; }

.operations-grid { gap: 10px; margin: 20px 0 16px; }
.operations-grid div { min-height: 78px; padding: 13px; }
.operations-grid span { font-size: 12px; line-height: 1.4; }
.operations-grid strong { font-size: 22px; }
.ai-health > div { margin-bottom: 8px; font-size: 12px; }
.ai-health b { font-size: 13px; }

.analytics-empty,
.analytics-error { font-size: 13px; line-height: 1.5; }
.analytics-error strong { font-size: 16px; }

@media (max-width: 820px) {
  .analytics-suite { padding: 18px; }
}

@media (max-width: 620px) {
  .analytics-kpi { min-height: 116px; }
  .retention-ring strong { font-size: 22px; }
  .rising-table__head,
  .rising-table__row {
    grid-template-columns: minmax(150px, 1fr) repeat(3, 52px);
    gap: 7px;
    padding-inline: 9px;
  }
}

@media (max-width: 430px) {
  .analytics-suite { padding: 14px; }
  .activity-cell span { font-size: 10px; }
  .rising-table__head,
  .rising-table__row { grid-template-columns: minmax(140px, 1fr) 52px 54px; }
}
'''
if MARKER not in css:
    css = css.rstrip() + override + "\n"
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
    if OLD_VERSION in content:
        content = content.replace(OLD_VERSION, NEW_VERSION)
    if NEW_VERSION not in content:
        raise RuntimeError(f"{path}: failed to update active version")
    write(path, content)

changelog = read("CHANGELOG.md")
entry = '''## v3.1.2 (2026-08-05)
### Analytics 字体与可读性修复
- Analytics 基础正文提高到 14px，卡片标题提高到 16px，辅助文字、图例、平台名称和表格内容统一提高到可读范围。
- 日期热力图、收藏覆盖、双周期对比、回访用户、平台构成、上升最快猪猪和运行健康等区块同步调整，不再以 7–9px 作为最终显示字级。
- 提高表格行高、卡片内边距和正文行高，同时保留桌面信息密度。
- 新增 1366px 桌面与 430px 窄屏 Chromium 布局测试，验证最终计算字级与横向溢出。

'''
if "## v3.1.2 (2026-08-05)" not in changelog:
    changelog = changelog.replace("# 更新\n", "# 更新\n" + entry, 1)
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
    assert "v3.1.2 readable typography override" in css
    assert "同步任务已启动；已关闭自动轮询" in page
''',
)

write(
    "tests/test_analytics_readability.py",
    '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")
OVERRIDE = CSS.split("/* v3.1.2 readable typography override */", 1)[1]


def test_readability_override_covers_all_dense_analytics_regions():
    required = {
        ".analytics-suite": "font-size: 14px",
        ".analytics-card__head h3": "font-size: 16px",
        ".analytics-card__head small": "font-size: 12px",
        ".activity-cell span": "font-size: 10.5px",
        ".platform-row > div": "font-size: 12.5px",
        ".rising-table__row": "min-height: 48px",
        ".rising-table__row small": "font-size: 11px",
        ".operations-grid span": "font-size: 12px",
    }
    for selector, declaration in required.items():
        assert selector in OVERRIDE
        assert declaration in OVERRIDE


def test_mobile_date_labels_do_not_return_to_micro_type():
    assert "@media (max-width: 430px)" in OVERRIDE
    assert ".activity-cell span { font-size: 10px; }" in OVERRIDE
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

const html = `<!doctype html><style>:root{--line:#444;--surface:#222;--surface-strong:#282228;--bg:#181318;--pink:#e973a4;--pink-2:#ef9aba;--pink-soft:#321d27;--violet:#8b83f5;--muted:#b8abb3;--ink:#fff;--green:#67d9a6;--danger:#f77;--orange:#fa5;--ease:ease;--shadow-soft:none}${CSS}</style><section class="analytics-suite"><header class="analytics-card__head"><div><span>Audience</span><h3>平台用户构成</h3></div><small>最近 7 日</small></header><div class="activity-cell"><i></i><span>08-05</span></div><div class="platform-row"><div><span>aiocqhttp@default</span><b>18</b></div><i><em></em></i></div><div class="rising-table__row"><span><i>1</i><b>测试猪猪</b><small>sample-pig</small></span><span>3</span><span>0</span><span>+3</span></div><div class="operations-grid"><div><span>烧烤次数</span><strong>15</strong></div></div></section>`;

test('representative analytics text uses readable computed sizes', () => {
  const dom = new JSDOM(html, {pretendToBeVisual: true});
  const {window} = dom;
  const size = selector => parseFloat(window.getComputedStyle(window.document.querySelector(selector)).fontSize);
  const minHeight = selector => parseFloat(window.getComputedStyle(window.document.querySelector(selector)).minHeight);
  assert.ok(size('.analytics-suite') >= 14);
  assert.ok(size('.analytics-card__head h3') >= 16);
  assert.ok(size('.analytics-card__head small') >= 12);
  assert.ok(size('.activity-cell span') >= 10.5);
  assert.ok(size('.platform-row > div') >= 12);
  assert.ok(size('.rising-table__row') >= 13);
  assert.ok(minHeight('.rising-table__row') >= 48);
  assert.ok(size('.rising-table__row small') >= 11);
  assert.ok(size('.operations-grid span') >= 12);
  dom.window.close();
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
    '''## Analytics 可读性修复

- Analytics 基础正文提升至 14px，卡片标题提升至 16px。
- 放大日期刻度、辅助说明、平台名称、覆盖分布和表格文字。
- 提高表格行高、卡片内距与正文行高，改善高 DPI 屏幕辨认度。
- 保持桌面信息密度，并通过 430px 窄屏横向溢出测试。
- 通过完整 pytest、jsdom 与真实 Chromium 可读性和性能测试。
''',
)

write(
    ".github/workflows/release-v3.1.2.yml",
    '''name: Release v3.1.2

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
''',
)
