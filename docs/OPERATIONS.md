# 運維、升級與故障排查

本文面向插件管理員與維護者，說明身份遷移、資料存儲、資源同步、安全更新、備份與故障處理。

> 本頁的 SQLite 停止載入／JSON 唯讀預檢是此分支的**未發佈維護變更**，不代表 v3.12.1 已有此保護。可安裝版本以 GitHub 正式穩定 Release 的 tag、ZIP 與 SHA256SUMS 為準。

## 1. 版本與身份

### v3.12.1 更新前確認

目前 metadata 版本仍是 v3.12.1，最低支援 AstrBot `>=4.26.0`。分支新增修補不會自動成為 v3.12.1 的既有 Release 資產。

正式更新前確認 GitHub 已建立非草稿、非預發布的目標 Release，以及對應 tag、ZIP 與 SHA256SUMS；main CI 或 Release workflow 執行／失敗時，不把分支版本當成已發布版本。從插件管理工作台的安全更新取得穩定版後，重載插件或重啟 AstrBot 才會載入新程式。

正式發版須同步 metadata、Changelog 和 Release Notes，通過 PR 檢查及 main CI，再由 Release workflow 對該精確提交建立新 tag、ZIP 與 SHA256SUMS。既有穩定版 tag、ZIP 不覆寫，不用安全更新器安裝任意分支。

插件更新與 `rollpig-source upgrade` 更新公共源服務是兩件事。插件版本不代表公共源已切換 resource_version，也不應刪除玩家豬籍或本地 EX。

目前插件身份為 `astrbot_plugin_rollpig_plus`，GitHub 倉庫為 `casama233/astrbot_plugin_rollpig`。前者由 metadata 決定，倉庫名稱不同不是衝突。

### 為什麼 v3.2.0 要換身份？

歷史上原版與增強版曾可能共用 `astrbot_plugin_rollpig`。獨立命名空間避免共用配置、誤遷移原版資料，或相同命令由兩個插件處理卻寫入同一資料目錄。

## 2. 新安裝

手動安裝目錄應與插件身份一致：

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

重啟 AstrBot，確認後台顯示「今日小豬 · 增強版」。不要將 v3.2.0+ 放入舊程式／配置命名空間強行啟動；身份驗證會拒絕不安全的混用。

## 3. 從舊增強版升級到 v3.2.0+

### 可自動遷移的前提

必須能確認舊資料屬於本增強分支，例如存在 v3.1.4 來源標記，或符合增強版 SQLite／多檔案指紋。無法確認的原版資料不會自動搬運。

### 遷移安全流程

```text
Copy → Verify → Atomic Commit
```

先複製，不直接改寫舊資料；SQLite 使用安全備份流程，其他檔案以 SHA-256 等方式核對。全部成功才切換，舊目錄仍保留。配置僅遷移 `_conf_schema.json` 支援的欄位，不複製未知／已廢棄欄位。

### 遷移後要做什麼？

檢查 `/今日小豬`、`/我的豬圈`、統計、圖鑑、本地圖片及 SQLite 健康狀態。確認新插件正常後，再手動停用舊插件。

> 身份遷移不會替管理員停用舊插件。兩者同時註冊相同命令可能重複回覆。

## 4. SQLite 運行模型

### v3.0+ 的權威來源

規範化 SQLite 表承擔核心運行時權威：每日抽取、收藏、烤／吃狀態、AI 文案與身份映射等以 SQL 事實表為主；SQLite 模式的統計直接聚合 SQL。兼容 JSON 用於遷移、匯出和回滾，不持續雙寫為最新副本。

### `storage_backend=auto`

推薦模式。新安裝建立 SQLite；可讀的舊 JSON 先備份，匯入臨時 DB，通過完整性、外鍵、規範化一致性和事實對帳才原子切換。

**只有初次遷移尚未正式提交的失敗，才保留原 JSON 繼續運行。**既有 SQLite 無法開啟／驗證時停止插件載入，不讓舊／空 JSON 接管。DB 消失但仍有 SQL 權威記錄、不能核驗的狀態文件或 WAL／SHM，也不視為新安裝。

`sqlite` 模式同樣保留此恢復保護。`json` 只適用原生 JSON 安裝或已完成對帳回滾的安裝；既有 JSON 仍先唯讀解析，不能讀取時停止，不覆寫為預設值。改成 json 不能繞過 SQL 保護。

停止載入時，本插件管理頁亦不可用；使用 AstrBot 載入日誌和 [SQLite 恢復保護](SQLITE-RECOVERY.md)。本批没有只讀恢復工作台。

### SQLite 運行參數

使用 WAL、`foreign_keys=ON`、`synchronous=NORMAL`，寫鎖等待由 `storage_busy_timeout_ms` 控制，預設 5000 ms。具體有效範圍見 [配置參考](CONFIGURATION.md)。

## 5. 資料與目錄

實際根目錄由 `StarTools.get_data_dir("astrbot_plugin_rollpig_plus")` 決定，不假設固定絕對路徑。完整資料目錄包含的內容不止資料庫：

- `rollpig.db`、WAL／SHM、權威記錄及恢復材料。
- 圖鑑／歷史兼容資料、`local_overrides.json`、`deleted_pigs.json`。
- `images/` 本地圖片、本地 EX 及其他玩法狀態。
- `cloud_resources/` 資源快取與同步狀態、PigHub 快取。

舊 JSON 未持續更新並不代表資料遺失，也不能把它當成最新恢復點。

## 6. 手動備份建議

健康運行時可先從管理頁產生 JSON 匯出並核對時間、SHA-256。**JSON 匯出不是整個資料目錄備份**，不包含全部本地圖片、EX 或其他未受管檔案。

主機搬遷、重大升級或檔案級操作前，停止所有可能寫入此資料目錄的 AstrBot／插件程序，再備份整個目錄。使用 WAL 時不能只複製 rollpig.db 而漏掉相關材料。備份完成、核驗後才進行人工操作。

不要先刪除疑似損壞的 DB、WAL、SHM 或權威記錄來「重置」。載入已停止時不能依靠插件管理頁匯出；先保留完整目錄，在副本上排查，詳見 [恢復步驟](SQLITE-RECOVERY.md)。

## 7. 私人資源同步

預設啟用 AstrBot v1 專用源，新安裝每 6 小時檢查；已有明確配置保持原值。可關閉同步或改用有權使用的兼容 HTTPS 私人源。

舊 `pig.felislab.cc` 精確 manifest 地址會遷移至 AstrBot 專用源；其他自訂地址不改写。私人源失敗不偷偷轉向官方公共鏈。

### 同步安全策略

只接受 HTTPS，限制重定向、私網目的地、manifest／包／單檔大小及圖片像素；所有宣告的大小與 SHA-256 驗證成功才切換 active 資源。失敗保留最近一次驗證快取，無快取才用內置資源。

公共 Vercel／GitHub 鏡像目前仍受 `PUBLIC_MIRROR_FAIL_CLOSED` 封鎖。舊配置存在不等於生效；只有獨立來源、授權、客戶端和發布驗證完成才可恢復，見 [公共災備邊界](PUBLIC-MIRROR-FAIL-CLOSED.md)。

### 資源優先級

基礎層由有效雲端／私人資源或內置資源提供；本地新增、編輯、自訂圖片優先，刪除屏蔽最後套用。因此同步不應復活已屏蔽 ID；在管理頁「本地資源」可檢查與取消屏蔽。

Felis 官方直讀 overlay 屬獨立客戶端來源，不是公共鏡像再分發權。完整分層、manifest 和 403 說明見 [資源管理](RESOURCE-MANAGEMENT.md)。

## 8. PigHub 圖片導入與自建公共源投稿

管理頁可從 PigHub 選圖，補充名稱、描述與文案；下載受 `resource_max_file_size_mb`、來源安全規則、圖片驗證和標準化限制。本地上傳保存至插件資料目錄，不修改倉庫內置圖片。

提交公共源須明確確認，並使用 rights-v3 權利資料；送出的是小豬資料、圖片與相關 EX，不是群友、群組或聊天原文。能下載或本地使用不等於能再次公開分發。

維護者持有伺服器端 `public_source_admin.token` 才有審核能力。依 `rollpig-public-source-service` 的 rights-aware 流程，**審核通過不等於正式發布**：`publication_status=not_published`、空 resource_version、未切換 v1 都不是上線成功。正式發布另經來源驗證、候選檢查及原子切換；不得因舊介面文案寫「批准發布」便聲稱已生效。

Token 不應出現在前端、schema 或日誌。服務程式已合併也不能代替生產驗證，或擅自解除投稿 API 的隔離。

## 9. 管理面板安全更新

更新器只連接 `casama233/astrbot_plugin_rollpig` 的穩定 Release，不接受任意 URL、自訂分支或預發布版本。

### 安全限制

下載上限 64 MiB，檔案數上限 3000，解壓總體積上限 256 MiB；拒絕路徑穿越、符號連結和異常壓縮比。Release 提供 SHA-256 就強制核對，缺少校驗檔時要求額外確認。雜湊校驗不等於獨立數位簽章。

替換前備份程式；失敗嘗試回滾，交易日誌協助中斷恢復。不覆蓋玩家歷史、本地圖片、玩法資料或配置。

### 更新後為什麼版本沒有立即變？

安裝完成不會自動重啟 AstrBot。磁碟上的已安裝版本和目前記憶體中載入的版本可能不同；確認更新結果後手動重載／重啟。尚未成功檢查更新，不能據此判定「已是最新」。

## 10. AI 烤豬文案

`enable_ai_roast_copy=false` 為預設。開啟後使用當前會話模型；超時由 `ai_generation_timeout_seconds` 控制，模型不可用、報錯或超時會回退本地文案。同一隻豬每天最多嘗試一次生成，成功文案保留七個自然日窗口供復用，不因多人烤同一豬重複付費。

AI 文案失敗不應讓 `/今日烤豬` 整體失效。

## 11. 常見故障排查

### 問題：啟動時提示插件命名空間錯誤

檢查手動 clone 目錄是否仍叫 `astrbot_plugin_rollpig`。v3.2.0+ 應使用 `astrbot_plugin_rollpig_plus` 等獨立身份目錄，不以直接覆蓋舊目錄繞過遷移。

### 問題：一個指令回覆兩次

檢查原版／舊增強版是否仍與增強版同時啟用；身份遷移不會自動停用舊插件。

### 問題：每天重置時間不對

檢查 `timezone`。`local` 使用 AstrBot 主機系統時區，跨區部署可明確填 `Asia/Hong_Kong` 等 IANA 時區；修改後重載插件。

### 問題：公共資源同步失敗

查看同步狀態與日誌，檢查 HTTPS 地址、DNS／TLS，確需代理時才開 `resource_use_system_proxy`。不要先刪 active 快取，也不要把被封鎖的公共鏡像當成可用備援。

### 問題：開了系統代理後同步反而卡住

預設不信任系統代理，避免失效 HTTP_PROXY／HTTPS_PROXY 卡住連線。伺服器可直連時保持關閉。

### 問題：SQLite 顯示不健康或回退

先區分「初次遷移未提交，仍使用原 JSON」與「已有 SQL 需要恢復」。後者在此維護分支停止載入，插件工作台不可用；查看 AstrBot 載入日誌，停機備份完整目錄，在副本上核验数据库或备份，再恢复并重载。

不要直接切換 `storage_backend=json`、刪 DB 或刪權威記錄绕过检查。健康 SQL 才能從管理頁先匯出、對帳並明確回滾；JSON 匯出時間可能早於最新進度。詳見 [SQLite 恢復保護](SQLITE-RECOVERY.md)。

### 問題：管理頁深度 Analytics 沒有載入

深度分析按需載入，不應阻擋核心總覽、圖鑑、同步、SQLite 及安全更新。先確認是否點擊載入入口；剛升級可重新進入插件頁或刷新 AstrBot 後台，避免殘留舊前端狀態。

### 問題：聊天圖片發送超時後出現重複訊息

圖片超時視為投遞不確定，不立即補發另一份 fallback。若能重現，記錄 AstrBot 版本、適配器、群聊／私聊、時間戳與完整日誌；不能單憑 timeout 判定訊息未送達。

## 12. 發版前維護檢查

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py rollpig_core.py updater.py storage services
pytest -q
pre-commit run --all-files --show-diff-on-failure
npm ci
npm test
```

另確認 metadata、Changelog、Release Notes、README 支援版本、命令 decorator、配置 schema／文件一致，且管理頁指向正確穩定 Release。檢查精確提交的 CI、Wiki、完整 AstrBot 載入與相關瀏覽器回歸；測試綠燈不是素材授權批准，也不代表生產環境已升級。

更多開發流程見 [貢獻指南](../CONTRIBUTING.md)。
