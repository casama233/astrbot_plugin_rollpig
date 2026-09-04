<div align="center">

<img src="https://raw.githubusercontent.com/casama233/astrbot_plugin_rollpig/main/logo.png" width="168" alt="今日小豬 · 增強版 Logo">

# 今日小豬 · 增強版

本分支程式版本：**v3.12.1** · EX 等級徽章置底、逐豬文案與安全更新修正。**可更新的穩定版本**以 [GitHub 穩定 Release](https://github.com/casama233/astrbot_plugin_rollpig/releases/latest) 為準；只有對應 tag、ZIP 與 SHA256SUMS 建立完成才算正式發布，main 合併本身不代表已可更新。

### 每天抽一隻。抽著抽著，群裡就多了一座豬圈和一間後廚。

`astrbot_plugin_rollpig_plus` · AstrBot 每日互動 × 永久豬籍 × EX 成長 × 群聊後廚

[![CI](https://github.com/casama233/astrbot_plugin_rollpig/actions/workflows/ci.yml/badge.svg)](https://github.com/casama233/astrbot_plugin_rollpig/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/casama233/astrbot_plugin_rollpig?display_name=tag&sort=semver)](https://github.com/casama233/astrbot_plugin_rollpig/releases)
[![AstrBot](https://img.shields.io/badge/AstrBot-4.26.0%2B-f59e42)](https://github.com/AstrBotDevs/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](LICENSE)

![動態訪問量](https://count.kjchmc.cn/get/@astrbot_plugin_rollpig_plus?theme=minecraft)

[30 秒開始](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/getting-started/index.md) · [玩家玩法](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/gameplay/index.md) · [指令百科](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/COMMANDS.md) · [管理面板](#管理面板) · [完整 Wiki](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/index.md)

</div>

> [!CAUTION]
> **本插件代碼由 AI 生成，並經人工審閱。** 即使經過審閱，仍可能存在未發現的缺陷、安全風險或相容性問題。請謹慎使用；在重要帳號、生產環境或敏感場景部署前，建議先自行審查代碼並充分測試。

> [!IMPORTANT]
> **項目來源與署名說明（2026-08-19）**
>
> 本倉庫是 [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig) 的 AstrBot 延續分支，其更早來源為 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)。後續增強開發中，部分功能設計、指令表面及／或實現曾參考或移植自 [Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)。此前 README、metadata 與 LICENSE 對這段來源關係說明不足，現已補充並進行逐項來源與授權審計。
>
> 詳細項目沿革、MIT 署名、代碼／功能設計／圖片與文案的不同授權邊界，以及目前審計範圍見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。在來源審計完成前，無法確認再分發權的第三方圖片、文案或資源不應被視為本項目原創或可自由再分發。

> [!NOTE]
> **它還是那個 `/今日小豬`。只是現在抽完不一定就完了。** 你的豬會留下豬籍、重複返場、長 EX；群友可以預約烤你、往鍋裡添柴、把 Roast Charge 燒光，再全群一起把烤箱救回來。晚上還有人負責把事故寫進《豬圈日報》。

## 🐷 現在這隻豬會什麼？

| 豬圈區域 | 會發生什麼 |
| --- | --- |
| 🐣 每日小豬 | 每人每天固定一隻；重查不洗豬，昨日／明日／本週都有獨立視圖 |
| 📚 永久豬籍 | `/我的豬圈` 記住真正解鎖過的種類、返場次數、本命與 EX Lv.；退役資源仍可保留歷史豬籍 |
| ⭐ EX 成長 | 同一隻從第 2 次開始進 EX；正式官方豬可沿 EX Lv.1–5 換描述、完整文案與圖片 |
| 🎯 新豬保底 | 連續重複 + 跨自然日疲勞共同提高條件式新豬重抽機會，總上限 80% |
| 🔥 群聊後廚 | 烤自己、烤群友、隨機烤、吃群友、次日保護與 60/30/10 反噬 |
| ⚡ Roast Charge | 每人每群獨立儲存烤箱能量；預設 2 格，缺少的 Charge 逐格自然恢復 |
| 🪵 預約與添柴 | 目標未抽豬可以先埋伏；`/添柴 @目標` 加入預約，裸 `/添柴` 會依補貨／預約上下文自動路由 |
| ⛽ 烤箱補貨 | `/烤箱補貨` 發起，全群活躍豬友 `/添柴`；達標後為符合條件且缺能量的玩家恢復最多 1 格 |
| 📰 豬圈日報 | 把成功燒烤、逃脫、反噬、被吃與群聊稱號整理成海報；手動查看只讀，自動推送按群 opt-in |
| 🎨 創作者後廚 | 本地豬、EX 差分、私人豬源與公共源人工審核都能從管理工作台完成 |

## ⚡ 快速開始

### 環境

| 項目 | 要求 |
| --- | --- |
| AstrBot | `>= 4.26.0` |
| Python | `>= 3.10` |
| Python 依賴 | `Pillow >= 10.0.0`、`httpx >= 0.27.0, < 1.0.0` |
| 插件身份 | `astrbot_plugin_rollpig_plus` |

推薦直接在 AstrBot 插件管理介面搜尋 **「今日小豬 · 增強版」** 或 `astrbot_plugin_rollpig_plus`。

手動安裝：

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

完成後重啟 AstrBot，確認載入身份為 `astrbot_plugin_rollpig_plus`。

> [!IMPORTANT]
> v3.2.0 起增強版使用獨立程式、配置與資料命名空間。不要把新版直接塞進舊 `astrbot_plugin_rollpig` 目錄；舊版升級先看 [運維、身份遷移與恢復](docs/OPERATIONS.md)。

### 第一次進豬圈

```text
/今日小豬
```

然後建議立刻再試：

| 指令 | 豬圈翻譯 |
| --- | --- |
| `/豬豬幫助` | 看目前這個實例真正開了哪些玩法；幫助卡會跟配置一起變 |
| `/我的豬圈 [頁碼]` | 翻永久豬籍，看看哪些已經拱進你家、哪些還沒來 |
| `/找豬 關鍵詞` | 按 ID、名稱、描述或完整梗文案翻豬牌 |
| `/烤群友 @某人` | 把群友送往 60/30/10 的後廚 |
| `/烤箱補貨` | 沒火了就發起一次群體補貨 |
| `/添柴` | 有補貨就補貨；沒有補貨時按待結算預約上下文處理 |
| `/添柴 @某人` | 明確加入對某人的預約烤豬 |
| `/豬圈日報` | 看今天誰最會烤、誰最慘、誰跑得最快 |

完整 command surface、繁簡別名與限制以 [指令百科](docs/COMMANDS.md) 和運行時 `/豬豬幫助` 為準。

## 📚 永久豬籍不是臨時相簿

`/我的豬圈` 看的是玩家歷史上真正擁有過什麼，而不是「目前豬源有哪些」。圖鑑會把現役已解鎖與仍有歷史所有權的退役小豬放在同一套 read model 裡；管理員明確 tombstone 的內容仍會尊重屏蔽。

圖鑑卡面也會直接告訴你：

- 現役入圈進度；
- 老豬留檔數量；
- 最常返場的小豬；
- 最高 EX；
- 每隻豬的返場次數；
- 哪些還沒拱進你家。

保底怎麼算看 [永久圖鑑與新豬保底](docs/gameplay/collection-pity.md)，EX 怎麼長看 [EX 成長](docs/gameplay/ex-growth.md)。

## 🔥 後廚規則，先記三句

1. **Charge 決定你能不能點火。** 預設每人每群 2 格，`group_roast_cooldown_hours` 現在表示「每缺一格 Charge 的恢復時間」，不是整個人的單一冷卻。
2. **60/30/10 決定點火後誰出事。** 60% 成功、30% 逃脫、10% 反噬；添柴不提高成功率。
3. **`/添柴` 是上下文入口。** 補貨輪次進行中時裸 `/添柴` 支持補貨；`/添柴 @目標` 明確支持預約。沒有補貨且只有一張預約時，裸 `/添柴` 也會加入那張；多張就要求指定目標。

舊 `/添煤` / `/加煤` / `/烤箱添煤` / `/烤箱添柴` 僅保留為補貨相容入口，不再作為玩家文檔主推命令。

精確規則見 [Roast Charge](docs/gameplay/roast-charge.md)、[60/30/10](docs/gameplay/roast-outcomes.md) 與 [預約烤豬技術規則](docs/ROAST-RESERVATIONS.md)。

## 📰 豬圈日報

手動 `/豬圈日報` 只讀。自動日報有全局 master switch，但每個群仍要自己 opt-in；沒有顯式開啟的群不會因為「曾經有人養過豬」就突然收到晚報。

可選「今日祭品」預設關閉，而且只可能在自動日報流程觸發；手動翻報紙不會吃人。

詳見 [豬圈日報玩家頁](docs/gameplay/daily-report.md) 與 [日報技術規則](docs/DAILY-REPORT.md)。

## ⚙️ 管理面板

AstrBot 插件頁內的 RollPig 工作台包含：

| 工作區 | 主要能力 |
| --- | --- |
| 數據總覽 | 使用者、抽取、活躍、收藏、熱門小豬與聚合趨勢 |
| 豬豬圖鑑 | 搜尋、新增、編輯、刪除、PigHub 選圖、下載原圖重修 |
| EX 成長 | 編輯 EX Lv.1–5 描述／完整文案／圖片並查看實際生效預覽 |
| 本地資源 | 管理新增、基礎源覆蓋、自訂圖片、刪除屏蔽與公共投稿 |
| 公共源審核 | 維護者查看候選、圖片、重複提示並批准／拒絕 |
| AstrBot 豬源 | 同步官方／私人 v1 manifest、查看協議與診斷狀態 |
| 數據存儲 | SQLite 驗證、JSON 匯出、派生狀態修復與安全回退 |
| 插件更新 | 只接受本倉庫穩定 Release，下載校驗、備份後替換 |

管理寫操作仍走 AstrBot Plugin Page 認證橋接、同源與 CSRF 邊界；文案可以豬言豬語，權限不能跟著胡鬧。

## ☁️ 資源與同步

小豬圖鑑採明確分層：

```text
內置／AstrBot v1／私人 manifest 基礎層
                 ↓
       本地新增／覆蓋／自訂圖片
                 ↓
              刪除屏蔽
                 ↓
           最終可抽取圖鑑
```

同步只替換基礎層，不應吞掉管理員的本地創作。預設 AstrBot 專用 manifest 為：

```text
https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

普通瀏覽器或不相容客戶端可能收到 403；這是協議相容性閘門，不等於不可偽造的秘密認證。真正封閉的私人源應使用你自己的 Token / mTLS 等邊界。

公共投稿只會在管理員明確確認後提交小豬 ID、名稱、描述、完整文案、圖片及對應 EX 差分；不提交群聊原文、群號、SQLite、備份或插件配置。人工審核批准後才會發佈。

> [!WARNING]
> 公開資源同步與第三方素材仍受來源與再分發權約束。來源或授權無法確認的圖片、文案、資源包與鏡像條目應在審計完成前停止公開分發；MIT 軟件授權不會自動授予第三方圖片或文案的再分發權。詳見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。

完整規則見 [資源管理](docs/RESOURCE-MANAGEMENT.md)。

## 🛡️ 資料與安全

- 正常運行以 SQLite 規範化資料承擔核心權威；JSON 留作匯出與災難回退。
- 資源下載在 manifest、大小、SHA-256、圖片限制全部通過後才原子切換。
- 更新與同步失敗保留最後可用資料，不先把能跑的豬圈拆掉。
- 增強版使用獨立 namespace，身份遷移採 Copy → Verify → Atomic Commit。
- 群聊收藏採 claim-aware logical-user 邊界，避免把不能證明相同身份的資料硬合併。

詳見 [OPERATIONS.md](docs/OPERATIONS.md) 與 [COLLECTION-IDENTITY.md](docs/COLLECTION-IDENTITY.md)。

## 🔧 常用配置

- `enable_new_pig_pity` / `pity_step_percent`：連續重複保底。
- `enable_daily_duplicate_pity`：跨日疲勞保底。
- `group_roast_max_charges`：每人每群最大 Roast Charge，預設 2。
- `group_roast_cooldown_hours`：**每格缺失 Charge 的恢復時間**，預設 8 小時。
- `enable_roast_reservation` / `roast_reservation_max_participants`：預約烤豬。
- `enable_oven_refill` / `oven_refill_*`：群體補貨。
- `enable_daily_report` / `daily_report_*`：豬圈日報。
- `resource_sync_enabled` / `resource_manifest_url`：官方／私人豬源同步。
- `storage_backend`：SQLite / JSON 回退策略。

完整預設值與有效範圍看 [配置參考](docs/CONFIGURATION.md)。

## 📖 文檔中心

| 想做什麼 | 去哪裡 |
| --- | --- |
| 我只想抽豬 | [30 秒開始養豬](docs/getting-started/index.md) |
| 我想看所有玩家玩法 | [玩家玩法總覽](docs/gameplay/index.md) |
| 我忘了命令 | [指令百科](docs/COMMANDS.md) |
| 我想知道 Charge / 添柴到底怎麼算 | [Roast Charge](docs/gameplay/roast-charge.md) |
| 我想做一隻自己的豬 | [創作者後廚](docs/creators/index.md) |
| 我是管理員 | [配置參考](docs/CONFIGURATION.md) / [運維手冊](docs/OPERATIONS.md) |
| 我維護豬源 | [資源管理](docs/RESOURCE-MANAGEMENT.md) / [豬源維護](docs/RESOURCE-SOURCE-MAINTENANCE.md) |
| 我在寫插件代碼 | [架構](docs/ARCHITECTURE.md) / [文案規範](docs/COPY-STYLE.md) / [貢獻指南](CONTRIBUTING.md) |

## 🧪 開發與驗證

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py legacy_main.py storage services renderers
pytest -q
pre-commit run --all-files --show-diff-on-failure
```

Release 流程還會跑 AstrBot 真實載入 smoke、Marketplace package、Wiki strict build 與 Resource Source gate。

## 致謝與來源

- 原始核心：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- AstrBot 直接上游／本倉庫 GitHub parent：[MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig)
- 後續部分功能設計、指令表面及／或實現參考與移植來源：[Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)
- 公共圖片平台：[PigHub](https://pighub.top/) 與 [PigHub-DB](https://github.com/BadFish-HSrui/PigHub-DB)

本增強分支持續保留上游作者署名與 MIT 授權資訊。更完整的來源、授權邊界與 2026-08 provenance audit 見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。

## License

本專案採用 [MIT License](LICENSE)。第三方圖片、文案、資料與其他非代碼資源的再分發權需按其各自來源另行確認。