---
title: 永久圖鑑與新豬保底
description: 重複不是白抽。搞懂永久收藏、連續重複保底、跨日疲勞與 80% 上限。
---

# 📚 永久圖鑑與新豬保底：重複很多次以後，系統真的會心虛

每天第一次 `/今日小豬` 得到的結果，不只活一天。

只要你真正抽到一隻小豬，它就會進入你的**永久圖鑑**；之後再抽到同一隻，會累積次數、推進 EX，也會影響新豬保底。

<div class="pig-highlight" markdown>

<span class="pig-command">/我的豬圈</span>

這裡看的不是「今天有什麼」，而是**你這個玩家歷史上真正解鎖過什麼**。

</div>

## 先把最容易誤會的地方說清楚

保底**不是**「今天有 20% 機率直接送你新豬」。

實際流程是：

<div class="pig-flowline" markdown>
<div><b>1</b><span>先從完整有效圖鑑正常抽一個候選</span></div>
<div><b>2</b><span>如果候選本來就是未解鎖 → 直接拿走，保底不插手</span></div>
<div><b>3</b><span>如果候選已解鎖，而且圖鑑還有未見小豬 → 才計算保底率</span></div>
<div><b>4</b><span>保底判定成功 → 從「尚未解鎖」集合重新抽一隻</span></div>
</div>

所以 Wiki 裡寫的保底百分比，指的是：

> **「初始候選已經重複時，把它改判成一隻未見小豬」的條件式機率。**

如果你已經全圖鑑，沒有未見集合可以重抽，保底自然也不會憑空創造第 N+1 隻豬。

## 兩套保底會一起算

目前預設同時開啟兩套機制：

<div class="pig-card-grid">
<div class="pig-card" markdown>
<span class="pig-card__icon">🎯</span>

### 連續重複保底
每次最終真的抽到**已解鎖**小豬，`duplicate_streak` 會 +1；一旦最終抽到新豬，就重置為 0。

預設每層：**+15%**。
</div>

<div class="pig-card" markdown>
<span class="pig-card__icon">🥱</span>

### 跨日重複疲勞
只看**連續自然日**。昨天、前天……如果每天最終抽到的都是當時已經解鎖的小豬，就形成跨日疲勞鏈。

預設第 **2 個連續重複日**開始，每層 **+5%**，這部分最多 **+15%**。
</div>
</div>

兩者相加後，最終保底率仍共同受 **80%** 上限限制。

## 預設數值會長成什麼樣？

下面假設你每天的「初始候選」都很倒楣地再次落在已解鎖小豬上，而且前面的保底判定都沒成功。

| 當前連續重複日 | 舊連續重複層 | 基礎保底 | 跨日疲勞 | 條件式總保底 |
| ---: | ---: | ---: | ---: | ---: |
| 第 1 天 | 0 | 0% | 0% | **0%** |
| 第 2 天 | 1 | 15% | 5% | **20%** |
| 第 3 天 | 2 | 30% | 10% | **40%** |
| 第 4 天 | 3 | 45% | 15% | **60%** |
| 第 5 天 | 4 | 60% | 15% | **75%** |
| 第 6 天 | 5 | 75% | 15% | **80%（封頂）** |

第一天沒有加成是刻意的：你必須先真的遭遇一次重複，系統才開始積累「你是不是有點太倒楣」的證據。

## 🧪 保底實驗室

這個小工具使用**目前預設配置**計算條件式重抽率；它只是在 Wiki 前端算公式，**不讀你的真實存檔，也不模擬機器人的實際抽取結果**。

<div class="pig-pity-lab" data-pity-lab>
  <div class="pig-pity-control">
    <label for="pity-legacy">先前連續重複次數 <strong data-pity-legacy-value>1</strong></label>
    <input id="pity-legacy" data-pity-legacy type="range" min="0" max="8" value="1">
  </div>
  <div class="pig-pity-control">
    <label for="pity-days">前面連續重複自然日 <strong data-pity-days-value>1</strong></label>
    <input id="pity-days" data-pity-days type="range" min="0" max="8" value="1">
  </div>
  <div class="pig-pity-result">
    <span>如果這次初始候選又重複</span>
    <strong data-pity-total>20%</strong>
    <small data-pity-breakdown>15% 連續重複 + 5% 跨日疲勞</small>
  </div>
  <div class="pig-pity-gauge"><i data-pity-gauge></i></div>
</div>

## 跳過一天會怎樣？

跨日疲勞要求「相鄰自然日」連續成立，所以：

```text
週一：重複
週二：重複
週三：沒抽
週四：又重複
```

週四不會把週一、週二當成一條仍在延伸的跨日疲勞鏈。

但舊的 `duplicate_streak` 是另一個狀態；**單純跳過一天不等於抽到新豬，所以不會因為缺席自動清零。**

## 「昨天被吃掉」會不會把跨日判定弄丟？

不會因為畫面上顯示 `吃掉了` 就完全失憶。

歷史資料會保留被替換前的原始小豬；計算跨日重複鏈時，若某天的可見結果已經被 `eaten` 狀態覆蓋，邏輯會嘗試使用保存的原始抽取結果判斷那天到底是不是重複。

## 圖鑑、EX、保底之間的關係

<div class="pig-versus">
<div class="pig-versus__side" markdown>
<span class="pig-versus__label">抽到新豬</span>

- 永久圖鑑 +1 種
- 該豬第一次解鎖
- `duplicate_streak` → 0
- EX 從基礎狀態開始
</div>
<div class="pig-versus__arrow">↔</div>
<div class="pig-versus__side pig-versus__side--new" markdown>
<span class="pig-versus__label">再次抽到舊豬</span>

- 永久種類數不變
- 該豬抽取次數 +1
- EX 繼續成長
- 連續重複狀態累積
</div>
</div>

所以「重複」不是純廢抽：它同時是 **EX 成長素材 + 下一次保底燃料**。

## 管理員可調哪些值？

- `enable_new_pig_pity`：連續重複保底總開關
- `pity_step_percent`：每層連續重複加成，預設 15
- `enable_daily_duplicate_pity`：跨日疲勞開關
- `daily_duplicate_pity_start_day`：從第幾個連續重複日開始，預設 2
- `daily_duplicate_pity_step_percent`：跨日每層加成，預設 5
- `daily_duplicate_pity_max_percent`：跨日部分上限，預設 15

目前程式層的最終共同上限為 **80%**。

完整配置名稱見 [配置參考](../CONFIGURATION.md)，EX 顯示規則見 [EX 成長](ex-growth.md)。

<div class="pig-highlight" markdown>

### 🐽 一句話總結

第一次重複：**系統先記小本本。**  
第二、第三、第四次：**小本本開始冒煙。**  
到後面：**它最多拿 80% 的條件式重抽率勸你去看看沒見過的新豬。**

</div>
