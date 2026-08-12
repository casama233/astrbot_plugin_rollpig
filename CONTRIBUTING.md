# 貢獻指南

感謝你願意協助維護 `astrbot_plugin_rollpig`。本倉庫已經不只是單一 `main.py` 插件：目前包含 SQLite 存儲層、身份遷移、安全更新器、管理頁、瀏覽器測試與資源同步，因此任何修改都應把「資料安全、向後兼容與可驗證性」放在第一位。

## 開發環境

最低建議環境：

- Python 3.10+
- Node.js（只有管理頁／瀏覽器測試需要）
- Git

Python 依賴：

```bash
python -m venv .venv
```

啟用虛擬環境後：

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pytest pre-commit
pre-commit install
```

若修改管理頁或瀏覽器測試：

```bash
npm ci
```

## 倉庫結構

| 路徑 | 用途 |
| --- | --- |
| `main.py` | AstrBot 插件入口、命令、管理頁 API、圖片渲染與主要協調邏輯 |
| `rollpig_core.py` | 可獨立測試的核心判斷邏輯 |
| `services/` | 抽取、烤豬等領域服務 |
| `storage/` | JSON／SQLite 存儲、遷移、規範化表與恢復邏輯 |
| `identity_migration.py` | v3.2+ 獨立插件身份與舊增強版資料遷移 |
| `updater.py` | 管理面板安全更新器 |
| `pages/pig-manager/` | AstrBot 插件管理頁前端 |
| `resource/` | 內置小豬資料、圖片與字體 |
| `tests/` | Python 回歸測試與 Node.js／瀏覽器測試 |
| `docs/` | 當前文檔及歷史性能／驗證記錄 |

## 修改前先判斷影響面

### 修改聊天指令

若新增、刪除或更名 `@filter.command(...)`：

1. 同步更新 `render_help_image()` 的聊天幫助卡。
2. 同步更新 [`docs/COMMANDS.md`](docs/COMMANDS.md)。
3. 若改變行為／限制，更新 README 的常用指令表。
4. 為重要語義補回歸測試，尤其是只讀 @ 查看、每日唯一抽取、烤／吃資格與懲罰。

### 修改配置

若改 `_conf_schema.json`：

1. 保證程式初始化能正確讀取與容錯。
2. 同步更新 [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)。
3. 評估舊配置遷移是否應保留該鍵。
4. 新數值配置應有合理範圍與安全預設。

### 修改 SQLite／資料模型

這是高風險修改。至少要考慮：

- 舊資料能否無損升級。
- 遷移中途崩潰是否會留下可恢復狀態。
- `PRAGMA integrity_check`、外鍵與規範化一致性是否仍能通過。
- 是否會讓兼容匯出／回滾丟失事實。
- 跨進程／並發每日抽取唯一性是否仍成立。
- 是否需要 schema migration 與對應測試。

不要透過「刪掉損壞 DB 再重建」掩蓋資料問題；維護流程必須保留恢復證據。

### 修改身份遷移

`identity_migration.py` 的首要目標是**不誤遷移原版插件資料**。任何放寬來源判定的修改都需要證明不會把未知 `astrbot_plugin_rollpig` 資料直接搬入增強版命名空間。

### 修改安全更新器／網路下載

不要降低以下邊界：

- 更新來源固定到官方倉庫穩定 Release。
- 拒絕任意 URL、任意分支與不受控預發布包。
- 防路徑穿越、符號連結、壓縮炸彈與異常檔案數量。
- 公共資源下載限制 HTTPS、重定向與私網目的地。
- 在替換 active 資源或程式碼前完成驗證。

若確實需要改安全模型，PR 必須清楚說明威脅模型、理由與新增測試。

### 修改管理頁

核心管理功能應保持「增強層失敗不拖垮核心頁面」：

- 總覽、圖鑑、同步、SQLite 管理與安全更新不應依賴深度 Analytics 才能工作。
- 深度 Analytics 應繼續按需載入。
- 聚合分析不要回傳使用者 ID、群 ID 或原始聊天內容。
- 注意 AstrBot Plugin Page Bridge 的認證資源載入方式與 SPA 重掛載。

## 測試

與 CI 對齊的 Python 檢查：

```bash
python -m compileall -q main.py rollpig_core.py updater.py storage services
pytest -q
pre-commit run --all-files --show-diff-on-failure
```

CI 目前會在 Python 3.10 與 3.12 執行核心檢查。

管理頁測試：

```bash
npm test
```

瀏覽器性能腳本：

```bash
npm run test:browser-perf
```

不是每個 PR 都需要重跑性能測試；但若修改管理頁載入策略、Analytics、DOM 監聽、快取或大型資源，建議執行並保存前後對比。

## 文檔測試

文檔修改至少人工確認：

- Markdown 相對連結存在。
- 指令名與 `main.py` decorator 一致。
- 配置鍵、預設值與 `_conf_schema.json` 一致。
- 版本與插件身份與 `metadata.yaml` 一致。
- SQLite 語義沒有退回已過期的 v2.x 敘述。
- 安裝範例使用 `astrbot_plugin_rollpig_plus` 新身份目錄。

## 代碼風格

- 優先小而可驗證的修改，避免在修單一問題時順便重寫整個存儲層。
- 保持現有 Python 類型標註與命名習慣。
- 網路、檔案與資料遷移邏輯應有明確失敗邊界和日誌。
- 對使用者可見的錯誤訊息應能提示下一步，而不是只輸出底層例外。
- 不要在 PR 中提交本地資料庫、使用者資料、Cookie、Token 或管理頁認證資訊。

## Commit 與 PR

建議 commit 聚焦單一目的，例如：

```text
fix: prevent duplicate adapter fallback
feat: add group roast protection
docs: refresh v3.2 migration guide
test: cover sqlite recovery path
```

PR 說明至少包含：

- 改了什麼。
- 為什麼要改。
- 使用者／管理員影響。
- 若是 bug：根因。
- 資料遷移或兼容風險。
- 跑過哪些測試。

## 發版維護

準備新版本時，至少同步：

1. `metadata.yaml` 版本。
2. `main.py` 中對外顯示／User-Agent 等版本資訊（若適用）。
3. `CHANGELOG.md`。
4. README 的版本徽章與版本敏感敘述。
5. 受影響的 `docs/COMMANDS.md`、`docs/CONFIGURATION.md`、`docs/OPERATIONS.md`。
6. Release 工作流與安全更新契約測試。

不要讓「程式已升級、文檔仍描述上一代資料模型」再次發生。

## 問題回報

提交 Issue 時，請盡量附上：

- AstrBot 版本。
- 插件版本。
- 平台／適配器。
- 是否群聊或私聊。
- 可重現步驟。
- 預期結果與實際結果。
- 已去除敏感資訊的相關日誌。

若涉及資料損壞，不要先刪除 DB 或備份檔再回報；原始恢復證據通常比重新生成後的狀態更有價值。
