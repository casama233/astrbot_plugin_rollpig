---
title: AI 小豬工坊
description: 在 Pig Manager 裡批量策劃、參考既有小豬生圖、微調並安全入庫。
---

# 🤖 AI 小豬工坊

AI 小豬工坊把「想一隻豬」和「真的放進本地圖鑑」接成一條管理流程。

它的工作流受到 [AutoPig-Studio](https://github.com/Gusare124/AutoPig-Studio) 啟發，但不是把另一套 FastAPI 服務塞進 AstrBot；RollPig 直接復用自己的 Plugin Page、AI Provider、本地圖鑑與資源寫入邊界。

<div class="pig-highlight" markdown>

**入口：** AstrBot → 今日小豬 Plugin Page → **Pig Manager** → **AI 小豬工坊**

</div>

## 一次完整流程

<div class="pig-steps" markdown>
<div class="pig-step" markdown>
<div markdown="1">

### 1. 先讓 AI 開策劃會

填寫風格方向、批量數量與額外要求。文字策劃直接使用 AstrBot 當前 AI Provider，因此不需要再為「想名字／寫文案」配置第二份聊天模型 Key。

AI 會產出：

- 中文名稱；
- 英文小寫 ID；
- 1–2 個視覺特徵；
- 短描述；
- 完整圖鑑文案。

策劃 Prompt 會帶入一部分當前有效圖鑑，盡量避免和已存在的小豬明顯撞題。

</div>
</div>
<div class="pig-step" markdown>
<div markdown="1">

### 2. 挑一隻「參考豬」

每個候選都可以從**目前有效圖鑑**挑一隻已有圖片的小豬作參考。

參考圖的作用不是複製角色，而是讓生圖模型保留 RollPig 小豬的核心視覺語言：四足體態、身體比例、臉型、豬鼻和簡潔遊戲資產構圖，再只增加少量主題元素。

</div>
</div>
<div class="pig-step" markdown>
<div markdown="1">

### 3. 生成、看圖、再叫主廚重畫

按 **生成小豬** 後，完整圖片先留在插件服務端草稿區。管理頁只取得一個短期 `draft_id` 和 256px 預覽，不會把完整大圖在瀏覽器與服務端之間反覆 base64 搬運。

不滿意時可以寫微調反饋，例如：

> 帽子小一點、保留粉色豬鼻、不要背景、配件不要遮住耳朵。

再按一次即可按同一任務重畫。

</div>
</div>
<div class="pig-step" markdown>
<div markdown="1">

### 4. 確認後才入庫

只有按下 **確認並入庫**，草稿才會經過現有本地圖鑑寫入邊界成為真正的小豬。

V1 的 AI 工坊只允許**新增 ID**。如果 ID 已存在，請回到原本的「豬豬圖鑑」編輯器修改，避免工坊繞過既有覆蓋、圖片與 rollback 規則。

入庫後可以繼續：

- 編輯基礎資料；
- 做 EX Lv.1–5；
- 檢查效果後再投稿公共豬源。

</div>
</div>
</div>

## 生圖 Provider 怎麼配？

文字策劃和生圖是分開的：**沒有生圖 Provider 時，策劃功能仍然可用。**

工坊目前接受 OpenAI-compatible `chat/completions` 圖像端，需要：

- Base URL；
- 圖像模型名稱；
- API Key。

API Key 提交後只保存在插件服務端的工坊配置裡。狀態 API 只告訴前端「是否已配置 Key」，不會把已保存的 Key 再讀回瀏覽器。

!!! warning "Base URL 與圖片 URL 有額外限制"
    Base URL 預設必須是 HTTPS；只有 `localhost`、`127.0.0.1`、`::1` 可以使用 HTTP。  
    如果模型不是直接回 data URL，而是回遠端圖片地址，V1 只接受與生圖 API **同 hostname** 的 HTTPS 圖片。使用獨立 CDN 的 Provider 應配置成回 base64/data URL。

這個限制是故意的：管理插件不應該因為一個模型回覆，就變成可以替外部任意抓 URL 的下載器。

## 草稿會一直佔空間嗎？

不會。

AI 生成的完整圖片先放在：

`plugin_data_dir/pig_studio_drafts`

預設草稿 TTL 是 **6 小時**。過期草稿會在工坊初始化／後續生成時清理；成功入庫後，對應草稿圖片和 metadata 也會立即刪除。

## V1 還沒有什麼？

AutoPig-Studio 還有「上傳角色立繪 → 轉成小豬」的玩法。RollPig 首版暫時**沒有**把它一起塞進來。

原因不是做不到，而是這條路會額外引入：

- 大文件上傳；
- 角色圖 + 小豬參考圖的雙圖多模態請求；
- 更嚴格的圖片大小／格式／內容邊界；
- 更複雜的失敗重試與臨時文件管理。

先把「圖鑑參考豬 → 新小豬」基礎生成鏈跑穩，再獨立加入角色轉豬，會比第一版一次塞完更可靠。

<div class="pig-highlight" markdown>

### 🐷 一句話總結

**AI 可以幫你開腦洞、畫草稿；真正進豬圈之前，最後那一下仍由管理員確認。**

</div>
