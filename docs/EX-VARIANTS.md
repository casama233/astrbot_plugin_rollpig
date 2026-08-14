# EX Lv. 成長差分

EX 差分讓同一隻已解鎖小豬在重複抽取後，隨既有 `EX Lv.` 顯示不同圖片、描述或完整文案，而不改變小豬 ID、名稱、抽取機率或玩法規則。

## 1. EX Lv. 如何計算

本功能**不新增玩家存儲欄位**。沿用永久圖鑑原本的抽取次數：

```text
EX Lv. = max(0, count - 1)
```

第一次解鎖為 `EX Lv.0`；第二次抽中為 `EX Lv.1`，依此類推。玩家 EX 等級可以高於 5，但資源差分目前只允許配置 `EX Lv.1`～`EX Lv.5`；高於 5 時繼續使用 Lv.5 或更低的最後有效差分。

## 2. 稀疏差分與逐欄位繼承

差分不要求每一級都配置，也不要求圖片、描述、文案一起變更。

例如：

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

此例的實際效果：

| 玩家等級 | 圖片 | 描述 | 文案 |
| --- | --- | --- | --- |
| EX 0–1 | 基礎圖 | 基礎描述 | 基礎文案 |
| EX 2–3 | EX2 圖 | EX2 描述 | 基礎文案 |
| EX 4 | EX2 圖 | EX2 描述 | EX4 文案 |
| EX 5+ | EX5 圖 | EX2 描述 | EX4 文案 |

圖片、`description`、`analysis` 分別向下尋找最近一個已配置值，因此內容作者只需要提供真正發生變化的部分。

## 3. 可修改與不可修改欄位

每個 EX 等級只允許：

- `image`：差分圖片檔名；
- `description`：短描述；
- `analysis`：完整文案。

EX 差分**不能**修改：

- `id`；
- `name`；
- 抽取權重／保底；
- 熟食、人類、可烤／可吃等玩法規則；
- 玩家收藏數據。

因此 EX 成長是展示與收藏層，不會讓同一 ID 在高等級時變成另一種規則實體。

## 4. 資源目錄與內建內容

資源源可以選擇性增加：

```text
resource/
├─ pig.json
├─ image/
│  └─ ...
├─ pig_ex_variants.json
└─ ex_variants/
   ├─ sleep-pig-ex2.png
   └─ sleep-pig-ex5.gif
```

官方內建資源現在會帶至少一組非空 EX 成長內容；回歸測試會驗證 `pig_ex_variants.json` 不是空佔位、所有 ID 都存在於 `pig.json`、每隻已配置小豬在有效等級確實產生可見差分，並固定稀疏繼承與 EX 5+ 行為。

只有 `pig_ex_variants.json` 實際引用的圖片才能存在於 `ex_variants/`；缺圖、未引用圖片、不安全檔名、超大或無法解碼的圖片都會被資源建構器拒絕。

## 5. AstrBot Resource Protocol v1 擴展

EX 差分使用 **v1 的可選欄位**，不提升 `schema_version`，所以沒有 EX 能力的舊資源包仍然完全有效。

帶 EX 差分的 manifest 會額外包含：

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

如果遠端 manifest 在相同 `resource_version` 下新增了 EX 可選欄位，而本機舊快照還沒有 `pig_ex_variants.json`，新版插件會補同步，而不是因版本號相同直接略過。

## 6. 顯示規則與優先級

EX 差分用於玩家**已擁有**的小豬展示，包括今日／歷史／週視圖、永久圖鑑及相關烤豬卡片所使用的玩家當前收藏等級。

`/明日小豬` 是預測，不代表玩家已擁有明日結果，因此不套用玩家目前的 EX 差分。

預設公共資源優先級維持：雲端 EX → 內建 EX。管理員若只覆蓋某隻小豬的基礎資料而沒有建立本地 EX，遠端／內建 EX 仍會被阻擋，避免同步內容偷偷套回本地修改過的小豬。

當管理員**明確建立本地 EX** 後，該隻小豬改由本地 EX 取得最高展示優先級：

```text
本地 EX → 雲端 EX → 內建 EX
```

本地 EX 仍只允許圖片、短描述、完整文案三種展示欄位，不會繞過核心 schema 去改玩法身份。

## 7. Gameplay Event 與全鏈路回歸

當群聊中本人完成當天重複抽取並形成 `EX Lv.` 成長時，插件可以透過 Gameplay Event v1 記錄 `ex_level_up`：

```json
{
  "kind": "ex_level_up",
  "actor_id": "user-id",
  "pig_id": "sleep-pig",
  "metadata": {
    "from": 2,
    "to": 3
  }
}
```

事件使用確定性 ID 去重，同一天重複查看今日結果不會重複記錄。此事件目前主要為後續日報／成就統計預留，不改變收藏權威資料。

EX 還有一支明確的全鏈路 contract test，固定收藏次數 → EX 等級、今日／歷史／週視圖、料理卡、圖片解析、明日預測隔離、事件去重、本地 override，以及壞掉的 active EX 回退 bundled EX。後續重構不能只讓純 resolver 測試通過，卻把真正玩家路徑改壞。

## 8. 本地 EX 視覺化編輯

AstrBot Plugin Page 提供獨立的 **EX 成長管理** 頁，不需要手改 JSON：

- 按小豬搜尋與選擇；
- 分別編輯 EX Lv.1–5；
- 短描述與完整文案留空即繼承；
- 每級可上傳／移除差分圖片；
- 可單獨重設某一級；
- 顯示「實際生效預覽」，直接解析稀疏繼承後真正會看到的描述、文案、圖片與來源。

本地資料分開保存在：

```text
plugin_data/
├─ local_ex_variants.json
└─ local_ex_variants/
   └─ <pig-id>-ex<1-5>.png
```

這個本地 EX store 不和基礎 `local_overrides` 混成一份資料，因此可以獨立驗證、重設與投稿。

## 9. 公共源投稿與審核

EX 公共源工作流使用**投稿 envelope v2**，但正式資源仍是 **Resource Protocol v1**。這兩個版本不要混為一談。

EX-aware 投稿一次包含：

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

安全與相容規則：

- 舊 base-only 投稿仍走既有 envelope v1 路徑；
- EX 投稿只能攜帶目前這一隻小豬的 Lv.1–5 差分；
- EX 圖片固定 `<pig-id>-ex<level>.png`，最多五張；
- 所有引用圖片必須剛好被提交，不能缺圖或夾帶未引用圖片；
- 圖片走既有 decode／normalize 安全流程；
- EX 資料存入 sidecar `submission_ex`，不修改舊 `submissions` schema；
- 審核頁可在批准前查看基礎資料、基礎圖、每級 EX 文案差分與 EX 圖片；
- 拒絕不改動正式 catalog／`v1`；
- 批准時基礎小豬、基礎圖片、EX JSON、EX 圖片先進入同一 candidate catalog，只有 `build_source()` 整包驗證成功後才一起原子發布。

因此不允許出現「基礎豬已發布，但 EX 圖片只上了一半」的狀態。

服務端部署方式與 `app.py` / `app_v2.py` / resource builder 的版本一致性要求見 `deploy/README.md`。

## 10. 完成範圍

EX 產品閉環現在包含：

- EX 差分資料模型與嚴格校驗；
- 稀疏逐欄位繼承；
- 雲端／內建差分載入；
- 非空官方內建 EX 內容；
- v1 manifest 可選 EX 資源；
- 同步安全校驗與原子啟用；
- 玩家展示與 EX 成長事件接入；
- 全鏈路 EX 回歸契約；
- 本地 EX 視覺化編輯與實際生效預覽；
- EX 差分連同基礎小豬一起投稿；
- EX 差分／圖片人工審核；
- 批准後 base + EX 同版原子發布。

「100% 完成」仍以 [`EX-ACCEPTANCE.md`](EX-ACCEPTANCE.md) 的驗收閘門為準：功能 PR 只代表程式碼已具備能力，正式 release 前仍必須確認 stacked PR 全部合併、測試／smoke 通過，以及實際公共源服務已部署新版 `app_v2.py`。
