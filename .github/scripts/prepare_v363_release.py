from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one {old!r}, got {count}")
    write(path, text.replace(old, new, 1))


# Stable version metadata / protocol-facing headers. The AstrBot revision smoke no
# longer embeds a release version; since #64 it validates the checked-out snapshot.
replace_once("metadata.yaml", 'version: "3.6.2"', 'version: "3.6.3"')
replace_once(
    "legacy_main.py",
    "AstrBot-RollPig/3.6.2 (+https://github.com/casama233/astrbot_plugin_rollpig)",
    "AstrBot-RollPig/3.6.3 (+https://github.com/casama233/astrbot_plugin_rollpig)",
)
replace_once(
    "legacy_main.py",
    '"X-RollPig-Version": "3.6.2"',
    '"X-RollPig-Version": "3.6.3"',
)
replace_once(
    "updater.py",
    '"User-Agent": "AstrBot-RollPig-Safe-Updater/3.6.2"',
    '"User-Agent": "AstrBot-RollPig-Safe-Updater/3.6.3"',
)

# Current-version documentation headers.
for path, old, new in (
    ("docs/COMMANDS.md", "本文以 v3.6.2 的 `main.py` 實作為準。", "本文以 v3.6.3 的 `main.py` 實作為準。"),
    ("docs/CONFIGURATION.md", "本文對應 v3.6.2 的 `_conf_schema.json`。", "本文對應 v3.6.3 的 `_conf_schema.json`。"),
    ("docs/OPERATIONS.md", "說明 v3.6.2 的身份遷移", "說明 v3.6.3 的身份遷移"),
    ("docs/RESOURCE-MANAGEMENT.md", "本文對應 v3.6.2，", "本文對應 v3.6.3，"),
):
    replace_once(path, old, new)

# README current-version badge, highlights and upgrade targets.
readme = read("README.md")
if readme.count("current-3.6.2-ef5d82") != 1:
    raise RuntimeError("README current-version badge marker not found exactly once")
readme = readme.replace("current-3.6.2-ef5d82", "current-3.6.3-ef5d82", 1)
start = readme.find("## 3.6.2 版本亮點\n")
end_marker = "完整變更請閱讀 [CHANGELOG](CHANGELOG.md)"
end = readme.find(end_marker, start)
if start < 0 or end < 0:
    raise RuntimeError("README release highlight block not found")
new_block = """## 3.6.3 版本亮點

| 修復 / 收口 | 說明 |
| --- | --- |
| 🐷 永久豬圈歷史保留 | 已解鎖但退出現役公共豬源的歷史小豬會繼續出現在 `/我的豬圈`；它們不會重新進入抽池、搜尋或公共源 |
| 📰 日報 reload 安全 | `/豬圈日報` 改由 live plugin instance 解析 sender，修復模組重載後零參 `super()` 可能觸發的 `TypeError` |
| 🧭 指令入口正式收口 | 15 個 AstrBot command decorator 全部由真正 `main.py` Star 入口持有，priority=1000，已移除 v3.6.2 runtime rebind workaround |
| 🧱 讀取 / Renderer 邊界 | Catalog、ResourceRead、單豬卡、圖鑑、週報與料理卡已拆為 service / renderer 邊界，`legacy_main.py` 不再重複持有這些策略 |
| 🔥 烤豬規則單一來源 | 普通烤群友與預約烤豬共用 `RoastService` 的 60/30/10 policy；日報只觀察 outcome event，不再複製完整玩法流程 |

"""
readme = readme[:start] + new_block + readme[end:]
readme = readme.replace("**v3.2.0+ → v3.6.2**", "**v3.2.0+ → v3.6.3**")
readme = readme.replace("**v3.1.4 或更早增強版 → v3.6.2**", "**v3.1.4 或更早增強版 → v3.6.3**")
write("README.md", readme)

# Move the complete Unreleased engineering work into the stable v3.6.3 section.
changelog = read("CHANGELOG.md")
marker = "## v3.6.2 (2026-08-14)\n"
pos = changelog.find(marker)
if pos < 0:
    raise RuntimeError("CHANGELOG v3.6.2 marker not found")
new_head = """# 更新

## 未發佈

- 暫無。

## v3.6.3 (2026-08-14)

### 版本主題：永久收藏與架構穩定性收口

### 修復

- 修復 catalog read boundary 在 `_reload_catalog_layers()` 已改以 `self.pig_list` 接收合併結果後，仍以已移除的 `merged` 變量保存 catalog，導致完整插件初始化可觸發 `NameError`；新增持久化契約測試防止回歸。
- 修復永久豬圈把「目前 active catalog」錯當成永久收藏全集：玩家已解鎖、但後來退出現役公共豬源的歷史小豬會由 `pig_snapshots` 補入 `/我的豬圈` read model，保留收藏可見性與歷史資料；退役小豬不會重新加入每日抽池、隨機／搜尋 catalog，管理員 tombstone 仍可明確隱藏。
- 修復 `DailyReportMixin.pigsty_daily_report()` 在模組重載／MRO class identity 變化後使用零參 `super()._event_sender_id(event)` 可能觸發 `TypeError: super(type, obj)`；改由 live plugin instance `self._event_sender_id(event)` 分派，並避免重複寫入日報會話資料。

### 架構

- 完成 command registration boundary：15 個 RollPig 指令 decorator 全部收回 `main.py` 真正 Star 入口，helper/mixin 僅保留業務方法；每個 command 顯式 `priority=1000` 並由薄 wrapper 委派，移除 v3.6.2 的 runtime handler rebind / registry 重排 workaround。
- 完成 catalog/resource read boundary：新增純 `CatalogService`，集中 base/local/tombstone 合併、ID 查找、圖鑑排序、頁數、隨機與搜尋；新增 `ResourceReadService` 固定 local override → EX variant → cloud → bundled 圖片解析順位。
- 完成 renderer boundary：單豬卡、永久圖鑑、隨機／搜尋九宮格、本週小豬與料理卡的 PIL 繪製移入 `renderers/`；renderer 不取得 AstrBot/storage/sync 依賴，domain read 仍由插件 orchestration 準備。
- 完成 roast/group interaction boundary：普通烤群友與預約烤豬共用 `RoastService` 的單一 60/30/10 outcome policy；`DailyReportMixin` 改為 outcome event hook，不再複製完整烤豬流程。
- AstrBot Market Smoke 現在對 PR checked-out revision 建乾淨 snapshot，直接交給官方 validator worker 的 `PluginManager.load()`，避免 PR CI 實際偷驗 default branch。

### 相容性

- 可由 **v3.6.0 / v3.6.1 / v3.6.2 直接升級**；不修改 SQLite schema、資源協議、烤豬概率、保底或 EX 等級語義。
- PR #68 的 identity-fragment collection merge **未包含在本版**；該修復仍需完成 claim-aware end-to-end 驗證，避免跨平台串資料、重算保底或虛增 EX count。

"""
changelog = new_head + changelog[pos:]
write("CHANGELOG.md", changelog)

# Release contract tests.
replace_once("tests/test_identity_migration_plus.py", 'version: "3.6.2"', 'version: "3.6.3"')
replace_once("tests/test_source_regressions.py", 'version: "3.6.2"', 'version: "3.6.3"')
replace_once("tests/test_source_regressions.py", "AstrBot-RollPig/3.6.2", "AstrBot-RollPig/3.6.3")
replace_once("tests/test_v312_release_contract.py", 'version: "3.6.2"', 'version: "3.6.3"')
replace_once("tests/test_v312_release_contract.py", "AstrBot-RollPig/3.6.2", "AstrBot-RollPig/3.6.3")
replace_once("tests/test_v312_release_contract.py", "AstrBot-RollPig-Safe-Updater/3.6.2", "AstrBot-RollPig-Safe-Updater/3.6.3")

release_notes = """## 🐷 今日小豬 · 增強版 v3.6.3

v3.6.3 是 **永久收藏與架構穩定性收口** patch release。本版不加入烤箱充能／補貨等新玩法，先把 v3.6.2 之後已完成的架構拆分與玩家可感知的資料／日報問題正式發佈。

### 玩家可感知修復

- **永久豬圈不再因換源「掉豬」**：已解鎖但已退出現役公共豬源的歷史小豬，會由永久收藏 snapshot 繼續顯示在 `/我的豬圈`。它們不會重新進入每日抽池、隨機／搜尋 catalog；明確 tombstone 仍然生效。
- **豬圈日報 reload 安全**：修復模組重載後零參 `super()` 可能出現 `TypeError: super(type, obj)` 的問題，sender resolution 改由 live plugin instance 分派。
- **完整初始化穩定性**：修復 catalog reload 保存已移除 `merged` 變量造成的 `NameError`。

### 已完成的架構收口

- 15 個 AstrBot command decorator 全部由 `main.py` 真正 Star 入口註冊，priority 固定為 1000；v3.6.2 runtime registry rebind workaround 已移除。
- `CatalogService` / `ResourceReadService` 固定 catalog merge、搜尋、排序與圖片解析策略。
- 單豬卡、永久圖鑑、搜尋／隨機網格、週報與料理卡已拆入獨立 renderer。
- 普通烤群友與預約烤豬共用 `RoastService` 的單一 60/30/10 outcome policy；日報只消費 outcome event。
- AstrBot Market Smoke 現在使用 checked-out revision snapshot + 官方 validator worker，真正驗證 PR revision 的 `PluginManager.load()`。

### 刻意沒有包含

- PR #68 的 identity-fragment collection merge 暫不進 v3.6.3。它仍需補齊 claim-aware end-to-end 測試，避免跨平台 raw ID 串資料、保底狀態錯算或 EX count 虛增。
- 烤箱 Charge、群體補貨、共享 roast copy、GIF 一等支援仍屬後續 Roadmap。

### 相容性與驗證

- v3.6.0 / v3.6.1 / v3.6.2 可直接升級。
- 不修改 SQLite schema、Resource Protocol、60/30/10 概率、保底或 EX 等級語義。
- Python 3.10 / 3.12 全量測試、pre-commit、Marketplace Package、AstrBot checked-out revision Market Smoke 均為發版門檻。
"""
write(".github/release-v3.6.3.md", release_notes)

print("v3.6.3 release files prepared")
