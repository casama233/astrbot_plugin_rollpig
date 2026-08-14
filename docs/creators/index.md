---
title: 做一隻自己的小豬
description: 從本地新增、PigHub 選圖、512×512 圖片、EX 差分到公共豬源投稿。
---

# 🎨 做一隻自己的小豬：從「我有一個怪點子」到公共豬源

如果你只是想做一隻自己的小豬，**不需要先學會手搓 manifest，也不需要直接改倉庫裡的 `pig.json`。**

正常路線是管理面板：

<div class="pig-creator-pipeline">
  <div><b>01</b><span>✍️ 寫 ID / 名稱 / 描述 / 完整文案</span></div>
  <div><b>02</b><span>🖼️ 上傳圖片，或從 PigHub 挑一張再加工</span></div>
  <div><b>03</b><span>💾 儲存為本地新增 / 本地覆蓋</span></div>
  <div><b>04</b><span>🧪 在自己的實例先玩、先看、先改</span></div>
  <div><b>05</b><span>📮 想公開再投稿到 AstrBot 公共豬源</span></div>
</div>

## 一隻基礎小豬需要什麼？

最核心四個欄位：

```json
{
  "id": "coffee-pig",
  "name": "咖啡豬",
  "description": "今天先不要跟我講話",
  "analysis": "凌晨三點還醒著不是因為自律，是因為你和咖啡建立了錯誤的合作關係。"
}
```

### `id`

這是機器真正認豬的名字。

- 只允許小寫英文字母、數字、`-`、`_`
- 長度 1–64
- 公共源已存在的 ID 不能再拿來當另一隻新豬

好的 ID 像：

```text
coffee-pig
sleepy_pig
pig-404
```

不要把顯示名稱硬塞進 ID，也不要拿一串會後悔的 UUID 當藝術表達。

### `name`

玩家看到的名稱。可以中文，可以騷，但最好讓人看完知道自己今天到底抽到了什麼。

### `description`

短描述。適合放一句很快能讀完的性格 / 狀態。

### `analysis`

完整文案。這裡才是 RollPig 的靈魂區。

<div class="pig-highlight" markdown>

**推薦文案結構：**

先讓玩家「哦，這是在說我」，再補一刀。

例如：

> 「你今天很有行動力。主要體現在打開五個任務、完成零個，以及熟練地把焦慮從上午搬到晚上。」

不要寫成冷冰冰的資料庫描述；它是一張每天會被群友截圖的卡。

</div>

## 圖片怎麼處理？

管理面板保存後會把本地上傳圖片標準化成 **512×512 PNG**。

你可以：

- 直接上傳自己有權使用的圖片；
- 從 PigHub 在面板裡挑圖，再補自己的名稱、描述和文案；
- 先「下載原圖重修」，本地修完再重新上傳。

!!! warning "有圖不代表有授權"
    PigHub 在這個插件裡只是選圖來源之一。要公開投稿或再發布，仍應確保你有權使用對應圖片與文案。技術上能下載，不等於版權上自動自由使用。

## 本地新增、覆蓋、刪除到底是三層什麼？

RollPig 的有效圖鑑不是每次同步就把本地東西全部沖掉。

<div class="pig-layer-stack">
  <div class="pig-layer pig-layer--top"><strong>刪除屏蔽層</strong><span>你明確不要的 ID，優先級最高</span></div>
  <div class="pig-layer pig-layer--mid"><strong>本地覆蓋層</strong><span>新增、改名、改文案、自訂圖片</span></div>
  <div class="pig-layer pig-layer--base"><strong>基礎層</strong><span>AstrBot 公共源 / 私人源；失敗時回退內置資源</span></div>
</div>

所以：

- 新 ID → 顯示為「本地新增」
- 已存在 ID 再改 → 顯示為「覆蓋基礎源」
- 本地圖片 → 優先於遠端 / 內置圖片
- 刪除 → 本地資料移除，並建立 tombstone 屏蔽基礎層同 ID
- 取消屏蔽 → 如果基礎層還有同 ID，它會重新出現

這也是為什麼正常同步**不應該吃掉你的本地創作**。

## 想讓同一隻豬長出 EX 變體？

基礎豬做好之後，可以再做 **EX Lv.1–5 差分**。

每一級可以選擇覆蓋：

- 圖片
- `description`
- `analysis`

沒有配置的欄位會向較低等級繼承。

EX 差分**不能改 ID、名稱或玩法規則**，它是同一隻豬抽多次後的外觀 / 文案成長，不是偷偷在 Lv.4 換成另一個物種。

詳細格式看 [EX 差分規則](../EX-VARIANTS.md)。

## 📮 怎麼投稿公共豬源？

公共投稿從管理面板的「本地新增與覆蓋」發起。

流程：

<div class="pig-steps">
<div class="pig-step" markdown><span class="pig-step__n">1</span><div>

### 先在本地完成
把 ID、名稱、描述、完整文案和圖片都做完，自己先確認卡片看起來正常。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">2</span><div>

### 明確確認公開提交
面板不會悄悄把你的本地豬傳出去。公共投稿需要管理員在瀏覽器再次確認。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">3</span><div>

### 插件重新檢查
提交前會檢查完整欄位、圖片格式和大小；投稿圖片使用目前真正生效的 512×512 PNG。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">4</span><div>

### 進入人工審核
成功回應只代表「排進隊列」，**不代表已經上公共源**。
</div></div>

<div class="pig-step" markdown><span class="pig-step__n">5</span><div>

### 批准後才發佈
維護端會重新校驗整個資源目錄、建立不可變 release、備份，再原子切換 `v1`。
</div></div>
</div>

## 投稿會傳什麼？

會提交：

- 小豬 ID
- 名稱
- 描述
- 完整文案
- 標準化圖片

**不會**提交：

- 群友資料
- 群組 ID
- 聊天內容
- SQLite
- JSON 備份
- 插件配置

## 為什麼投稿成功了，別人還看不到？

因為公共源是**人工審核**。

成功提交 ≠ 成功發佈。

維護者批准並生成新資源版本後，其他實例才會在下次同步時拿到。如果對方的同步間隔仍是預設值，可能要等下一輪自動檢查，或由管理員手動同步。

## 什麼情況會被服務拒絕？

常見包括：

- 公共源已存在同 ID
- 待審核隊列已經有同 ID
- 重複圖片
- 欄位不完整
- 圖片不符合限制
- 超過投稿大小限制
- 來源短時間投稿過多，觸發每日限速

插件不會對具有副作用的投稿自動無腦重試，避免網路抖一下就幫你投出三胞胎。

## 我想自己維護私人豬源

那才需要進入 manifest 世界。

最小 v1 manifest 需要：

- `resource_version`
- `pig_json.path / size / sha256`
- 每張圖片的 `filename / path / size / sha256`
- HTTPS 託管

完整協議、大小上限、原子切換與回退方式，直接看：

- [資源管理手冊](../RESOURCE-MANAGEMENT.md)
- [資源相容性](../RESOURCE-SOURCE-COMPATIBILITY.md)
- [豬源維護](../RESOURCE-SOURCE-MAINTENANCE.md)

<div class="pig-highlight" markdown>

### 🎨 一句話總結

**先本地做得好笑，再考慮讓全世界一起抽到。**

公共源是發佈渠道，不是草稿箱；PigHub 是選圖工具，不是版權自動販賣機；EX 是成長，不是換皮逃逸。

</div>
