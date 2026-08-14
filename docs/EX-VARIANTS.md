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

## 4. 資源目錄

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

## 6. 顯示規則

EX 差分用於玩家**已擁有**的小豬展示，包括今日／歷史／週視圖、永久圖鑑及相關烤豬卡片所使用的玩家當前收藏等級。

`/明日小豬` 是預測，不代表玩家已擁有明日結果，因此不套用玩家目前的 EX 差分。

管理員本地 override 的優先級高於 AstrBot／私人源的 EX 差分：只要某個 ID 有本地資料 override，就不會再用遠端或內置 EX 文案；有本地自訂圖片時也永遠優先使用本地圖片。這保持 v3.3+ 的「本地修改不被同步偷偷覆蓋」原則。

## 7. Gameplay Event

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

## 8. 目前範圍

本階段完成的是：

- EX 差分資料模型與嚴格校驗；
- 稀疏逐欄位繼承；
- 遠端／內置差分載入；
- v1 manifest 可選 EX 資源；
- 同步安全校驗與原子啟用；
- 玩家展示與 EX 成長事件接入。

**尚未包含**管理面板的視覺化 EX 編輯器，以及把 EX 差分連同基礎小豬一起投稿／審核到公共源的 UI 工作流。這些會在運行時格式穩定後再建立，避免讓公共源審核協議和核心格式同時變動。
