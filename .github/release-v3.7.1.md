# 今日小豬 · 增強版 v3.7.1

> **豬圈開始有 Wiki 了。**
>
> v3.7.1 是 v3.7.0 之後的穩定性、文檔與體驗收口版：不重新改玩法概率，而是把繁簡指令相容、管理面板統計準確性，以及兩輪「今日小豬 Wiki」正式納入穩定發佈。

## 📖 今日小豬 Wiki 正式入圈

本版加入完整的 MkDocs Material Wiki，文檔源直接和插件程式碼放在同一個倉庫、同一套 PR / CI 裡維護，不再另外養一份容易漂移的 Wiki。

第一、第二輪 Wiki 已包含：

- 🐷 5 分鐘開始養豬
- 🎮 玩家玩法總覽
- 📚 永久圖鑑、新豬保底、跨日疲勞保底
- 🧪 可互動的 Pity Lab 保底實驗室
- ⭐ EX Lv.1–5 成長
- 🔥 60 / 30 / 10 烤群友 outcome 與次日保護
- 🎰 前端假烤架演示
- ⚡ Roast Charge 與群體烤箱補貨
- 📰 豬圈日報
- 🎨 做一隻自己的小豬／公共豬源投稿
- 🧯 症狀式故障排查
- 📖 指令、配置、資源、架構與維護 Reference

Wiki 有繁／簡中文搜尋詞庫、Light / Night 豬圈主題、卡片 3D hover、Charge 動效、EX shimmer、首頁小豬粒子效果，以及 `prefers-reduced-motion` / 手機降級。

**特效可以騷，正文不能看不清。**

## 🎨 做豬不需要先當運維

創作者指南重新把最簡單的真實路線放到第一位：

> **群內 @ 管理員 → 把圖片、名稱、描述、文案交給他 → 管理員代為新增、試抽、修改、投稿。**

普通群友不需要自己部署 AstrBot、不需要有伺服器，也不需要先學 manifest。

只有本來就在管理 RollPig 實例、或想長期維護大量小豬／私人豬源的進階創作者，才需要使用管理面板、本地 override 與 manifest 流程。

## 🈶 繁簡指令與 AstrBot dispatch 修復

包含 v3.7.0 發佈後合入的指令相容修復：

- 新增 `/豬圈日報狀態`、`/豬圈日報開啟`、`/豬圈日報關閉` compact 指令；
- 同時保留 `/豬圈日報 狀態|開啟|關閉` 帶空格形式；
- 簡體、繁體與常見混合字形 alias 一起驗證；
- adapter 只轉發到既有 Daily Report handler，不複製權限或狀態邏輯；
- AstrBot Market Smoke 使用當前官方 `CommandFilter` 驗證每個合法輸入只命中正確 handler，防止前綴誤吞或重複 dispatch。

## 📊 管理面板統計口徑校準

包含 v3.7.0 後合入的 Dashboard Accuracy & Motion：

- Overview / Analytics 採 claim-aware logical-user 統計；
- 已證明屬於同一人的 legacy fragment 不再重複計使用者、抽取與收藏；
- 重疊收藏次數採 `MAX`，避免 migration copy 虛增 EX；
- 移除用推導值拼出的假 sparkline，只保留可證明的歷史序列或明確標示的 snapshot；
- AI 文案成功率改為 `ready / (ready + failed)`，不把仍在 generating 的請求當失敗；
- 管理面板加入新的 telemetry、hover、halo、trend bar 等沉浸式動效，同樣尊重 reduced-motion。

## 🐷 Wiki 文案與規則校準

建 Wiki 的過程也順手抓出並修正了幾個舊文檔漂移：

- `ROAST-CHARGES.md` 不再把已經上線的 `/烤箱補貨` / `/添煤` 寫成「未來 Phase 3B」；
- 補貨文檔補齊 2 人群特殊門檻、30% / 最少 3 人 / 基礎上限 8、每成功一輪 +2、每日預設 2 輪、每人最多 +1 Charge 等現行規則；
- 保底頁明確說明百分比是「初始候選重複時的條件式重抽率」，不是無條件新豬概率；
- 60/30/10 頁明確區分真正 victim、逃脫、反噬與次日保護；
- 故障排查強調先判斷玩法阻擋／配置／資源／storage，再碰資料庫。

## 🧪 驗證

Wiki 兩輪合併前均經：

- `mkdocs build --strict --clean`
- Python 3.10 / 3.12 full pytest
- pre-commit
- Marketplace Package
- AstrBot Market Smoke / official plugin load worker

v3.7.1 發版 PR 會再次對完整最新 `main` 跑同一組發佈門檻。

## 升級

可由 **v3.7.0 直接升級**。

本版不修改：

- SQLite schema
- 永久收藏／EX 算法
- 新豬保底概率
- 60 / 30 / 10 烤豬概率
- Resource Protocol

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。
