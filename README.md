<div align="center">

<img src="https://raw.githubusercontent.com/casama233/astrbot_plugin_rollpig/main/logo.png" width="168" alt="今日小豬 · 增強版 Logo">

# 今日小豬 · 進階版

本專案以 [GitHub 穩定 Release](https://github.com/casama233/astrbot_plugin_rollpig/releases/latest) 作為唯一且權威的當前版本發佈入口。在進行初次安裝或後續版本更新時，請務必從該頁面取得對應的正式版 ZIP 壓縮包，並搭配隨附的 `SHA256SUMS` 校驗檔完成完整性驗證後再行部署，以確保執行環境的安全與穩定。

### 每天抽一隻小豬，抽著抽著，群裡就熱鬧地搭起了一座豬圈和一間後廚。

`astrbot_plugin_rollpig_plus` · AstrBot 每日抽豬 × 永久豬籍檔案 × EX 形態成長 × 群聊後廚大作戰

[![CI](https://github.com/casama233/astrbot_plugin_rollpig/actions/workflows/ci.yml/badge.svg)](https://github.com/casama233/astrbot_plugin_rollpig/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/casama233/astrbot_plugin_rollpig?display_name=tag&sort=semver)](https://github.com/casama233/astrbot_plugin_rollpig/releases)
[![AstrBot](https://img.shields.io/badge/AstrBot-4.26.0%2B-f59e42)](https://github.com/AstrBotDevs/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](LICENSE)

![動態訪問量](https://count.kjchmc.cn/get/@astrbot_plugin_rollpig_plus?theme=minecraft)

[30 秒開始](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/getting-started/index.md) · [玩家玩法](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/gameplay/index.md) · [指令百科](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/COMMANDS.md) · [管理面板](#管理面板) · [完整 Wiki](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/index.md)

</div>

> [!CAUTION]
> **本插件程式碼由 AI 輔助生成，並經人工審閱把關。** 儘管如此，程式仍可能潛藏未發現的漏洞、安全隱患或相容性問題。請務必謹慎使用；在部署至重要帳號、正式生產環境或敏感場景前，強烈建議先自行審查源碼並完成充分測試。

> [!IMPORTANT]
> **專案來源與版權署名說明（2026-08-19）**
>
> 本倉庫是 [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig) 的 AstrBot 延續分支，其更早來源為 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)。後續增強開發中，部分功能設計、指令表面及／或實現曾參考或移植自 [Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)。此前 README、metadata 與 LICENSE 對這段來源關係說明不足，現已補充並進行逐項來源與授權審計。
>
> 詳細項目沿革、MIT 署名、代碼／功能設計／圖片與文案的不同授權邊界，以及目前審計範圍見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。在來源審計完成前，無法確認再分發權的第三方圖片、文案或資源不應被視為本項目原創或可自由再分發。

> [!NOTE]
> **它还是你熟悉的那个 `/今日小豬`，只不过现在抽完猪才算刚刚开始。** 抽到的小猪会录入永久猪籍、在群里反复返场、解锁 EX 形态；群友不仅能预约把你架上烤架、往灶膛里添柴火、一口气烧光 Roast Charge，还能在炸炉后全群合力把烤箱抢救回来。到了夜里，更有专人把白天的种种事故写进《猪圈日报》。

## 🐷 這隻小豬現在有哪些本事？

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

## ⚡ 火速開張

### 環境

| 項目 | 要求 |
| --- | --- |
| AstrBot | `>= 4.26.0` |
| Python | `>= 3.10` |
| Python 依賴 | 依 [`requirements.txt`](requirements.txt) 自動安裝 Pillow、httpx、OpenCC |
| 插件身份 | `astrbot_plugin_rollpig_plus` |

建議直接打開 AstrBot 的插件管理頁面，搜尋 **「今日小豬 · 增強版」** 或 `astrbot_plugin_rollpig_plus` 即可安裝。

手動部署步驟：

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

裝好後請重啟 AstrBot，並確認載入的插件識別為 `astrbot_plugin_rollpig_plus`。

> [!IMPORTANT]
> 自 v3.2.0 版本起，增強版已採用獨立的程式碼、設定檔與資料命名空間。請勿直接將新版檔案覆蓋進舊有的 `astrbot_plugin_rollpig` 資料夾；若需從舊版升級，請先詳閱 [運維、身份遷移與恢復](docs/OPERATIONS.md)。

基礎玩法均內建中文字型與離線素材，免設定本機絕對路徑、無需登入 Gemini，也不必準備私人源權杖。至於 AI 擴充功能與自訂豬源，依需求手動開啟即可。

### 初次踏入豬圈

```text
/今日小豬
```

接著不妨馬上試試這幾招：

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

完整的指令清單、繁簡體別名與使用限制，請以 [指令百科](docs/COMMANDS.md) 及執行時期的 `/豬豬幫助` 為準。

## 📚 永久豬籍簿，不只是臨時相簿

`/我的豬圈` 统计的是玩家历来真正养过的所有小猪，而非「目前猪圈里还留着几只」。图鉴会将现役已解锁与仍有历史纪录的退役猪只整合在同一套读取模型中；至于管理员明确标记 tombstone 的内容，依旧会老老实实屏蔽。

图鉴卡片上还会直观列出：

- 当前现役图鉴的收集进度；
- 退役老猪的归档数量；
- 最常跑回来串门的小猪；
- 最高 EX；
- 每只小猪各自的返场次数；
- 还有哪些小猪尚未拱进你家门槛。

保底机制怎么计算请参考 [永久圖鑑與新豬保底](docs/gameplay/collection-pity.md)，EX 形态如何解锁成长请见 [EX 成長](docs/gameplay/ex-growth.md)。

## 🔥 後廚規矩，先記牢這三條

1. **Charge 决定了你手头能不能点火。** 默认每位玩家在每个群拥有 2 格，而 `group_roast_cooldown_hours` 代表的是「每消耗一格 Charge 后的恢复时间」，并非整个人的单一总冷却。
2. **70/20/10 决定点火之后究竟谁遭殃。** 70% 代表烤制成功、20% 则是小猪溜走、10% 会引发炉火反噬；中途添柴并不会拉高成功率。
3. **`/添柴` 是依赖上下文的快捷入口。** 当群体补货轮次正在进行时，单发 `/添柴` 会直接参与补货；`/添柴 @目標` 则明确对应预约支持。若当前没有补货活动且场内仅有一张预约单，单发 `/添柴` 也会自动跟进该预约；一旦存在多张预约单，就必须明确指定目标。

原有的 `/添煤` / `/加煤` / `/烤箱添煤` / `/烤箱添柴` 仅作为补货兼容指令保留，不再列入玩家手册的主推用法。

详细的数值与判定细则，请参阅 [Roast Charge](docs/gameplay/roast-charge.md)、[70/20/10](docs/gameplay/roast-outcomes.md) 与 [預約烤豬技術規則](docs/ROAST-RESERVATIONS.md)。

## 📰 豬圈日報

手动执行 `/豬圈日報` 仅作只读浏览。自动日报虽然设有全局总开关，但各群仍需手动开启订阅（opt-in）；未明确启用的群聊，绝不会因为「曾经有人抽过猪」就在半夜莫名收到晚报。

附加的「今日祭品」功能默认处于关闭状态，且仅会在自动日报流程中触发；平时手动翻看报纸绝对不会把猪吃掉。

具体规则详见 [豬圈日報玩家頁](docs/gameplay/daily-report.md) 与 [日報技術規則](docs/DAILY-REPORT.md)。

<a name="管理面板"></a>

## ⚙️ 管理後台

AstrBot 插件页面内的 RollPig 控制台涵盖了：

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

所有管理端的写入操作依然严格经过 AstrBot Plugin Page 鉴权桥接、同源校验与 CSRF 防护；虽然文案可以满口猪言猪语，但系统权限绝不能跟着胡闹。

## ☁️ 資源庫與同步

小猪图鉴采取清晰的分层架构：

```text
內置／AstrBot v1／私人 manifest 基礎層
                 ↓
       本地新增／覆蓋／自訂圖片
                 ↓
              刪除屏蔽
                 ↓
           最終可抽取圖鑑
```

同步操作只会覆盖更新基础层，绝不会抹除管理员在本地创作的内容。默认的 AstrBot 专用 manifest 地址为：

```text
https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

普通浏览器或不兼容的客户端访问时可能会收到 403；这只是协议兼容性闸门，不能当作不可伪造的机密认证。若需部署真正封闭的私人猪源，请自行配置 Token 或 mTLS 等安全边界。

发起公共投稿时，仅会在管理员明确确认后上传小猪 ID、名称、简介、完整文案、立绘及对应的 EX 差分图；绝不会收集群聊记录、群号、SQLite 数据库、备份档或插件配置。稿件须经人工审核通过后才会正式发布。

> [!WARNING]
> 公開資源同步與第三方素材仍受來源與再分發權約束。來源或授權無法確認的圖片、文案、資源包與鏡像條目應在審計完成前停止公開分發；MIT 軟件授權不會自動授予第三方圖片或文案的再分發權。詳見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。

完整的投稿与同步规范请见 [資源管理](docs/RESOURCE-MANAGEMENT.md)。

## 🛡️ 資料與安全防護

- 日常运行期间，系统以规范化的 SQLite 数据库作为核心权威存储；JSON 文件则保留用于数据导出与灾难恢复回退。
- 拉取外部资源时，必须完整通过 manifest 校验、体积限制、SHA-256 哈希核对及图片规格检查后，才会执行原子切换。
- 一旦更新或同步中途出错，系统将自动保留最后一份可用数据，绝不会先把好端端运行着的猪圈拆毁。
- 增强版拥有独立的命名空间，跨版本身份迁移严格遵循 Copy → Verify → Atomic Commit 流程。
- 跨群图鉴收藏采用 claim-aware logical-user 隔离边界，杜绝将无法证明属于同一身份的数据强行合并。

詳見 [OPERATIONS.md](docs/OPERATIONS.md) 與 [COLLECTION-IDENTITY.md](docs/COLLECTION-IDENTITY.md)。

## 🔧 常用參數配置

- `enable_new_pig_pity` / `pity_step_percent`：连抽重复触发的保底机制。
- `enable_daily_duplicate_pity`：跨日连续抽猪的疲劳补偿保底。
- `group_roast_max_charges`：每位玩家在单个群聊内的 Roast Charge 上限，默认为 2。
- `group_roast_cooldown_hours`：**每消耗一格 Charge 所需的恢复时长**，默认为 8 小时。
- `enable_roast_reservation` / `roast_reservation_max_participants`：烤猪预约相关设置。
- `enable_oven_refill` / `oven_refill_*`：群内集体补货相关设置。
- `enable_daily_report` / `daily_report_*`：猪圈日报推送设置。
- `resource_sync_enabled` / `resource_manifest_url`：官方及私人猪源同步配置。
- `storage_backend`：SQLite 与 JSON 数据回退策略。

所有配置项的完整默认值与合法取值范围，请查阅 [配置參考](docs/CONFIGURATION.md)。

## 📖 文件與指南中心

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

## 🧪 開發與自動化驗證

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py legacy_main.py storage services renderers
pytest -q
pre-commit run --all-files --show-diff-on-failure
```

发版流水线还会自动执行 AstrBot 真实加载冒烟测试、插件市场打包校验、Wiki 严格构建以及资源源站门禁检查。

## 致謝與專案來源

- 原始核心架构：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- AstrBot 直接上游／本倉庫 GitHub parent：[MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig)
- 後續部分功能設計、指令表面及／或實現參考與移植來源：[Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)
- 公共图库素材平台：[PigHub](https://pighub.top/) 与 [PigHub-DB](https://github.com/BadFish-HSrui/PigHub-DB)

本增強分支持續保留上游作者署名與 MIT 授權資訊。更完整的來源、授權邊界與 2026-08 provenance audit 見 [`ATTRIBUTION.md`](ATTRIBUTION.md)。

## License

本專案採用 [MIT License](LICENSE)。第三方圖片、文案、資料與其他非代碼資源的再分發權需按其各自來源另行確認。