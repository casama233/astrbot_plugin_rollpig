# 今日小豬增強版文檔

這個目錄同時保存「目前仍適用的使用／運維文檔」與「特定版本的技術驗證記錄」。新使用者請優先閱讀前者；帶版本號的檔案主要供維護與回歸追蹤使用。

## 使用與運維文檔

| 文檔 | 內容 |
| --- | --- |
| [`../README.md`](../README.md) | 專案總覽、安裝、快速開始與主要能力 |
| [`COMMANDS.md`](COMMANDS.md) | 完整聊天指令、別名、上下文限制與玩法規則 |
| [`CONFIGURATION.md`](CONFIGURATION.md) | `_conf_schema.json` 全配置說明、預設值與建議 |
| [`RESOURCE-MANAGEMENT.md`](RESOURCE-MANAGEMENT.md) | 本地資源分層、私人 manifest、PigHub 投稿與同步排錯 |
| [`OPERATIONS.md`](OPERATIONS.md) | 身份遷移、SQLite、備份、同步、安全更新與故障排查 |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 開發環境、測試、提交與文檔維護規範 |
| [`../CHANGELOG.md`](../CHANGELOG.md) | 版本變更記錄 |

## 歷史技術記錄

以下檔案是特定版本的管理頁驗證或性能證據，不應被當成當前安裝／操作手冊：

- `admin-ui-authenticated-assets-v310.md` — v3.1.0 認證資源橋接設計與驗證。
- `admin-ui-performance-v3.1.1.md` — v3.1.1 管理頁按需載入與性能記錄。
- `admin-ui-review.md` — 管理頁審查紀錄。
- `performance-v3.1.1.json` / `performance-v3.1.2.json` — 瀏覽器性能測量輸出。
- `readability-v3.1.2.json` — v3.1.2 字體／可讀性測量輸出。

## 維護原則

當功能、指令、配置或資料語義變更時，請至少同步檢查：

1. `README.md` 是否仍準確描述當前版本。
2. `docs/COMMANDS.md` 是否與 `@filter.command(...)` 和實際限制一致。
3. `docs/CONFIGURATION.md` 是否與 `_conf_schema.json` 一致。
4. `docs/RESOURCE-MANAGEMENT.md` 是否與圖鑑分層、manifest 及 PigHub 流程一致。
5. `docs/OPERATIONS.md` 是否與 `storage/`、`identity_migration.py`、`updater.py` 的行為一致。
6. `CHANGELOG.md` 是否記錄對使用者有感的變更。

版本化性能／審查檔案可以保留作歷史證據，但不要讓它們取代當前文檔。
