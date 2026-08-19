---
title: 烤群友 70/20/10 與次日保護
description: 成功、逃脫、反噬到底怎麼算；誰會被記一次被烤，誰第二天會拿到保護。
---

# 🔥 烤群友 70 / 20 / 10：烤架不是你家的，它偶爾有自己的想法

普通 `/烤群友 @某人`、隨機烤群友，以及預約烤豬真正結算時，都共用同一套核心結果：

<div class="pig-outcome-grid">
<div class="pig-outcome pig-outcome--success">
  <strong>70%</strong><span>🔥 成功</span><small>目標上料理卡，記一次實際被烤</small>
</div>
<div class="pig-outcome pig-outcome--escape">
  <strong>20%</strong><span>💨 逃脫</span><small>烤架空了，只留下群友的笑聲</small>
</div>
<div class="pig-outcome pig-outcome--backlash">
  <strong>10%</strong><span>💥 反噬</span><small>如果主廚自己可料理，主廚反而上桌</small>
</div>
</div>

這三個權重就是 **70 / 20 / 10**。Roast Charge、預約、添柴都不會偷偷把它改成別的比例。

!!! info "添柴不是成功率 Buff"
    預約裡多人添柴目前代表群聊參與與 Gameplay Event，**不會把成功率堆高**。到目標真正觸發預約時，仍然是 70/20/10。

## 三種結果到底改了什麼？

### 🔥 70% 成功

- 目標被記錄為這次真正的 `victim`；
- 本群「今天被烤次數」對目標 +1；
- 產生料理卡；
- 日報可以把它計入成功燒烤、最慘食材等統計。

普通成功**不會把永久圖鑑裡的小豬 ID 改成另一隻熟食豬**。它是一個群聊玩法事件與料理展示，不等於重抽今天的小豬。

### 💨 20% 逃脫

- 目標沒有被記一次實際被烤；
- 不增加次日保護用的「昨天被烤次數」；
- 仍然是一個可進入 Gameplay Event / 日報統計的逃脫事件；
- 如果這次普通群烤已經消耗 Charge，逃跑不會把電費吐回來。

### 💥 10% 反噬

烤架轉頭檢查主廚自己。

如果主廚今天的小豬仍符合可料理條件：

- 這次真正的 `victim` 變成主廚；
- 主廚在本群被烤次數 +1；
- 料理卡改為主廚自己的今日小豬。

如果主廚當時沒有可料理的小豬，反噬仍然發生，但主廚會「僥倖躲過」，這次沒有真正 victim。

## 🎰 Wiki 點火演示

這是前端展示，用 70/20/10 權重讓你直觀看結果分布；**它不調用插件、不讀 Charge，也不是 AstrBot 真實 RNG**。

<div class="pig-roast-demo" data-roast-demo>
  <button type="button" class="pig-roast-button" data-roast-fire>🔥 點一下假烤架</button>
  <div class="pig-roast-screen" aria-live="polite">
    <span data-roast-glyph>🐷</span>
    <strong data-roast-result>還沒點火</strong>
    <small data-roast-note>放心，Wiki 沒權限真的烤你的群友。</small>
  </div>
  <div class="pig-roast-history" data-roast-history aria-label="最近的演示結果"></div>
</div>

## 次日保護：昨天被烤太多，今天發防火毯

當 `enable_roast_protection=true` 時，插件會按**同一群聊**查看某位玩家昨天實際被烤到幾次。

預設閾值：

> **昨天同一群實際被烤 ≥ 3 次 → 今天普通玩法受保護。**

這裡的「實際被烤」不是「有人對你按過幾次指令」。

| 昨天發生的事 | 算進保護計數？ |
| --- | --- |
| 對你群烤，70% 成功 | ✅ 算 |
| 對你群烤，但你 20% 逃脫 | ❌ 不算 |
| 別人想烤你，10% 反噬把主廚烤了 | ❌ 你不算；主廚算 |
| 預約最後成功烤到你 | ✅ 算 |
| 只是建立預約、還沒結算 | ❌ 不算 |

因此保護看的是**昨天真正上過幾次料理台的人**，不是被點名次數。

## 今天有保護後，哪些東西會被攔？

普通流程會尊重保護，包括：

- `/烤群友 @某人`
- 隨機烤群友候選篩選
- 建立預約烤豬
- 普通吃群友選目標

後門強制模式可以突破「被烤保護」這一層，但**不能把基本資格一起刪掉**。例如目標是人類、已經是 `吃掉了`、或根本沒有今日小豬時，仍然不是普通可料理目標。

<div class="pig-highlight" markdown>

### 🛡️ 所以保護不是無敵

它更像是：「你昨天已經被這個群玩得很慘了，今天正常排隊先放過你。」

至於超管拿著 `/強行點火` 走後門，那是另一個法律體系。

</div>

## Roast Charge 跟結果是兩件事

Charge 解決的是：

> **「你現在有沒有資格發起這次普通點火？」**

70/20/10 解決的是：

> **「火已經點了，接下來到底誰出事？」**

所以一次普通群烤即使最後逃脫或反噬，Charge 還是按發起規則消耗。完整能源機制看 [Roast Charge 與烤箱補貨](roast-charge.md)。

## 預約烤豬的結算

目標今天還沒抽豬時，如果開啟預約：

1. 第一位主廚建立預約並支付正常的 1 格 Charge；
2. 其他人添柴，不重複收 Charge；
3. 目標之後在**同一群**真正顯示自己的今日小豬；
4. 預約一次性觸發；
5. 仍按 70/20/10；
6. 不會因「終於結算」再向主廚收第二次 Charge。

更底層的一次性狀態規則見 [預約烤豬技術規則](../ROAST-RESERVATIONS.md)。

## 管理員可調什麼？

- `enable_roast_protection`：次日保護開關
- `roast_protection_threshold`：昨天被烤多少次後今天保護，預設 3
- `group_roast_max_charges`：普通群烤可儲存 Charge 數
- `group_roast_cooldown_hours`：每格自然恢復時間

**70/20/10 本身目前不是配置項。** 它由核心 Roast policy 統一提供，避免不同入口各玩各的。

<div class="pig-highlight" markdown>

### 🔥 一句話總結

70%：**你朋友熟了。**  
20%：**你朋友跑了。**  
10%：**你開始思考為什麼料理卡上是自己的名字。**

</div>

## 烤豬卡文案來源

料理卡不再只靠少量固定菜名。插件內置一份可離線使用的「豬言豬語」文案包，菜名與正文獨立組合；同一群最近使用過的組合會暫時避開，減少短時間撞文案。

官方 Resource Protocol v1 manifest 可選發布 `roast_copy` 文案包。同步成功時優先使用遠端包；遠端未提供、下載失敗或校驗不通過時，仍使用插件內置包，不影響抽豬與烤豬主流程。

啟用 AI 料理文案後，每隻豬每天仍最多發起一次模型請求，但單次要求生成最多 4 條不同候選，並把最近七天候選合併使用；舊版本已保存的單條 AI 文案仍可直接讀取。AI 文案與本地文案共用近期防重複記錄。
