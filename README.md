<div align="center">

![astrbot_plugin_rollpig](https://raw.githubusercontent.com/casama233/astrbot_plugin_rollpig/main/logo.png)

# astrbot_plugin_rollpig

_✨ AstrBot「今日小豬」增強維護版 ✨_

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/AstrBot-4.24.2%2B-orange.svg)](https://github.com/AstrBotDevs/AstrBot)
![版本](https://img.shields.io/badge/version-3.2.0-pink.svg)
![動態訪問量](https://count.kjchmc.cn/get/@astrbot_plugin_rollpig?theme=gelbooru)

</div>

> [!IMPORTANT]
> 自 **v3.2.0** 起，本增強分支使用獨立插件身份 `astrbot_plugin_rollpig_plus`。若你曾使用本倉庫 v3.1.4 或更早版本，請先閱讀下方「升級與身份遷移」以及 [`docs/OPERATIONS.md`](docs/OPERATIONS.md)。

## 專案簡介

這是一個為 AstrBot 維護的「今日小豬」互動插件。每位使用者每天可抽取一隻固定的小豬，並在之後逐步解鎖永久圖鑑；同時提供昨日／明日／週報、圖鑑搜尋、烤豬、群友互動、管理面板、雲端資源同步與 SQLite 持久化等功能。

本倉庫基於 `MegSopern/astrbot_plugin_rollpig` 持續增強，保留 Bear_lele、MegSopern 的原作者署名與 MIT License。

- 上游 AstrBot 版本：`>= 4.24.2`
- Python：`>= 3.10`
- 主要 Python 依賴：`Pillow >= 10.0.0`、`httpx >= 0.27.0, < 1.0.0`
- 當前插件版本：`3.2.0`

## 主要功能

- **每日固定抽取**：同一使用者同一天重複查詢不會改變結果。
- **永久豬圈圖鑑**：記錄解鎖種類、抽取次數、本命豬與 `EX Lv.`。
- **連續重複保底**：可配置地提高下一次抽到未解鎖小豬的機率。
- **昨日／明日／本週**：可查昨日紀錄、明日固定預測與七日週報。
- **圖鑑探索**：支援隨機展示與按 ID、名稱、描述、完整文案搜尋。
- **烤豬玩法**：支援今日烤豬、烤群友、隨機烤群友、吃群友與群聊日報。
- **AI 烤豬文案**：可選啟用；模型不可用、超時或失敗時自動回退本地模板。
- **管理面板**：新增／編輯／刪除小豬、PigHub 選圖、資源同步、統計、SQLite 維護與安全更新。
- **公共資源同步**：下載前限制來源、大小與圖片像素，並以 manifest 尺寸與 SHA-256 驗證後原子替換。
- **SQLite 單一運行時權威**：v3.0 起規範化 SQLite 表是預設運行時資料來源；JSON 僅保留作兼容、匯出與災難回退用途。
- **獨立身份遷移**：v3.2.0 起與原版插件的程式、配置及資料命名空間分離。

## 安裝

### 方法一：AstrBot 插件管理介面

若你的 AstrBot 插件來源已索引本增強版，請搜尋 **「今日小豬 · 增強版」** 或插件名 `astrbot_plugin_rollpig_plus` 安裝。

### 方法二：手動安裝

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

安裝完成後重啟 AstrBot，並確認後台載入的插件名稱為 `astrbot_plugin_rollpig_plus`。

> [!WARNING]
> 不要把 v3.2.0+ 手動 clone 到舊目錄名 `astrbot_plugin_rollpig` 後直接啟動。新版本會檢查插件身份與命名空間，以避免增強版和原版共用配置或資料。

## 快速開始

最推薦先輸入：

```text
/豬豬幫助
```

插件會生成完整的聊天指令幫助卡。常用指令如下：

| 指令 | 用途 |
| --- | --- |
| `/今日小豬` | 抽取或查看自己今天的小豬 |
| `/今日小豬 @某人` | 啟用 `at_view_pig` 後只讀查看對方今日結果，不會替對方抽取 |
| `/我的豬圈 [頁碼]` | 查看永久圖鑑，每頁 12 隻 |
| `/昨日小豬` | 查看昨天真實抽取紀錄 |
| `/明日小豬` | 查看明日固定預測與 1–5 星豬運，不提前解鎖 |
| `/本週小豬` | 生成本週七日小豬週報 |
| `/隨機小豬 [1-9]` | 從本地圖鑑隨機展示，不影響每日結果 |
| `/找豬 關鍵詞` | 按 ID、名稱、描述或完整文案搜尋 |
| `/今日烤豬` | 把自己今日小豬生成趣味料理卡 |
| `/烤群友 @某人` | 群聊中嘗試烤指定群友 |
| `/隨機烤群友` | 從本群今日可烤成員中隨機選擇 |
| `/吃群友 @某人` | 以可配置成功率吃掉群友；失敗時發起者會變成「吃掉了」 |
| `/隨機吃群友` | 從本群今日可吃成員中隨機選擇 |
| `/豬圈日報` | 顯示本群今日抽豬與被吃概況 |

完整指令、別名、限制條件、後門口令與群聊玩法規則請看：[`docs/COMMANDS.md`](docs/COMMANDS.md)。

## 管理面板

在 AstrBot 管理介面的「插件頁面」中開啟 **今日小豬** 管理頁，可完成：

- 查看總使用者、累計抽取、今日活躍、人均解鎖與收藏率。
- 查看近 14 日趨勢、熱門小豬與按需載入的深度 Analytics。
- 新增、搜尋、編輯、刪除小豬。
- 上傳圖片並標準化為 `512×512 PNG`。
- 從 PigHub.top 搜尋／瀏覽圖片並建立本地小豬資料。
- 手動同步公共資源並查看同步狀態。
- 檢查與安裝本倉庫最新穩定 Release。
- 查看 SQLite 狀態、執行備份／匯出／驗證／回退等維護操作。

管理面板中的本地新增、編輯與圖片會儲存在插件資料目錄，不會因更新插件程式碼而被覆蓋。

## 配置

所有可配置項目都定義於 `_conf_schema.json`。推薦直接透過 AstrBot 插件配置介面修改，而不是手工編輯運行時配置檔。

完整配置表、預設值與建議請看：[`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)。

常見項目包括：

- `at_view_pig`：是否允許 @ 他人只讀查看今日小豬。
- `enable_new_pig_pity` / `pity_step_percent`：連續重複保底。
- `enable_roast` / `enable_group_roast` / `enable_group_eat`：烤豬與群聊玩法開關。
- `eat_success_percent`：吃群友成功率。
- `eaten_next_day_failure_percent`：被吃後次日抽豬失敗率。
- `enable_ai_roast_copy`：AI 烤豬文案。
- `timezone`：每日邊界時區。
- `resource_sync_*`：公共資源同步。
- `storage_backend` / `storage_busy_timeout_ms`：資料後端與 SQLite 寫鎖等待時間。

## 資料、資源與優先級

小豬圖鑑會按以下邏輯組合：

1. 公共雲端資源；不可用時回退插件內置 `resource/`。
2. 管理面板建立的本地新增／編輯與自訂圖片。
3. 本地刪除屏蔽；被刪除的雲端小豬不會在下次同步後自動復活。

對一般管理員而言，**建議透過管理面板維護小豬**。直接修改倉庫內 `resource/pig.json` 與 `resource/image/` 更適合開發或提交上游資源，因為它們屬於插件程式包本身。

內置資料格式：

```json
[
  {
    "id": "pig",
    "name": "豬",
    "description": "普通小豬",
    "analysis": "你性格溫和，喜歡簡單的生活。"
  }
]
```

對應圖片可使用 `png`、`jpg`、`jpeg`、`webp`、`gif`，檔名需與 `id` 相同，例如 `pig.png`。

## SQLite、備份與恢復

v3.0 起，規範化 SQLite 表是正常模式下的單一運行時權威；`storage_backend=auto` 會讓新安裝直接建立 SQLite，舊 JSON 安裝則先備份、導入臨時資料庫並完成完整性與事實級對帳後再原子切換。

`storage_backend=json` 僅建議作緊急災難回退；若資料庫無效，插件會保留恢復證據並避免以損壞資料覆蓋有效資料。

詳細資料檔、遷移流程、備份、安全更新與故障排查請看：[`docs/OPERATIONS.md`](docs/OPERATIONS.md)。

## 升級與身份遷移

v3.2.0 起，本增強版使用獨立資料與配置命名空間。首次安裝時只會在能確認舊資料確實來自本增強分支時執行遷移；流程為 **Copy → Verify → Atomic Commit**，成功後舊資料仍保留，不會自動刪除。

若同時啟用了舊插件，系統只會警告，不會替你停用或移除。請確認新插件資料正常後再手動停用舊插件，避免重複註冊指令。

## 開發與測試

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py rollpig_core.py updater.py storage services
pytest -q
pre-commit run --all-files --show-diff-on-failure
```

管理頁另有 Node.js 測試：

```bash
npm ci
npm test
```

詳細開發規範見 [`CONTRIBUTING.md`](CONTRIBUTING.md)。版本變更見 [`CHANGELOG.md`](CHANGELOG.md)。

## 文檔索引

- [`docs/COMMANDS.md`](docs/COMMANDS.md) — 聊天指令、別名與玩法規則
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — 全部配置項目
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — 安裝升級、遷移、存儲、同步、更新與故障排查
- [`docs/README.md`](docs/README.md) — 文檔目錄與歷史技術說明索引
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 開發與貢獻流程
- [`CHANGELOG.md`](CHANGELOG.md) — 發版歷史

## 致謝

- 原始核心邏輯：[Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)
- AstrBot 版本上游：[MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig)
- 本增強維護分支：`casama233/astrbot_plugin_rollpig`

## License

本專案採用 [MIT License](LICENSE)。衍生維護仍保留原作者署名與授權資訊。

![Star History Chart](https://api.star-history.com/svg?repos=casama233/astrbot_plugin_rollpig&type)
