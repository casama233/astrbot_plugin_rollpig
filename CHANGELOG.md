# 更新

## 未發佈

- Felis 34 項直讀資源的專案自有 EX1–EX5 文案層已完成全量逐豬精修：34/34 隻、共 170 組 `description` / `analysis` 均依基礎圖片與原始基礎文案語義重新手寫；不讀取或搬運 Felis EX/variant 文案與圖片，固定 allowlist、provenance 與 text-only 合約維持不變。

## v3.12.0

發布日期：2026-08-27

v3.12.0 是面向長期維護的功能面收斂與資源穩定化版本：退役沒有持續使用價值的 AI 工坊和重複管理頁，保留唯一主管理頁內的完整 EX 能力；同時收錄 v3.11.12 後已完成的公共豬源替換、災備 fail-closed 與 Felis 直讀 EX 文案隔離。沒有新增玩家指令或玩法。

### 管理面收斂

- 移除 AI 小豬工坊與相關生圖草稿、遠端圖片抓取、provider 草稿生成後端；主管理頁不再暴露 AI 工坊入口。
- 移除獨立 EX 管理 Plugin Page，EX1–EX5 的名稱、短描述、完整文案、差分圖片與 Base ↔ EX 實際生效預覽全部保留在主管理頁小豬編輯 modal。
- 清理舊版獨立 EX 頁 migration、頁面 smoke 與重複前端 contract；overlay 升級時會清理已知 legacy Page 名稱，避免殘留死入口。

### 公共豬源與來源邊界

- `roasted-pig` 與 `pigsleep` 採用來源受控的高品質替換圖，沿用既有 Bearlele/MegSopern MIT 資源 ID，不增加目錄數量；machine-readable provenance 與精確 SHA-256 gate 驗證替換內容。
- `papa-pig` 因外部下載來源／再分發權未證實而保持 withheld；PigHub-only 本地資源不在本次遷移範圍內。
- 公共災備豬源在來源／再分發審計期間維持 fail-closed：官方鏈只訪問 curryudon primary；主源不可用時使用最近一次已驗證本地快取或內置資源，不讀取舊 Vercel/GitHub 公共鏡像。

### Felis 直讀 EX 文案隔離

- 34 項 Felis direct 基礎資源仍由非商業 Bot 客戶端直接讀取官方上游並在本機快取，不重新託管到 curryudon 公共源。
- 專案自有 EX 文案層只處理 `description` / `analysis`，不讀取 Felis upstream EX/variant 文案或圖片；固定 allowlist、provenance 與 text-only 合約由回歸測試鎖定。
- EX 文案層只影響展示，不改抽取 ID、稀有度、保底、收藏計數、EX 等級計算、SQLite schema、Resource Protocol v1 或 rights-v3 投稿協議。

### 相容性

- 可由 v3.11.12 直接升級；AstrBot 最低版本仍為 `>=4.24.2`。
- 不新增玩家指令、不新增配置鍵，不修改 SQLite schema、Resource Protocol v1、rights-v3 投稿協議或玩法概率。
