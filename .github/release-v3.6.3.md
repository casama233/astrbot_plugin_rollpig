## 🐷 今日小豬 · 增強版 v3.6.3

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
