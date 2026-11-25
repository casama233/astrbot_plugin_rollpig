---
title: Roast Charge 與烤箱補貨
description: 後廚現在有電表。烤太多沒火？叫全群來添柴。
---

# 🔥 Roast Charge：後廚現在真的有能源條

以前的群烤機制運作起來很像是：

> 烤一次。  
> 緊接著整個人進入冷卻狀態。<br>
> 八個小時後再來吧。

現在採用的是 **可累積儲存的烤箱 Charge 機制**。

<div class="pig-charge-panel" markdown>
<div class="pig-charge-row">
<span class="pig-charge-label">YOUR OVEN</span>
<span class="pig-charge-meter" data-charge-demo>
<span class="pig-charge-cell is-full"></span>
<span class="pig-charge-cell is-full"></span>
</span>
<strong>預設 2 / 2</strong>
</div>

每位玩家在**不同群組**各自擁有獨立的 Charge 額度。你在 A 群把火力耗盡，完全不會影響 B 群烤箱的正常供電。
</div>

## 哪些操作會扣除 1 格數？

在預設規則下：

- 一般發起 <span class="pig-command">/烤群友 @某人</span> 並成功執行一次嘗試：**扣除 1 Charge**
- 針對還沒抽今日小豬的對象建立新預約單：**扣除 1 Charge**
- 其他群友接著為同一張預約單加柴火：**完全免費**
- 目標稍後現身並觸發既有的預約單：**不會重複扣款**
- 後門類 bypass 指令：維持原本設定，不消耗一般 Charge

最關鍵的是：**70% 成功 / 20% 逃脫 / 10% 反噬** 的判定邏輯，並未因這次 Charge 改版而暗中更動。

!!! danger "10% 還是那個 10%"
    能量系統僅負責把關「你此刻能不能點火」。至於點火之後究竟誰會被烤熟，依舊遵循原本的 outcome policy。

## Charge 要如何回充？

原有的 `group_roast_cooldown_hours` 參數目前代表：

> **每消耗掉一格 Charge，需要等待多久才會自然回滿一格。**

預設時間維持在 8 小時。

舉例來說，假設你手上有 2 格，並在短時間內連續開烤兩次：

```text
現在      □ □   0 / 2
+ 8 小時  🔥 □   1 / 2
+16 小時  🔥 🔥  2 / 2
```

當第一格已經回充到一半時，就算你立刻花掉剩下的那一格，第一格原本的恢復進度也不會歸零重算。

## 我可不想乾等 8 個小時。

太好了，群裡的大家也這麼想。

### ⛽ `/烤箱補貨`

凡是今天已經在**本群實際玩過 RollPig** 的玩家，都能發起一輪全群補貨。

<span class="pig-command">/烤箱補貨</span>

發起人自己就是第一位響應者。系統會依據本群今日的活躍人數，以及今天已經成功補貨的輪數，自動算出這輪需要多少人湊齊。

預設計算規則包含：

- 基礎響應門檻：占今日活躍玩家的 **30%**
- 一般情況下至少需湊滿 **3 人**；若本群今日僅有 2 位活躍玩家，則固定要求 2 人
- 基礎人數需求上限為 **8 人**
- 本群今天每成功完成一輪補貨，下一輪的預設門檻就會增加 **2 人**
- 每個群組每天預設最多只能成功補貨 **2 輪**
- 最終門檻人數絕對不會超過本群今日的實際活躍人數

群組管理員有權調整以上各項參數。

### 🪵 `/添柴`

當補貨輪次啟動後，其他符合資格的活躍豬友可以進行以下操作：

<span class="pig-command">/添柴</span>

每位玩家限計入一次。一旦響應人數達標，這輪補貨便會立刻結算。

<div class="pig-highlight" markdown>

**補貨達標並不等於「全體瞬間回滿能量」。**<br>
系統僅會幫符合條件、且當下確實缺少 Charge 的本群活躍玩家補回 **+1 格**，同時不會超過個人的上限容量。

白話一點講：這只是正常進貨，不是在後廚搞核融合。

</div>

## `/添柴` 還能用來幫預約單添柴嗎？

當然可以，這也正是我們把兩套機制整合進同一個指令入口的原因。

<div class="pig-highlight" markdown>

- **場上有補貨輪次進行中**：單獨輸入 `/添柴` 會優先算作支持補貨；
- **明確想鎖定某位群友的烤架**：請輸入 `/添柴 @目標`；
- **場上無補貨 + 僅有一張待結算預約單**：單獨輸入 `/添柴` 會直接加入該張預約；
- **場上無補貨 + 同時有多張預約單**：Bot 會提示你明確指定 `@目標`。

如此一來你就不必多記另一組主指令。**同樣一把柴火，Bot 會先幫你分辨清楚究竟要丟進哪個爐子。**

</div>

## 完整情境演練

<div class="pig-steps">
<div class="pig-step" markdown><span class="pig-step__n">1</span><div>

### 玩家 B 先連續開烤兩次
B 在本群原本擁有 2 / 2 Charge，連續兩次開火後變為 0 / 2。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">2</span><div>

### 玩家 B 發起群體補貨
B 發送了 `/烤箱補貨`。假設今天群裡共有 10 位活躍豬友，套用預設 30% 與最低 3 人的規則後，這一輪共需要 3 位支持者。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">3</span><div>

### C、D 添柴
玩家 C 輸入 `/添柴`，玩家 D 輸入 `/添柴`。加上發起人 B，響應人數順利達標。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">4</span><div>

### 後廚火力重啟
符合資格且能量未滿的活躍玩家各自最多恢復 1 格。B 的能量從 0 / 2 回升至 1 / 2，又能開始物色下一隻倒楣小豬了。
</div></div>
</div>

## 如何與預約烤豬機制連動？

假設你明確輸入了 `/烤群友 @A`，但 A 今天還沒在本群抽過小豬：

1. 首位發起的主廚負責建立預約單，並扣除 1 Charge；
2. 其他群友接著輸入 `/添柴 @A` 即可加入，不會重複扣除 Charge；
3. 再次輸入 `/烤群友 @A` 同樣保留作為相容的加入方式；
4. 稍後 A 終於在本群抽出了今日小豬；
5. 先前掛著的預約單便會一次性全部結算；
6. 並不會因為「A 總算上線抽豬」而再向主廚多收一筆電費。

關於預約機制的完整規則，請參閱 **[預約烤豬技術規則](../ROAST-RESERVATIONS.md)**。

## 管理員可自訂哪些設定？

常用設定項目包含：

- `group_roast_max_charges`：Charge 容量上限，可設範圍為 1–5
- `group_roast_cooldown_hours`：單格自然回充所需時間
- `enable_oven_refill`：是否啟用全群補貨功能
- `oven_refill_daily_limit`：單一群組每日可成功補貨的輪數上限
- `oven_refill_support_ratio_percent`：群內活躍成員人數的門檻比例
- `oven_refill_min_supporters`：發起補貨所需的最少支援人數
- `oven_refill_max_base_supporters`：基礎支援人數上限
- `oven_refill_extra_supporters_per_success`：當日每次成功補貨後，下一輪需額外增加的支援人數
- `oven_refill_round_timeout_minutes`：單次補貨任務的有效持續時間

詳細參數設定請參閱 **[完整配置參考](../CONFIGURATION.md)**。

!!! info "舊版升級"
    Charge 系統遷移不會直接重置舊有的 `roast_cooldowns`。仍處於舊版冷卻中的玩家將透過延遲遷移轉換為 Charge 狀態，並沿用原本的 `last_used_at` 作為恢復基準，既不會因版本更新直接回滿，也不會承受雙重冷卻懲罰。

<div class="pig-highlight" markdown>

### 🔥 核心玩法速覽

舊版：**烤完就只能乾等冷卻。**
新版：**積攢 Charge → 點火開烤 → 耗盡燃料 → 呼叫群友添柴 → 繼續開烤。**

後廚就此告別單純的冷卻倒數，正式升級為考驗群內動員力的能源補給站。

</div>
