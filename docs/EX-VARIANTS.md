# EX Lv. 成長與差分契約

EX 差分讓同一隻已解鎖小豬在重複抽取後，隨 `EX Lv.` 使用不同圖片、短描述或完整文案，而不改變小豬 ID、名稱、抽取機率或玩法規則。

本頁同時定義運行時行為、資源來源、覆蓋率口徑與 CI 保證。**「每隻豬都有可用 EX1～EX5」與「每隻豬的五級文案都由人工逐隻撰寫」是兩個不同指標，不得混用。**

## 1. 現況快照（2026-09-02）

目前可以確認的三組數字如下：

| 指標 | 現況 | 代表的意思 |
| --- | ---: | --- |
| 運行／物化 EX 覆蓋 | 進入有效 catalog 的 ID 均可得到 EX1～EX5 | 明確 authoring 不足時，由 deterministic baseline 補齊，因此是可用性指標 |
| bundled lineage 手寫文案 | **99 / 99** | `resource/pig.json` 內 99 隻 bundled 小豬均有專案自有、完整 EX1～EX5 `description`／`analysis` |
| Felis 直讀精修文案 | **22 / 34** | 34 個固定 Felis 直讀 ID 中，22 個已逐圖、逐原義與逐梗精修；其餘 12 個仍使用本倉庫語義種子生成 |

以目前互不重疊的 bundled 與 Felis 直讀範圍計算，已逐隻人工精修的有效總數為 **121**。這個數字不包括 deterministic baseline，也不等於公共豬源全部 ID 的手寫覆蓋率。

因此，對外描述應使用：

- 「所有有效小豬都有可運行的 EX1～EX5」描述**物化覆蓋**；
- 「bundled 99/99 手寫、Felis 22/34 精修」描述**人工內容覆蓋**；
- 公共豬源獨有項應另行按 provenance 與文案審查進度統計，不能沿用舊的 `201/201 全手寫` 說法。

## 2. EX Lv. 如何計算與顯示

本功能不新增玩家存儲欄位，沿用永久圖鑑中的實際抽取次數：

```text
EX Lv. = max(0, count - 1)
```

第一次解鎖為 `EX Lv.0`，第二次抽中為 `EX Lv.1`，依此類推。

玩家等級本身**不封頂**。例如第十次抽中同一隻小豬時，卡面與圖鑑顯示 `EX Lv.9`；目前內容差分只定義 EX1～EX5，因此 EX6 以上繼續沿用最高可用差分，不會把收藏等級偽裝成 EX5。

EX 差分用於玩家已擁有的小豬，包括今日、昨日／歷史、本週、永久圖鑑及相關料理卡。`/明日小豬` 只是預測，不代表已取得明日結果，因此不提前套用玩家收藏等級。

單張靜態卡與 GIF 卡只有在資料明確帶有 `_ex_level` 時才顯示 `EX Lv.n` 徽章：真正的 EX0 會顯示，沒有擁有狀態的預測卡不會被誤標。

## 3. 差分資料模型

每個 EX 等級只允許以下可選欄位：

- `image`
- `description`
- `analysis`

EX 差分不能修改小豬 ID、名稱、抽取權重、保底、熟食／人類／可烤／可吃等玩法標記，也不能改寫玩家收藏次數或其他權威狀態。

資料仍支援逐欄位稀疏繼承。例如：

```json
{
  "schema_version": 1,
  "pigs": {
    "sleep-pig": {
      "2": {
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

EX2 寫入的 `description` 會沿用到更高級，直到後續等級再次覆寫同一欄位；`image` 與 `analysis` 同理。官方 bundled 手寫層要求完整五級，但本地作者與投稿者不需要機械複製沒有變化的欄位。

## 4. 倉庫內的 canonical 來源

目前受版本控制的主要來源是：

```text
resource/
├─ pig.json                         # bundled 99 隻基礎 catalog
├─ image/                           # bundled 基礎圖片
├─ bundled_ex_copy.json             # bundled 手寫文案首個分片
├─ bundled_ex_copy_phase*.json      # bundled 手寫文案後續分片
├─ felis_direct_ex_copy.json        # 34 個 Felis 直讀 ID 的專案自有文字層
└─ ex_variants/                     # 只有被差分明確引用時才存在／使用
```

`bundled_ex_copy*.json` 由 `bundled_ex_copy.py` 合併與驗證，必須：

- 只引用 `resource/pig.json` 中的 ID；
- 每隻完整提供 EX1～EX5；
- 每級同時有非空 `description` 與 `analysis`；
- 五級描述互不相同、五級完整文案互不相同；
- 不包含圖片欄位；
- 不允許不同分片重複定義同一 ID。

以下是 builder 為相容舊輸入仍可理解、但 canonical 倉庫與 Resource Source workflow **禁止提交**的生成／舊 authoring 路徑：

```text
resource/pig_ex_variants.json
resource/ex_curated/
```

它們不能再被文檔寫成目前的正式手寫來源，也不能和發布物中的同名輸出混為一談。

## 5. Resource Source 如何物化

`.github/workflows/resource-source.yml` 會執行：

```text
python scripts/build_resource_source.py \
  --source resource \
  --output dist/astrbot-rollpig-source \
  --version <resource-version>
```

builder 會：

1. 驗證 `resource/pig.json` 與基礎圖片一一對應；
2. 載入 `bundled_ex_copy*.json` 的明確手寫層；
3. 對沒有明確 authoring 的有效 ID 使用 deterministic baseline；
4. 把稀疏資料物化成每隻 EX1～EX5 的單一 Resource Protocol v1 文件；
5. 校驗差分圖片、安全預算、尺寸與解碼；
6. 原子生成完整發布目錄。

目前發布輸出為：

```text
dist/astrbot-rollpig-source/
├─ pig.json
├─ images/
├─ pig_ex_variants.json
├─ ex_variants/
├─ manifest.json
├─ health.json
└─ asset_provenance.json
```

發布物中的 `pig_ex_variants.json` 是**物化結果**，不是倉庫內人工 authoring 的唯一來源。

## 6. CI 實際保證什麼

Resource Source workflow 目前保證：

- canonical `resource/` 不提交 `pig_ex_variants.json` 或 `ex_curated/`；
- 發布版 `pig_ex_variants.json` 的 ID 集合與該次 `pig.json` 完全一致；
- 每個 ID 恰好有 EX1～EX5；
- 五級 `description` 均非空且互不相同；
- 五級 `analysis` 均非空且互不相同；
- manifest 與 health 的 `ex_variant_pig_count` 等於該次 catalog 數量；
- 基礎與差分資源通過圖片、大小、SHA-256、provenance 與整包安全檢查。

這些 gate 證明的是「生成後完整可用」，**不會單憑物化輸出證明每個 ID 都由人工撰寫**。人工覆蓋必須另外由 `bundled_ex_copy*.json`、Felis 精修清單及公共源審查記錄統計。

## 7. 運行時來源優先級與失敗回退

正常展示優先級是：

```text
管理員本地 EX
  → 已驗證的 active cloud／Resource Source EX
  → 內建專案自有 EX 文案
  → deterministic safety baseline
```

具體約束：

- 管理員明確建立的本地 EX 具有最高優先級；
- active cloud EX 必須先通過 schema、ID、圖片與完整包校驗，損壞資料不得半套生效；
- 雲端 EX 無效或缺失時回退內建 authoring，再不足才使用安全 baseline；
- 管理員只覆蓋某隻豬的基礎資料、但沒有建立本地 EX 時，公共 EX 不得偷偷改寫該本地豬；
- Felis 直讀層只使用本倉庫維護的文字規格，不讀取 Felis 上游 EX／variant 文案或圖片。

## 8. 本地 EX 管理

AstrBot Plugin Page 的 EX 成長工作區可：

- 搜尋與選擇小豬；
- 分別編輯 EX1～EX5；
- 編輯短描述、完整文案與差分圖片；
- 以留空方式使用本地稀疏繼承；
- 單獨重設某一級；
- 查看實際生效預覽。

本地資料保存在：

```text
plugin_data/
├─ local_ex_variants.json
└─ local_ex_variants/
   └─ <pig-id>-ex<1-5>.<ext>
```

本地資料不會因公共資源同步而被覆蓋。

## 9. 升級事件與回歸範圍

玩家當天真正完成重複抽取並形成 EX 成長時，首次成功寫入 Gameplay Event v1 `ex_level_up` 會在今日小豬圖片前顯示一次 `✨ 重逢第 N 次 · EX Lv.a → Lv.b`。事件 ID 會跨群聊與私聊作用域確定性去重，因此同一天換群或重複查看不能再次顯示；私聊事件只保存到 `private:<user-id>` 作用域，不會混入任何群組日報。事件寫入失敗、首次解鎖、查看他人、過期抽取與明日預測均不顯示升級提示。

回歸測試應至少固定：

- `count` 到 EX 等級的換算；
- EX0、EX1、EX5 與 EX5 以上的展示；
- 今日、歷史、本週、圖鑑與料理卡套用；
- 靜態卡與 GIF 卡的等級徽章；
- 明日預測隔離；
- 稀疏欄位繼承與最高級回退；
- active cloud 損壞時回退 bundled；
- 本地基礎覆蓋隔離與本地 EX 最高優先級；
- `ex_level_up` 去重。

## 10. 覆蓋率更新規則

每次增刪 catalog、完成一批人工文案或調整 Felis allowlist 時，維護者應分別更新：

1. **catalog 數量**：當前被統計範圍有多少 ID；
2. **物化覆蓋率**：其中多少 ID 能生成完整 EX1～EX5；
3. **人工文案覆蓋率**：其中多少 ID 的五級內容經逐隻人工審查；
4. **差分圖片覆蓋率**：其中多少 ID／等級有獨立圖片；
5. **來源範圍**：bundled、Felis 直讀與公共豬源必須分開列示。

不得以「CI 生成後 100%」替代「人工文案 100%」，也不得把過去 compatibility catalog 的舊總數直接套到目前 bundled catalog、Felis allowlist 或公共豬源。

最後更新：2026-09-02
