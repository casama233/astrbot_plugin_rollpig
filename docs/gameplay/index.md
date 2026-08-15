---
title: 玩家玩法總覽
description: 從抽豬、永久豬籍、EX 到烤箱 Charge、補貨與豬圈日報。
---

# 🎮 玩家玩法總覽

> **先說結論：** 你每天還是只需要 `/今日小豬`。只是現在抽完以後，事情可以繼續發展很久。

<div class="pig-card-grid">
<div class="pig-card" markdown>
<span class="pig-card__icon">🐷</span>

### 每日小豬
今天、昨天、明天、本週。每天第一次抽取後結果固定，不靠瘋狂刷新換命。

<span class="pig-command">/今日小豬</span>
<span class="pig-command">/昨日小豬</span>
<span class="pig-command">/明日小豬</span>
<span class="pig-command">/本週小豬</span>
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">📚</span>

### 永久豬籍與保底
你解鎖過的小豬會留在永久豬圈；重複抽取會累積次數，並參與新豬保底與跨日疲勞保底。

<span class="pig-command">/我的豬圈</span>

[看保底到底怎麼算 →](collection-pity.md)
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">⭐</span>

### EX 成長
同一隻小豬抽第二次開始進入 EX。資源作者還能為 EX Lv.1–5 做圖片、描述或完整文案差分。

[了解 EX 成長 →](ex-growth.md)
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">🔥</span>

### 群聊後廚
烤自己、烤群友、隨機烤、吃群友。群烤還有預約、添柴、60/30/10 結算與次日保護。

<span class="pig-command">/烤群友 @某人</span>

[看看 60/30/10 到底誰熟 →](roast-outcomes.md)
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">⚡</span>

### Roast Charge
群烤不再是一次用完等整段冷卻，而是每個人、每個群各自有可儲存的烤箱能量。

[看看烤箱怎麼供電 →](roast-charge.md)
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">🪵</span>

### 群體烤箱補貨
沒 Charge 了？發起補貨，叫今天真的在這個群抽過豬的人一起 `/添柴`。成功後為符合條件的活躍玩家恢復有限能量。

<span class="pig-command">/烤箱補貨</span>
<span class="pig-command">/添柴</span>
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">📰</span>

### 豬圈日報
把一天的抽豬、成功燒烤、逃脫、反噬與被吃事件整理成一張統計海報。

[看今天誰最慘 →](daily-report.md)
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">🔎</span>

### 圖鑑探索
不想等明天？你可以隨機看豬，也可以按 ID、名稱、描述或文案搜尋本地圖鑑，不影響今天的抽取結果。

<span class="pig-command">/隨機小豬</span>
<span class="pig-command">/找豬 關鍵詞</span>
</div>
</div>

## `/添柴`：同一把柴，兩個後廚場景

`/添柴` 是現在玩家要記的 canonical 入口：

- 有進行中的烤箱補貨 → 裸 `/添柴` 支持補貨；
- 想明確加入某張預約 → `/添柴 @目標`；
- 沒有補貨且本群只剩一張待結算預約 → 裸 `/添柴` 自動加入；
- 沒有補貨但有多張預約 → 要求 `@目標`。

**你不用猜 Bot 把柴送去哪。Bot 會先看哪口鍋真的在冒煙。**

## 一條典型的現在版群聊時間線

<div class="pig-steps">
<div class="pig-step" markdown><span class="pig-step__n">1</span><div>

### 上午：先抽
A、B、C 各自 `/今日小豬`。收藏、EX 與今天的群活躍名單開始形成。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">2</span><div>

### 下午：有人開始手癢
B 對 A `/烤群友 @A`。如果 A 還沒在本群抽豬，會進預約流程；其他人可以 `/添柴 @A` 蹲同一口鍋。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">3</span><div>

### 傍晚：烤箱沒油
連續群烤後，B 的 Charge 見底。這時群裡可以發起 `/烤箱補貨`，活躍豬友用 `/添柴` 推進本輪進度。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">4</span><div>

### 晚上：事故被寫進報紙
`/豬圈日報` 把誰烤得最多、誰最慘、誰逃得最快、誰反噬最多整理出來。
</div></div>
</div>

!!! tip "只想查一個精確規則？"
    直接用頂部搜尋。Wiki 搜尋已針對「Roast Charge」「60/30/10」「烤箱補貨」「添柴」「EX 成長」「新豬保底」「跨日疲勞」「豬圈日報」等詞做中文分詞補強。
