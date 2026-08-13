<div align="center">

<img src="./logo.png" width="168" alt="今日小豬 · 增強版 Logo">

# 今日小豬 · 增強版

### 每天一隻專屬小豬，把群聊變成一座會成長的收藏館

`astrbot_plugin_rollpig_plus` · AstrBot 每日互動、永久圖鑑與可視化資源管理插件

[![CI](https://github.com/casama233/astrbot_plugin_rollpig/actions/workflows/ci.yml/badge.svg)](https://github.com/casama233/astrbot_plugin_rollpig/actions/workflows/ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/casama233/astrbot_plugin_rollpig?display_name=tag&sort=semver)](https://github.com/casama233/astrbot_plugin_rollpig/releases)
![Current Version](https://img.shields.io/badge/current-3.3.0-ef5d82)
[![AstrBot](https://img.shields.io/badge/AstrBot-4.24.2%2B-f59e42)](https://github.com/AstrBotDevs/AstrBot)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-2ea44f)](LICENSE)

[快速開始](#快速開始) · [玩法一覽](#玩法一覽) · [管理面板](#管理面板) · [資源管理](#資源管理) · [文檔中心](#文檔中心)

</div>

> [!NOTE]
> 這不是一個只會回覆隨機圖片的簡單插件。每位使用者都有穩定的每日結果、可持續累積的永久圖鑑、跨日記錄與群聊玩法；管理員則擁有獨立的數據、資源及存儲工作台。

## 3.3.0 版本亮點

| 能力 | 帶來的改進 |
| --- | --- |
| 🧩 本地資源分層 | 一眼分辨「本地新增」與「覆蓋基礎源」，不再猜測哪一筆資料會生效 |
| 🚫 屏蔽管理 | 刪除小豬會進入可查看的屏蔽清單，管理員可安全取消屏蔽 |
| 🖼️ 原圖重修 | 編輯時可下載目前生效的原圖，重修後再上傳替換 |
| 🌐 PigHub 投稿 | 明確確認後，只把名稱與圖片提交到公共人工審核隊列 |
| ☁️ 私人豬源 | 不再預填會拒絕第三方客戶端的受限來源，改由管理員接入自有 HTTPS manifest |
| 📚 文檔重整 | README、配置、運維、資源管理及發版說明按正式專案方式維護 |

完整變更請閱讀 [CHANGELOG](CHANGELOG.md)；資源層、私人源及投稿流程詳見 [資源管理手冊](docs/RESOURCE-MANAGEMENT.md)。

## 為什麼選擇增強版

<table>
<tr>
<td width="33%" valign="top">

### 🐷 有記憶的每日互動

同一使用者同一天得到固定結果，不會因重複查詢改變；昨日、明日、本週與永久圖鑑共同形成可持續的收集體驗。

</td>
<td width="33%" valign="top">

### 🎮 為群聊設計的玩法

今日烤豬、烤群友、吃群友、隨機互動與豬圈日報，兼顧趣味、冷卻、保護與失敗回退。

</td>
<td width="33%" valign="top">

### 🛡️ 可運維的正式插件

SQLite 事務、JSON 備份、安全更新、資源校驗、身份隔離與管理面板，讓資料可觀察、可恢復、可長期維護。

</td>
</tr>
</table>

## 玩法一覽

- **每日固定抽取**：每日第一次抽取後結果固定，避免反覆刷新刷結果。
- **永久豬圈圖鑑**：記錄解鎖種類、抽取次數、本命豬與 `EX Lv.`。
- **重複保底**：可配置提高下一次抽到未解鎖小豬的機率。
- **時間視圖**：昨日真實記錄、明日固定預測、七日週報。
- **圖鑑探索**：隨機展示，或按 ID、名稱、描述、完整文案搜尋。
- **群聊互動**：烤自己、烤群友、隨機烤、吃群友與群聊日報。
- **AI 文案**：可選生成烤豬文案；模型不可用時自動回退本地模板。
- **管理工作台**：統計、圖鑑、本地資源、私人豬源、存儲及安全更新集中管理。

## 快速開始

### 環境要求

| 項目 | 要求 |
| --- | --- |
| AstrBot | `>= 4.24.2` |
| Python | `>= 3.10` |
| Python 依賴 | `Pillow >= 10.0.0`、`httpx >= 0.27.0, < 1.0.0` |
| 插件身份 | `astrbot_plugin_rollpig_plus` |

### 安裝

推薦在 AstrBot 插件管理介面搜尋 **「今日小豬 · 增強版」** 或 `astrbot_plugin_rollpig_plus` 安裝。

手動安裝：

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

完成後重啟 AstrBot，確認載入的插件身份是 `astrbot_plugin_rollpig_plus`。

> [!IMPORTANT]
> v3.2.0 起增強版使用獨立的程式、配置與資料命名空間。不要把新版直接放進舊 `astrbot_plugin_rollpig` 目錄；由舊版升級時請先閱讀 [身份遷移與恢復](docs/OPERATIONS.md#3-從舊增強版升級到-v320)。

### 第一次使用

先輸入：

```text
/豬豬幫助
```

常用指令：

| 指令 | 用途 |
| --- | --- |
| `/今日小豬` | 抽取或查看自己今天的小豬 |
| `/今日小豬 @某人` | 啟用對應配置後，只讀查看對方今日結果 |
| `/我的豬圈 [頁碼]` | 查看永久圖鑑 |
| `/昨日小豬` / `/明日小豬` | 查看真實昨日記錄或明日固定預測 |
| `/本週小豬` | 生成七日小豬週報 |
| `/隨機小豬 [1-9]` | 隨機展示，不影響每日結果 |
| `/找豬 關鍵詞` | 搜尋 ID、名稱、描述或文案 |
| `/今日烤豬` | 生成趣味料理卡 |
| `/烤群友 @某人` / `/吃群友 @某人` | 群聊互動玩法 |
| `/豬圈日報` | 查看本群今日概況 |

全部指令、別名和玩法限制請看 [指令手冊](docs/COMMANDS.md)。

## 管理面板

在 AstrBot 管理介面的「插件頁面」開啟 **今日小豬**：

| 工作區 | 主要能力 |
| --- | --- |
| 數據總覽 | 總使用者、累計抽取、今日活躍、人均解鎖、收藏率、14 日趨勢與熱門小豬 |
| 豬豬圖鑑 | 搜尋、新增、編輯、刪除、PigHub 選圖、AI 草稿、下載原圖重修 |
| 本地資源 | 查看本地新增與基礎源覆蓋、管理刪除屏蔽、取消屏蔽、提交 PigHub 審核 |
| 私人豬源 | 顯示同步診斷、手動同步及基礎層狀態；來源失敗時保留現有資源 |
| 數據存儲 | SQLite 驗證、派生狀態修復、JSON 匯出與安全回退 |
| 插件更新 | 只接受官方穩定 Release，下載、校驗、備份後再替換，不自動重啟 |

所有管理寫操作都經 AstrBot Plugin Page 認證橋接、同源檢查與 CSRF 驗證；深度分析只返回聚合結果，不暴露使用者、群號或聊天原文。

## 資源管理

小豬圖鑑採用明確的分層模型：

```mermaid
flowchart LR
    A["插件內置資源"] --> B["基礎層"]
    P["私人 HTTPS manifest"] --> B
    B --> C["本地新增／資料覆蓋／自訂圖片"]
    C --> D["刪除屏蔽"]
    D --> E["最終可抽取圖鑑"]
```

優先級由低至高：

1. 插件內置資源；私人源成功同步後，由私人源成為基礎層。
2. 管理面板建立的本地新增、資料覆蓋與自訂圖片。
3. 本地刪除屏蔽。

這代表同步和更新不會悄悄覆蓋管理員的本地編輯；刪除的基礎小豬也不會在下一次同步後自行復活。

### PigHub 與私人源的定位

- [PigHub](https://pighub.top/) 是公共圖片分享及人工審核平台，適合投稿單張名稱與圖片。
- PigHub 不是本插件完整的 `pig.json` 元資料源；描述、文案與本地規則不會隨投稿上傳。
- 如需在多個實例間同步完整圖鑑，請維護你有權使用的 HTTPS manifest。
- 舊預設 `pig.felislab.cc` 是 nonebot 專用受限源，會拒絕本 AstrBot 插件，因此 v3.3.0 不再預填。

manifest 格式、安全限制與故障排查請看 [資源管理手冊](docs/RESOURCE-MANAGEMENT.md)。

## 資料與安全

| 設計 | 行為 |
| --- | --- |
| SQLite 單一運行時權威 | 正常模式下以規範化 SQL 表承擔核心讀寫與唯一性約束 |
| JSON 按需輸出 | 僅在匯出、回退與災難恢復時生成兼容文件 |
| 原子資源替換 | manifest、大小、SHA-256 與圖片尺寸全部通過後才切換基礎層 |
| 本地資料隔離 | 插件更新不覆蓋插件資料目錄中的圖鑑、圖片與歷史記錄 |
| 失敗保留現況 | 同步、遷移或更新失敗時保留最後可用版本與恢復證據 |
| 公開投稿需確認 | PigHub 投稿每次都需管理員確認，只傳送名稱與圖片 |

詳細備份、SQLite、身份遷移、更新及恢復流程請看 [運維手冊](docs/OPERATIONS.md)。

## 配置

全部配置定義於 `_conf_schema.json`，推薦透過 AstrBot 插件配置介面修改。

常用配置：

- `at_view_pig`：是否允許 @ 他人只讀查看今日小豬。
- `enable_new_pig_pity` / `pity_step_percent`：連續重複保底。
- `enable_roast` / `enable_group_roast` / `enable_group_eat`：互動玩法開關。
- `enable_ai_roast_copy`：AI 烤豬文案。
- `timezone`：每日邊界時區。
- `resource_sync_enabled` / `resource_manifest_url`：私人豬源同步。
- `storage_backend` / `storage_busy_timeout_ms`：SQLite 與回退策略。

完整預設值、範圍及建議請看 [配置手冊](docs/CONFIGURATION.md)。

## 升級策略

- **v3.2.0+ → v3.3.0**：直接更新；現有 SQLite、本地小豬、自訂圖片和屏蔽記錄會保留。
- **v3.1.4 或更早增強版 → v3.3.0**：先完成獨立身份遷移，再確認新資料正常。
- **原版與增強版同時存在**：系統只提示衝突，不會擅自停用或刪除另一個插件。
- **舊公共源配置**：既有配置不會被偷偷改寫；若仍指向受限 nonebot 源，面板會顯示診斷，請改成自有 manifest 或停用同步。

## 文檔中心

| 文檔 | 適合誰 | 內容 |
| --- | --- | --- |
| [指令手冊](docs/COMMANDS.md) | 使用者、群管理員 | 指令、別名、限制與玩法規則 |
| [配置手冊](docs/CONFIGURATION.md) | 插件管理員 | 全配置項、預設值與建議 |
| [資源管理手冊](docs/RESOURCE-MANAGEMENT.md) | 資源維護者 | 分層、manifest、PigHub 投稿與 403 排查 |
| [運維手冊](docs/OPERATIONS.md) | 系統管理員 | 遷移、SQLite、備份、恢復與安全更新 |
| [市場分發](docs/MARKETPLACE.md) | 發版維護者 | 16 MB 限制、精簡包及驗證規則 |
| [貢獻指南](CONTRIBUTING.md) | 開發者 | 開發環境、測試與提交規範 |
| [版本記錄](CHANGELOG.md) | 所有人 | 每個正式版本的可見變更 |

## 開發與驗證

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py rollpig_core.py updater.py storage services
pytest -q
pre-commit run --all-files --show-diff-on-failure
npm ci
npm test
```

Release 由 `metadata.yaml` 的穩定版本號觸發，CI 生成 `astrbot_plugin_rollpig_plus-vX.Y.Z.zip` 與 `SHA256SUMS`，並檢查 AstrBot 市場 16 MB 上限。

## 致謝

- 原始核心：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- AstrBot 上游：[MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig)
- 公共圖片平台：[PigHub](https://pighub.top/) 與 [PigHub-DB](https://github.com/BadFish-HSrui/PigHub-DB)

本增強分支持續保留原作者署名與 MIT 授權資訊。

## License

本專案採用 [MIT License](LICENSE)。
