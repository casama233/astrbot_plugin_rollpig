# 運維、升級與故障排查

本文面向插件管理員與維護者，說明 v3.12.1 的身份遷移、資料存儲、資源同步、安全更新、備份與常見故障處理。

## 1. 版本與身份

### v3.12.1 穩定版更新

本版最低支援 AstrBot `>=4.26.0`。請從插件管理工作台的安全更新功能檢查穩定版本，確認取得 v3.12.1 後執行更新，完成後重載插件或重啟 AstrBot。新渲染器會將 EX Lv.n 固定在卡片底部；PNG 與 GIF 使用相同布局。

`main` 合併只是原始碼更新。正式發版必須同步 metadata.yaml、Changelog 與 Release Notes，經 PR 檢查及合併後 main CI 通過，再由 Release workflow 對該精確提交建立新 tag、ZIP 和 SHA256SUMS。既有穩定版 tag 與 ZIP 不應覆寫，也不應繞過安全更新器安裝任意分支。

本操作更新 AstrBot 插件程式，與 `rollpig-source upgrade` 更新公共源服務是兩件事；插件 v3.12.1 不表示公共源已發布新 resource_version，也不刪除玩家豬籍或本地 EX 資料。


目前插件身份：

```text
astrbot_plugin_rollpig_plus
```

倉庫仍為：

```text
casama233/astrbot_plugin_rollpig
```

這兩者不是衝突：`metadata.yaml` 中的插件名稱決定 AstrBot 插件身份，而 GitHub 倉庫 URL 可以保持原地址。

### 為什麼 v3.2.0 要換身份？

歷史上原版與增強版可能共享 `astrbot_plugin_rollpig` 這個名稱。v3.2.0 將增強版的程式、配置與資料命名空間拆開，避免：

- 原版和增強版共用同一份配置。
- 誤把原版資料當成增強版 SQLite／多檔案資料遷移。
- 同一命令由兩個插件同時註冊但資料落在同一目錄。

## 2. 新安裝

手動安裝時，建議目錄名與新插件身份一致：

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

完成後重啟 AstrBot，確認後台顯示「今日小豬 · 增強版」。

不要把 v3.2.0+ 放到舊 `astrbot_plugin_rollpig` 程式／配置命名空間中強行啟動；身份驗證會拒絕不安全的混用方式。

## 3. 從舊增強版升級到 v3.2.0+

首次載入新身份時，插件會嘗試辨識舊增強版資料來源。

### 可自動遷移的前提

插件必須能確認舊資料確實來自本增強分支，例如：

- 存在 v3.1.4 寫入的來源標記；或
- 舊資料符合增強版 SQLite／多檔案指紋要求。

如果只能看到無法確認來源的原版資料，插件會拒絕自動搬運，避免污染新命名空間。

### 遷移安全流程

資料搬移遵循：

```text
Copy → Verify → Atomic Commit
```

核心原則：

1. 先複製，不直接改寫舊資料。
2. SQLite 使用安全備份流程；其他檔案以 SHA-256 等方式核對。
3. 全部驗證成功後才切換新資料。
4. 遷移成功後舊目錄仍保留，不會被自動刪除。

配置遷移只帶入目前 `_conf_schema.json` 仍支援的欄位；未知或已廢棄欄位不會一起複製。

### 遷移後要做什麼？

至少檢查：

- `/今日小豬` 能否讀到既有今日資料或正常抽取。
- `/我的豬圈` 的歷史解鎖數是否合理。
- 管理頁統計與圖鑑是否可讀。
- 本地自訂圖片／本地新增小豬是否仍存在。
- SQLite 狀態是否健康。

確認新插件正常後，再手動停用舊插件。

> [!WARNING]
> 若舊插件仍啟用，系統只會警告，不會代替管理員停用。兩個插件同時註冊相同命令可能導致重複響應。

## 4. SQLite 運行模型

### v3.0+ 的權威來源

從 v3.0.0 起，**規範化 SQLite 表是正常模式下的單一運行時權威**。

這代表：

- 每日抽取、圖鑑、烤豬／吃豬狀態、AI 文案與身份映射等熱路徑以 SQL 事實表為主。
- 管理頁統計在 SQLite 模式下直接聚合 SQL 表。
- JSON 兼容資料主要用於遷移、匯出、回滾與災難恢復，不再是正常熱路徑的主要寫入權威。

### `storage_backend=auto`

推薦使用。

新安裝：直接建立 SQLite。

舊 JSON 安裝：

1. 備份關鍵兼容資料。
2. 建立臨時 SQLite。
3. 導入歷史與運行資料。
4. 執行完整性、外鍵與規範化一致性檢查。
5. 執行事實級對帳。
6. 全部通過後才原子切換。

### SQLite 運行參數

目前設計使用：

- WAL。
- `foreign_keys=ON`。
- `synchronous=NORMAL`。
- 可配置 `busy_timeout`，預設 `5000 ms`。

## 5. 資料與目錄

實際根目錄由 AstrBot 的 `StarTools.get_data_dir("astrbot_plugin_rollpig_plus")` 決定，不要假設所有部署都使用同一個絕對路徑。

插件資料目錄中可能出現：

- `rollpig.db` 及 SQLite 相關檔案。
- 圖鑑／歷史兼容資料。
- `local_overrides.json` — 本地新增／編輯覆蓋資料（在兼容／遷移場景可能使用）。
- `deleted_pigs.json` — 本地刪除屏蔽。
- `images/` — 本地自訂圖片。
- `cloud_resources/` — 公共資源快取、active 資源與同步狀態。
- `pighub_images.json`、`pighub_thumbnails/` — PigHub 快取。
- AI 文案、烤豬狀態及其他兼容／恢復資料。

v3.0+ 不保證每一份舊 JSON 都會在正常運行中持續被重寫；不要以「某 JSON 最近沒有變」判定資料遺失。

## 6. 手動備份建議

在進行重大升級、主機搬遷或手工資料操作前：

1. 停止會持續寫入插件資料的 AstrBot 實例，或至少確保沒有並發寫入。
2. 優先使用管理面板提供的備份／匯出功能。
3. 若必須做檔案級備份，完整保存插件資料目錄，而不是只複製 `rollpig.db` 單檔。
4. SQLite 使用 WAL 時，不要在運行中隨意漏掉旁路檔案後就宣稱備份完整。
5. 備份完成後再進行人工修改。

不要直接刪除疑似損壞的 `rollpig.db`、`-wal` 或 `-shm` 來「重置」；先保留恢復證據，再用管理面板或受控流程修復／回退。

## 7. 私人資源同步

v3.4.0+ 預設啟用 AstrBot v1 專用源，自動同步間隔為 24 小時。管理員仍可關閉同步，或改填有權使用、兼容 v1 基本欄位的 HTTPS 私人源。

舊版曾預填的 `pig.felislab.cc` 是 nonebot 專用受限來源，會對本 AstrBot 插件回傳 HTTP 403。既有配置會保留作診斷證據，不會被更新程序靜默覆蓋。

### 同步安全策略

同步器不是簡單下載覆蓋，而是先驗證再切換：

- 只接受 HTTPS manifest。
- 限制重定向主機與解析結果，拒絕危險／私網目的地。
- 限制 manifest 與資源包大小。
- 限制單檔大小與圖片像素。
- 對 manifest 宣告的大小與 SHA-256 做校驗。
- 整包全部通過後才替換 active 資源。

同步失敗時會繼續使用舊快取；沒有舊快取時回退插件內置資源。

### 資源優先級

有效圖鑑按以下邏輯組合：

1. AstrBot 專用源或私人源基礎層；不可用時使用插件內置資源。
2. 本地新增／編輯覆蓋與自訂圖片。
3. 本地刪除屏蔽。

因此，管理員刪掉一隻基礎小豬後，下次同步不會直接把它「復活」。管理面板的「本地資源」頁可查看本地新增、覆蓋與屏蔽，並可取消屏蔽。

完整 manifest 格式、分層語義與 403 排錯方式見 [`RESOURCE-MANAGEMENT.md`](RESOURCE-MANAGEMENT.md)。

## 8. PigHub 圖片導入與自建公共源投稿

管理頁可瀏覽／搜尋 PigHub.top 並選擇圖片，再由管理員補充小豬名稱、描述與完整文案。

圖片導入會受到：

- `resource_max_file_size_mb`。
- 下載來源與網路安全規則。
- 圖片驗證與標準化。

管理頁上傳的小豬圖會轉成 `512×512 PNG` 保存到插件資料目錄，而不是修改倉庫內置 `resource/image/`。

本地資源頁可把本地小豬提交到本專案自建的 AstrBot 公共源人工審核。每次操作都要求管理員明確確認，會發送 ID、名稱、描述、完整文案與圖片，不發送群友、群組或聊天資料。PigHub 僅保留為選圖來源。

只有維護者伺服器放置 `public_source_admin.token` 後，管理面板才顯示待審核區。批准操作會建立新資源版本並原子發佈；該 Token 不會出現在前端、配置 schema 或日誌中。

## 9. 管理面板安全更新

更新器固定連接：

```text
casama233/astrbot_plugin_rollpig
```

只檢查最新**穩定 Release**，不接受：

- 任意 URL。
- 自訂分支。
- 預發布版本。

### 安全限制

更新包具有額外限制，包括：

- 下載大小上限約 64 MiB。
- 最多約 3000 個檔案。
- 解壓總體積上限約 256 MiB。
- 拒絕路徑穿越。
- 拒絕符號連結。
- 拒絕異常壓縮比。
- Release 若提供 SHA-256 檔案則強制核對。
- 若沒有可用 SHA-256，介面會顯示風險並要求額外確認。

替換程式碼前會在插件資料目錄建立備份；安裝失敗會嘗試回滾。更新流程不應覆蓋圖鑑歷史、本地圖片、懲罰狀態或 AstrBot 插件配置。

### 更新後為什麼版本沒有立即變？

安全更新完成後**不會自動重啟 AstrBot**。請由管理員確認更新結果後手動重啟或重新載入插件。

## 10. AI 烤豬文案

`enable_ai_roast_copy=false` 為預設。

啟用後：

- 使用當前會話模型。
- 調用超時由 `ai_generation_timeout_seconds` 控制。
- 模型不可用、報錯或超時時回退本地料理文案。
- 同一隻豬同一天最多實際嘗試一次生成，避免多人重複烤同一豬造成 Token 浪費。
- 成功文案會保留七個自然日窗口供復用。

因此「AI 文案失敗」通常不應讓 `/今日烤豬` 整體失效。

## 11. 常見故障排查

### 問題：啟動時提示插件命名空間錯誤

檢查手動 clone 目錄是否仍叫：

```text
astrbot_plugin_rollpig
```

v3.2.0+ 應使用獨立身份目錄，例如：

```text
astrbot_plugin_rollpig_plus
```

若是從舊版本升級，請不要用直接覆蓋舊目錄的方式繞過身份遷移。

### 問題：一個指令回覆兩次

優先檢查原版／舊增強版是否與 `astrbot_plugin_rollpig_plus` 同時啟用。身份遷移不會自動停用舊插件。

### 問題：每天重置時間不對

檢查 `timezone`：

- `local` = AstrBot 主機系統時區。
- 建議跨區部署明確填 `Asia/Hong_Kong`、`Asia/Shanghai` 等 IANA 時區。

修改後重新載入插件。

### 問題：公共資源同步失敗

依序檢查：

1. 管理頁同步狀態與 AstrBot 日誌。
2. manifest URL 是否 HTTPS。
3. 伺服器 DNS／TLS 是否正常。
4. 若必須經代理出網，再考慮開啟 `resource_use_system_proxy`。
5. 不要先刪除現有 `cloud_resources/active`；同步器本身會在失敗時保留舊快取。

### 問題：開了系統代理後同步反而卡住

`resource_use_system_proxy` 預設為 `false` 就是為了避免失效 `HTTP_PROXY`／`HTTPS_PROXY` 造成 TLS 卡住。若伺服器可以直連，保持關閉。

### 問題：SQLite 顯示不健康或回退

不要直接覆蓋資料庫。

1. 查看管理面板存儲狀態。
2. 保存現有資料與恢復證據。
3. 執行完整性／外鍵／投影或規範化一致性檢查。
4. 若有有效備份，按管理面板提供的回滾流程操作。
5. 只有在明確理解影響時才切換 `storage_backend=json` 做緊急回退。

### 問題：管理頁深度 Analytics 沒有載入

v3.1.1 起深度 Analytics 是按需載入，核心總覽、圖鑑、同步、SQLite 與安全更新不需要等待整套 Analytics 資源。先確認是否點擊了深度分析入口；若增強資源失敗，核心管理功能理論上仍應可用。

若剛升級管理頁，可重新進入插件頁或刷新 AstrBot 管理後台，避免瀏覽器保留舊版本前端狀態。

### 問題：聊天圖片發送超時後出現重複訊息

v3.1.3 已將圖片適配器超時視為「投遞狀態不確定」，不再立即補發另一份 fallback。若仍能穩定重現重複訊息，請記錄：

- AstrBot 版本。
- 平台適配器。
- 是否群聊／私聊。
- 完整日誌與時間戳。

這類問題更可能與適配器實際投遞語義有關，需要以日誌重現判斷。

## 12. 發版前維護檢查

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py rollpig_core.py updater.py storage services
pytest -q
pre-commit run --all-files --show-diff-on-failure
npm ci
npm test
```

並人工檢查：

- `metadata.yaml` 版本是否正確。
- `CHANGELOG.md` 是否新增版本條目。
- README 的當前版本與存儲語義是否仍正確。
- `docs/COMMANDS.md` 是否與命令 decorator 一致。
- `docs/CONFIGURATION.md` 是否與 `_conf_schema.json` 一致。
- 管理頁安全更新是否指向正確穩定 Release。

更多開發流程見 [`../CONTRIBUTING.md`](../CONTRIBUTING.md)。
