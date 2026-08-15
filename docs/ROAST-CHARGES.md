# 烤箱 Charge 與群體補貨

群烤已從「每次 `/烤群友` 後整體等待固定冷卻」改為 **使用者 × 群組** 的儲存式烤箱能量，並接入群體補貨。

> 玩家只需要記住兩條主入口：`/烤箱補貨` 發起補貨，`/添柴` 支持。`/添柴 @目標` 則明確加入預約烤豬。舊 `/添煤` 等寫法只保留補貨相容，不再作為玩家文檔主入口。

## 預設 Charge 規則

- 每位玩家在每個群組各自擁有 **2 / 2** 格烤箱能量。
- 普通 `/烤群友` 成功發起一次嘗試消耗 **1 格**。
- 建立一張「目標尚未抽豬」的預約烤豬消耗主廚 **1 格**。
- 後續群友對同一預約「添柴」免費，不重複消耗。
- 目標之後在本群抽豬、觸發已存在的預約時不再消耗第二次能量。
- 後門口令維持原語義：繞過普通限制，不消耗能量。
- 60% 成功 / 30% 逃脫 / 10% 反噬的 outcome policy 完全不變。

## 自然恢復模型

既有 `group_roast_cooldown_hours` 配置鍵保留，但語義改為「**每格缺失能量的恢復時間**」。預設仍是 8 小時。

缺失能量採隊列式逐格恢復。例如 2 / 2 連續用兩次後變成 0 / 2：

```text
T+0h   0 / 2
T+8h   1 / 2
T+16h  2 / 2
```

如果第一格正在恢復時又消耗剩餘能量，不會重置已累積的恢復進度。

配置：

```text
group_roast_max_charges = 2
```

範圍 1–5。設為 1 時，行為退化為舊版的單格固定冷卻模型，方便管理員保持舊節奏。

## 舊冷卻遷移

Charge migration 不清空舊 `roast_cooldowns`：

- 舊冷卻已過期或從未使用：首次讀取視為滿能量；
- 舊冷卻仍生效：視為「剛剛已經花掉 1 格」，預設 2 格容量時仍保留另一格可用，並沿用原 `last_used_at` 作第一格的恢復起點。

因此升級不會突然讓舊玩家多背一輪完整冷卻，也不會把舊使用紀錄當成完全沒發生。

## 群體烤箱補貨

`/烤箱補貨` 與 `/添柴` 是玩家主入口。

### `/添柴` 上下文

- 補貨輪次正在進行時，裸 `/添柴` 支持補貨；
- `/添柴 @目標` 明確加入該目標的待結算預約；
- 沒有補貨且只有一張待結算預約時，裸 `/添柴` 直接加入該預約；
- 沒有補貨但有多張預約時，要求明確 `@目標`；
- 舊 `/添煤`、`/加煤`、`/烤箱添煤`、`/烤箱添柴` 僅作補貨相容入口。

### 參與資格

補貨只在群聊中運作。發起者與支持者必須是當天已在本群形成 RollPig 活躍記錄的成員；支持者按身份去重，同一輪每人只計一次。

### 需求人數

第一輪需求由今天本群活躍人數計算：

```text
base = max(minimum_supporters, ceil(active_count × ratio_percent))
base = min(maximum_base_supporters, base)
required = base + successes_today × extra_per_success
required = min(active_count, required)
```

特殊情況：

- `active_count < 2`：無法形成有效協作需求；
- `active_count == 2`：固定需要 2 人；
- 一般情況預設比例為 30%、最少 3 人、基礎上限 8 人；
- 每成功一輪後，下一輪預設再增加 2 名需求，但永遠不超過當天實際活躍人口。

預設每群每天最多成功補貨 2 輪，可由配置調整。

### 成功效果

達到需求人數後，系統會為本群符合條件、目前確實缺 Charge 的活躍玩家各恢復 **最多 +1 格**：

- 不直接補滿；
- 不突破個人的 `group_roast_max_charges`；
- 若所有符合條件的人本來就滿 Charge，該輪會以 `no_missing_charges` 收口，而不是虛報成功。

### Gameplay Event

補貨流程寫入既有 Gameplay Event：

- `oven_refill_started`
- `oven_refill_supported`
- `oven_refill_succeeded`
- `oven_refill_failed`

日報可以聚合這些事件，但日報不成為 Charge state authority。

## 補貨狀態與恢復

補貨 campaign metadata 保存在獨立輔助狀態中，按群組／自然日保存輪次、支持者與成功次數。插件啟動時會處理中斷中的 completion marker；舊日期資料只保留有限窗口，避免長期堆積。

Charge 本身仍由既有 SQLite / JSON 權威邊界管理，因此補貨成功只是透過既有 grant path 增加一格，不建立第二套能量真相源。

## Storage 邊界

SQLite 模式沿用 `roast_cooldowns` 權威表並增加：

- `charges`
- `refill_anchor`

舊列以 `charges = -1` 表示尚未完成 lazy migration。首次消耗時才依舊 `last_used_at` 原子轉成 charge state。

JSON fallback 使用 `roast_state.json -> roast_charges`，但與 SQLite 共用 `roast_charges.py` 的純 token-bucket policy，避免兩條存儲路徑產生不同計時語義。

Charge key 使用 canonical `_storage_user_key()` + group ID，因此沿用 claim-aware Collection Identity Boundary，不枚舉 sibling Bot instance，也不退回裸 user ID。

## 相關配置

```text
group_roast_max_charges
group_roast_cooldown_hours
enable_oven_refill
oven_refill_daily_limit
oven_refill_support_ratio_percent
oven_refill_min_supporters
oven_refill_max_base_supporters
oven_refill_extra_supporters_per_success
oven_refill_round_timeout_minutes
```

精確預設值與 UI 說明以 `_conf_schema.json` / `CONFIGURATION.md` 為準。
