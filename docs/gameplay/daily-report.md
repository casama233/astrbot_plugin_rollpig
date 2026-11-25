---
title: 豬圈每日快報
description: 經歷了一整天的抽豬、架火燒烤、驚險逃脫與慘遭反噬，到了晚上總得有人出來寫份總結報告。
---

# 📰 豬圈每日快報：今天誰最倒楣，晚上準時揭曉

你們群裡今天肯定上演了不少精彩戲碼：

- 有人歐氣爆發抱回新豬；
- 有人專情養豬把同一隻衝上更高 EX；
- 有人四處點火瘋狂燒烤群友；
- 也有人腳底抹油連續驚險逃脫；
- 有人 10% 連遭兩次反噬；
- 也有人真被端上了餐桌。

**《豬圈日報》會在入夜後，把這些荒唐事故整理成人類看得懂的戰報。**

<div class="pig-highlight" markdown>

<span class="pig-command">/豬圈日報</span>

手動查詢只會生成本群今日的統計海報。**它是純唯讀的。** 就算你手癢連刷十次，也不會把無辜群友獻祭十回。

</div>

## 豬圈小票

這張小票把今日頭條置頂，往下依序列出各項數據、熱門豬隻與稱號榜單。

## 今日豬圈名人堂

想看整週戰況，請輸入 `/豬圈日報 八卦`。週日晚間也可在已啟用週刊的群選週一祭品。投票方式與生效時間見[週日小報與週一祭品](../COMMANDS.md#週日小報與週一祭品)。

<div class="pig-card-grid">
<div class="pig-card" markdown>
<span class="pig-card__icon">🔥</span>

### 燒烤狂人
今天主動出擊、成功把群友烤熟次數最多的人。
</div>
<div class="pig-card" markdown>
<span class="pig-card__icon">🍖</span>

### 最慘食材
今天實打實被成功烤熟次數最多的人。
</div>
<div class="pig-card" markdown>
<span class="pig-card__icon">💨</span>

### 逃脫大師
今天從烤箱裡成功溜走次數最多的人。
</div>
<div class="pig-card" markdown>
<span class="pig-card__icon">💥</span>

### 反噬之王
今天觸發反噬次數最多的人。主廚看到這名字，建議先面壁思過。
</div>
</div>

若稱號出現同分，日報會如實並列，絕不硬抽一位當「唯一冠軍」。

## 自動日報會不會半夜突襲所有群組？

不會。

目前採用 **per-group opt-in（單群主動開啟）**：就算全域開啟了自動推送，只要該群沒明確啟用，就不會因為過去有人抽過豬而突然收到日報。

常用指令：

<span class="pig-command">/豬圈日報</span>
<span class="pig-command">/豬圈日報狀態</span>
<span class="pig-command">/豬圈日報開啟</span>
<span class="pig-command">/豬圈日報關閉</span>

帶空格的寫法一樣有效：

<span class="pig-command">/豬圈日報 狀態</span>
<span class="pig-command">/豬圈日報 開啟</span>
<span class="pig-command">/豬圈日報 關閉</span>

簡體 `/猪圈日报` 及對應控制詞皆可正常觸發。Wiki 統一展示繁體標準寫法，免得同一頁把八種別名排成滿漢全席。

目前開關自動推送僅認 **AstrBot 管理員** 權限，不以 QQ、Telegram 等平台原生的群主或管理員身分判定。

!!! info "今天才開，不補昨天"
    群組今天才開啟訂閱的話，不會回溯補發先前的舊日報。自動推送的隨機延遲也嚴格壓在所屬自然日內，絕不把「昨晚戰報」拖到隔天凌晨才發。

## 抓不到頭像怎麼辦？

稱號卡會優先抓取平台事件回傳的暱稱與頭像。

萬一平台未提供、連線超時或下載失敗：

> **日報照發不誤，絕不罷工。**

系統會自動改用暱稱首字作為預設頭像，海報依舊完整出圖。

## 「今日祭品」是什麼來頭？

這是個**選配功能，且預設為關閉**。

`daily_report_random_eat_enabled = false`

若管理員手動開啟，它也僅限於**定時自動日報發送時**觸發：系統會鎖定報告當日、在本群實際玩過 RollPig 且當下仍保有可被吃小豬的玩家，從中挑出一名祭品。

手動：

<span class="pig-command">/豬圈日報</span>

絕對唯讀，絕不觸發祭品。

!!! danger "所以請放心查日報"
    你不會因為「多看一眼昨天誰最慘」，就把自己變成今天最慘的那個。

## Roast Charge / 補貨紀錄也會上報嗎？

烤箱補貨相關事件已正式接入 Gameplay Event。日報能捕捉今天群裡發生的補貨、應援與添柴動態，並在戰報附上一行簡短摘要。

不過日報僅負責**彙整與展示**，並非 Roast Charge 的權威帳本。具體還剩幾格能量，仍以既有 storage / domain write 邊界為準。

## 進階規則與管理員設定

若需查閱定時排程、補發機制、頭像快取、單群開啟、祭品抽選或資料留存的完整細節：

- [日報技術規則 →](../DAILY-REPORT.md)
- [完整配置參考 →](../CONFIGURATION.md)

<div class="pig-highlight" markdown>

### 📰 一句話總結

白天：**群友各自造孽。**<br>
晚上：**《豬圈日報》把案底印成戰報，明天繼續看誰倒大楣。**

</div>
