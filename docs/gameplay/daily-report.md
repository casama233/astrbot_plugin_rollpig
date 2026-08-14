---
title: 豬圈日報
description: 一天的抽豬、燒烤、逃脫和反噬，晚上總要有人寫報告。
---

# 📰 豬圈日報：今天誰最慘，晚上見分曉

你們群今天可能發生了很多事：

- 有人抽到新豬；
- 有人把同一隻養到更高 EX；
- 有人瘋狂烤群友；
- 有人連續逃脫；
- 有人 10% 反噬連吃兩次；
- 還有人真的被吃了。

**《豬圈日報》負責在晚上把這些事故整理成人能看的東西。**

<div class="pig-highlight" markdown>

<span class="pig-command">/豬圈日報</span>

手動查看只會生成今天本群的統計海報。**它是只讀的。** 你連查十次，也不會因為好奇心把某位群友獻祭十次。

</div>

## 海報裡通常有什麼？

除了今日活躍、抽豬人數、成功燒烤、被吃人數、逃脫與反噬等統計，日報還會整理一組非常有必要公開處刑的稱號：

<div class="pig-card-grid">
<div class="pig-card" markdown>
<span class="pig-card__icon">🔥</span>

### 燒烤狂人
今天主動成功烤到其他群友次數最多的人。
</div>
<div class="pig-card" markdown>
<span class="pig-card__icon">🍖</span>

### 最慘食材
今天實際被成功燒烤次數最多的人。
</div>
<div class="pig-card" markdown>
<span class="pig-card__icon">💨</span>

### 逃脫大師
今天從烤箱裡跑掉最多次的人。
</div>
<div class="pig-card" markdown>
<span class="pig-card__icon">💥</span>

### 反噬之王
今天觸發反噬次數最多的人。主廚看到這個名字應該先反思一下。
</div>
</div>

稱號如果真的並列，日報會保留並列關係，不會硬抽一個人假裝「唯一第一」。

## 自動日報會不會突然騷擾所有群？

不會。

現在採 **per-group opt-in**：即使插件全局允許自動日報，一個群沒有明確開啟，就不會因為曾經有人抽過豬而自動收到。

常用控制：

<span class="pig-command">/豬圈日報</span>
<span class="pig-command">/豬圈日報 狀態</span>
<span class="pig-command">/豬圈日報 開啟</span>
<span class="pig-command">/豬圈日報 關閉</span>

目前開啟／關閉自動推送以 **AstrBot 管理員** 身份判定，不拿 QQ、Telegram 等平台原生群主／群管理員角色代替。

!!! info "今天才開，不補昨天"
    群組今天才 opt-in 時，不會倒回去補發更早日期的舊日報。自動推送的隨機延遲也會限制在報告所屬自然日內，不把「8 月 14 日晚報」拖到 8 月 15 日凌晨才冒出來。

## 頭像拿不到怎麼辦？

稱號卡會優先嘗試使用平台事件提供的暱稱與頭像。

如果平台不提供、超時或下載失敗：

> **日報不會跟著罷工。**

它會退回到暱稱首字占位，整張圖照常生成。

## 「今日祭品」是什麼鬼？

這是一個**可選功能，而且預設關閉**。

`daily_report_random_eat_enabled = false`

如果管理員主動開啟，它也只允許在**定時自動日報流程**中觸發：從鎖定報告日期、在本群實際參與 RollPig、且當時仍有可被吃小豬的玩家中選擇祭品。

手動：

<span class="pig-command">/豬圈日報</span>

永遠只讀，不觸發祭品。

!!! danger "所以請放心查日報"
    你不會因為「再看一次昨天誰最慘」而突然讓自己變成今天最慘。

## Roast Charge / 補貨也會進日報嗎？

v3.7.0 已把烤箱補貨相關事件接入 Gameplay Event。這意味著日報可以知道今天群裡是否發生過補貨、支持／添煤等玩法事件。

但日報只做**聚合與展示**，不成為 Roast Charge 的權威狀態來源。能量到底有幾格，還是由既有 storage / domain write 邊界說了算。

## 精確規則與管理員配置

如果你需要定時、補發、頭像快取、群組 opt-in、祭品或資料保存的精確行為：

- [日報技術規則 →](../DAILY-REPORT.md)
- [完整配置參考 →](../CONFIGURATION.md)

<div class="pig-highlight" markdown>

### 📰 一句話總結

白天：**群友自由發揮。**  
晚上：**《豬圈日報》負責留案底。**

</div>
