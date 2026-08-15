# 🐷 今日小豬文檔中心：玩家先養豬，維護者再看機房

`docs/` 同時保存目前適用的玩家／管理／運維文檔與少量歷史技術證據。**帶版本號的性能、審查或 migration 記錄不是當前操作手冊。**

## 玩家先從這裡進

| 文檔 | 內容 |
| --- | --- |
| [`index.md`](index.md) | Wiki 首頁：先抽一隻，再決定今天要搞多大 |
| [`getting-started/index.md`](getting-started/index.md) | 30 秒開始養豬 |
| [`gameplay/index.md`](gameplay/index.md) | 玩家玩法總覽 |
| [`gameplay/collection-pity.md`](gameplay/collection-pity.md) | 永久豬籍、新豬保底與跨日疲勞 |
| [`gameplay/ex-growth.md`](gameplay/ex-growth.md) | EX Lv.1–5 成長與官方手寫內容 |
| [`gameplay/roast-charge.md`](gameplay/roast-charge.md) | Roast Charge、群體補貨與 contextual `/添柴` |
| [`gameplay/roast-outcomes.md`](gameplay/roast-outcomes.md) | 60/30/10、真正 victim 與次日保護 |
| [`gameplay/daily-report.md`](gameplay/daily-report.md) | 豬圈日報、opt-in 與可選祭品 |
| [`creators/index.md`](creators/index.md) | 普通群友／創作者怎麼做一隻自己的豬 |
| [`troubleshooting/index.md`](troubleshooting/index.md) | 按症狀排障，先別炸資料庫 |

## 精確規則與管理文檔

| 文檔 | 內容 |
| --- | --- |
| [`COMMANDS.md`](COMMANDS.md) | 完整 command surface、別名、上下文與限制 |
| [`CONFIGURATION.md`](CONFIGURATION.md) | `_conf_schema.json` 對應的全配置、預設與範圍 |
| [`ROAST-CHARGES.md`](ROAST-CHARGES.md) | Charge token-bucket、補貨狀態與存儲邊界 |
| [`ROAST-RESERVATIONS.md`](ROAST-RESERVATIONS.md) | 預約、添柴、一次性結算與競態邊界 |
| [`EX-VARIANTS.md`](EX-VARIANTS.md) | EX 稀疏差分、圖片／描述／文案繼承 |
| [`EX-ACCEPTANCE.md`](EX-ACCEPTANCE.md) | EX 產品閉環與官方內容驗收 |
| [`DAILY-REPORT.md`](DAILY-REPORT.md) | 日報統計、排程、補發與副作用 |
| [`RESOURCE-MANAGEMENT.md`](RESOURCE-MANAGEMENT.md) | 本地層、私人 manifest、公共投稿與同步排錯 |
| [`RESOURCE-SOURCE-MAINTENANCE.md`](RESOURCE-SOURCE-MAINTENANCE.md) | AstrBot v1 豬源建構、部署與回退 |
| [`RESOURCE-SOURCE-COMPATIBILITY.md`](RESOURCE-SOURCE-COMPATIBILITY.md) | 豬源 compatibility floor 與 cut-over 契約 |
| [`OPERATIONS.md`](OPERATIONS.md) | 身份遷移、SQLite、備份、更新、恢復 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Gameplay Event、邊界與漸進式模組化 |
| [`COLLECTION-IDENTITY.md`](COLLECTION-IDENTITY.md) | claim-aware logical-user 邊界 |
| [`COPY-STYLE.md`](COPY-STYLE.md) | 玩家文案、Wiki 與圖鑑 renderer 的 Piggy Voice 規範 |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 開發、測試、提交與文檔維護 |
| [`../CHANGELOG.md`](../CHANGELOG.md) | 正式版本可見變更 |

## 歷史技術證據

例如 `admin-ui-*`、`performance-v*.json`、`readability-v*.json` 等只保留作歷史測量／審查證據。它們可以回答「當時怎麼驗的」，不能回答「現在怎麼用」。

## 文檔維護契約

功能、指令、配置、資料或玩家文案變更時，至少同步檢查：

1. **README + Wiki 玩家入口**：有沒有還在主推被降級為 compatibility 的舊命令。
2. **`COMMANDS.md` + `main.py`**：command / alias / 權限 / context 是否一致。
3. **`CONFIGURATION.md` + `_conf_schema.json`**：key、預設、範圍與語義是否一致；尤其不要把 `group_roast_cooldown_hours` 再寫回舊「整段冷卻」。
4. **動態 `/豬豬幫助` + `player_copy.py`**：玩家看見的功能是否和文檔同一套命名。
5. **`/添柴`**：玩家文檔只主推 canonical `/添柴`；`/添煤` 只留在相容說明／搜尋同義詞。預約與補貨上下文必須講清楚。
6. **永久豬籍 renderer**：卡面上的收藏、歷史、EX 和翻頁文案也屬於玩家 copy，不是「代碼裡的字就不用管」。
7. **EX / 日報 / 資源 / 運維**：各自的技術手冊要跟真實 authority、事件與失敗語義一致。
8. **`CHANGELOG.md`**：正式發版時補上玩家有感的變更。

文檔不是功能做完後順手補的附件。**玩家看見的規則如果比程式慢一版，那就是產品 bug。**
