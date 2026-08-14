## 🐷 今日小豬 · 增強版 v3.6.1

v3.6.1 是針對 v3.6.0 實機回報的 **hotfix patch release**，不新增玩法、不改資料格式，集中修復指令衝突、事件穿透、繁體字體 fallback 與缺圖恢復。

### 修復

- **豬圈日報指令衝突**：移除 `legacy_main` 的舊 `豬圈日報` 註冊，只保留 `DailyReportMixin` 的完整統計海報版本；AstrBot 指令管理器不應再顯示 RollPig 自身的兩條同名日報衝突。
- **RollPig 指令穿透到 LLM／其他插件**：所有 RollPig 聊天指令在匹配後會安全呼叫 `event.stop_event()`；`/今日小豬` 等命令完成後不再繼續被其他插件或 LLM 當成普通訊息處理。
- **繁體／AI 文案字體**：優先使用正式包已包含的 `荆南麦圆体.otf`，修復舊獨立繁體字體不存在時 Pillow default 被誤當有效 CJK 字體的問題。
- **PigHub 歷史／本地缺圖自癒**：若小豬 metadata 仍保留通過既有 PigHub URL 安全校驗的 `source_url`，發送前會嘗試重新下載、做大小限制與圖片解碼／標準化，再恢復本地圖片；修復失敗仍維持原有無圖降級，不會阻塞每日抽取。
- **損壞 cloud cache 提前修復**：已有 resource version、但 `_load_cloud_pigs()` 判定本地 cache 不完整時，重啟後會提前觸發 `force=True` 的完整原子同步，不必等待正常同步週期。

### 相容性

- 可由 **v3.6.0 直接升級**；SQLite／JSON、永久圖鑑、本地 override、歷史記錄、EX 差分、日報及預約烤豬資料均不需要 migration。
- PigHub 自癒只接受既有安全校驗允許的 PigHub 圖片 URL，不會把歷史 metadata 中的任意外部 URL 當作下載來源。
- 本版沒有 Repository Security Advisory；按實際內容標示為穩定性 hotfix。

### 驗證

- Python 3.10 / 3.12 全量測試
- pre-commit / pre-commit.ci
- Marketplace Package
- AstrBot 官方 Market Smoke
- v3.6.1 專用 AST/source regression contracts
