# EX Lv. 成長差分

EX 差分讓同一隻已解鎖小豬在重複抽取後，隨既有 `EX Lv.` 顯示不同圖片、描述或完整文案，而不改變小豬 ID、名稱、抽取機率或玩法規則。

## 1. EX Lv. 如何計算

本功能**不新增玩家存儲欄位**。沿用永久圖鑑原本的抽取次數：

```text
EX Lv. = max(0, count - 1)
```

第一次解鎖為 `EX Lv.0`；第二次抽中為 `EX Lv.1`，依此類推。玩家 EX 等級可以高於 5，但資源差分目前只配置 `EX Lv.1`～`EX Lv.5`；高於 5 時繼續使用 Lv.5 的最後有效差分。

## 2. 官方 201 隻全部精品手寫

目前正式官方目錄合併後共 **201 隻小豬**：

- bundled 主目錄：99 隻；
- 凍結 pre-v3.4 compatibility floor 恢復：102 隻；
- 人工 curated EX 覆蓋：**201 / 201**。

這 201 隻不是靠統一模板加等級後綴，也不是由生成器臨時補文案。每一隻都明確 authoring：

- EX1、EX2、EX3、EX4、EX5 五級；
- 五句互不相同的 `description`；
- 五段互不相同的 `analysis`；
- 文案沿著該角色原本的梗、性格或設定形成連續的五段成長弧。

例如有的角色從「只會整活」逐步成長到「能控制整活的邊界」，有的從「被動適應」走到「主動選擇」，也有純喜劇角色一路把原始梗養成穩定招牌。EX 因此不是只換一句形容詞，而是在重複抽取時真正多一段角色內容。

### Authoring 結構

為了避免把 201 × 5 級內容塞進一個難維護的巨型 JSON，官方 authoring 分成：

```text
resource/
├─ pig.json
├─ pig_ex_variants.json       # 最早 10 隻精品手寫
├─ ex_curated/
│  ├─ 01-origin-and-classics.json
│  ├─ 02-life-and-personality.json
│  ├─ ...
│  └─ 10-compat-final-curated-pack.json
├─ image/
└─ ex_variants/               # 可選 EX 圖片
```

`pig_ex_variants.json` 與 `ex_curated/*.json` 使用同一套 schema。正式 Resource Source builder 會在發布前合併它們，最後只輸出一份標準的 `pig_ex_variants.json` 給客戶端，因此 **Resource Protocol 不需要知道 authoring pack 的存在**。

bundled 插件本地只有 99 隻主目錄豬，所以載入 `ex_curated/` 時會只取當前 `pig_list` 存在的 ID；那 102 隻 compatibility-only 文案會等 Resource Source 合併出完整 201 隻 catalog 後再一起物化。

## 3. 生成基線現在只是一層安全兜底

程式仍保留確定性的五級 baseline generator，原因是：

- 本地自建小豬可能沒有官方 curated 文案；
- 測試 fixture / 非官方資源需要向後兼容；
- 未來新 ID 在內容尚未補齊時不應直接讓展示崩潰。

但對**正式官方 release**，生成基線不算完成內容。CI 會在 builder 之前先檢查 authoring corpus：

```text
handcrafted EX IDs == official merged pig IDs
```

目前必須是：

```text
201 == 201
```

而且每一隻都必須明確有 Lv1～Lv5、五個不同描述、五段不同完整文案。只要新增官方豬卻沒有補精品手寫 EX，Resource Source gate 會直接失敗，即使生成器理論上能兜底也不能放行正式發布。

## 4. 創作者仍可使用稀疏覆寫

官方全量精品內容不改變原本的稀疏 EX 協議。自訂／本地／投稿作者仍然只需要寫真正改變的部分，例如：

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

圖片、`description`、`analysis` 仍採**逐欄位向高級繼承**：EX2 寫了 `description`，它會沿用到更高級，直到後面再次覆寫 `description`；其他欄位同理。

因此「官方 201 隻全部手寫五級」是官方內容品質要求，不會強迫第三方作者也機械複製五份資料。

## 5. 可修改與不可修改欄位

每個 EX 等級只允許 `image`、`description`、`analysis`。EX 差分**不能**修改：

- 小豬 ID / 名稱；
- 抽取權重與保底；
- 熟食、人類、可烤、可吃等玩法規則；
- 玩家收藏次數與其他權威狀態。

因此 EX 成長是展示與收藏層，不會讓同一 ID 在高等級突然變成另一個玩法實體。

## 6. 發布物化與 Resource Protocol v1

正式 Resource Source 流程先合併 bundled 主 catalog 與凍結 compatibility floor，再保留 `ex_curated/` authoring packs，最後由 builder：

1. 驗證 base authoring + curated packs 沒有重複 ID；
2. 驗證官方 handcrafted ID 集合與合併後 `pig.json` **完全相等**；
3. 驗證每隻恰好 EX1～EX5；
4. 驗證五級描述與五級完整文案均非空且各不相同；
5. 合併任何 EX 圖片與稀疏欄位繼承；
6. 物化成單一發布版 `pig_ex_variants.json`；
7. 寫入 manifest / health 的 EX 覆蓋統計。

正式發布要求：

```text
ex_variant_pig_count == pig_count == 201
```

EX 仍使用 **AstrBot Resource Protocol v1 的可選欄位**，不提升 `schema_version`。manifest 可包含：

```json
{
  "ex_variant_pig_count": 201,
  "ex_variants": {
    "path": "pig_ex_variants.json",
    "size": 1234,
    "sha256": "..."
  },
  "variant_images": []
}
```

差分 JSON 與圖片和基礎資源一樣走大小、SHA-256、圖片解碼、整包預算、staging 與原子切換校驗。任何 EX 差分驗證失敗時，不會用半套內容覆蓋目前 active 資源。

## 7. 顯示規則與優先級

EX 差分用於玩家**已擁有**的小豬展示，包括今日／歷史／週視圖、永久圖鑑及相關料理卡片。

`/明日小豬` 是預測，不代表玩家已擁有明日結果，因此不提前套用玩家目前的 EX 收藏成長。

官方／公共來源優先級仍是：

```text
雲端 EX → 內建 curated EX → 安全 baseline
```

安全 baseline 對官方 201 隻正常情況下不應被用到；它只負責非官方／本地／未完整資料的容錯。

若管理員只覆蓋某隻小豬的基礎資料而沒有建立本地 EX，公共 EX 不會偷偷改寫該本地豬；管理員明確建立本地 EX 後，本地 EX 仍取得最高展示優先級。

## 8. Gameplay Event 與回歸 Gate

玩家完成當天重複抽取並形成 `EX Lv.` 成長時，插件可記錄 Gameplay Event v1 `ex_level_up`。事件使用確定性 ID 去重，同一天重複查看今日結果不會重複記錄。

全鏈路 contract test 固定：收藏次數 → EX 等級、今日／歷史／週視圖、料理卡、圖片解析、明日預測隔離、事件去重、本地 override，以及壞掉的 active EX 回退 bundled EX。

內容 gate 額外固定：

- base + 10 個 curated documents 無重複 ID；
- 原始 10 隻 + 新增 191 隻 = 201 隻 explicit handcrafted；
- bundled 99 隻全部在 handcrafted 集合；
- compatibility-only 102 隻全部在 handcrafted 集合；
- 每隻恰好 Lv1～Lv5；
- 五級 `description` 各不相同；
- 五級 `analysis` 各不相同；
- Resource Source 合併後 handcrafted set == `pig.json` set；
- manifest / health 的 `ex_variant_pig_count == pig_count`。

## 9. 本地 EX 視覺化編輯

AstrBot Plugin Page 提供獨立的 **EX 成長管理** 頁，不需要手改 JSON：

- 按小豬搜尋與選擇；
- 分別編輯 EX Lv.1–5；
- 短描述與完整文案留空即按本地稀疏規則繼承；
- 每級可上傳／移除差分圖片；
- 可單獨重設某一級；
- 顯示「實際生效預覽」。

本地資料保存在：

```text
plugin_data/
├─ local_ex_variants.json
└─ local_ex_variants/
   └─ <pig-id>-ex<1-5>.png
```

## 10. 公共源投稿與審核

EX 公共源工作流使用**投稿 envelope v2**，正式資源仍是 **Resource Protocol v1**。兩個版本彼此獨立。

EX-aware 投稿一次包含基礎 record／圖片、`ex_variants` 與可選 `variant_images`。公開契約保證：

- 舊 base-only 投稿保持 envelope v1 相容；
- EX 投稿只能攜帶目前小豬的 Lv.1–5 差分；
- EX 圖片固定 `<pig-id>-ex<level>.png`，最多五張；
- 引用圖片與實際提交集合必須完全一致；
- 審核員可在批准前查看基礎資料／圖片與每級 EX 差分／圖片；
- reject 不改動目前正式資源；
- approve 只有在 base + EX 整包驗證成功後才發布成同一個新 resource version。

通用 builder 對沒有完整 EX 的非官方／投稿候選仍有安全 baseline，避免協議斷裂；但一個 ID 若要正式納入**官方 curated catalog**，仍必須補完明確的五級精品文案才能通過官方 handcrafted gate。

因此不允許出現「官方基礎豬已納入 release，但精品 EX 內容仍靠生成兜底」的狀態。

> 公共源服務端實作、持久化細節、反向代理與 production 部署配置由私有運維倉庫維護。公開倉庫承諾客戶端／投稿契約與 Resource Protocol 行為。

## 11. 完成範圍

EX 產品閉環現在包含：差分資料模型、**201 隻官方豬的五級精品手寫文案**、安全 baseline、稀疏覆寫、Resource Protocol v1 EX 資源、同步安全校驗、玩家展示、Gameplay Event、本地視覺化編輯、EX 公共投稿／人工審核，以及 base + EX 同版發布契約。

production 是否完成仍以 [`EX-ACCEPTANCE.md`](EX-ACCEPTANCE.md) 的真實部署／同步 smoke gate 為準；「倉庫內 201/201 全手寫」不等於宣稱尚未執行的 production 部署已完成。
