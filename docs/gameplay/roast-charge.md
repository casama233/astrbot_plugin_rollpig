---
title: Roast Charge 與烤箱補貨
description: 後廚現在有電表。烤太多沒火？叫全群來添柴。
---

# 🔥 Roast Charge：後廚現在真的有能源條

以前的群烤邏輯很像：

> 烤一次。  
> 然後整個人進冷卻。  
> 八小時後再見。

現在的玩法是 **可儲存的烤箱 Charge**。

<div class="pig-charge-panel" markdown>
<div class="pig-charge-row">
<span class="pig-charge-label">YOUR OVEN</span>
<span class="pig-charge-meter" data-charge-demo>
<span class="pig-charge-cell is-full"></span>
<span class="pig-charge-cell is-full"></span>
</span>
<strong>預設 2 / 2</strong>
</div>

每位玩家在**每個群**都有自己的一組 Charge。你在 A 群把火燒光，不代表 B 群的烤箱也跟著停電。
</div>

## 什麼時候會消耗 1 格？

預設情況下：

- 普通 <span class="pig-command">/烤群友 @某人</span> 成功發起一次嘗試：**-1 Charge**
- 對還沒抽豬的目標建立一張新的預約：**-1 Charge**
- 後續群友對同一張預約添柴：**免費**
- 目標之後出現並觸發已存在的預約：**不再扣第二次**
- 後門類 bypass：沿用原語義，不消耗普通 Charge

最重要的是：**60% 成功 / 30% 逃脫 / 10% 反噬**沒有因 Charge 改版而被偷偷重寫。

!!! danger "10% 還是那個 10%"
    能量系統只是決定「你現在能不能點火」。至於點著以後到底誰熟了，仍然看原本的 outcome policy。

## Charge 怎麼恢復？

既有 `group_roast_cooldown_hours` 現在代表：

> **每缺一格 Charge，需要多久自然恢復。**

預設仍是 8 小時。

例如你有 2 格，短時間內連烤兩次：

```text
現在      □ □   0 / 2
+ 8 小時  🔥 □   1 / 2
+16 小時  🔥 🔥  2 / 2
```

如果第一格已經恢復到一半時你又花掉剩下那格，第一格的進度不會被「重新計時」。

## 我不想等 8 小時。

很好。群友也不想。

### ⛽ `/烤箱補貨`

今天已經在**本群實際參與 RollPig** 的玩家，可以發起一次群體補貨輪次。

<span class="pig-command">/烤箱補貨</span>

發起者本身就算第一位支持者。系統會根據今天本群的活躍人數，以及本群今天已成功補貨的次數，計算這一輪需要多少人。

預設策略包括：

- 基礎支持比例：活躍玩家的 **30%**
- 一般情況最少需要 **3 人**；若今天本群只有 2 名活躍玩家，固定需要 2 人
- 基礎需求最多按 **8 人**封頂
- 本群今天每成功補貨一輪，下一輪預設再多要求 **2 人**
- 每群每天預設最多成功補貨 **2 輪**
- 最終要求永遠不會高於今天本群的實際活躍人數

管理員可以調整這些數值。

### 🪵 `/添柴`

補貨輪次已開始後，其他符合條件的活躍豬友可以：

<span class="pig-command">/添柴</span>

每人只計一次。人數到達本輪要求後，補貨會結算。

<div class="pig-highlight" markdown>

**補貨成功不是「全員瞬間補滿」。**  
它只會為符合條件、目前確實缺 Charge 的本群活躍玩家恢復 **+1 格**，而且不會突破自己的最大容量。

換句話說：這是補貨，不是後廚核聚變。

</div>

## `/添柴` 還能給預約添？

能，而且這就是現在把兩套玩法收成同一個入口的原因。

<div class="pig-highlight" markdown>

- **有補貨輪次**：裸 `/添柴` 優先支持補貨；
- **明確想蹲某位群友的鍋**：`/添柴 @目標`；
- **沒補貨 + 只有一張待結算預約**：裸 `/添柴` 直接加入那張；
- **沒補貨 + 多張預約**：Bot 要求你指定 `@目標`。

所以不需要再背另一條主命令。**同一把柴，Bot 先分清楚你想燒哪口鍋。**

</div>

## 一個完整案例

<div class="pig-steps">
<div class="pig-step" markdown><span class="pig-step__n">1</span><div>

### B 先烤兩次
B 在本群原本有 2 / 2 Charge。連續開火後變成 0 / 2。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">2</span><div>

### B 發起補貨
B 輸入 `/烤箱補貨`。如果今天這群共有 10 位活躍豬友，按預設 30% 和最少 3 人規則，本輪需要 3 位支持者。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">3</span><div>

### C、D 添柴
C `/添柴`，D `/添柴`。連同發起者 B，進度達標。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">4</span><div>

### 後廚重新營業
符合條件且缺能量的活躍玩家各恢復最多 1 格。B 從 0 / 2 變成 1 / 2，又可以開始想下一位受害者了。
</div></div>
</div>

## 和預約烤豬怎麼配合？

如果你明確 `/烤群友 @A`，但 A 今天還沒有在這個群抽豬：

1. 第一位主廚建立預約，支付 1 Charge；
2. 其他人可以 `/添柴 @A`，不重複扣 Charge；
3. 再次 `/烤群友 @A` 也保留為相容加入方式；
4. A 之後在本群抽出今日小豬；
5. 已存在的預約一次性結算；
6. 不會因為「A 終於出現」再向主廚收一次電費。

完整預約語義見 **[預約烤豬技術規則](../ROAST-RESERVATIONS.md)**。

## 管理員可以調什麼？

常見配置包括：

- `group_roast_max_charges`：最大 Charge，範圍 1–5
- `group_roast_cooldown_hours`：每格自然恢復時間
- `enable_oven_refill`：是否開啟群體補貨
- `oven_refill_daily_limit`：每群每天可成功補貨輪數
- `oven_refill_support_ratio_percent`：活躍人數需求比例
- `oven_refill_min_supporters`：最少支持者
- `oven_refill_max_base_supporters`：基礎需求上限
- `oven_refill_extra_supporters_per_success`：當天每成功一次後，下輪額外需要多少支持者
- `oven_refill_round_timeout_minutes`：一輪補貨能掛多久

精確配置請看 **[完整配置參考](../CONFIGURATION.md)**。

!!! info "舊版升級"
    Charge migration 不會粗暴清空舊 `roast_cooldowns`。仍在舊冷卻中的玩家會以 lazy migration 方式換算成 Charge state，保留原 `last_used_at` 作恢復起點，不會因更新突然滿血，也不會被雙倍懲罰。

<div class="pig-highlight" markdown>

### 🔥 一句話總結

以前：**烤完等。**  
現在：**存 Charge → 開火 → 沒油 → 全群添柴 → 再開火。**

後廚終於從「冷卻功能」發展成了一個需要群眾基礎的能源工程。

</div>
