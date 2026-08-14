# RollPig 架構與事件層

本文記錄 v3.5.x 之後的漸進式拆分方向。目標不是一次重寫 `legacy_main.py`，而是在不改變既有 SQLite／JSON 權威資料與玩法語義的前提下，讓新功能有穩定的接入點。


## AstrBot command registration boundary

v3.6.2 後不再依賴運行時修改 handler metadata。所有 `@filter.command` / `@filter.command_group` 必須直接定義在真正的 `main.py` Star 入口；`legacy_main.py` 與 feature mixin 只保留可測試的業務方法。`main.py` 的薄 wrapper 只負責 AstrBot 註冊並 `await super().<handler>(...)` 委派，不複製玩法邏輯。

所有 RollPig command 在 decorator 上顯式聲明 `priority=1000`，既不依賴註冊順序，也不需要 import 後重新排序 registry。handler 內仍保留 `event.stop_event()` 作為第二層隔離。AstrBot Market Smoke 必須同時驗證 `handler.__module__ == main`、`handler_module_path == main` 與 priority；任何後續拆分都不得把 command decorator 移回 helper module。

這是漸進式拆分的第一個硬邊界：**命令註冊屬於入口，玩法實作屬於 service/feature。** 後續可以安全地逐步搬走 `legacy_main.py` 內容，而不再改變 AstrBot 的 handler ownership。

## Catalog / resource read boundary

第二階段把「有效圖鑑怎樣被讀取」從 `legacy_main.py` 的大型流程抽成兩個無 AstrBot 依賴的小服務：

- `CatalogService`：負責 base + local override + tombstone 的純合併規則、按 ID 查找、圖鑑解鎖優先排序、頁數、隨機抽樣與 `/找豬` 的文字搜尋；
- `ResourceReadService`：只負責圖片路徑解析，固定沿用 **local override → EX variant → cloud base → bundled base** 的既有 precedence。

這兩個 service **不負責** storage mutation、JSON/SQLite IO、remote resource sync、公開源投稿/審核、PIL renderer 或 AstrBot event。`legacy_main.py` 暫時保留這些 orchestration，但 `_reload_catalog_layers()`、`_find_catalog_pig()`、`find_image_file()`、圖鑑排序、隨機與搜尋已改為委派 service。

這個邊界的目的不是立刻刪除 `legacy_main.py`，而是先讓 renderer 與 command 只依賴穩定的 read policy。下一階段可以把 `render_pig_image`、`render_pigsty_image`、`render_catalog_grid`、`render_weekly_summary` 逐步移入 renderer 模組，而不再重新實作圖鑑與圖片 precedence。

## Gameplay Event v1

`gameplay_events.py` 定義跨功能共用的事件 JSON 形狀、事件名稱、去重寫入、讀取與自然日裁剪。PR #51 已建立的 `daily_report_state.json -> events` 暫時繼續作為持久化容器，因此既有資料**不需要遷移**。

事件最小形狀：

```json
{
  "version": 1,
  "id": "唯一事件 ID",
  "kind": "roast_success",
  "actor_id": "發起者",
  "target_id": "目標",
  "victim_id": "實際受害者",
  "at": 0
}
```

新功能可選增加 `pig_id` 與 `metadata`。舊日報事件沒有 `version`、`pig_id` 或 `metadata` 仍然有效；讀取端必須保持向下兼容。

## 事件名稱

目前日報正式消費：`roast_success`、`roast_escape`、`roast_backlash`、`daily_sacrifice`。

事件層同時預留下一階段的穩定名稱，包括：

- 收藏：`draw_completed`、`pig_unlocked`、`ex_level_up`、`pity_triggered`；
- 預約烤豬：已啟用 `roast_reservation_created/joined/triggered`；`roast_reservation_cancelled` 保留給未來顯式取消流程；
- 烤箱補貨：`oven_refill_started/supported/succeeded/failed`。

預留名稱只建立契約，不代表對應玩法已經啟用。

## 寫入邊界

`DailyReportMixin._record_daily_report_event()` 保留原有「日報關閉時不寫輔助事件」語義，確保 PR #51 行為不變；新的 `_record_gameplay_event()` 是後續玩法可使用的共用入口。

目前事件仍存放在日報輔助狀態中，是刻意的低風險過渡。等 EX、預約與補貨都接入後，再評估把事件持久化抽成獨立 repository 或 SQLite 表，而不是現在提前做資料遷移。

## 後續拆分順序

1. `main.py` 保持唯一 AstrBot command registration 入口。
2. catalog/resource read policy 只經 `CatalogService` / `ResourceReadService`。
3. 把 PIL 圖片輸出逐步拆到獨立 renderer；renderer 不直接決定 catalog precedence。
4. 再拆 collection/storage orchestration、烤豬與管理面板 service。
5. 最後才評估把 Gameplay Event 持久化從日報狀態提升為獨立存儲權威。


## Renderer Boundary

第三階段把單豬卡、永久圖鑑、隨機／搜尋九宮格與本週小豬的 PIL 繪製移入 `renderers/`。renderer 不 import AstrBot，不讀寫 storage，不知道資源同步、命令事件或插件生命周期。

`legacy_main.py` 只保留 compatibility facade：先從既有 domain read API 準備 collection／weekly entries、palette 與字體，再把明確輸入交給 renderer。圖片路徑仍經 `find_image_file()` → `ResourceReadService`；圖鑑排序／查找／頁數仍經 `CatalogService`，renderer 不重新實作 precedence 或 catalog policy。

目前 `render_roast_image`、管理面板縮圖與其他舊圖像輸出尚在 `legacy_main.py`。後續應按同一原則逐個拆分，而不是讓 `renderers/` 取得整個 plugin instance。
