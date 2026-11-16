<div align="center">

<img src="https://raw.githubusercontent.com/casama233/astrbot_plugin_rollpig/main/logo.png" width="168" alt="今日小豬 · 增強版 Logo">

# 今日小豬 · 增強版

本分支程式版本：**v3.12.4** · 鏡像來源／撤回收口、既有 SQLite 啟動前檢查與管理頁來源顯示修正。**可更新的穩定版本**以 [GitHub 穩定 Release](https://github.com/casama233/astrbot_plugin_rollpig/releases/latest) 為準；只有對應 tag、ZIP 與 SHA256SUMS 建立完成才算正式發布，main 合併本身不代表已可更新。

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
> **它还是那个 `/今日小豬`，只是现在抽完还没完。** 你的猪会留下猪籍、反复返场、长 EX；群友能预约烤你、往锅里添柴、把 Roast Charge 烧光，再全群合力把烤箱救回来。夜里还有人负责把事故记进《猪圈日报》。

## 🐷 現在這隻豬會什麼？

| 豬圈區域 | 會發生什麼 |
| --- | --- |
| 🐣 每日小豬 | 每人每天固定一隻；重查不洗豬，昨日／明日／本週都有獨立視圖 |
| 📚 永久豬籍 | `/我的豬圈` 記住真正解鎖過的種類、返場次數、本命與 EX Lv.；退役資源仍可保留歷史豬籍 |
| ⭐ EX 成長 | 同一隻從第 2 次開始進 EX；正式官方豬可沿 EX Lv.1–5 換描述、完整文案與圖片 |
| 🎯 新豬保底 | 連續重複 + 跨自然日疲勞共同提高條件式新豬重抽機會，總上限 80% |
| 🔥 群聊後廚 | 烤自己、烤群友、隨機烤、吃群友、次日保護與 70/20/10 反噬 |
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
| Python 依賴 | 依 [`requirements.txt`](requirements.txt) 自動安裝 Pillow、httpx、OpenCC |
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

基本功能使用隨包中文字體和離線資源，無需設定本機絕對路徑、Gemini 登入或私人源令牌。AI 附加功能與自訂豬源按需開啟。

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
| `/烤群友 @某人` | 把群友送往 70/20/10 的後廚 |
| `/烤箱補貨` | 沒火了就發起一次群體補貨 |
| `/添柴` | 有補貨就補貨；沒有補貨時按待結算預約上下文處理 |
| `/添柴 @某人` | 明確加入對某人的預約烤豬 |
| `/豬圈日報` | 看今天誰最會烤、誰最慘、誰跑得最快 |

完整 command surface、繁簡別名與限制以 [指令百科](docs/COMMANDS.md) 和運行時 `/豬豬幫助` 為準。

## 📚 永久豬籍不是臨時相簿

`/我的豬圈` 认的是玩家历史上真正养过哪些猪，而不是「当前猪圈里还有啥」。图鉴会把现役已解锁和仍有历史记录的退役小猪放在同一套 read model 里；管理员明确 tombstone 的内容仍会老实屏蔽。

图鉴卡面还会直接告诉你：

- 现役入圈进度；
- 老猪留档数量；
- 最常返场的小猪；
- 最高 EX；
- 每只猪的返场次数；
- 哪些还没拱进你家。

保底怎么算看 [永久圖鑑與新豬保底](docs/gameplay/collection-pity.md)，EX 怎么长看 [EX 成長](docs/gameplay/ex-growth.md)。

## 🔥 後廚規則，先記三句

1. **Charge 决定你能不能点火。** 默认每人每群 2 格，`group_roast_cooldown_hours` 现在表示「每缺一格 Charge 的恢复时间」，不是整个人的单一冷却。
2. **70/20/10 决定点火后谁倒霉。** 70% 成功、20% 逃脱、10% 反噬；添柴不会提高成功率。
3. **`/添柴` 是上下文入口。** 补货轮次进行中时裸 `/添柴` 支持补货；`/添柴 @目標` 明确支持预约。没有补货且只有一张预约时，裸 `/添柴` 也会跟进那张；多张就得指定目标。

旧 `/添煤` / `/加煤` / `/烤箱添煤` / `/烤箱添柴` 仅保留为补货兼容入口，不再作为玩家文档主推命令。

精确规则见 [Roast Charge](docs/gameplay/roast-charge.md)、[70/20/10](docs/gameplay/roast-outcomes.md) 与 [預約烤豬技術規則](docs/ROAST-RESERVATIONS.md)。

## 📰 豬圈日報

手动 `/豬圈日報` 只读。自动日报有全局 master switch，但每个群仍要自己 opt-in；没显式开启的群不会因为「曾经有人养过猪」就半夜突然收到晚报。

可选「今日祭品」默认关闭，而且只可能在自动日报流程触发；手动翻报纸不会吃人。

详见 [豬圈日報玩家頁](docs/gameplay/daily-report.md) 与 [日報技術規則](docs/DAILY-REPORT.md)。

## ⚙️ 管理面板

AstrBot 插件页内的 RollPig 工作台包含：

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

管理写操作仍走 AstrBot Plugin Page 认证桥接、同源与 CSRF 边界；文案可以猪言猪语，权限不能跟着胡闹。

## ☁️ 資源與同步

小猪图鉴采用明确分层：

```text
內置／AstrBot v1／私人 manifest 基礎層
                 ↓
       本地新增／覆蓋／自訂圖片
                 ↓
              刪除屏蔽
                 ↓
           最終可抽取圖鑑
```

同步只替换基础层，不会吞掉管理员的本地创作。默认 AstrBot 专用 manifest 为：

```text
https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

普通浏览器或不兼容客户端可能收到 403；这是协议兼容性闸门，不等同于不可伪造的秘密认证。真正封闭的私人源请用你自己的 Token / mTLS 等边界。

公共投稿只会在管理员明确确认后提交小猪 ID、名称、描述、完整文案、图片及对应 EX 差分；不提交群聊原文、群号、SQLite、备份或插件配置。人工审核批准后才会发布。

> [!WARNING]
> 公開資源同步與第三方素材仍受來源與再分發權約束。來源或授權無法確認的圖片、文案、資源包與鏡像條目應在審計完成前停止公開分發；MIT 軟件授權不會自動授予第三方圖片或文案的再分發權。詳見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。

完整规则见 [資源管理](docs/RESOURCE-MANAGEMENT.md)。

## 🛡️ 資料與安全

- 正常运行时以 SQLite 规范化数据承担核心权威；JSON 留作导出与灾难回退。
- 资源下载在 manifest、大小、SHA-256、图片限制全部通过后才原子切换。
- 更新与同步失败会保留最后可用数据，不先把能跑的猪圈拆掉。
- 增强版使用独立 namespace，身份迁移采用 Copy → Verify → Atomic Commit。
- 群聊收藏采用 claim-aware logical-user 边界，避免把不能证明相同身份的数据硬凑一块。

詳見 [OPERATIONS.md](docs/OPERATIONS.md) 與 [COLLECTION-IDENTITY.md](docs/COLLECTION-IDENTITY.md)。

## 🔧 常用配置

- `enable_new_pig_pity` / `pity_step_percent`：连续重复保底。
- `enable_daily_duplicate_pity`：跨日疲劳保底。
- `group_roast_max_charges`：每人每群最大 Roast Charge，默认 2。
- `group_roast_cooldown_hours`：**每格缺失 Charge 的恢复时间**，默认 8 小时。
- `enable_roast_reservation` / `roast_reservation_max_participants`：预约烤猪。
- `enable_oven_refill` / `oven_refill_*`：群体补货。
- `enable_daily_report` / `daily_report_*`：猪圈日报。
- `resource_sync_enabled` / `resource_manifest_url`：官方与私人猪源同步。
- `storage_backend`：SQLite / JSON 回退策略。

完整默认值与有效范围见 [配置參考](docs/CONFIGURATION.md)。

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

Release 流程还会运行 AstrBot 真实加载 smoke、Marketplace package、Wiki strict build 与 Resource Source gate。

## 致謝與來源

- 原始核心：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- AstrBot 直接上游／本倉庫 GitHub parent：[MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig)
- 後續部分功能設計、指令表面及／或實現參考與移植來源：[Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)
- 公共图片平台：[PigHub](https://pighub.top/) 与 [PigHub-DB](https://github.com/BadFish-HSrui/PigHub-DB)

本增強分支持續保留上游作者署名與 MIT 授權資訊。更完整的來源、授權邊界與 2026-08 provenance audit 見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。

## License

本專案採用 [MIT License](LICENSE)。第三方圖片、文案、資料與其他非代碼資源的再分發權需按其各自來源另行確認。