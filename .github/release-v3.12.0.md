# v3.12.0

## 長期維護面收斂

- 退役 AI 小豬工坊前端、五個 Web API 與 runtime mixin，減少額外 Provider、API Key、草稿與遠端生圖鏈路的長期維護面。
- 移除重複的 `pig-manager-ex` 與 `pig-manager-ex-public-source` 獨立 Plugin Pages；EX 1–5 編輯、真實發送卡預覽、rights-v3 投稿與審核完整保留在唯一的 `pig-manager` 主管理頁。
- 升級 migration 會清理歷史 overlay 安裝殘留的退役程式與 Page；不刪除 `plugin_data`，不修改既有本地小豬或 EX 差分。

## 資源與來源穩定性

- 收錄 `roasted-pig`／`pigsleep` 來源受控替換與精確 provenance/SHA-256 gate，不增加公共圖鑑 ID。
- 官方公共源鏈在未完成鏡像審計前維持 fail-closed，只讀 curryudon primary；失敗時沿用最近一次已驗證本機快取或內置資源。
- Felis 34 項直讀資源只加入本專案自有的 text-only EX 文案，不鏡像 Felis EX 圖片或 variant payload。

## 相容性

- 可由 v3.11.11 或 v3.11.12 直接升級；AstrBot 最低版本仍為 `>=4.24.2`。
- 不新增指令，不修改 SQLite schema、永久豬籍、EX 等級與資料、Resource Protocol v1、rights-v3 投稿協議或玩家玩法。
- 既有 v3.11.12 tag 與 Release ZIP 維持不可變；AstrBot 市場應發布本 v3.12.0 成品。
