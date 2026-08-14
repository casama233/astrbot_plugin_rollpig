# 今日小豬 · 增強版 v3.7.0

v3.7.0 是 v3.6.5 之後的玩法與架構大型更新。本版把「烤群友」從單一硬冷卻升級成可儲存 Charge，加入群體協作烤箱補貨，同時重做動態幫助、渲染與讀取快取、狀態持久化，以及公共豬源審核／瀏覽體驗。

## 🔥 Phase 3：烤箱 Charge

- 普通 `/烤群友` 與建立預約改為按「使用者 × 群組」消耗烤箱能量，預設 **2 格**。
- 每格沿用原 `group_roast_cooldown_hours` 作自然恢復週期；`group_roast_max_charges` 可配置 1–5 格。
- SQLite / JSON 共用同一 token-bucket policy，避免兩套後端出現玩法差異。
- 舊版 `roast_cooldowns.last_used_at` 以 lazy migration 轉成 charge state：仍在舊冷卻中的玩家視為已消耗一格，不會因升級被重置，也不會被雙重懲罰。
- 預約第一位主廚消耗一格；後續添柴與目標日後觸發不重複消耗。
- 後門 bypass、烤豬資格判定與既有 **60 / 30 / 10** outcome policy 保持不變。

## ⛽ 群體烤箱補貨

- 新增群體協作補貨玩法，讓當日活躍群友共同恢復烤箱能源，而不是單純等待硬冷卻。
- 補貨按群組／自然日保存狀態，支援參與者去重、進度、成功輪次與每日限制。
- 成功補貨只恢復有限 Charge，且受最大能量上限約束，不會形成無限烤豬。
- 補貨事件接入 Gameplay Event 與豬圈日報，可追蹤補貨成功與添煤參與。
- SQLite primary write path、JSON 相容路徑與初始化／恢復流程均加入回歸測試。

## 🧭 動態幫助系統

- `/豬豬幫助` 升級為依目前功能、配置與指令面動態生成的幫助內容。
- 幫助渲染拆到獨立 renderer / feature boundary，避免把命令註冊、業務邏輯與 PIL 繪圖重新混在一起。
- 新增幫助卡與文字 fallback 測試，確保新功能加入後不再依賴手動維護一張容易過期的靜態說明。

## ⚡ 渲染、讀取與持久化效能

- 新增豬卡渲染快取與 renderer performance contracts，降低重複圖片合成開銷。
- 加入渲染 backpressure，避免高併發下無限制堆積昂貴的 PIL 任務。
- Resource read path 增加快取，減少相同 catalog / image resolution 的重複查找。
- 新增集中式 state persistence 邊界，降低高頻玩法狀態寫入造成的重複 I/O。
- 相關 cache / persistence 均有失效與回歸測試，資料權威仍由現有 storage/domain write 邊界控制。

## 🐷 公共豬源審核與正式源瀏覽

- 修復 AstrBot Plugin Page sandbox 下，批准／拒絕依賴原生 `window.confirm` / `window.prompt` 而可能完全無反應的問題；改為頁內審核對話框與明確二次確認。
- 公共豬源管理新增正式源圖鑑瀏覽器：支援搜尋 ID、名稱、描述／完整文案、分頁、圖片預覽與完整資料查看。
- 疑似重複提示可直接跳到現有正式公共豬，縮短人工審核流程。
- 正式源資料經 AstrBot 本地同源代理讀取，圖片不要求 sandbox 直接跨域訪問外部來源。
- 批准／拒絕補上真實 mutation 回歸測試，避免 UI 看似成功、實際沒有提交審核動作。

## 📰 豬圈日報安全收口

- 群組自動日報的開啟／關閉權限進一步收緊為 AstrBot 管理員。
- 固化祭品契約：`daily_report_random_eat_enabled` 預設關閉，且只有定時自動日報流程可觸發；手動 `/豬圈日報` 永遠只讀，不改變玩家祭品狀態。
- Charge／補貨事件可進入日報聚合，但日報本身不成為玩法 state authority。

## 🧪 驗證與相容性

- 本輪功能在合併前均經 Python 測試、compile、pre-commit 與 AstrBot / Marketplace 既有 CI 契約驗證。
- 可由 **v3.6.5 直接升級**。
- Charge 會對舊 roast cooldown 做惰性兼容遷移；不需要使用者手工改資料。
- 永久圖鑑、EX、保底與既有 60/30/10 烤豬 outcome 語義不因本次更新重新計算。

## 升級建議

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。若你自行維護公共源審核服務，請同時同步本版對應的 source review 前後端檔案，以取得完整審核與瀏覽修復。
