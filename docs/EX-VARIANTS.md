# EX Lv. 成長差分

EX 差分讓同一隻已解鎖小豬在重複抽取後，隨既有 `EX Lv.` 顯示不同圖片、描述或完整文案，而不改變小豬 ID、名稱、抽取機率或玩法規則。

## 1. EX Lv. 如何計算

本功能**不新增玩家存儲欄位**。沿用永久圖鑑原本的抽取次數：

```text
EX Lv. = max(0, count - 1)
```

第一次解鎖為 `EX Lv.0`；第二次抽中為 `EX Lv.1`，依此類推。玩家 EX 等級可以高於 5，但資源差分目前只允許配置 `EX Lv.1`～`EX Lv.5`；高於 5 時繼續使用 Lv.5 或更低的最後有效差分。

## 2. 稀疏差分與逐欄位繼承

差分不要求每一級都配置，也不要求圖片、描述、文案一起變更。例如：

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

圖片、`description`、`analysis` 分別向下尋找最近一個已配置值，因此內容作者只需要提供真正發生變化的部分。

| 玩家等級 | 圖片 | 描述 | 文案 |
| --- | --- | --- | --- |
| EX 0–1 | 基礎圖 | 基礎描述 | 基礎文案 |
| EX 2–3 | EX2 圖 | EX2 描述 | 基礎文案 |
| EX 4 | EX2 圖 | EX2 描述 | EX4 文案 |
| EX 5+ | EX5 圖 | EX2 描述 | EX4 文案 |

## 3. 可修改與不可修改欄位

每個 EX 等級只允許 `image`、`description`、`analysis`。EX 差分**不能**修改 ID、名稱、抽取權重／保底、熟食／人類／可烤／可吃等玩法規則或玩家收藏數據。

因此 EX 成長是展示與收藏層，不會讓同一 ID 在高等級時變成另一種規則實體。

## 4. 資源目錄與內建內容

資源源可以選擇性增加：

```text
resource/
├─ pig.json
├─ image/
├─ pig_ex_variants.json
└─ ex_variants/
   └─ ...
```

官方內建資源帶有非空 EX 成長內容。回歸測試會驗證 EX pig ID、schema、可見差分、稀疏繼承與 EX 5+ 行為。

只有 `pig_ex_variants.json` 實際引用的圖片才能存在於 `ex_variants/`；缺圖、未引用圖片、不安全檔名、超大或無法解碼的圖片都會被資源建構器拒絕。

## 5. AstrBot Resource Protocol v1 擴展

EX 差分使用 **v1 的可選欄位**，不提升 `schema_version`，所以沒有 EX 能力的舊資源包仍然完全有效。

帶 EX 差分的 manifest 可額外包含：

```json
{
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

預設公共資源優先級：

```text
雲端 EX → 內建 EX
```

若管理員只覆蓋某隻小豬的基礎資料而沒有建立本地 EX，公共 EX 會被阻擋；管理員明確建立本地 EX 後，優先級變為：

```text
本地 EX → 雲端 EX → 內建 EX
```

## 7. Gameplay Event 與全鏈路回歸

玩家完成當天重複抽取並形成 `EX Lv.` 成長時，插件可記錄 Gameplay Event v1 `ex_level_up`。事件使用確定性 ID 去重，同一天重複查看今日結果不會重複記錄。

全鏈路 contract test 固定收藏次數 → EX 等級、今日／歷史／週視圖、料理卡、圖片解析、明日預測隔離、事件去重、本地 override，以及壞掉的 active EX 回退 bundled EX。

## 8. 本地 EX 視覺化編輯

AstrBot Plugin Page 提供獨立的 **EX 成長管理** 頁，不需要手改 JSON：

- 按小豬搜尋與選擇；
- 分別編輯 EX Lv.1–5；
- 短描述與完整文案留空即繼承；
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

EX-aware 投稿一次包含基礎 record／圖片、`ex_variants` 與可選 `variant_images`：

```json
{
  "submission_version": 2,
  "record": {
    "id": "sleep-pig",
    "name": "睡覺豬",
    "description": "...",
    "analysis": "..."
  },
  "image": "<base64 base image>",
  "ex_variants": {
    "schema_version": 1,
    "pigs": {}
  },
  "variant_images": []
}
```

公開契約保證：

- 舊 base-only 投稿保持 envelope v1 相容；
- EX 投稿只能攜帶目前小豬的 Lv.1–5 差分；
- EX 圖片固定 `<pig-id>-ex<level>.png`，最多五張；
- 引用圖片與實際提交集合必須完全一致；
- 審核員可在批准前查看基礎資料／圖片與每級 EX 差分／圖片；
- reject 不改動目前正式資源；
- approve 只有在 base + EX 整包驗證成功後才發布成同一個新 resource version。

因此不允許出現「基礎豬已發布，但 EX 只發布一半」的狀態。

> 公共源服務端實作、持久化細節、反向代理與 production 部署配置已移出本公開插件倉庫，由私有運維倉庫維護。公開倉庫只承諾客戶端／投稿契約與 Resource Protocol 行為。

## 10. 完成範圍

EX 產品閉環包含：差分資料模型、稀疏繼承、官方內容、Resource Protocol v1 可選 EX 資源、同步安全校驗、玩家展示、事件、本地視覺化編輯、EX 公共投稿／人工審核，以及 base + EX 同版發布契約。

「100% 完成」仍以 [`EX-ACCEPTANCE.md`](EX-ACCEPTANCE.md) 的驗收閘門為準。倉庫功能完整不等於 production 已完成部署；正式 release 前仍需要實際公共源服務與第二客戶端同步 smoke。
