# EX Lv. 成長差分

EX 差分讓同一隻已解鎖小豬在重複抽取後，隨既有 `EX Lv.` 顯示不同圖片、描述或完整文案，而不改變小豬 ID、名稱、抽取機率或玩法規則。

## 1. EX Lv. 如何計算

本功能**不新增玩家存儲欄位**。沿用永久圖鑑原本的抽取次數：

```text
EX Lv. = max(0, count - 1)
```

第一次解鎖為 `EX Lv.0`；第二次抽中為 `EX Lv.1`，依此類推。玩家 EX 等級可以高於 5，但資源差分目前只允許配置 `EX Lv.1`～`EX Lv.5`；高於 5 時繼續使用 Lv.5 或更低的最後有效差分。

## 2. 官方五級文案基線 + 稀疏覆寫

正式官方目錄中的**每一隻小豬**都有 EX1～EX5 五級可見文案基線。每級至少包含獨立 `description` 與 `analysis`，所以即使某隻豬沒有專門畫 EX 圖，也不會只看到 EX 數字變化。

基線由該豬既有的 `id`、`name`、`description`、`analysis` 確定性生成，因此：

- 同一份 catalog 每次生成結果一致；
- 每隻豬都保留自己的原始角色設定作為文案核心；
- EX1～EX5 的描述與完整文案逐級不同；
- 兼容下限恢復回來的舊公共源小豬也會自動獲得完整五級文案；
- 新增官方小豬後，Resource Source CI 會要求它也具備完整 EX1～EX5 覆蓋。

在這個基線之上，資源作者仍然使用原本的**稀疏差分**格式，只寫真正需要手工覆寫的欄位。例如：

```json
{
  "schema_version": 1,
  "pigs": {
    "sleep-pig": {
      "2": {
        "image": "sleep-pig-ex2.png",
        "description": "睡得更香了"
      },
      "4": {
        "analysis": "EX Lv.4 才出現的新旁白。"
      },
      "5": {
        "image": "sleep-pig-ex5.gif"
      }
    }
  }
}
```

手工覆寫仍採**逐欄位向上繼承**：例如 EX2 寫了 `description`，它會一直沿用到更高級，直到後面再次覆寫 `description`；圖片與 `analysis` 同理。沒有被手工覆寫的欄位，則繼續使用該級官方基線。

因此作者不必為了「完整五級」機械複製五份資料：官方基線負責保證每級都有內容，稀疏資源負責放真正值得特製的差分。

目前 bundled starter pack 中的 10 隻示範小豬已進一步提供**完整五級手寫文案**；其他官方／兼容小豬由五級基線保證完整成長內容，後續可逐步追加更個性化的手寫覆寫或 EX 圖片。

## 3. 可修改與不可修改欄位

每個 EX 等級只允許 `image`、`description`、`analysis`。EX 差分**不能**修改 ID、名稱、抽取權重／保底、熟食／人類／可烤／可吃等玩法規則或玩家收藏數據。

因此 EX 成長是展示與收藏層，不會讓同一 ID 在高等級時變成另一種規則實體。

## 4. 資源目錄與內建內容

資源源可以增加：

```text
resource/
├─ pig.json
├─ image/
├─ pig_ex_variants.json
└─ ex_variants/
   └─ ...
```

原始 authoring `pig_ex_variants.json` 可以保持稀疏；正式 Resource Source builder 會在發布時把它與官方五級基線合併，產生**物理完整**的發布版 `pig_ex_variants.json`。發布版中 `ex_variant_pig_count` 必須等於 `pig_count`，每隻豬都必須有 Lv1～Lv5。

只有 EX 差分實際引用的圖片才能存在於 `ex_variants/`；缺圖、未引用圖片、不安全檔名、超大或無法解碼的圖片都會被資源建構器拒絕。

## 5. AstrBot Resource Protocol v1 擴展

EX 差分使用 **v1 的可選欄位**，不提升 `schema_version`，所以沒有 EX 能力的舊資源包仍然完全有效。

帶 EX 差分的 manifest 可額外包含：

```json
{
  "ex_variant_pig_count": 201,
  "ex_variants": {
    "path": "pig_ex_variants.json",
    "size": 1234,
    "sha256": "..."
  },
  "variant_images": [
    {
      "filename": "sleep-pig-ex2.png",
      "path": "ex_variants/sleep-pig-ex2.png",
      "size": 5678,
      "sha256": "..."
    }
  ]
}
```

差分 JSON 與圖片和基礎資源一樣走大小、SHA-256、圖片解碼、整包預算、staging 與原子切換校驗。任何 EX 差分驗證失敗時，不會用半套內容覆蓋目前 active 資源。

如果遠端 manifest 在相同 `resource_version` 下新增 EX 可選欄位，而本機舊快照還沒有 `pig_ex_variants.json`，新版插件會補同步，而不是因版本號相同直接略過。

## 6. 顯示規則與優先級

EX 差分用於玩家**已擁有**的小豬展示，包括今日／歷史／週視圖、永久圖鑑及相關料理卡片。

`/明日小豬` 是預測，不代表玩家已擁有明日結果，因此不套用玩家目前的 EX 差分。

官方／公共來源仍按既有資源優先級讀取：

```text
雲端 EX → 內建 EX → 官方五級基線
```

當雲端或內建 EX 是稀疏 authoring 資料時，載入後會疊加到當前實際 `pig_list` 的五級基線上，因此 active catalog 中的兼容豬也有完整文字成長。

若管理員只覆蓋某隻小豬的基礎資料而沒有建立本地 EX，公共 EX／官方基線不會偷偷改寫該本地豬；管理員明確建立本地 EX 後，本地 EX 仍取得最高展示優先級。

## 7. Gameplay Event 與全鏈路回歸

玩家完成當天重複抽取並形成 `EX Lv.` 成長時，插件可記錄 Gameplay Event v1 `ex_level_up`。事件使用確定性 ID 去重，同一天重複查看今日結果不會重複記錄。

全鏈路 contract test 固定收藏次數 → EX 等級、今日／歷史／週視圖、料理卡、圖片解析、明日預測隔離、事件去重、本地 override，以及壞掉的 active EX 回退 bundled EX。

此外，內容 gate 會驗證：

- bundled catalog 每一隻豬都有有效 EX1～EX5；
- 五級 `description` 各不相同；
- 五級 `analysis` 各不相同；
- compatibility-only pig 同樣能生成完整五級內容；
- Resource Source 發布結果的 EX pig 集合與 `pig.json` 完全相等；
- manifest / health 的 `ex_variant_pig_count == pig_count`。

## 8. 本地 EX 視覺化編輯

AstrBot Plugin Page 提供獨立的 **EX 成長管理** 頁，不需要手改 JSON：

- 按小豬搜尋與選擇；
- 分別編輯 EX Lv.1–5；
- 短描述與完整文案留空即按本地稀疏規則繼承；
- 每級可上傳／移除差分圖片；
- 可單獨重設某一級；
- 顯示「實際生效預覽」。

本地資料分開保存在：

```text
plugin_data/
├─ local_ex_variants.json
└─ local_ex_variants/
   └─ <pig-id>-ex<1-5>.png
```

## 9. 公共源投稿與審核

EX 公共源工作流使用**投稿 envelope v2**，正式資源仍是 **Resource Protocol v1**。兩個版本彼此獨立。

EX-aware 投稿一次包含基礎 record／圖片、`ex_variants` 與可選 `variant_images`。公開契約保證：

- 舊 base-only 投稿保持 envelope v1 相容；
- EX 投稿只能攜帶目前小豬的 Lv.1–5 差分；
- EX 圖片固定 `<pig-id>-ex<level>.png`，最多五張；
- 引用圖片與實際提交集合必須完全一致；
- 審核員可在批准前查看基礎資料／圖片與每級 EX 差分／圖片；
- reject 不改動目前正式資源；
- approve 只有在 base + EX 整包驗證成功後才發布成同一個新 resource version；
- 即使投稿沒有手寫 EX，正式 builder 也會為新加入 catalog 的小豬產生官方五級文字基線。

因此不允許出現「基礎豬已發布，但 EX 只發布一半」的狀態。

> 公共源服務端實作、持久化細節、反向代理與 production 部署配置已移出本公開插件倉庫，由私有運維倉庫維護。公開倉庫只承諾客戶端／投稿契約與 Resource Protocol 行為。

## 10. 完成範圍

EX 產品閉環包含：差分資料模型、官方全量五級文案基線、稀疏手寫覆寫、Resource Protocol v1 EX 資源、同步安全校驗、玩家展示、事件、本地視覺化編輯、EX 公共投稿／人工審核，以及 base + EX 同版發布契約。

程式與內容 gate 完成後，production 是否「100% 完成」仍以 [`EX-ACCEPTANCE.md`](EX-ACCEPTANCE.md) 為準：必須完成正式服務部署，以及真實 EX 投稿 → 審核 → approve → 新 resource release → 第二客戶端同步 smoke。
