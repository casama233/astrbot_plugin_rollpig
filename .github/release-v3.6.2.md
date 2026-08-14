## 🐷 今日小豬 · 增強版 v3.6.2

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
