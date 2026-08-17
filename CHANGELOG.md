# 更新

## 未發佈

- 新增 GIF 小豬端到端支援：PigHub／手動上傳會保留動畫 GIF，不再一律轉成 PNG；抽到動畫小豬時整張小豬卡會逐幀合成並保留幀時長與循環設定；公共豬源投稿與審核圖片亦按實際格式保留 GIF。管理頁縮圖仍使用靜態 PNG 快取，並為動畫加入幀數、總時長與尺寸安全上限。
- README 首屏新增醒目的 AI 代碼風險提示：說明本插件代碼由 AI 生成並經人工審閱，但仍可能存在未發現缺陷、安全風險或相容性問題，建議重要環境部署前自行審查與測試。
- 修正管理面板 KPI 迷你圖的資料語義：累計抽取卡改畫真實「近 14 日每日抽取」而非人造累計斜線；今日活躍保留每日活躍趨勢，沒有歷史序列的四項快照指標不再顯示偽趨勢裝飾。
- `/豬豬幫助` 新增 `@` 指令輸入提示：請手動輸入指令後再選擇群友，直接複製他人的整條「指令 + @」消息可能無法被 AstrBot 當成結構化 At 指令識別（#134）。
- 新增 PR／Release 文檔維護門禁：每個 PR 都必須新增 Changelog 記錄並聲明 `Wiki-Impact`；canonical 指令與配置 schema 變更必須同步對應 Wiki，Release 在打包前會再次驗證版本 Changelog、Release Notes 與 Wiki 覆蓋。

## v3.9.1 (2026-08-17)

v3.9.1 是 v3.9.0 的維護版本，集中修正 **管理面板迷你趨勢圖失真** 與 **動態幫助卡繁簡混排／字型問題**，不改遊戲規則、資料格式或資源協議。

## 管理面板

- 修正頂部 KPI mini sparkline 仍以 0 作固定 Y 軸基線，令全部為正值的時間序列被壓扁；現在按實際局部 min/max 自適應縮放，並為平坦／非平坦資料加入安全留白。
- sparkline 幾何統一由實際 `width / height / padding` 計算，移除硬編碼 area baseline；SVG stroke 使用 `non-scaling-stroke`，卡片尺寸變化時不再把線寬一起拉伸。
- 這些變更只影響管理頁視覺呈現，不修改任何統計值或分析口徑。

## 動態幫助卡

- `/豬豬幫助` 生成的快速指令卡固定使用 **簡體中文 `zh-CN`**：標題、分類、說明、頁尾與顯示命令全部統一為簡體。
- 顯示命令改用已註冊的簡體 canonical 命令，例如 `/今日小猪`、`/我的猪圈`、`/猪圈日报`、`/烤箱补货`。
- renderer 不再優先使用 `font_traditional`，幫助卡統一使用標準中文 `font_bold`，避免繁體專用字型造成缺字、錯字形或繁簡混排。
- 幫助圖片 cache version 升級，舊的繁體 bitmap 不會繼續命中。
- 繁體指令 alias 仍完整保留；玩家仍可輸入 `/今日小豬`、`/豬豬幫助` 等舊指令，只是不再顯示於生成圖片。

## Changelog 維護

- 修復 `CHANGELOG.md` 在 v3.6.5 之後的歷史斷檔：重新以已發佈的 `.github/release-v*.md` 為來源回填 v3.7.0～v3.9.0 正式版本紀錄。
- 「未發佈」區重新清空，避免已經上線的功能長期留在未發佈章節造成版本語義錯亂。

## 本版合入 PR

- #131 — 修正管理面板 KPI mini sparkline 的局部縮放與 SVG 幾何。
- #132 — 快速指令幫助卡固定簡體中文並移除繁體字型依賴。

## 相容性

可由 v3.9.0 直接升級。本版不改變：

- SQLite schema 與永久豬籍 authority
- Resource Protocol v1
- 抽豬概率、新豬保底與跨日疲勞保底
- EX 等級計算
- Roast Charge、60/30/10、`/添柴` 與預約結算規則

## 驗證

- Python 3.10 / 3.12 全量 CI
- Marketplace Package
- AstrBot Market Smoke
- 管理趨勢 UI contract
- 動態幫助、字體、cache 與 Wiki bridge contract

## v3.9.0 (2026-08-16)

v3.9.0 聚焦在 **管理體驗、聊天可讀性、Wiki 與視覺一致性**。本版把原本已存在但分散的 EX 能力真正接回主管理頁，同時重做動態幫助、豬圈日報與管理分析視覺。

### 管理頁：EX 1–5 正式回到主流程

- 每張小豬卡與既有小豬編輯流程都可直接進入 **EX Lv.1–5 管理**。
- 可分級編輯短描述、完整文案、差分圖片，支援圖片上傳／移除／預覽與單層重設。
- 保留既有稀疏繼承規則，直接顯示每層「實際生效」結果與來源。
- 公共豬源詳情不再只有關閉按鈕：新增目前實例 EX 摘要、管理本地 EX、在本地圖鑑定位。
- 完全復用既有 `ExAdminMixin` / `ex/variants` API，沒有新增第二套 EX 儲存格式，也不改 EX 等級或玩法語義。

### 聊天圖片與字體

- `/豬豬幫助` 改成更短的雙欄瀑布流快速指令卡，移除大量卡中卡與無效留白；最壞完整功能組合也受高度回歸門檻保護。
- 幫助卡完整保留繁體中文字型路徑，避免罕見繁體字退回缺字／錯字形。
- 指令描述收斂成一句話，完整機制與數值交由 Wiki 說明。
- `豬圈日報` 重做為更緊湊的視覺戰報，改善資訊層級與聊天端掃讀效率。
- 圖鑑縮圖背景與管理面板視覺對齊，減少透明素材在不同頁面的底色落差。

### 管理分析

- 近 14 日豬圈脈搏由硬折線改為不改動真實數據點的平滑 Bézier 曲線。
- 修正趨勢面板被右欄強制拉高造成的大面積空白。
- 新增峰值活躍、日均活躍、14 日抽取總數、14 日新解鎖總數摘要帶。

### Wiki

- 玩家首頁、快速開始、玩法與故障排查進一步去重，降低相同規則散落多頁造成的維護漂移。
- 修復 AstrBot Plugin Page sandbox 內 Wiki 連結無法正常開啟的問題。
- Wiki 固定為 Slate 深色主題，移除容易造成視覺不一致的亮色切換路徑。

### 本版合入 PR

- #121 — 繁體幫助卡字型完整性
- #122 — 玩家 Wiki 去重與簡化
- #123 — 管理頁 Wiki sandbox 導航
- #124 — 緊湊動態幫助卡
- #125 — 14 日趨勢平滑與摘要
- #126 — 圖鑑縮圖背景一致性
- #127 — 主管理頁 EX 1–5 / 公共豬源操作整合
- #128 — 緊湊視覺豬圈日報
- #129 — Wiki 深色 Slate 單主題

### 相容性

可由 v3.8.1 直接升級。本版不改變：

- SQLite schema 與永久豬籍 authority
- Resource Protocol v1
- 抽豬概率、新豬保底與跨日疲勞保底
- EX 等級計算
- Roast Charge、60/30/10、`/添柴` 與預約結算規則

### 驗證

本批 PR 在合入過程中除各自 CI 外，針對重疊區域額外做了組合回歸：

- 繁體字型 + 緊湊幫助卡共同契約
- Wiki sandbox 導航 + 14 日趨勢 + EX 主管理頁共同契約
- EX integration JavaScript `node --check`
- Python 3.10 / 3.12 CI、Marketplace Package、AstrBot Market Smoke 由 release PR 再做最終整體驗證。

## v3.8.1 (2026-08-16)

這是一個針對 **AstrBot 後台插件首頁／升級殘留** 的修復版本。

### 修復內容

- 修復從舊版本以 overlay/overwrite 方式升級後，`pages/ex-manager/`、`pages/ex-public-source/` 可能殘留，導致 AstrBot 仍把 **EX 成長管理** 當成插件主管理頁的問題。
- 新增啟動時 installation migration：確認新版替代頁存在後，自動清理 RollPig 明確擁有的 legacy Plugin Page。
- 若舊 Page 目錄因權限或文件佔用無法完整刪除，會退而停用其 `index.html`，避免 AstrBot 繼續 discover 舊入口。
- 替代頁缺失時不刪舊頁；未知／使用者自建 Page 不會被 migration 觸碰。
- 新增真實 overlay-upgrade 回歸測試，直接驗證舊 `ex-manager` 殘留 → migration → `pig-manager` 恢復為第一個 Plugin Page 的完整流程。
- 將 installation migration module 納入 CI 顯式 compile gate。

### 升級後預期

AstrBot Plugin Page 應只發現：

1. `pig-manager` — 豬圈管理（預設首頁）
2. `pig-manager-ex` — EX 成長管理
3. `pig-manager-ex-public-source` — EX 公共源

已受舊版殘留影響的安裝，在載入 v3.8.1 後會自動自愈，不需要手動刪除舊 Page 目錄。

### 相容性

可由 v3.8.0 直接升級。本版不修改：

- SQLite schema
- Resource Protocol v1
- 抽豬概率／新豬保底
- EX 等級計算與官方 EX 文案
- Roast Charge／`/添柴` 數值與結算
- 永久豬籍 authority

### 驗證

修復 PR #119 已通過：

- CI（Python 3.10 / 3.12）
- Marketplace Package
- AstrBot Market Smoke
- 官方 AstrBot plugin load worker

## v3.8.0 (2026-08-15)

> **這次不是再補一個小 hotfix，而是把「養熟、添柴、說豬話、看 Wiki」四條線一起收成正式版本。**
>
> v3.8.0 集中完成官方 EX 內容、烤箱／預約安全、contextual `/添柴`、玩家文案與文檔統一，以及 Wiki 真正按內容寬度響應的版面系統。

### ⭐ 201 / 201 官方豬全部手寫 EX1–EX5

官方有效圖鑑現在完整覆蓋 **201 隻小豬 × 5 個 EX 等級**：

- 每隻都有明確手寫的 EX Lv.1–5；
- 五級 `description` 各不相同；
- 五級 `analysis` 各不相同；
- compatibility 恢復的舊官方豬也包含在正式 EX corpus；
- Resource Source 發布前會驗證 handcrafted EX ID 與最終官方豬 ID 完全一致。

通用 EX 生成器仍保留，但只作本地／非官方／未完成內容的安全兜底；正式官方豬不能靠模板混過 release gate。

EX 仍是展示與收藏成長層：**不修改豬 ID、抽取概率、保底、60/30/10 或玩法資格。**

### 🪵 `/添柴` 現在真的只要記一條命令

`/添柴` 成為玩家正式入口，並按群聊上下文自己判斷你在給哪口鍋送柴：

- `/添柴 @目標` → 明確加入該目標的待結算預約；
- 有烤箱補貨輪次時，裸 `/添柴` → 支持補貨；
- 沒有補貨且只有一張待結算預約時，裸 `/添柴` → 自動加入那張預約；
- 同時有多張預約時 → 要求 `@目標`，不替玩家亂猜；
- 主廚建立預約時已算第一位參與者，不能再把自己重複塞進柴火簿；
- 已 resolved 的預約保持終態，不會被競態請求重新打開。

舊 `/添煤`、`/加煤`、`/烤箱添煤`、`/烤箱添柴` 只保留為向後兼容入口，不再出現在玩家幫助與主文檔中。

### 🔥 烤箱補貨與預約結算再加一道保險

這版把群體補貨和預約的異常／競態邊界一起收緊：

- 補貨依賴父級烤群友玩法開關；
- 單輪補貨加入 TTL，預設 120 分鐘，超時殭屍輪會關閉；
- 補貨進入結算後若遇到 storage error，採 fail-closed 封帳，避免部分玩家已拿到 Charge 後重試再次發放；
- 若進程在 `completing` 階段中斷，重啟後同樣按已進入結算處理；
- 建立／添柴與抽豬觸發共用 reservation lock，鎖內再次確認目標狀態；
- 60% 成功 / 30% 逃脫 / 10% 反噬沒有改動。

### 🐷 整個插件開始說同一種「豬話」

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

### 📚 README / Wiki / 指令與配置文檔一起更新

這次文檔不是「功能改了順手補兩句」，而是完整審查玩家入口與維護手冊。實際修掉的過期資訊包括：

- 玩家頁仍主推 `/添煤`；
- `COMMANDS.md` 還把實作固定寫成 v3.6.3；
- 8 小時仍被描述成整個人的單一 cooldown，而不是每缺一格 Charge 的恢復時間；
- `CONFIGURATION.md` 漏掉 `group_roast_max_charges`；
- 預約配置 hint 沒有主推 `/添柴 @目標`。

新增文案／文檔 contract tests，之後這些語義再漂回去會直接讓 CI 變紅。

### 🖥️ Wiki 響應式改成看「真正內容寬度」

v3.7.3 先修了手機 Hero 被切掉；v3.8.0 進一步把整套自製 Wiki UI 改成真正的 responsive system。

MkDocs Material 的左右 navigation / TOC 會先吃掉桌面寬度，所以現在元件不只看 viewport，而是用 content container queries 根據 `.md-content__inner` 真正拿到的寬度變形。

同時修正 `md_in_html` 在最終 HTML 中自動加入 `<p>` wrapper 後，原先 direct-child flex/grid 規則失效的問題，涵蓋 Hero、HUD、按鈕、徽章、跑馬燈、Charge、OLD → NEW、60/30/10、creator pipeline、triage 等自製元件。

首頁桌面版會隱藏文檔 sidebar、讓 landing page 有更多空間；**手機版仍保留 Material navigation drawer**。中等寬度的頂部 tabs 改為安全橫向 scroll，不再硬擠標籤。

### 🧪 發版驗證

功能 PR 合併前已分別通過：

- Python 3.10 / 3.12 full pytest
- pre-commit
- Piggy Wiki strict build + rendered Markdown contract
- Marketplace Package
- AstrBot Market Smoke
- 當前官方 AstrBot plugin load worker
- AstrBot Resource Source（涉及 EX／官方資源的變更）

本發版 PR 會再基於所有 PR 已合併後的最新 `main` 跑一次完整門檻；合併後由既有 Release workflow 自動建立 `v3.8.0` tag、ZIP 與 `SHA256SUMS`。

### ⬆️ 升級

可由 **v3.7.3 直接升級到 v3.8.0**。

本版不修改：

- SQLite schema
- Resource Protocol v1
- 新豬保底算法與概率上限
- 60 / 30 / 10 烤豬 outcome
- Roast Charge 預設容量與恢復數值
- 永久收藏 authority / EX 等級計算公式

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。

## v3.7.3 (2026-08-15)

> **這次不加新玩法，專心把兩個明顯的介面回歸收乾淨。**
>
> v3.7.3 是 v3.7.2 的穩定性 hotfix：修回 AstrBot 主管理入口，並修正 Wiki v3 首頁在手機上的裁切問題。

### 🐷 豬圈管理重新成為預設入口

新增 EX 獨立 Plugin Pages 後，AstrBot 會按 Page 目錄名排序，側欄又直接打開第一個 Page；原本的 `ex-manager` 因此排在 `pig-manager` 前面，造成點擊「今日小豬」時先進 EX 成長管理，看起來像原本的數據總覽、豬豬圖鑑與本地資源整頁消失。

本版已把入口順序重新固定為：

1. `pig-manager` — 豬圈管理（預設）
2. `pig-manager-ex` — EX 成長管理
3. `pig-manager-ex-public-source` — EX 公共源

原主管理頁的數據統計、豬豬管理、本地／雲端資源與既有管理功能都沒有被刪除；這次只是修正 AstrBot 的預設 Page 選擇結果。

同時加入回歸測試，之後再新增 Plugin Page 時，如果 `pig-manager` 被擠出第一位，CI 會直接失敗。

> 如果你曾經手動收藏舊的 `ex-manager` / `ex-public-source` Plugin Page 深鏈，升級後請改用新的 Page 名稱；從 AstrBot 正常 UI 進入不需要額外操作。

### 📱 Wiki v3 手機版不再被切掉右半邊

修正首頁 Hero 被 intrinsic / min-content 寬度反向撐開、再被 `overflow: hidden` 裁掉的問題。

本版新增最後載入的 mobile containment layer，並針對 900 / 600 / 430px 斷點收斂：

- Hero grid 改用 `minmax(0, 1fr)`；
- Hero 內容、console、CTA、徽章與 live strip 補上安全的 `min-width: 0` / `max-width: 100%`；
- kicker、CTA、badge 可以正常換行；
- 小螢幕 Hero padding、標題字級與 CTA 重新收斂；
- 430px 以下 HUD stats 收成單欄。

桌面版 Wiki v3 的原視覺與動畫保留不變。

### 🧪 發版驗證

合併前的完整整合 revision 已通過：

- Python 3.10 / 3.12 CI
- Piggy Wiki strict build / rendered checks
- Marketplace Package
- AstrBot Market Smoke
- 當前官方 AstrBot plugin load worker

發版 PR 會再對最新 `main` 執行完整門檻；合併後由既有 Release workflow 自動建立 `v3.7.3` tag、ZIP 與 `SHA256SUMS`。

### ⬆️ 升級

可由 **v3.7.2 直接升級**。

本版不修改：

- SQLite schema
- 永久收藏 / EX 成長算法
- 新豬保底概率
- 60 / 30 / 10 烤豬概率
- Roast Charge 核心規則
- Resource Protocol 公開契約

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。

## v3.7.2 (2026-08-15)

> **Wiki 不再只是站在門外。這次它真的搬進插件裡了。**
>
> v3.7.2 是一個「把整座豬圈接起來」的體驗收口版：插件幫助、管理面板、玩家 Wiki、手機響應式與公共豬源運維邊界全部重新接好。玩法概率沒偷偷動，豬還是那些豬——只是現在更知道該去哪裡找答案了。

### 📖 插件 ↔ Wiki：正式接線

`/豬豬幫助` 不再只是一張孤零零的幫助圖：

- 幫助圖底部新增 **今日小豬 Wiki** CTA；
- 發圖後再補一條可直接點擊的 Wiki URL；
- 幫助圖生成失敗時，直接給排障入口；
- 幫助快取版本升級，舊快取不會繼續把新入口藏起來。

管理面板右上角也新增 `📚 文檔`：

- 📖 玩家 Wiki
- ⚙️ 管理員手冊
- 🎨 投稿指南

真正需要排查時，插件會開始把你送到**對的那一頁**：

- 豬源同步失敗 / 403 / 校驗 / timeout → 直接進「豬源同步排障」；
- 管理頁深度分析 / Plugin Page Bridge 載入失敗 → 直接進「管理頁定向排障」。

兩個深鏈使用固定 anchor，Wiki CI 會檢查最終 HTML 真的存在對應位置，避免某天改個中文標題就把插件裡的連結炸掉。

一句話：

> **不要再把所有錯誤都丟給 README。**

### 🎮 Wiki v3：群友先玩，管理員靠後

這一輪重新校準了 Wiki 的主要讀者：**普通群友。**

原本的「5 分鐘開始養豬」改成 **「30 秒開始養豬」**，把不屬於玩家 onboarding 的「安裝插件」「重啟 AstrBot」拿掉。

現在第一次進 Wiki，只需要知道三件事：

1. `/今日小豬`
2. `/我的豬圈`
3. `/烤群友`、補貨、添煤、日報——然後事情開始失控。

安裝、遷移、資源同步、備份與運維全部退回管理員區，不再堵在群友第一步前面。

首頁也進一步「豬化」：

- Pigsty LIVE HUD
- 玩法跑馬燈
- 霓虹 / 玻璃層次
- Roast Charge 能量視覺
- 更明顯的卡片 hover depth 與按鈕掃光
- OLD → NEW 改成非強制等高的進化結構
- 寬屏 Hero 中文標題改按容器寬度縮放，不再在有右側 TOC 時被撐成接近直排

手機響應式與 `prefers-reduced-motion` 仍保留，不拿可讀性換特效。

### 📱 管理面板：手機上終於不互相打架

管理面板補了一輪平板 / 手機 / 小屏手機響應式收口：

- `900px`：topbar、品牌區與導航可以安全收縮，不再把整頁撐出橫向滾動；
- `680px`：儲存、更新、公共源與 Dialog 操作組重新堆疊，長標籤不再擠成奇怪的按鈕牆；
- `440px`：圖鑑 / PigHub 網格收成單欄，Dialog 與 toast 留在動態視口內；
- coarse-pointer 裝置補足 44px 觸控目標。

同時新增 browser regression contract，把 900 / 680 / 440 三個斷點鎖進測試。

### 🔒 公共豬源：插件客戶端公開，服務端運維退到私有

本版也完成公共豬源的倉庫邊界收口。

公開插件倉庫**繼續保留**：

- 插件側投稿 / 審核整合與管理 UI；
- Resource Protocol v1 公開契約與資源 builder；
- EX schema / manifest 行為；
- 相容性基線邏輯與客戶端回歸測試。

但公共源的**服務端實作、systemd / Nginx 生產配置、線上遷移命令與服務端審核回歸**不再留在目前公開插件 tree 中，由服務端運維側獨立維護。

這不是 Git 歷史重寫；以前已公開的 commit 仍然存在。這次只是把「插件應該公開的協議 / 客戶端」和「服務端生產運維面」重新劃清邊界。

對普通插件使用者沒有額外操作要求。

### 🧪 發版門檻

本輪各功能合併前已分別通過：

- Python 3.10 / 3.12 full pytest
- pre-commit
- Marketplace Package
- Piggy Wiki `mkdocs build --strict --clean`
- Wiki rendered HTML / stable deep-link gate
- AstrBot Resource Source（涉及資源邊界的變更）
- AstrBot Market Smoke
- 當前官方 AstrBot plugin load worker

v3.7.2 發版 PR 會再對**完整最新 main**跑一輪正式驗證，再由倉庫既有 Release workflow 自動產出 tag、ZIP 與 `SHA256SUMS`。

### ⬆️ 升級

可由 **v3.7.1 直接升級**。

本版不修改：

- SQLite schema
- 永久收藏 / EX 成長算法
- 新豬保底概率
- 60 / 30 / 10 烤豬概率
- Roast Charge 核心規則
- Resource Protocol 公開契約

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。

---

**豬圈沒有突然多一套數值。**

只是現在：

> 你抽完豬知道去哪看玩法；出錯知道去哪排查；管理員拿手機也不必和按鈕搏鬥；而服務端的後廚門，也終於不再敞在公共插件倉庫裡。

## v3.7.1 (2026-08-15)

> **豬圈開始有 Wiki 了。**
>
> v3.7.1 是 v3.7.0 之後的穩定性、文檔與體驗收口版：不重新改玩法概率，而是把繁簡指令相容、管理面板統計準確性，以及兩輪「今日小豬 Wiki」正式納入穩定發佈。

### 📖 今日小豬 Wiki 正式入圈

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

### 🎨 做豬不需要先當運維

創作者指南重新把最簡單的真實路線放到第一位：

> **群內 @ 管理員 → 把圖片、名稱、描述、文案交給他 → 管理員代為新增、試抽、修改、投稿。**

普通群友不需要自己部署 AstrBot、不需要有伺服器，也不需要先學 manifest。

只有本來就在管理 RollPig 實例、或想長期維護大量小豬／私人豬源的進階創作者，才需要使用管理面板、本地 override 與 manifest 流程。

### 🈶 繁簡指令與 AstrBot dispatch 修復

包含 v3.7.0 發佈後合入的指令相容修復：

- 新增 `/豬圈日報狀態`、`/豬圈日報開啟`、`/豬圈日報關閉` compact 指令；
- 同時保留 `/豬圈日報 狀態|開啟|關閉` 帶空格形式；
- 簡體、繁體與常見混合字形 alias 一起驗證；
- adapter 只轉發到既有 Daily Report handler，不複製權限或狀態邏輯；
- AstrBot Market Smoke 使用當前官方 `CommandFilter` 驗證每個合法輸入只命中正確 handler，防止前綴誤吞或重複 dispatch。

### 📊 管理面板統計口徑校準

包含 v3.7.0 後合入的 Dashboard Accuracy & Motion：

- Overview / Analytics 採 claim-aware logical-user 統計；
- 已證明屬於同一人的 legacy fragment 不再重複計使用者、抽取與收藏；
- 重疊收藏次數採 `MAX`，避免 migration copy 虛增 EX；
- 移除用推導值拼出的假 sparkline，只保留可證明的歷史序列或明確標示的 snapshot；
- AI 文案成功率改為 `ready / (ready + failed)`，不把仍在 generating 的請求當失敗；
- 管理面板加入新的 telemetry、hover、halo、trend bar 等沉浸式動效，同樣尊重 reduced-motion。

### 🐷 Wiki 文案與規則校準

建 Wiki 的過程也順手抓出並修正了幾個舊文檔漂移：

- `ROAST-CHARGES.md` 不再把已經上線的 `/烤箱補貨` / `/添煤` 寫成「未來 Phase 3B」；
- 補貨文檔補齊 2 人群特殊門檻、30% / 最少 3 人 / 基礎上限 8、每成功一輪 +2、每日預設 2 輪、每人最多 +1 Charge 等現行規則；
- 保底頁明確說明百分比是「初始候選重複時的條件式重抽率」，不是無條件新豬概率；
- 60/30/10 頁明確區分真正 victim、逃脫、反噬與次日保護；
- 故障排查強調先判斷玩法阻擋／配置／資源／storage，再碰資料庫。

### 🧪 驗證

Wiki 兩輪合併前均經：

- `mkdocs build --strict --clean`
- Python 3.10 / 3.12 full pytest
- pre-commit
- Marketplace Package
- AstrBot Market Smoke / official plugin load worker

v3.7.1 發版 PR 會再次對完整最新 `main` 跑同一組發佈門檻。

### 升級

可由 **v3.7.0 直接升級**。

本版不修改：

- SQLite schema
- 永久收藏／EX 算法
- 新豬保底概率
- 60 / 30 / 10 烤豬概率
- Resource Protocol

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。

## v3.7.0 (2026-08-15)

v3.7.0 是 v3.6.5 之後的玩法與架構大型更新。本版把「烤群友」從單一硬冷卻升級成可儲存 Charge，加入群體協作烤箱補貨，同時重做動態幫助、渲染與讀取快取、狀態持久化，以及公共豬源審核／瀏覽體驗。

### 🔥 Phase 3：烤箱 Charge

- 普通 `/烤群友` 與建立預約改為按「使用者 × 群組」消耗烤箱能量，預設 **2 格**。
- 每格沿用原 `group_roast_cooldown_hours` 作自然恢復週期；`group_roast_max_charges` 可配置 1–5 格。
- SQLite / JSON 共用同一 token-bucket policy，避免兩套後端出現玩法差異。
- 舊版 `roast_cooldowns.last_used_at` 以 lazy migration 轉成 charge state：仍在舊冷卻中的玩家視為已消耗一格，不會因升級被重置，也不會被雙重懲罰。
- 預約第一位主廚消耗一格；後續添柴與目標日後觸發不重複消耗。
- 後門 bypass、烤豬資格判定與既有 **60 / 30 / 10** outcome policy 保持不變。

### ⛽ 群體烤箱補貨

- 新增群體協作補貨玩法，讓當日活躍群友共同恢復烤箱能源，而不是單純等待硬冷卻。
- 補貨按群組／自然日保存狀態，支援參與者去重、進度、成功輪次與每日限制。
- 成功補貨只恢復有限 Charge，且受最大能量上限約束，不會形成無限烤豬。
- 補貨事件接入 Gameplay Event 與豬圈日報，可追蹤補貨成功與添煤參與。
- SQLite primary write path、JSON 相容路徑與初始化／恢復流程均加入回歸測試。

### 🧭 動態幫助系統

- `/豬豬幫助` 升級為依目前功能、配置與指令面動態生成的幫助內容。
- 幫助渲染拆到獨立 renderer / feature boundary，避免把命令註冊、業務邏輯與 PIL 繪圖重新混在一起。
- 新增幫助卡與文字 fallback 測試，確保新功能加入後不再依賴手動維護一張容易過期的靜態說明。

### ⚡ 渲染、讀取與持久化效能

- 新增豬卡渲染快取與 renderer performance contracts，降低重複圖片合成開銷。
- 加入渲染 backpressure，避免高併發下無限制堆積昂貴的 PIL 任務。
- Resource read path 增加快取，減少相同 catalog / image resolution 的重複查找。
- 新增集中式 state persistence 邊界，降低高頻玩法狀態寫入造成的重複 I/O。
- 相關 cache / persistence 均有失效與回歸測試，資料權威仍由現有 storage/domain write 邊界控制。

### 🐷 公共豬源審核與正式源瀏覽

- 修復 AstrBot Plugin Page sandbox 下，批准／拒絕依賴原生 `window.confirm` / `window.prompt` 而可能完全無反應的問題；改為頁內審核對話框與明確二次確認。
- 公共豬源管理新增正式源圖鑑瀏覽器：支援搜尋 ID、名稱、描述／完整文案、分頁、圖片預覽與完整資料查看。
- 疑似重複提示可直接跳到現有正式公共豬，縮短人工審核流程。
- 正式源資料經 AstrBot 本地同源代理讀取，圖片不要求 sandbox 直接跨域訪問外部來源。
- 批准／拒絕補上真實 mutation 回歸測試，避免 UI 看似成功、實際沒有提交審核動作。

### 📰 豬圈日報安全收口

- 群組自動日報的開啟／關閉權限進一步收緊為 AstrBot 管理員。
- 固化祭品契約：`daily_report_random_eat_enabled` 預設關閉，且只有定時自動日報流程可觸發；手動 `/豬圈日報` 永遠只讀，不改變玩家祭品狀態。
- Charge／補貨事件可進入日報聚合，但日報本身不成為玩法 state authority。

### 🧪 驗證與相容性

- 本輪功能在合併前均經 Python 測試、compile、pre-commit 與 AstrBot / Marketplace 既有 CI 契約驗證。
- 可由 **v3.6.5 直接升級**。
- Charge 會對舊 roast cooldown 做惰性兼容遷移；不需要使用者手工改資料。
- 永久圖鑑、EX、保底與既有 60/30/10 烤豬 outcome 語義不因本次更新重新計算。

### 升級建議

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。若你自行維護公共源審核服務，請同時同步本版對應的 source review 前後端檔案，以取得完整審核與瀏覽修復。

## v3.6.5 (2026-08-15)

### 版本主題：群日報 opt-in、收藏身份安全與公共源審核加固

### 修復

- 豬圈日報自動推送改為 **per-group opt-in**：新群與既有未標記群一律默認關閉；只有群主、群管理員或 AstrBot 管理員使用 `/豬圈日報 開啟` 後才會自動推送，並提供 `/豬圈日報 關閉`、`/豬圈日報 狀態`。全局 `daily_report_auto_send` 僅保留為 master switch。
- scheduler 只遍歷顯式啟用群，`auto_enabled_since` 阻止新開啟群補發更早日期；23:50 + 隨機延遲被限制在報告自然日內，不再跨午夜。
- 修正日報「熱門豬」誤導：當所有豬都只出現一次時，不再任選一隻標成最熱門，改為明確顯示形態分散；若烤豬 storage 總量包含缺少 Gameplay Event 人物明細的舊記錄，保留真實總量並標註缺失明細，人物稱號只按可追溯事件計算。
- 修復公共源審核圖片代理使用錯誤 GET query API 導致管理頁只顯示 🐽 fallback；改用 AstrBot `request.query`，並為 review list/image 敏感 GET 加 same-origin + CSRF。
- 公共源審核新增現役 catalog 的正規化名稱近似與 64-bit dHash 圖片感知相似提示；提示只輔助人工審核，不會自動拒絕合理變體，同 ID／待審完全相同 SHA-256 仍為硬拒絕。

### 資料與身份安全

- 完成 claim-aware Collection Identity Boundary：`CollectionService` 只讀取目前 namespaced identity 與已由 `identity_claims` 證明屬於同一 logical user 的舊 fragment，不自動合併 sibling Bot instance，也不把其他平台同 raw ID 的資料串入。
- 永久 ownership 可跨安全 fragment 聯集；`first_unlocked` 取最早、`last_drawn` 取最晚、同豬 `count` 取 `max` 而不是相加，避免 migration copy 虛增 EX Lv.。
- `duplicate_streak`、`total_draws`、`active_days` 不跨 fragment 算術合併；目前 gameplay state 仍以最高優先級 fragment 為權威，舊資料不會把已失效保底重新帶回。

### 公共源安全

- 明確區分協議門檻與身份認證：`User-Agent` / `X-RollPig-*` 可被開源客戶端模擬，只作 protocol gate；公開投稿安全依賴內容驗證、來源 HMAC 指紋節流、人工審核與服務端管理 token。
- 新增全局待審上限 200，duplicate index 依 canonical `pig.json` revision cache，避免每次刷新重算全 catalog 圖片。
- review service systemd sandbox 增加 `PrivateDevices`、`ProtectHome`、`ProtectKernel*`、`ProtectControlGroups`、`LockPersonality`、`MemoryDenyWriteExecute`、`RestrictAddressFamilies`；管理 Bearer token 仍只存在維護者主機，不進插件配置或瀏覽器。

### 相容性

- 可由 **v3.6.4 直接升級**；不修改 SQLite schema、玩家抽取權威、EX 算法、保底概率、烤豬概率或 Resource Protocol。
- 本版不包含烤箱 charge/refill 新玩法。
- 公共源審核的服務端 duplicate/security 加固需要維護者主機同步新版 `source_service/app.py` 與 systemd unit；一般插件使用者只需正常更新插件。

## v3.6.4 (2026-08-14)

### 版本主題：公共豬源兼容與 QQ 圖鑑投遞修復

### 修復

- 修復 v3.4.0 將舊 Felis 預設資源源切換到 AstrBot 專用源時，只以內置 99 隻小豬建立首版來源造成的內容縮水；固定 v3.4 cut-over 前最後一個 Felis RollPig 快照（199 IDs）作 compatibility floor，官方源必須保持其超集，同 ID 仍以目前 AstrBot canonical 資料與圖片為準。
- 新增公共源兼容建構與 live canonical 原子遷移工具；CI 固定舊快照 commit / resource version / pig.json SHA-256，禁止跟隨可變 Felis main，並以 `miku-pig`、`wechat-pig`、`duke-pig` 作回歸哨兵。
- 修復 QQ/NapCat/NTQQ 已實際送達 `/我的豬圈` 圖片，但等待 `NodeIKernelMsgService/sendMsg` 回執超時返回 `retcode=1200` 時，被誤報為「圖鑑圖片生成失敗」；此類 ACK timeout 現在視為投遞結果不確定，只記 warning、不重試、不發失敗提示，避免重複圖片。
- `/我的豬圈` 將圖片渲染與消息投遞錯誤分離；真正 render error 與真正 send error 使用不同提示，且頁碼範圍改按永久 display catalog 計算。

### 相容性

- 可由 **v3.6.3 直接升級**；不修改 SQLite schema、玩家 ownership、EX count、保底、烤豬概率或 Resource Protocol 版本。
- PR #68 identity-fragment merge 仍未包含；本版不引入烤箱 charge/refill 等新玩法。

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

## v3.6.1 (2026-08-14)

### 版本主題：指令隔離與資源自癒 Hotfix

### 修復

- 修復 `豬圈日報` 同時由 `daily_report_feature` 與 `legacy_main` 註冊造成 AstrBot 指令衝突；僅保留完整統計海報實作。
- RollPig 聊天指令在匹配後主動停止事件繼續傳播，避免 `/今日小豬` 等指令完成後仍落入其他插件或 LLM。
- AI 料理／繁體文案優先使用發行包內 `荆南麦圆体.otf`，不再因缺少舊的獨立繁體字體而誤用 Pillow 預設字體。
- 當歷史／本地 PigHub 小豬仍保有可信 `source_url` 但圖片檔遺失時，發送前會安全地重新下載、校驗並恢復本地圖片；失敗仍維持既有無圖降級。
- 已有版本狀態但本地 cloud cache 圖片不完整時，插件重啟後會提前嘗試完整原子重同步，不必等待正常同步週期。

## v3.6.0 (2026-08-14)

### 版本主題：群聊成長、完整日報與發行穩定性

### 新功能

- 豬圈日報升級為可配置統計海報與自動推送系統：加入真實並列稱號、平台頭像、跨午夜日期鎖定、重啟補發與可選「今日祭品」；手動查看不觸發祭品。

- 新增可配置預約烤豬：明確指定尚未抽豬的目標時，第一位主廚支付普通冷卻建立同群當日預約，後續群友可免費添柴；目標本人在同群顯示今日小豬後一次性按原 60/30/10 結算。
- 預約預設最多 12 人（可配置 2–20），建立時尊重昨日被烤保護；隨機烤與後門不建立預約，添柴不直接提高成功率。
- 預約狀態在消息投遞前先標記 resolved，避免適配器超時造成重複結算；流程接入 `roast_reservation_created/joined/triggered` 與既有燒烤 outcome Gameplay Event，因此日報可沿用原統計。
- 新增 [`docs/ROAST-RESERVATIONS.md`](docs/ROAST-RESERVATIONS.md) 說明群／日隔離、冷卻支付與一次性語義。
- 新增 EX Lv.1–5 稀疏成長差分：同一隻小豬可按玩家既有 `count - 1` EX 等級替換圖片、描述或完整文案，各欄位獨立向下繼承；EX 5 以上沿用最後有效差分。
- AstrBot Resource Protocol v1 增加可選 `pig_ex_variants.json`／`variant_images`，仍沿用大小、SHA-256、圖片解碼、128 MiB 預算、staging 與原子切換；舊 v1／私人來源不需要修改。
- 本地小豬 override 仍高於遠端／內置 EX 差分；`/明日小豬` 預測不套用玩家已擁有的 EX 成長，避免把收藏狀態洩漏到未來結果。
- 群聊本人重複抽取可寫入去重的 `ex_level_up` Gameplay Event，為後續日報與成就統計提供資料，不改變收藏權威狀態。
- 新增 [`docs/EX-VARIANTS.md`](docs/EX-VARIANTS.md) 說明格式、繼承、安全邊界與目前尚未包含的管理面板 EX 編輯／投稿範圍。


### 修復

- 修復管理面板「投稿公共源」在 sandbox 中依賴原生 `window.confirm` 導致點擊無反應；改用頁面內二次點擊確認並補齊成功／失敗反饋與回歸測試。
- 修復 v3.5.0 發行包排除 `resource/font/荆南麦圆体.otf` 導致 Linux 中文標題可能回退 DejaVu 顯示方框；Release／Marketplace 現在強制打包並在 CI 中斷言字體存在。

### 架構

- 新增共用 `gameplay_events.py` Gameplay Event v1 契約；PR #51 的日報事件保持原 JSON 相容，並改由共用寫入／去重／讀取／裁剪函式管理。
- `DailyReportMixin` 增加 `_record_gameplay_event()` 作為後續 EX 成長、預約烤豬與烤箱補貨的統一事件入口；原 `_record_daily_report_event()` 開關語義保持不變。
- 新增 `docs/ARCHITECTURE.md`，記錄漸進式拆分與事件持久化邊界。

## v3.5.0 (2026-08-14)

### 版本主題：自己的公共豬源與審核工作流

- 將本地小豬投稿從 PigHub 改為本專案自建的 AstrBot 公共豬源；PigHub 僅保留為管理面板選圖來源。
- 投稿會在管理員再次確認後傳送 ID、名稱、描述、完整文案及標準化圖片，不會傳送群友、群組、聊天、配置或存儲資料。
- 新增獨立審核服務、SQLite 隊列、重複 ID／圖片攔截、來源 HMAC 指紋及 24 小時投稿限速。
- 維護者面板新增待審核卡片、圖片預覽、批准發佈與拒絕功能；普通實例自動隱藏該區域。
- 審核 Token 僅由來源服務與維護者插件後端讀取，不進公開配置，也不下發瀏覽器。
- 批准投稿後先使用正式建構器全量校驗，再建立不可變資源版本、備份 canonical catalog 並原子切換 `v1`。
- 發佈失敗會恢復原 catalog；服務啟動時可修復已完成發佈但審核狀態尚未落庫的短暫崩潰窗口。
- 新增 OpenResty、systemd 部署範本與公共源維護文檔；正式插件 ZIP 排除服務端原始碼及部署檔。
- README、資源管理、運維、配置、文檔索引與市場描述更新到 v3.5.0。

## v3.4.0 (2026-08-14)

### 版本主題：AstrBot 專用豬源

- 建立 `AstrBot RollPig Resource Protocol v1`，以 `schema_version`、`client`、版本化 User-Agent 及專用請求標頭區分 AstrBot 增強版客戶端。
- 上線 `https://curryudon.top/astrbot-rollpig/v1/manifest.json`，首版提供完整 99 筆小豬資料與 99 張圖片。
- 普通瀏覽器、錯誤 Client／Protocol 與 nonebot 客戶端請求回傳 HTTP 403；正確 AstrBot v1 請求回傳 200。
- 新安裝預設啟用新來源；舊 `pig.felislab.cc` 受限地址會精確遷移，自訂私人來源不會被覆蓋。
- 官方來源強制校驗 manifest 的協議版本與客戶端標識；私人 manifest 保留向下兼容。
- 新增可重現的資源源建構器，拒絕壞資料、缺圖、多圖、非法 ID、超大或無法解碼圖片，並生成逐檔大小及 SHA-256。
- 新增資源源 CI Artifact、OpenResty 路由範本及完整維護手冊，正式部署採不可變版本目錄與原子連結切換，支援快速回退。
- 明確說明專用標頭是相容性閘門而非秘密；真正封閉的私人源應另加每實例 Token 或 mTLS。

## v3.3.0 (2026-08-14)

### 版本主題：可視化資源治理

這個版本把小豬素材從「只能新增、編輯、刪除」提升為可觀察、可恢復、可投稿、可接入私人源的完整管理流程；同時清理失效的預設雲源及專案展示資訊。

### 新功能

- 管理面板新增「本地資源」工作區，分開展示本地新增、基礎源覆蓋與刪除屏蔽。
- 每筆本地記錄會標示是否覆蓋基礎源、是否使用本地圖片，並可直接進入編輯。
- 新增取消屏蔽 API 與管理操作；SQLite 單一權威及舊 SQLite 兼容模式均以事務移除 tombstone。
- 編輯小豬時可下載目前生效的完整原圖，供本地重修後重新上傳。
- 本地小豬可在管理員明確確認後，依 PigHub 公開網頁流程提交名稱與圖片到人工審核隊列。

### 雲端與私人源

- 查明舊預設 `pig.felislab.cc` 會對本 AstrBot 插件回傳 HTTP 403，原因是來源只授權官方 `nonebot-plugin-rollpig-plus` 客戶端。
- 新安裝預設關閉資源同步，`resource_manifest_url` 預設留空，避免持續請求已知不相容來源。
- 既有配置不會被更新程序靜默刪除；面板會保留錯誤並給出針對性診斷。
- 面板遇到受限來源的 403 時會標記「來源不可用」，阻止無意義的重複手動同步。
- 完整保留自有 HTTPS manifest、SHA-256、大小、圖片像素及原子切換能力，作為私人豬源方案。

### 安全與隱私

- PigHub 投稿只接受本地 override，端點固定且每次需要 CSRF、同源檢查與顯式確認。
- 投稿只發送小豬名稱與圖片，不發送描述、文案、使用者、群組、聊天或存儲資料。
- 遠端回應限制為 256 KiB；返回圖片地址必須是無帳密的 HTTPS URL。
- 投稿不做自動重試與審核輪詢，避免具有副作用的請求造成重複資料。
- 原圖下載限制為已認證管理頁、有效小豬 ID、受支援格式及 50 MiB 上限。

### 文檔與專案展示

- README 重新設計為正式專案首頁，加入版本亮點、能力矩陣、管理工作區、資源分層、安全模型、升級策略與文檔導航。
- 移除不能代表本插件真實下載情況的第三方訪問量與 Star History 圖表。
- 新增 `docs/RESOURCE-MANAGEMENT.md`，完整說明資源層、私人 manifest、PigHub 投稿、安全邊界與故障排查。
- 同步更新配置、指令、運維、文檔索引、市場 metadata 及發版說明。

### 升級影響

- 從 v3.2.x 可直接升級；SQLite、歷史圖鑑、本地圖片、override 與 tombstone 均保留。
- 沒有配置私人源時，插件繼續使用內置資源和全部本地改動，抽豬功能不受影響。
- 既有安裝若仍保留舊受限 URL，升級後面板會顯示診斷；管理員可改填自有 manifest 或保持同步關閉。

### 驗證

- Python 3.10／3.12 語法與完整 pytest 回歸。
- SQLite tombstone 新增、刪除、恢復及兼容文檔同步測試。
- 管理頁 JavaScript module、DOM ID／引用及資源工作流契約測試。
- README 本地連結、metadata 版本一致性、release archive 與 AstrBot 市場 16 MB 上限檢查。

## v3.2.1 (2026-08-12)

### AstrBot 市場分發

- Release 包切換為獨立身份 `astrbot_plugin_rollpig_plus-vX.Y.Z.zip`，與 v3.1.4 舊身份橋接通道分離。
- 精簡發版字體與開發文件，使正式 ZIP 符合 AstrBot 市場 16 MB 上限。
- 新增市場 metadata、Release 資產名稱、SHA-256 及雙更新通道契約測試。
- 更新器改讀穩定 Releases 列表，只接受版本與 `astrbot_plugin_rollpig_plus` 資產名稱精確匹配的包。

## v3.2.0 (2026-08-11)

### 独立插件身份与安全迁移

- 插件市场身份切换为 `casama233/astrbot_plugin_rollpig_plus`，代码目录、配置和数据命名空间与原版彻底分离。
- 首次安装会优先验证 v3.1.4 来源标记；没有标记时仅接受增强版 SQLite/多文件指纹，避免把 MegSopern 原版数据误迁移。
- 旧数据采用 SQLite backup 或逐文件 SHA-256 的 Copy → Verify → Atomic Commit 流程，迁移成功后旧目录仍完整保留。
- 新配置首次创建时只迁移当前 schema 仍支持的旧配置项；未知或废弃字段不会带入。
- 拒绝在旧 `astrbot_plugin_rollpig` 代码/配置命名空间内启动，防止手动 clone 导致两个插件共用配置。
- 检测到旧插件同时启用时给出指令冲突警告，不會擅自停用或删除旧插件。

## v3.1.4 (2026-08-11)

### 插件身份迁移桥接

- 为现有增强版数据目录写入原子化来源标记，供后续 `astrbot_plugin_rollpig_plus` 安全识别，避免误迁移原版插件数据。
- 安全更新器遇到 `3.2.0+` 新插件身份时拒绝原地覆盖，改为提示从 AstrBot 插件市场安装新包并迁移。
- 保持当前插件名、数据目录和配置命名不变，本版本只建立迁移桥，不搬动或删除任何用户数据。

## v3.1.3 (2026-08-11)

### 消息投递修复

- 修复图片消息发送超时后又触发 fallback，导致渲染卡片、原图和文字描述重复发送的问题。
- 发送超时改为“投递状态不确定”：已开始投递的图片不再重试 fallback，临时文件保留 90 秒供慢适配器读取。
- fallback 图片链超时后不再补发第二条纯文本，避免迟到成功的图片链与重试文本并存。

## v3.1.2 (2026-08-05)
### Analytics 字体与可读性修复
- Analytics 基础正文提高到 14px，卡片标题提高到 16px，辅助文字、图例、平台名称和表格内容统一提高到可读范围。
- 日期热力图、收藏覆盖、双周期对比、回访用户、平台构成、上升最快猪猪和运行健康等区块同步调整，不再以 7–9px 作为最终显示字级。
- 提高表格行高、卡片内边距和正文行高，同时保留桌面信息密度。
- 新增 1366px 桌面与 430px 窄屏 Chromium 布局测试，验证最终计算字级与横向溢出。

## v3.1.1 (2026-08-05)
### 管理页按需加载与性能修复
- 管理页默认只运行轻量核心模块，不再自动请求或注入企业增强与 Analytics 整包资源。
- 新增“深度分析”按钮；只有点击后才通过认证桥接加载 Analytics 样式、脚本与聚合数据。
- 删除大体积源码的 `sessionStorage` 缓存、100ms Bridge 轮询、持续 DOM `MutationObserver` 与同步状态自动轮询。
- Analytics 按当前 `.shell` 根节点绑定，旧 SPA 根节点通过 `AbortController` 解除事件，避免重复挂载和重复刷新。
- 新增 jsdom 回归和真实 Chromium 性能测试，覆盖默认零增强请求、单实例挂载、SPA 多次重入、观察器/定时器数量与 JS 堆增长。

## v3.1.0 (2026-08-04)
### 认证桥接企业 UI 与浏览器级回归
- 核心数据总览、猪猪图鉴、同步、SQLite 管理和安全更新继续由轻量主模块独立运行，不等待任何增强资源。
- 新增只读 `ui/assets` 接口，只从插件目录固定白名单读取企业主题、反馈增强和 Analytics 源码，并通过 AstrBot Plugin Page Bridge 携带认证返回；浏览器不再直接请求会 401 的相对子资源。
- 主页面仅内联小型启动器，使用版本化会话缓存、SHA-256 校验、模块独立错误边界、可见诊断与重试；增强层失败不会隐藏或阻断核心视图。
- 恢复 v2.15.0 商业级企业主题与深度 Analytics，并支持 AstrBot 单页容器二次进入时重新挂载。
- 新增 jsdom 浏览器行为测试，覆盖核心视图切换、认证资源注入、资源失败降级、Analytics API 局部失败和 SPA 重挂载。

## v3.0.5 (2026-08-04)
### 紧急恢复附属页面可用性
- 撤回 v3.0.4 将数千行 CSS/JavaScript 内联进管理页的高风险方案，恢复最后已知可正常加载的轻量页面。
- 移除会返回 401 的相对增强资源请求；基础总览、图鉴、同步、SQLite 管理与安全更新继续可用。
- 企业增强主题与深度 Analytics 暂时停用，待通过真实 AstrBot 浏览器集成验证后再恢复。
- 不修改 SQLite 数据、API 数据结构、抽猪规则或其他业务流程。

## v3.0.4 (2026-08-04)
### 管理页受保护资源加载修复
- 修复 AstrBot 通过认证 API 注入插件页面时，相对脚本与样式子资源无法携带授权头而返回 401 的问题。
- 企业主题、交互反馈和深度 Analytics 现在直接内联进主页面，不再请求受保护的 `page/content` 子资源。
- 保留模块化 CSS/JS 源文件作为维护来源，并新增构建一致性测试，防止发布包重新引入外部受保护资源。
- 不修改 Analytics API、SQLite 单一权威、数据结构或业务流程。

## v3.0.3 (2026-08-04)
### Analytics 单页容器重新挂载修复
- 修复 AstrBot 管理后台复用同一个页面窗口时，旧版全局 ready 标志残留，导致新 DOM 沒有 `analyticsSuite` 卻跳過初始化的問題。
- Analytics 現在以當前 DOM 是否實際掛載為準，並使用版本化啟動狀態；舊狀態或缺失掛載會自動重新初始化。
- 刷新按鈕按當前 DOM 元素去重綁定，hashchange 監聽全局只註冊一次，避免重複進入頁面後疊加請求。
- 不修改 Analytics 只讀 API、SQLite 單一權威、資料結構或其他管理業務流程。

## v3.0.2 (2026-08-04)
### Analytics 初始化時序修復
- 修復 AstrBot 管理橋接尚未就緒時，深度 Analytics 過早標記為已初始化並永久退出的問題。
- Analytics 現在會以 100ms 間隔、最多 8 秒等待橋接；橋接就緒後才設置完成標記並讀取聚合資料。
- 重複注入保持冪等；橋接長期不可用時顯示局部錯誤與「重新連接」，普通總覽、圖鑑和管理操作不受影響。
- 所有管理頁資源快取鍵同步提升至 v3.0.2，不修改 SQLite 單一權威、API 契約或業務流程。

## v3.0.1 (2026-08-04)
### 管理頁 UI 快取與恢復證據修復
- 修復從舊版本直接升級到 v3.0.0 後，瀏覽器可能繼續使用舊版 `ui-feedback.js`，導致企業主題與 Analytics 增強層沒有載入的問題。
- 管理頁入口、企業主題、Analytics 主題、反饋核心與增強腳本統一加入版本化快取鍵；今後升級後無需依賴手動強制刷新才能看到新 UI。
- 修復檢查損壞 SQLite 時可能由 SQLite 重寫原始 `-shm` 旁路文件的問題；替換資料庫前會先保存原始 WAL／SHM 恢復證據。
- 不修改 v3 的 SQLite 單一運行時權威、資料遷移事實、業務命令或管理寫接口。

## v3.0.0 (2026-08-04)
### SQLite 單一運行時權威
- 規範化 SQLite 表成為唯一運行時權威；每日抽取、吃豬、烤豬、AI 文案、身份映射和後台圖鑑熱寫入不再重建或持久化整份兼容 JSON。
- schema 6 會在完整性、外鍵與規範化一致性檢查通過後晉升既有資料庫；舊文檔損壞不會覆蓋 SQL，規範化表損壞則拒絕晉升並保留恢復資料。
- 新安裝在 `auto` 模式直接建立 SQLite；舊 JSON 安裝會先完整備份，再匯入臨時資料庫、執行事實級對帳與完整性檢查後原子切換。
- JSON 兼容文件只在匯出、回滾或災難恢復時從 SQL 按需生成，生成過程不會寫回資料庫；`storage_backend=json` 保留為顯式緊急模式。
- 新增跨進程每日抽取唯一性、事務崩潰回滾、熱路徑零兼容文檔、舊資料自動遷移、晉升拒絕與派生統計修復測試。

## v2.15.0 (2026-08-04)
### 商業級 Analytics 管理後台
- 管理頁改為緊湊的企業級 Analytics 工作台，統一明暗主題、狀態語義、組件密度、響應式與無障礙體驗。
- 新增只讀 `analytics/insights` 聚合接口，展示雙週期增長、七日回訪、二十八日活動熱力、圖鑑覆蓋分佈、平台構成、上升豬豬及玩法運行健康。
- 深度分析只返回聚合數字和豬豬 ID／名稱，不返回用戶 ID、群號或原始聊天記錄；讀取失敗也不會影響原總覽、圖鑑和維護功能。
- SQLite 直接聚合規範化表；JSON 後端保留兼容統計路徑，不改變現有資料結構、寫入邏輯或業務流程。

## v2.14.0 (2026-08-04)
### SQL 原生統計與存儲可觀測性
- 管理面板的總用戶、累計抽取、平均解鎖、近 14 日趨勢與熱門小豬改為直接聚合規範化 SQL 表，不再遍歷整份 `pig_history` 運行快照。
- schema 5 新增日期／小豬與圖鑑反向查詢索引，改善大資料量下的趨勢和收藏統計性能。
- 存儲狀態面板顯示統計來源、schema、寫入權威以及最近一次自動／手動修復的動作、原因和時間。
- 保留 JSON 後端的原有統計回退路徑；SQLite 不可用或主動回滾後，管理面板仍可正常工作。
- 增加十萬用戶與三十萬每日記錄的 SQL 聚合壓力測試及索引、修復元資料回歸測試。

## v2.13.1 (2026-08-04)
### 新解鎖趨勢修復
- 修復 JSON→SQLite 遷移與投影重建把歷史抽取的 `was_new_unlock` 全部寫成 0，導致管理面板「新解鎖」曲線長期貼地的問題。
- schema 4 會根據每位用戶圖鑑的 `first_unlocked` 日期自動回填歷史抽取；被吃掉的記錄使用 `original_pig_id` 還原當天真正解鎖的小豬。
- 今後的 JSON 投影會在寫入 `daily_draws` 時直接計算新解鎖標記，不會再次丟失統計。

## v2.13.0 (2026-08-04)
### 每日 AI 生成權與 SQL 啟動快照
- 新增 `ai_roast_generation_attempts`，以 `(pig_id, generated_date)` 唯一鍵保證所有 AstrBot 實例每天每隻豬最多實際調用一次模型；生成失敗也會記錄，當天不重複消耗 Token。
- 當天首次成功生成直接使用新文案；同一天後續燒烤從該豬今天及此前六天的有效文案中隨機選擇，滾動窗口共七個自然日。
- SQLite 啟動時由規範化表重建用戶圖鑑、每日記錄、烤豬狀態、AI 快取、身份映射及本地圖鑑層，不再把兼容文檔作為運行時啟動來源。
- `identity_claims` 與 `identity_aliases` 改為 SQL 主寫；兼容 JSON 繼續事務同步，僅用於匯出、回滾和舊版災難恢復。
- SQLite 主寫資料庫檢測到兼容文檔損壞或過期時，只會由規範化 SQL 反向修復文檔；不會再用舊文檔覆蓋正確資料庫。

## v2.12.0 (2026-08-04)
### 烤豬、AI 文案與圖鑑後台 SQL 主寫
- 烤群友冷卻、每日被烤次數與每日後門改為規範化 SQL 表直接事務寫入，跨連接唯一性由資料庫約束承擔。
- 豬圈保護次數改為直接查詢 `daily_roast_counts`，聊天命令通過工作線程執行 SQLite I/O，不阻塞事件循環。
- AI 烤豬文案快取改為 SQL 讀取、清理與首寫獲勝；多進程並發生成時只保留當天第一份已提交文案。
- 管理後台新增、編輯和刪除小豬改為 `catalog_overrides`／`catalog_tombstones` 原子事務寫入。
- 兼容 JSON 仍在同一事務內同步，用於匯出、舊版回滾和災難恢復；上述熱路徑不再觸發對應投影全表重建。

## v2.11.1 (2026-08-04)
### 被吃懲罰與每日抽取原子性熱修復
- 修復 SQL 主寫路徑在“探測今日狀態”階段提前消費成功懲罰的問題；探測現在只判斷失敗或返回待選豬狀態。
- 成功消費次日懲罰只會與 `daily_draws`、圖鑑和統計寫入在同一個 `BEGIN IMMEDIATE` 事務中提交。
- 若抽取寫入、兼容文檔同步或進程在提交前失敗，懲罰與所有抽取記錄會一起回滾，不會出現“懲罰消失但沒有抽到豬”。

## v2.11.0 (2026-08-04)
### SQLite 核心寫入事務
- 每日抽豬改為規範化 SQL 表的直接事務寫入；`PRIMARY KEY(draw_date, user_id)` 現在真正承擔跨連接並發唯一性。
- 次日被吃懲罰的檢查、消費與失敗鎖定和每日抽取放在同一個 `BEGIN IMMEDIATE` 事務邊界內。
- 吃群友的當天替換、原豬保存、次日懲罰和事件記錄改為一次提交或全部回滾。
- 兼容文檔仍在同一事務中同步，供 JSON 匯出、舊版回滾和災難恢復使用，但熱寫入不再觸發歷史／烤豬投影全表刪除重建。
- JSON 後端繼續保留舊邏輯；已遷移的 v2.10 資料庫無需再次手動遷移即可使用 SQL 主寫路徑。

## v2.10.1 (2026-08-04)
### 管理面板確認框與遷移反饋熱修復
- 修復 AstrBot Plugin Page 的 iframe sandbox 阻止原生 `window.confirm()`，導致“遷移 SQLite”等按鈕點擊後無請求、無日誌、無前端反饋的問題。
- 遷移、重建索引、回滾 JSON、安裝更新和 AI 覆蓋文案改用頁面內確認對話框；繼續沿用原有 CSRF、互斥鎖和操作耗時反饋。
- SQLite 遷移在開始執行及安全失敗時寫入明確日誌，方便區分“前端未發請求”和“後端遷移失敗”。

## v2.10.0 (2026-08-04)
### SQLite 查詢路徑與投影修復
- 新增 schema migration v2：身份補充 legacy/創建時間索引，群成員關係拆為 `daily_draw_groups`，避免繼續查詢 `group_ids_json`。
- SQLite 的用戶圖鑑、每日結果、群成員和被吃名單改為直接 SQL 查詢；JSON 後端仍保留原有兼容讀取。
- 修復 `transaction()` 只有 Python 鎖而沒有資料庫事務的問題，現在使用獨立連接與 `BEGIN IMMEDIATE`，異常必定回滾並關閉連接。
- 資料庫驗證新增文檔與投影逐表計數對帳；啟動時可自動重建僅投影損壞的資料庫，管理面板也新增手動“重建索引”。
- 抽取保底與烤／吃特殊形態規則移入 `services/`，繼續縮小 `main.py` 的業務職責。
- 本版仍保留兼容文檔作為寫入權威層；直接 SQL 寫入與 SQLite 默認啟用留到 v3.0，避免在未完成增量事務前貿然切換。

## v2.9.3 (2026-08-04)
### 管理面板操作反饋與待重啟保護
- 修復安全更新後頁面文件已替換、但 AstrBot 尚未重啟時，新頁面請求舊後端路由並只顯示“未找到該路由”的問題；現在會明確提示頁面／運行時版本不一致並要求重啟。
- 新增醒目的“等待重啟”橫幅；待重啟期間禁用遷移、驗證、重建、匯出、回滾、同步與更新按鈕。
- 管理操作顯示獨立按鈕狀態、執行階段、已等待時間與耗時；v2.10 新增的投影重建也納入同一反饋和互斥機制。

## v2.9.2 (2026-08-04)
### 特殊形態判定與文案
- 修復 `/吃群友` 檢查發動者時沿用目標視角，導致發動者抽到豬排卻錯誤提示“對方今天是豬排”的問題。
- 分離發動者、燒烤目標與進食目標的資格規則：人類和“吃掉了”仍不可參與；豬排、豬油等熟食不能主動行動或重複燒烤，但現在可以被正常吃掉。
- 機械豬等普通特殊豬不會被誤判為熟食；吃群友成功文案會顯示實際目標名稱，熟食目標使用“開袋即食”文案。

## v2.9.1 (2026-08-04)
### 安全更新熱修復
- 修復 SHA-256 校驗誤調用不存在的 `hashlib.compare_digest`，改用標準庫 `hmac.compare_digest`；帶 `SHA256SUMS` 的穩定版更新不再報屬性錯誤。
- 新增回歸測試，防止更新器再次引用錯誤模塊。

## v2.9.0 (2026-08-03)
### SQLite 存儲與可回滾遷移
- 新增 `SQLiteStorage` 與 `StorageManager`；默認 `auto` 只在資料庫存在且完整時啟用 SQLite，舊安裝繼續安全使用 JSON。
- 遷移流程先備份七份關鍵 JSON，臨時建庫、刷新正交投影、逐文件 SHA-256 對帳並執行 SQLite 完整性與外鍵檢查，全部通過後才原子切換。
- 新增 `schema_migrations`、兼容文檔表及每日抽取、用戶圖鑑／統計、豬快照、被吃懲罰／事件、冷卻、每日烤豬、後門、AI 文案、圖鑑覆蓋／刪除投影表。
- 管理面板新增存儲狀態、遷移、驗證、JSON ZIP 匯出和安全回滾；所有寫操作沿用同源與 CSRF 校驗，不接受自定義文件路徑。
- SQLite 使用 WAL、外鍵、`synchronous=NORMAL` 和可配置寫鎖等待；雲資源與 PigHub 快取繼續使用 JSON，不納入關鍵事務資料庫。

## v2.8.0 (2026-08-03)
### 存儲架構與安全更新
- 新增 `StorageBackend` 抽象與兼容舊資料格式的 `JSONStorage` 後端；現有命令繼續讀取原 JSON，損壞恢復、批量落盤和回滾集中到統一持久化層，為 SQLite 遷移預留接口。
- 豬圈管理面板新增官方穩定版檢查與安全更新按鈕；來源固定為 `casama233/astrbot_plugin_rollpig`，拒絕任意 URL、分支和預發布版本。
- 更新包執行 HTTPS／倉庫身份、大小、文件數、解壓體積、路徑穿越、符號鏈接、異常壓縮比、metadata 與 Python 語法檢查；Release 提供 SHA-256 時強制核對，未提供時要求二次確認。
- 替換代碼前自動備份插件目錄，失敗恢復舊文件；AstrBot 插件資料與配置不在替換範圍，安裝完成後只提示手動重啟，不自動控制宿主進程。

## v2.7.0 (2026-08-03)
### 管理面板視覺升級
- 管理面板重構為「資料總覽」與「豬豬圖鑑」兩個獨立分頁，並使用 URL 錨點保存當前分頁，支持瀏覽器前進／返回。
- 六項核心指標改為數字遞增與微型趨勢線；14 日趨勢升級為動態面積折線圖，支持逐日懸停查看使用人數、抽取次數及新解鎖。
- 平均收藏率改為動態環形進度圖，熱門小豬改為流暢進場的橫向排行；圖表縮放只依據實際展示序列，避免累計抽取量壓扁趨勢線。
- 新增柔和光暈、玻璃層次、卡片分段進場、圖鑑懸停與彈窗彈性轉場，並完整支持系統深色模式及“減少動態效果”。
- 新增／編輯小豬表單加入「選擇圖片 → 補全資料 → 檢查發布」實時流程指示，現有 PigHub、AI 文案和雲同步功能保持兼容。

## v2.6.0 (2026-08-03)
### 跨平台兼容
- 身份鍵加入 AstrBot 適配器實例 ID，避免同一類型的多個 QQ／Discord 等機器人共享豬圈、冷卻與懲罰；舊 `v2|平台|...` 和更早的裸 ID 會按實例懶認領，不會直接清空既有圖鑑。
- Telegram 記錄 username 與數字用戶 ID 的雙向別名，`@username`、回復消息、隨機點名和數字 ID 可以指向同一份今日小豬記錄。
- 出站點名按平台編碼：OneBot、Discord、飛書和 WhatsApp 使用標準 At；Telegram 使用 username 或 `tg://user?id=`；Slack 與 QQ 官方使用平台原生文本 mention。
- 增加 OneBot 原始消息段與 WhatsApp `mentionedJids` 後備解析，適配器未生成標準 At 段時仍能識別目標。
- WhatsApp 優先使用 PN／手機號並保留無法解析的 LID JID，降低第三方適配器或 LID 快取缺失時認錯用戶的風險。
- 過濾 `@全體成員`、`@everyone` 與空 Reply 的默認用戶 `0`，避免把廣播或無效引用當作普通群友。

## v2.5.2 (2026-08-03)
### 修復
- 修復 QQ／aiocqhttp 等平台發送 `@` 時誤把內部 `v2|...` 身份鍵作為用戶 ID 的問題；發送消息段和文本回退前會還原為平台原生用戶 ID。

## v2.5.1 (2026-08-03)
### 修復
- 允許導入小於 256×256 的本地或 PigHub 圖片；統一規格化時會按比例放大並保存為 512×512 PNG，不再因低分辨率直接拒絕。

## v2.5.0 (2026-08-03)
### 管理面板優化
- AI 草稿生成增加可選的畫面／創作引導詞，管理員可補充圖片中的動作、服飾、顏色和想要的梗，幫助模型避免只看名稱和文件名產生誤解。
- 生成過程中在表單內顯示階段進度與動態狀態，完成或失敗後自動收起，不再只有全局轉圈等待。

## v2.4.0 (2026-08-03)
### 穩定性與安全
- 修復並發抽取可能令當日快取與永久圖鑑不一致的問題；相關 JSON 採用預寫、備份與失敗回滾的批量提交。
- `@他人` 現在只讀取對方已有結果，不再替對方抽取，也不能借此繞過次日懲罰。
- 新增平台命名空間與舊 ID 認領記錄：既有資料由首次使用的平台繼續繼承，其他平台的同號用戶保持隔離。
- JSON 損壞時保留 `.corrupt-*` 副本並優先從 `.bak` 恢復，避免靜默覆蓋原始資料。
- AI 文案按小豬分片加鎖並加入可配置超時，避免單個模型請求阻塞全部生成。
- 管理頁寫接口增加同源與 CSRF 校驗；統計計算和縮略圖處理移出事件循環，縮略圖改為壓縮 PNG。
- 雲同步限制重定向主機、拒絕私網解析、限制圖片尺寸，並在任務完成時立即落盤以降低峰值內存。
- 新增 IANA 時區配置，修復圖片句柄、裁剪、長文案溢出及管理員 ID 比較不一致。

### 工程
- 版本更新至 2.4.0，文檔最低 AstrBot 版本與元資料統一為 4.24.2。
- 移除未使用的 Jinja2 依賴，新增身份/IP 輔助模塊、回歸測試與 GitHub Actions CI。

### 管理面板優化
- AI 小豬草稿的描述改為嚴格 3-8 個漢字，一語道破小豬特質。
- AI 完整文案改為 40-120 字的簡短單段，強化梗感、風趣感與哲學意味，並增加後端長度兜底。

## v2.3.0 (2026-08-03)
### 管理面板優化
- 移除聊天指令 `/同步小豬資源` 及其繁簡體／刷新別名；公共資源同步統一從管理面板操作。
- 保留管理面板同步按鈕、狀態提示與後端同步 API，不影響自動同步配置。

## v2.2.0 (2026-08-03)
### 管理面板優化
- PigHub 選圖後可一鍵調用當前 AstrBot AI 模型，參考小豬名稱與現有圖鑑文案生成描述和完整文案草稿；生成結果仍可繼續手動修改。
- 新增／編輯小豬彈窗不再因點擊外部遮罩關閉，避免誤觸丟失尚未保存的內容。

## v2.1.0 (2026-08-02)
### 兼容性修復
- 兼容 WhatsApp Baileys 的 LID JID（如 `123…@lid`）與適配器規範後的手機號 ID：@ 提及、引用回復、隨機玩法和發送 @ 均會統一到同一用戶。
- 兼容升級前已經寫入的 LID 數字歷史鍵；檢測到舊記錄時沿用原鍵，不會因切換到手機號映射而重複解鎖或丟失今日結果。
- WhatsApp 群組 ID（`…@g.us`）繼續使用適配器的穩定群 ID，烤豬冷卻、保護、吃群友與豬圈日報不會因 JID 後綴變化而串組。
- WhatsApp 未安裝或映射暫不可用時自動保持原有跨平台 ID 解析，不影響 QQ、Discord、Telegram、Slack、飛書等適配器。

## v2.0.3 (2026-08-02)
### 優化
- 從 PigHub 選圖後自動生成穩定唯一 ID，並將 PigHub 標題帶入名稱字段；描述和完整文案繼續由管理員確認填寫。
- PigHub 來源確認後禁用本地文件輸入與「本地上傳」按鈕，避免同一次保存同時提交兩套圖片來源；後端也會拒絕混合來源請求。

## v2.0.2 (2026-08-02)
### 修復
- 管理面板近 14 日趨勢圖現在顯示全部 14 個日期刻度；此前為防止重疊只顯示每隔一天的刻度，容易誤以為只有 8 天資料。

## v2.0.1 (2026-08-02)
### 修復
- 週報現在會保留成員當天原本抽到的小豬；若之後被吃掉，會在該日卡片右上角標註「被吃掉了」，不會把週報內容替換成特殊形態。
- AI 烤豬文案統一使用隨插件附帶的「漢儀勇字小熊貓繁」字體，以覆蓋繁體及罕見字形；字體無法載入時仍會安全回退常規字體。

## v2.0.0 (2026-08-02)
### 新增
- 新增 `/吃群友 @某人` 與 `/隨機吃群友`：默認成功率 15%，成功會令目標、失敗會令發起者成為當天的「吃掉了」；兩種結果都會在次日首次抽豬時按默認 20% 概率失敗，失敗後鎖定至當天結束。
- 吃群友同樣遵守特殊形態資格與次日保護；隨機吃群友會自動排除受保護、已吃掉及其他不可行動成員。
- 新增 `/豬圈日報`／`/猪圈日报`，展示當前群的抽豬人數、被吃人數，並從當日被吃成員中隨機點名「可憐被吃」。
- 新增吃群友開關、成功率與次日失敗率配置，均可在插件配置頁調整。

## v1.9.0 (2026-08-02)
### 新增與修復
- 新增群聊被烤保護：同一成員當天在同一群實際被烤達到閾值（默認 3 次）後，次日自動獲得保護；普通燒烤會在消耗冷卻前攔截，後門強制模式可突破。逃脫不計數，反噬計入實際被反噬者。
- 特殊形態補齊：`豬油` 與豬排按熟食形態處理；`人類`、`吃掉了`、熟食形態與保護狀態均有獨立提示。`吃掉了` 作為獨立特殊形態，不能繼續參與任何正常燒烤流程。
- 新增 `enable_roast_protection` 與 `roast_protection_threshold` 配置項，可關閉保護或在 1-20 次之間調整閾值。

## v1.8.3 (2026-08-02)
### 優化
- AI 烤豬文案按「小豬 ID + 日期」全局限流：每隻豬每天至多調用一次模型，文案持久化保留最近 7 天；同日再次烤該豬會隨機復用這 7 天內的已有文案。
- `/我的豬圈` 調整為已解鎖小豬優先展示，未解鎖小豬順延至後續頁面；兩個區間內部仍保留管理員維護的圖鑑排序。

## v1.8.2 (2026-08-02)
### 優化
- AI 烤豬文案改為機靈、梗感與輕度黑色幽默風格：調侃範圍限定於虛構小豬、豬圈與抽卡命運，並增加反轉要求與標題前綴清洗；不涉及真實用戶或現實暴力細節。

## v1.8.1 (2026-08-02)
### 修復
- 統一提及目標解析：優先識別 AstrBot 標準 `At` 段，補充 Discord 原生 `mentions`、`<@用戶ID>` 格式和常見引用消息發送者字段；手動輸入支持 Discord、Slack、飛書等非純數字用戶 ID。
- 修復開啟 `at_view_pig` 後 `/今日小豬 @某人` 僅因 @ 不屬於 `message_str` 而無法查看對方結果的問題。
- 所有群聊提及發送統一走標準 `Comp.At`；適配器不支持時僅降級為帶用戶 ID 的文本，生成的今日小豬圖片和隨機烤群友流程不再被 @ 段發送失敗中斷。

## v1.8.0 (2026-08-02)
### 新增
- 完整補齊烤豬玩法：`/今日烤豬` 會攔截人類、熟食形態與已吃掉的小豬；可選啟用當前 AstrBot 模型生成料理文案，模型不可用時自動回退本地模板。
- 新增 `/烤群友 @某人`，支持 @ 或回復目標消息；按 60% 成功、30% 逃脫、10% 反噬判定，並以「群聊 + 發起者」為單位冷卻 8 小時（可配置）。
- 新增 `/隨機烤群友`，僅從當天在當前群聊抽過小豬且符合資格的成員中隨機選擇。
- 新增後門口令：`/打點後廚`、`/偷換烤架`、`/賄賂主廚`、`/加急生火` 每人每天一次；AstrBot 超級管理員可用 `/強行點火` 無限制強制成功。後門僅繞過概率與冷卻，不繞過目標資格。
- 幫助圖片卡新增完整燒烤玩法說明；繁簡指令與口令均可使用。

## v1.7.1 (2026-08-02)
### 修復
- 幫助圖片卡改用簡體中文，並固定使用插件內置字體渲染；避免部分 AstrBot 容器缺少完整 CJK 系統字體時出現繁體缺字或異常字距。

## v1.7.0 (2026-08-02)
### 修復與性能
- 修復 PigHub 選圖器縮略圖在 AstrBot 沙箱 iframe 內直接跨域加載而破圖的問題；網格現由插件服務端返回 RGBA Canvas 像素，不再輸出外部 `<img>` 請求。
- PigHub 索引保留內存與磁盤 12 小時快取；縮略圖採用按 URL 的內存（72 張）與磁盤（7 天）快取，網格最多 3 路並發且同一圖片請求會合併，降低對 PigHub 的重複壓力。
- 已加載的縮略圖會直接復用為選擇後的表單預覽；只有最終保存時才下載原圖並轉換為 512×512 PNG。

## v1.6.9 (2026-08-02)
### 修復
- 修復管理面板趨勢折線的 X 坐標計算優先級錯誤：最後數日的數據點不再被繪製到 SVG 範圍外並被裁切，已有用戶／解鎖資料會正常顯示。

### 元數據
- 顯示名稱改為「今日小豬 · 增強版」，描述明確為獨立維護 fork；內部插件 ID `astrbot_plugin_rollpig` 保持不變，以保留既有配置、圖鑑、歷史資料和管理頁路徑。

## v1.6.8 (2026-08-02)
### 優化
- `/豬豬幫助`／`/猪猪帮助` 改為發送日夜自適應的幫助圖片卡片，替代冗長純文本；卡片保留全部指令、參數示例、@ 他人開關狀態及管理員功能說明。

## v1.6.7 (2026-08-02)
### 新增
- 新增 `/豬豬幫助`／`/猪猪帮助` 指令，集中說明全部聊天指令、頁碼與搜索參數、料理卡、圖鑑，以及管理員同步與管理面板功能。
- 幫助會根據 `at_view_pig` 當前配置明確提示是否可用 `/今日小豬 @某人` 查看他人的今日小豬。

## v1.6.6 (2026-08-02)
### 新增
- 機器人發送的今日小豬、圖鑑、隨機／搜索結果、週報與烤豬圖片新增日夜主題：默認在 19:00-06:59 自動切換為低亮度夜間配色；可通過 `image_theme` 配置固定為 `light` 或 `dark`。

## v1.6.5 (2026-08-02)
### 修復
- 管理圖鑑縮略圖改為 192×192 RGBA Canvas 像素，完整保留 PNG 透明度和邊緣細節；不再將 128px RGB 縮略圖放大，卡片預覽與編輯頁顯示一致。

## v1.6.4 (2026-08-02)
### 修復
- 修復統計趨勢 SVG 的溢出繪製：圖表與 SVG 現在會裁切至卡片範圍，零值趨勢線不會橫跨到熱門小豬圖表或頁面外。

## v1.6.3 (2026-08-02)
### 修復
- 兼容 PigHub 當前的 `/images/` 圖片地址（同時保留 `/data/`），圖庫不再因安全白名單過嚴而顯示為空。
- PigHub 索引讀取限制為單入口 12 秒，並在管理頁超過 20 秒時明確顯示失敗原因，不再無限停留在“打開後加載”。
- 雲資源默認繞過系統代理直連；已修復失效代理導致 `pig.felislab.cc` TLS 連接超時、一直沒有“上次成功”的問題。需要代理的部署可在配置中顯式開啟。
- 雲資源面板新增上次嘗試、進行中、成功、未完成與失敗的常駐狀態說明；同步輪詢異常也會顯示給管理員。

## v1.6.2 (2026-08-02)
### 修復
- 徹底移除管理圖鑑對 `data:`／`blob:` 圖片 URL 的依賴，後端改為提供 RGB 縮略像素並由前端 Canvas 直接繪製，兼容 AstrBot 的沙箱 iframe。
- 編輯彈窗沿用 Canvas 顯示當前圖片；本地上傳通過 `createImageBitmap` 直接預覽，不再創建 Blob URL。
- PigHub 選圖新增服務端安全預覽接口，避免跨域或鑒權策略導致預覽破圖。

## v1.6.1 (2026-08-02)
### 修復
- 修復管理頁縮略圖在 AstrBot 受限 iframe 中顯示為破圖與小白條的問題，改用 Blob URL 與固定比例容器。
- 修復首次同步接近兩百張雲端圖片時容易觸發 `httpx.ReadTimeout` 的問題。
- 雲同步改為後台任務，Dashboard 請求無需等待整包下載完成。
- 圖片下載改為 4 路並發、至少 45 秒讀取窗口與最多 3 次退避重試。
- 網絡異常現在顯示可讀原因；舊快取、本地圖鑑覆蓋與刪除屏蔽繼續保留。

## v1.6.0 (2026-08-02)
### 新增
- 新增公有小豬雲資源同步，兼容 rollpig-plus 的版本化 manifest、尺寸與 SHA-256 校驗。
- 新增“雲端／內置基礎層 → 本地管理覆蓋層 → 刪除屏蔽層”的圖鑑合併策略。
- 管理面板新增雲資源狀態、手動同步以及 `/同步小豬資源` 管理員指令。
- 新增 PigHub 圖片挑選器，可搜索／分頁／隨機瀏覽圖片，再手動填寫名稱、描述與文案。

### 安全與穩定性
- 雲資源先下載到暫存目錄，全部校驗成功後才原子替換；失敗繼續使用舊快取或內置資源。
- PigHub 圖片由服務端從受信任的 `pighub.top/data/` 下載，統一校驗並轉為 512×512 PNG。
- 舊版整份本地圖鑑會自動遷移為覆蓋層與刪除屏蔽，不丟失管理員已有修改。

## v1.5.0 (2026-08-02)
### 新增
- 新增昨日小豬、明日預測、本週小豬週報。
- 新增本地隨機小豬與多字段找豬功能。
- 新增重複抽取 EX Lv.、本命豬與連續重複漸進保底。
- 新增純本地今日烤豬料理卡，不依賴外部 AI 服務。
- 永久歷史按日期保存實際抽取結果，為週報和昨日查詢提供資料。

### 優化
- 調整我的豬圈卡片與頁腳間距，並豐富成長摘要。

## v1.4.0 (2026-08-02)
### 新增
- `/今日小豬` 同時兼容繁體、簡體指令與常用別名。
- 新增 `/我的豬圈 [頁碼]` 永久解鎖圖鑑，兼容 `/我的猪圈`。
- 新增 AstrBot Plugin Page 管理面板，支持小豬素材的一條龍新增、編輯和刪除。
- 上傳圖片自動校驗、居中裁切並轉換為 512×512 PNG。
- 新增使用人數、抽取次數、平均解鎖率、趨勢與熱門小豬統計。

## v1.3.0 (2026-07-25)
### 新增
- 新增多款小豬形象素材，豐富隨機抽取結果池。
