## ☁️ 今日小豬 · 增強版 v3.4.0

> 我們不再借用不相容的 nonebot 資源地址，而是建立一套由 AstrBot 專案自己維護、驗證與回退的豬源體系。

### AstrBot 專用來源

- 預設端點：`https://curryudon.top/astrbot-rollpig/v1/manifest.json`
- 首版內容：99 筆完整資料、99 張圖片。
- 只接受 AstrBot RollPig v1 的 Client／Protocol 標頭與版本化 User-Agent。
- 普通瀏覽器、錯誤客戶端與 nonebot 請求會收到 HTTP 403。

### 安全與可靠性

- `pig.json` 與每張圖片都具備大小和 SHA-256。
- 插件完整下載、驗證後才原子替換 active 資源。
- 同步失敗會保留既有快取，沒有快取時回退內置資源。
- 伺服器保留不可變版本目錄，可原子切回上一版。
- 本地新增、覆蓋、自訂圖片與刪除屏蔽不受遠端更新影響。

### 從舊來源遷移

精確匹配舊 `pig.felislab.cc` nonebot 受限來源的配置，會在載入 v3.4.0 時遷移至 AstrBot v1 專用源；管理員自行配置的其他私人 URL 保持不變。

### 邊界說明

專用標頭能阻擋普通流量、誤配置及不相容客戶端，但開源客戶端的標頭可被模仿。若要建立真正封閉的私人源，應額外加入每實例獨立 Token 或 mTLS，而不是在公開插件中放置共用秘密。

完整設計與維護流程請看 [AstrBot 專用豬源維護手冊](https://github.com/casama233/astrbot_plugin_rollpig/blob/main/docs/RESOURCE-SOURCE-MAINTENANCE.md)。
