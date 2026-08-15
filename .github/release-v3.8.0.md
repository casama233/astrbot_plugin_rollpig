# 今日小豬 · 增強版 v3.8.0

> **這次不是再補一個小 hotfix，而是把「養熟、添柴、說豬話、看 Wiki」四條線一起收成正式版本。**
>
> v3.8.0 集中完成官方 EX 內容、烤箱／預約安全、contextual `/添柴`、玩家文案與文檔統一，以及 Wiki 真正按內容寬度響應的版面系統。

## ⭐ 201 / 201 官方豬全部手寫 EX1–EX5

官方有效圖鑑現在完整覆蓋 **201 隻小豬 × 5 個 EX 等級**：

- 每隻都有明確手寫的 EX Lv.1–5；
- 五級 `description` 各不相同；
- 五級 `analysis` 各不相同；
- compatibility 恢復的舊官方豬也包含在正式 EX corpus；
- Resource Source 發布前會驗證 handcrafted EX ID 與最終官方豬 ID 完全一致。

通用 EX 生成器仍保留，但只作本地／非官方／未完成內容的安全兜底；正式官方豬不能靠模板混過 release gate。

EX 仍是展示與收藏成長層：**不修改豬 ID、抽取概率、保底、60/30/10 或玩法資格。**

## 🪵 `/添柴` 現在真的只要記一條命令

`/添柴` 成為玩家正式入口，並按群聊上下文自己判斷你在給哪口鍋送柴：

- `/添柴 @目標` → 明確加入該目標的待結算預約；
- 有烤箱補貨輪次時，裸 `/添柴` → 支持補貨；
- 沒有補貨且只有一張待結算預約時，裸 `/添柴` → 自動加入那張預約；
- 同時有多張預約時 → 要求 `@目標`，不替玩家亂猜；
- 主廚建立預約時已算第一位參與者，不能再把自己重複塞進柴火簿；
- 已 resolved 的預約保持終態，不會被競態請求重新打開。

舊 `/添煤`、`/加煤`、`/烤箱添煤`、`/烤箱添柴` 只保留為向後兼容入口，不再出現在玩家幫助與主文檔中。

## 🔥 烤箱補貨與預約結算再加一道保險

這版把群體補貨和預約的異常／競態邊界一起收緊：

- 補貨依賴父級烤群友玩法開關；
- 單輪補貨加入 TTL，預設 120 分鐘，超時殭屍輪會關閉；
- 補貨進入結算後若遇到 storage error，採 fail-closed 封帳，避免部分玩家已拿到 Charge 後重試再次發放；
- 若進程在 `completing` 階段中斷，重啟後同樣按已進入結算處理；
- 建立／添柴與抽豬觸發共用 reservation lock，鎖內再次確認目標狀態；
- 60% 成功 / 30% 逃脫 / 10% 反噬沒有改動。

## 🐷 整個插件開始說同一種「豬話」

玩家高頻文案、動態 `/豬豬幫助`、預約／補貨提示、錯誤 fallback、永久豬圈和官方基礎豬文案做了一次完整 Piggy Voice 收口。

其中 48 隻過去偏「人格測評模板」的官方基礎豬重新手寫 `analysis`，從抽象形容詞改成具體角色設定、群聊行為和最後補一刀的節奏。

`/我的豬圈` 也不再像後台資料表：

- `我的猪圈 · 猪籍档案`
- `现役入圈`
- `老猪留档`
- `最常返场`
- `老猪籍`
- `还没拱进你家`

但收藏 authority、歷史保留、排序、EX、總抽取次數與分頁規則完全不變。

群聊 mention 排版也統一為 `@某人` 單獨一行，再從下一行開始正文，長提示更容易掃讀。

## 📚 README / Wiki / 指令與配置文檔一起更新

這次文檔不是「功能改了順手補兩句」，而是完整審查玩家入口與維護手冊。實際修掉的過期資訊包括：

- 玩家頁仍主推 `/添煤`；
- `COMMANDS.md` 還把實作固定寫成 v3.6.3；
- 8 小時仍被描述成整個人的單一 cooldown，而不是每缺一格 Charge 的恢復時間；
- `CONFIGURATION.md` 漏掉 `group_roast_max_charges`；
- 預約配置 hint 沒有主推 `/添柴 @目標`。

新增文案／文檔 contract tests，之後這些語義再漂回去會直接讓 CI 變紅。

## 🖥️ Wiki 響應式改成看「真正內容寬度」

v3.7.3 先修了手機 Hero 被切掉；v3.8.0 進一步把整套自製 Wiki UI 改成真正的 responsive system。

MkDocs Material 的左右 navigation / TOC 會先吃掉桌面寬度，所以現在元件不只看 viewport，而是用 content container queries 根據 `.md-content__inner` 真正拿到的寬度變形。

同時修正 `md_in_html` 在最終 HTML 中自動加入 `<p>` wrapper 後，原先 direct-child flex/grid 規則失效的問題，涵蓋 Hero、HUD、按鈕、徽章、跑馬燈、Charge、OLD → NEW、60/30/10、creator pipeline、triage 等自製元件。

首頁桌面版會隱藏文檔 sidebar、讓 landing page 有更多空間；**手機版仍保留 Material navigation drawer**。中等寬度的頂部 tabs 改為安全橫向 scroll，不再硬擠標籤。

## 🧪 發版驗證

功能 PR 合併前已分別通過：

- Python 3.10 / 3.12 full pytest
- pre-commit
- Piggy Wiki strict build + rendered Markdown contract
- Marketplace Package
- AstrBot Market Smoke
- 當前官方 AstrBot plugin load worker
- AstrBot Resource Source（涉及 EX／官方資源的變更）

本發版 PR 會再基於所有 PR 已合併後的最新 `main` 跑一次完整門檻；合併後由既有 Release workflow 自動建立 `v3.8.0` tag、ZIP 與 `SHA256SUMS`。

## ⬆️ 升級

可由 **v3.7.3 直接升級到 v3.8.0**。

本版不修改：

- SQLite schema
- Resource Protocol v1
- 新豬保底算法與概率上限
- 60 / 30 / 10 烤豬 outcome
- Roast Charge 預設容量與恢復數值
- 永久收藏 authority / EX 等級計算公式

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。
