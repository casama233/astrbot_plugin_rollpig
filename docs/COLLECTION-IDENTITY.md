# Collection Identity Boundary

本文件記錄 v3.6.4 之後永久收藏與身份 fragment 的安全讀取規則。

## 為什麼需要這個邊界

RollPig 曾先後使用裸 user ID、pre-instance v2 key，以及帶 adapter instance 的 v2 key。正常遷移會透過 `identity_claims` 決定哪一個 namespaced identity 可以繼承舊資料，但歷史資料可能同時保留在多個 key 下。

永久收藏需要能看見同一 logical user 已被確認擁有的舊 fragment；同時又不能把不同平台、不同 Bot instance 或同號使用者的資料串在一起。

## Claim-aware candidates

讀取候選只允許：

1. 當前 namespaced identity；
2. `_storage_user_key()` 剛完成合法 claim 後返回的舊 key；
3. `identity_claims.users` 已明確聲明屬於當前 identity candidate set 的 pre-instance / raw legacy key。

不會自動搜尋或合併 sibling Bot instance。raw ID 若已被另一平台 claim，也不會進入當前使用者的讀取集合。

## Ownership-first merge

`CollectionService.merge_ownership()` 只修復永久 ownership read model：

- pig ID：聯集；
- `first_unlocked`：最早日期；
- `last_drawn`：最晚日期；
- 同一 pig 的 `count`：取 `max`，不相加，避免 migration copy 把 EX Lv. 虛增。

最高優先級、第一個實際存在的 fragment 仍是 gameplay state 的權威來源。`duplicate_streak`、`total_draws`、`active_days` 不跨 fragment 相加或取歷史最大值，因此舊 fragment 不會改變目前保底概率。

## 為什麼不直接 sum

兩個 identity fragment 可能是：

- 完全不同的歷史區段；
- 同一次 migration 的完整複製；
- 部分重疊；
- 同一天同一筆 draw 同時存在兩份。

在沒有 logical draw timeline 去重之前，直接相加無法區分上述情況。`count +=` 會虛增 EX，`duplicate_streak = max(...)` 會把已失效的舊 streak 帶回保底，`total_draws +=` / `active_days +=` 也會製造不存在的統計。

若未來要精確修復跨 fragment 的歷史計數，必須以 `daily_draws` / JSON daily records 建立按 logical user + date 去重的 timeline，再由 timeline 重建 counters；不能在 collection read path 直接算術合併。

## Storage boundary

SQLite 與 JSON 都不自行判斷哪些 identity 應該合併。orchestration 先產生 claim-aware candidates，再逐 key 讀取 collection fragment，最後交給純 `CollectionService` 組合 read model。

這樣 storage 保持 persistence 職責，identity ownership policy 不會分散到 SQLite / JSON 兩套實作。

## 後續 Phase 3

只有在此邊界穩定後，才開始烤箱 Charge / Refill。Charge 狀態必須使用 canonical、claim-safe user × group identity，不能重新引入裸 user ID 或自行枚舉 sibling instance。
