# 今日小豬 · 增強版 v3.8.1

這是一個針對 **AstrBot 後台插件首頁／升級殘留** 的修復版本。

## 修復內容

- 修復從舊版本以 overlay/overwrite 方式升級後，`pages/ex-manager/`、`pages/ex-public-source/` 可能殘留，導致 AstrBot 仍把 **EX 成長管理** 當成插件主管理頁的問題。
- 新增啟動時 installation migration：確認新版替代頁存在後，自動清理 RollPig 明確擁有的 legacy Plugin Page。
- 若舊 Page 目錄因權限或文件佔用無法完整刪除，會退而停用其 `index.html`，避免 AstrBot 繼續 discover 舊入口。
- 替代頁缺失時不刪舊頁；未知／使用者自建 Page 不會被 migration 觸碰。
- 新增真實 overlay-upgrade 回歸測試，直接驗證舊 `ex-manager` 殘留 → migration → `pig-manager` 恢復為第一個 Plugin Page 的完整流程。
- 將 installation migration module 納入 CI 顯式 compile gate。

## 升級後預期

AstrBot Plugin Page 應只發現：

1. `pig-manager` — 豬圈管理（預設首頁）
2. `pig-manager-ex` — EX 成長管理
3. `pig-manager-ex-public-source` — EX 公共源

已受舊版殘留影響的安裝，在載入 v3.8.1 後會自動自愈，不需要手動刪除舊 Page 目錄。

## 相容性

可由 v3.8.0 直接升級。本版不修改：

- SQLite schema
- Resource Protocol v1
- 抽豬概率／新豬保底
- EX 等級計算與官方 EX 文案
- Roast Charge／`/添柴` 數值與結算
- 永久豬籍 authority

## 驗證

修復 PR #119 已通過：

- CI（Python 3.10 / 3.12）
- Marketplace Package
- AstrBot Market Smoke
- 官方 AstrBot plugin load worker
