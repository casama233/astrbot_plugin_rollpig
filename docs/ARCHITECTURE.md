# RollPig 架構與事件層

本文記錄 v3.5.x 之後的漸進式拆分方向。目標不是一次重寫 `legacy_main.py`，而是在不改變既有 SQLite／JSON 權威資料與玩法語義的前提下，讓新功能有穩定的接入點。

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

1. 先讓新功能只透過 Gameplay Event API 寫事件。
2. 把日報、統計、管理面板等讀模型改為消費共用事件。
3. 逐步把 `legacy_main.py` 的收藏、烤豬、資源與管理面板邏輯移入獨立 service／renderer／command 模組。
4. 最後再決定是否把事件持久化從日報狀態提升為獨立存儲權威。
