---
title: 常見故障與「為什麼不讓我養豬」
description: 玩家先看這裡。抽不到、烤不了、補不了、日報不發、資源 403，都從症狀開始排。
---

# 🧯 常見故障：先看症狀，別一上來就刪資料庫

RollPig 的錯誤有兩種：

1. **真的壞了**；
2. **規則正在非常認真地阻止你做一些豬圈法律不允許的事。**

這頁先幫你分清是哪一種。

<div class="pig-triage" markdown>
<div><span>🐷</span><strong>玩家問題</strong><small>抽不到、看不到、烤不了、吃不了</small></div>
<div><span>🔥</span><strong>群玩法</strong><small>Charge、保護、補貨、預約</small></div>
<div><span>☁️</span><strong>資源 / 管理</strong><small>同步、403、投稿、面板</small></div>
<div><span>🗄️</span><strong>資料層</strong><small>SQLite、遷移、備份、恢復</small></div>
</div>

## `/今日小豬` 今天突然抽不到

### 先問：昨天是不是被吃了？

如果昨天在「吃群友」流程中變成 `吃掉了`，今天第一次抽豬會依 `eaten_next_day_failure_percent` 做一次懲罰判定，預設失敗率 **20%**。

如果今天這次懲罰真的失敗：

> **今天就鎖到自然日結束，不是多按幾次 `/今日小豬` 就能洗掉。**

這是玩法，不是 API 掛了。

### 再問：每天邊界是不是你以為的午夜？

每日邊界由 `timezone` 決定。

如果設成 `Asia/Shanghai`、`America/Los_Angeles` 或其他 IANA 時區，插件按那個時區判斷今天；`local` 才跟伺服器本地時區走。

## `/今日小豬 @某人` 為什麼不幫他抽？

因為這個入口是**只讀查看**。

對方沒抽時只會告訴你「他還沒抽」，不會替他：

- 生成今日結果
- 解鎖圖鑑
- 觸發預約烤豬
- 繞過次日吃掉懲罰

如果你想等他出現再烤，請用預約流程，不要把查看命令當遠端控制器。

## `/烤群友` 提示對方不能烤

按這個順序看：

<div class="pig-checklist">
<label><input type="checkbox" disabled> 你是不是在群聊？</label>
<label><input type="checkbox" disabled> `enable_roast` 和 `enable_group_roast` 是否開啟？</label>
<label><input type="checkbox" disabled> 目標是不是你自己？烤自己請用 `/今日烤豬`。</label>
<label><input type="checkbox" disabled> 目標今天是不是「人類」或 `吃掉了`？</label>
<label><input type="checkbox" disabled> 目標昨天是不是在同一群被烤到達保護閾值？</label>
<label><input type="checkbox" disabled> 你自己的 Roast Charge 是否已經見底？</label>
</div>

如果目標**今天還沒抽豬**，而且 `enable_roast_reservation=true`，明確 `/烤群友 @某人` 應進入預約，而不是立刻結算。

## 明明烤的是 A，為什麼最後料理卡是我？

恭喜，抽到 **10% 反噬**。

普通群烤結果固定是：

- 60% 成功
- 30% 逃脫
- 10% 反噬

反噬時如果主廚自己的今日小豬可料理，真正被記為 victim 的是主廚。

完整看 [60/30/10 與次日保護](../gameplay/roast-outcomes.md)。

## 對方昨天被烤很多次，今天為什麼突然有盾？

預設 `enable_roast_protection=true` 且 `roast_protection_threshold=3`。

同一群昨天**實際被烤成功**達 3 次，今天普通烤群友、預約建立和普通吃群友選目標會尊重這層保護。

注意：

- 30% 逃脫不算一次
- 10% 反噬算真正上桌的主廚，不算原目標
- 後門強制模式可突破保護，但不突破基本資格

## `/烤箱補貨` 說我沒資格

群體補貨不是「任何看到群的人都能領電」。

你需要是**今天真的在這個群參與過 RollPig 的活躍玩家**。補貨發起者本身也要符合資格。

另外還可能因為：

- 本群今天成功補貨已達每日上限
- 已經有一輪正在進行
- 你自己的 Charge 本來就是滿的（是否能從結果受益與是否能支持是不同判斷）
- 管理員關閉 `enable_oven_refill`

玩法細節看 [Roast Charge 與烤箱補貨](../gameplay/roast-charge.md)。

## `/添煤` 沒加人頭

常見原因：

- 你今天沒有在本群參與 RollPig
- 這一輪你已經支持過一次
- 沒有有效的進行中補貨輪次
- 輪次已經剛好被別人推到結算

每人每輪只計一次。連按十次不會讓你變成一個 10 人煤礦工。

## 為什麼日報不自動發？

目前自動日報是 **global master switch + per-group opt-in** 兩層。

即使：

```text
daily_report_auto_send = true
```

某個群沒有由 AstrBot 管理員明確開啟，也不會自動收到。

先在群裡看：

<span class="pig-command">/豬圈日報狀態</span>

需要時再由管理員：

<span class="pig-command">/豬圈日報開啟</span>

另外，如果 `daily_report_skip_empty_groups=true`，當天沒有 RollPig 抽取活動的群會被跳過。

## 手動看日報會不會觸發「今日祭品」？

不會。

`daily_report_random_eat_enabled` 即使被管理員主動打開，也只允許在**定時自動日報流程**中生效；手動 `/豬圈日報` 是只讀。

## 公共 / 私人資源同步顯示 403

如果配置還指向舊的：

```text
https://pig.felislab.cc/resources/rollpig/manifest.json
```

那是 nonebot 專用受限來源，本 AstrBot 客戶端會被拒絕。

新版本正常預設 AstrBot 專用源：

```text
https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

如果你是自訂私人源也遇到 403，就要檢查伺服器自己的認證 / header / 反代規則，不要把所有 403 都歸因於 JSON 格式。

## 同步失敗會不會把整個圖鑑清空？

正常不會。

遠端資源會經過下載、大小、SHA-256、JSON、圖片、整包完整性等 staging 驗證；全部成功後才切換 active 資源。

失敗時：

- 有舊快取 → 繼續用舊快取
- 沒舊快取 → 回退內置資源
- 本地 override / tombstone 仍在更高層

所以看到一次同步紅字時，**先不要手動刪 `cloud_resources/` 和資料庫。**

## 投稿成功，但公共源裡找不到

投稿成功只代表：

> **已進人工審核隊列。**

不是自動發佈。

維護者批准、重新校驗並生成新資源版本後，其他實例還要等下一次同步才能看到。

做豬 / 投稿流程看 [創作者指南](../creators/index.md)。

## 管理面板更新後版本怎麼沒變？

安全更新完成後**不會自動重啟 AstrBot**。

管理員需要在確認更新成功後自行重啟或重新載入插件。這是刻意避免更新器替你擅自重啟整個 Bot。

## SQLite 看起來怪怪的，我可以直接刪 `rollpig.db` 嗎？

**不要把「直接刪資料庫」當第一個修復步驟。**

尤其 WAL 模式下，還可能存在 `-wal` / `-shm` 等相關狀態。正確順序：

1. 先停止或隔離持續寫入；
2. 保存完整插件資料目錄作證據 / 備份；
3. 看管理面板與日誌中的實際 storage 錯誤；
4. 再決定是受控恢復、回退 JSON，還是重新遷移。

完整流程看 [運維、備份與遷移](../OPERATIONS.md)。

## 管理員要回報 bug，最好帶什麼？

建議至少提供：

- 插件版本
- AstrBot 版本
- 適配器類型
- 問題指令
- 是否群聊 / 私聊
- 對應時間點前後的錯誤日誌
- 相關功能配置值（**不要貼 Token / 私密憑證**）
- 是否能穩定重現

如果是資源問題，再帶：

- `resource_manifest_url`（若不是私密地址）
- 同步狀態錯誤摘要
- HTTP 狀態碼
- 是公共源、私人源還是本地覆蓋

<div class="pig-highlight" markdown>

### 🧯 排障總原則

**先判斷是玩法阻擋、配置關閉、資源失敗，還是真的 storage / runtime error。**

不要因為一隻豬今天不肯出來，就先把整個豬圈地基炸了。

</div>
