from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "3.6.1"
NEW = "3.6.2"

CURRENT_VERSION_FILES = [
    "README.md",
    "docs/COMMANDS.md",
    "docs/CONFIGURATION.md",
    "docs/OPERATIONS.md",
    "docs/RESOURCE-MANAGEMENT.md",
    "legacy_main.py",
    "tests/test_identity_migration_plus.py",
    "tests/test_source_regressions.py",
    "tests/test_v312_release_contract.py",
    "updater.py",
]

for relative in CURRENT_VERSION_FILES:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(OLD)
    if count == 0:
        raise SystemExit(f"expected at least one {OLD} reference in {relative}")
    path.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print(f"updated {relative}: {count} version reference(s)")

changelog = ROOT / "CHANGELOG.md"
text = changelog.read_text(encoding="utf-8")
anchor = "## 未發佈\n\n- 暫無。\n\n## v3.6.1 (2026-08-14)"
replacement = """## 未發佈

- 暫無。

## v3.6.2 (2026-08-14)

### 版本主題：指令派發所有權 Hotfix

### 修復

- 修復 v3.6.0 將 decorated handlers 拆到 `legacy_main.py`／feature mixin 後，AstrBot 仍以函數定義模組記錄 `handler_module_path`，而真正 Star 只註冊在 `main.py`，造成 `/今日小豬` 等指令可被指令管理器發現、卻在 `StarRequestSubStage` 執行時因 `star_map` 找不到 helper module 而被跳過，最後落入其他插件／LLM 的嚴重回歸。
- `main.py` 現在在 feature import 完成後，把本插件 handler metadata 統一重新綁定到真正的 Star 入口，恢復 v3.5.x 時「插件入口與 handler owner 一致」的派發語義；函數本體、存儲與資料格式不變。
- RollPig command handler 明確提升至 priority `1000` 並重排 registry；搭配 v3.6.1 已加入的 handler 入口 `stop_event()`，形成「先執行 RollPig 指令，再停止後續通用 AI／消息 handler」的雙層隔離。
- AstrBot Market Smoke 新增真實 runtime registry 契約：以 `data.plugins.astrbot_plugin_rollpig_plus.main` 實際匯入插件後，必須驗證所有 RollPig handler owner 均為 `main`、所有 command priority ≥ 1000，且 `roll_pig` handler 存在；避免未來再次出現「指令列表可見但實際不派發」的回歸。

### 相容性

- 可由 **v3.6.0 / v3.6.1 直接升級**；SQLite／JSON、永久圖鑑、本地 override、歷史記錄、EX 差分、日報與預約烤豬資料均不需要 migration。
- 本版不新增玩法、不修改資源協議與資料 schema，只修正 AstrBot handler registry metadata 與指令執行順序。

## v3.6.1 (2026-08-14)"""
if anchor not in text:
    raise SystemExit("CHANGELOG release anchor not found")
changelog.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")

architecture = ROOT / "docs/ARCHITECTURE.md"
arch = architecture.read_text(encoding="utf-8")
marker = "\n## "
note = """

## AstrBot handler 所有權契約

v3.6.0 起核心實作可繼續拆在 `legacy_main.py` 或 feature mixin，但 AstrBot 的 handler metadata 會在 decorator 執行時使用函數的 `__module__`。真正的 Star 入口仍是 `main.py`，因此 `main.py` 必須在匯入 feature 後把本插件 handler 的 `handler_module_path` 重新綁定到入口模組；否則 WakingCheck 可以看見指令，`StarRequestSubStage` 卻可能因 `star_map` 找不到 helper module 而跳過 handler。

所有 RollPig command 同時使用高於普通消息 handler 的明確優先級，並在自身 handler 入口停止事件傳播。`.github/workflows/astrbot-market-smoke.yml` 會用目前 AstrBot master 實際匯入插件並驗證 handler owner、priority 與 `roll_pig` 存在性；任何後續架構拆分都不得移除這項契約。
"""
if "## AstrBot handler 所有權契約" not in arch:
    pos = arch.find(marker)
    if pos == -1:
        arch += note
    else:
        arch = arch[:pos] + note + arch[pos:]
    architecture.write_text(arch, encoding="utf-8")

release_note = ROOT / ".github" / "release-v3.6.2.md"
release_note.write_text(
    """## 🐷 今日小豬 · 增強版 v3.6.2

v3.6.2 是針對 v3.6.0 架構拆分後「指令可見但不執行、最終掉進 LLM」的 **緊急 hotfix patch release**。本版不新增玩法、不改資料格式。

### 核心修復

- **修復真正的指令派發根因**：AstrBot 在 decorator 執行時以函數定義模組記錄 handler ownership；v3.6.0 把指令實作搬到 `legacy_main.py`／feature mixin 後，handler metadata 與真正註冊在 `main.py` 的 Star 發生錯位。WakingCheck 仍能看到 `/今日小豬`，但執行階段可能因 `star_map` 找不到 helper module 而跳過 RollPig，讓消息落入其他插件或 LLM。
- **入口 ownership 重綁定**：`main.py` 匯入全部 feature 後，會把 RollPig handler metadata 統一綁定到真正的 `main` Star 入口，恢復 v3.5.x 的派發語義。
- **命令優先級保護**：RollPig command priority 固定至少為 `1000` 並重新排序 registry，避免通用 AI／消息 handler 在 RollPig 指令前先消費事件。
- **雙層隔離**：保留 v3.6.1 已加入的 handler 入口 `event.stop_event()`；現在先保證 RollPig 真正先被 dispatch，再由它停止後續插件／LLM。
- **新增真實 AstrBot runtime 契約**：Market Smoke 會以 `data.plugins.astrbot_plugin_rollpig_plus.main` 實際匯入插件並檢查所有 RollPig handler owner、command priority 及 `roll_pig` handler。此次修復驗證結果為 `15 handlers / 15 commands`，`roll_pig owner=...main`、`priority=1000`，官方 market validator 同時 PASS。

### 相容性

- 可由 **v3.6.0 / v3.6.1 直接升級**。
- SQLite／JSON、永久圖鑑、本地 override、歷史記錄、EX 差分、日報與預約烤豬資料均不需要 migration。
- 不修改資源協議或資料 schema。

### 驗證

- Python 3.10 / 3.12 全量測試
- pre-commit / pre-commit.ci
- Marketplace Package
- AstrBot 官方 Market Smoke
- AstrBot 真實 handler registry ownership / priority contract
""",
    encoding="utf-8",
)

print("v3.6.2 release files prepared")
