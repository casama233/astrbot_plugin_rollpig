# 烤箱 Charge（Phase 3A）

Phase 3A 將原本「每次 `/烤群友` 後整體等待固定冷卻」改為 **使用者 × 群組** 的儲存式烤箱能量。

## 預設規則

- 每位玩家在每個群組各自擁有 **2 / 2** 格烤箱能量。
- 普通 `/烤群友` 成功發起一次嘗試消耗 **1 格**。
- 建立一張「目標尚未抽豬」的預約烤豬消耗主廚 **1 格**。
- 後續群友對同一預約「添柴」免費，不重複消耗。
- 目標之後在本群抽豬、觸發已存在的預約時不再消耗第二次能量。
- 後門口令維持原語義：繞過普通限制，不消耗能量。
- 60% 成功 / 30% 逃脫 / 10% 反噬的 outcome policy 完全不變。

## 恢復模型

既有 `group_roast_cooldown_hours` 配置鍵保留，但語義改為「**每格缺失能量的恢復時間**」。預設仍是 8 小時。

缺失能量採隊列式逐格恢復。例如 2 / 2 連續用兩次後變成 0 / 2：

```text
T+0h   0 / 2
T+8h   1 / 2
T+16h  2 / 2
```

如果第一格正在恢復時又消耗剩餘能量，不會重置已累積的恢復進度。

新增配置：

```text
group_roast_max_charges = 2
```

範圍 1–5。設為 1 時，行為退化為舊版的單格固定冷卻模型，方便管理員保持舊節奏。

## v3.6.4 舊冷卻遷移

Phase 3A 不清空舊 `roast_cooldowns`：

- 舊冷卻已過期或從未使用：首次讀取視為滿能量；
- 舊冷卻仍生效：視為「剛剛已經花掉 1 格」，預設 2 格容量時仍保留另一格可用，並沿用原 `last_used_at` 作第一格的恢復起點。

因此升級不會突然讓舊玩家多背一輪完整冷卻，也不會把舊使用紀錄當成完全沒發生。

## Storage 邊界

SQLite 模式沿用 `roast_cooldowns` 權威表並增加：

- `charges`
- `refill_anchor`

舊列以 `charges = -1` 表示尚未完成 lazy migration。首次消耗時才依舊 `last_used_at` 原子轉成 charge state。

JSON fallback 使用 `roast_state.json -> roast_charges`，但與 SQLite 共用 `roast_charges.py` 的純 token-bucket policy，避免兩條存儲路徑產生不同計時語義。

Charge key 使用 canonical `_storage_user_key()` + group ID，因此沿用 claim-aware Collection Identity Boundary，不枚舉 sibling Bot instance，也不退回裸 user ID。

## Phase 3B

本階段 **不包含** `/烤箱補貨` 與 `/添煤`。

Phase 3B 會建立群體補貨事件，成功時為符合條件的本群玩家恢復 **+1 格**，而不是直接補滿，並寫入已預留的 Gameplay Event：

- `oven_refill_started`
- `oven_refill_supported`
- `oven_refill_succeeded`
- `oven_refill_failed`

在 Phase 3A 的 charge/storage contract 穩定後再接入，避免同一個 PR 同時重寫冷卻、預約與群體補貨。
