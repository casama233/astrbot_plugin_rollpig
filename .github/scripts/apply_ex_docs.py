from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"documentation anchor not found: {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# README: make the collection growth capability visible without claiming the
# still-planned visual admin authoring flow.
replace_once(
    "README.md",
    "- **永久豬圈圖鑑**：記錄解鎖種類、抽取次數、本命豬與 `EX Lv.`。",
    "- **永久豬圈圖鑑**：記錄解鎖種類、抽取次數、本命豬與 `EX Lv.`；資源包可為 EX Lv.1–5 提供稀疏立繪／描述／文案差分。",
)
replace_once(
    "README.md",
    "完整變更請閱讀 [CHANGELOG](CHANGELOG.md)；使用方式見 [資源管理手冊](docs/RESOURCE-MANAGEMENT.md)，發佈與回退流程見 [豬源維護手冊](docs/RESOURCE-SOURCE-MAINTENANCE.md)。",
    "完整變更請閱讀 [CHANGELOG](CHANGELOG.md)；EX 成長格式見 [EX 差分手冊](docs/EX-VARIANTS.md)，資源使用方式見 [資源管理手冊](docs/RESOURCE-MANAGEMENT.md)，發佈與回退流程見 [豬源維護手冊](docs/RESOURCE-SOURCE-MAINTENANCE.md)。",
)

# Resource management: document v1 optional extension and priority boundary.
replace_once(
    "docs/RESOURCE-MANAGEMENT.md",
    "下載的是目前真正生效的圖片：本地圖片優先，其次 AstrBot／私人源，最後才是內置資源。",
    "下載的是目前真正生效的圖片：本地圖片優先，其次 AstrBot／私人源的 EX／基礎圖片，最後才是內置資源。只要某 ID 存在本地資料 override，遠端／內置 EX 文案差分也不會蓋過本地內容。",
)
marker = """對應 `pig.json`：

```json
[
  {
    \"id\": \"pig\",
    \"name\": \"小豬\",
    \"description\": \"普通但可靠\",
    \"analysis\": \"今天適合把簡單的事情做好。\"
  }
]
```

### 必要條件
"""
replacement = marker.replace(
    "\n### 必要條件\n",
    """

### 可選 EX Lv. 差分

Resource Protocol v1 可選增加 `pig_ex_variants.json` 與 `ex_variants/`。manifest 對應增加 `ex_variants` 檔案 metadata 及 `variant_images` 陣列；沒有這些欄位的既有 v1／私人來源仍然有效。

EX Lv.1–5 可分別覆蓋圖片、描述或完整文案，未配置欄位會向較低等級繼承。差分不允許修改 ID、名稱或玩法規則。完整格式與顯示語義見 [`EX-VARIANTS.md`](EX-VARIANTS.md)。

差分 JSON 與圖片會和基礎資源一起執行大小、SHA-256、解碼、整包預算與 staging 校驗；任一差分失敗時不會切換 active 資源。

### 必要條件
""",
)
replace_once("docs/RESOURCE-MANAGEMENT.md", marker, replacement)
replace_once(
    "docs/RESOURCE-MANAGEMENT.md",
    "- manifest 最多 500 張圖片，整包聲明大小不得超過 128 MiB。",
    "- 基礎 manifest 最多 500 張圖片；可選 EX 差分最多 1000 張圖片，基礎與差分合計仍受 128 MiB 整包上限限制。",
)

# Source maintenance: builders/deployers need to know the extra optional files.
replace_once(
    "docs/RESOURCE-SOURCE-MAINTENANCE.md",
    """manifest.json
health.json
pig.json
images/
  pig.png
  ...
""",
    """manifest.json
health.json
pig.json
images/
  pig.png
  ...
# 可選 EX 成長差分
pig_ex_variants.json
ex_variants/
  pig-ex2.png
  ...
""",
)
replace_once(
    "docs/RESOURCE-SOURCE-MAINTENANCE.md",
    "插件仍向下兼容未聲明 `schema_version`／`client` 的私人 manifest；本專案預設源則強制要求兩者正確。",
    "插件仍向下兼容未聲明 `schema_version`／`client` 的私人 manifest；本專案預設源則強制要求兩者正確。EX 成長使用 v1 的可選 `ex_variants`／`variant_images` 欄位，不需要提升協議版本；舊來源不提供時維持基礎圖與文案。",
)
replace_once(
    "docs/RESOURCE-SOURCE-MAINTENANCE.md",
    "- 超過 500 張圖片的來源。",
    "- 超過 500 張基礎圖片，或超過 1000 張 EX 差分圖片的來源。\n- EX 差分引用未知小豬、超出 Lv.1–5、使用非法欄位、缺圖或存在未引用差分圖片。",
)
replace_once(
    "docs/RESOURCE-SOURCE-MAINTENANCE.md",
    "全部通過後才會原子建立輸出目錄，並為 `pig.json` 與每張圖片生成大小和 SHA-256。",
    "全部通過後才會原子建立輸出目錄，並為 `pig.json`、可選 `pig_ex_variants.json` 與每張基礎／差分圖片生成大小和 SHA-256。",
)

# Unreleased changelog: keep architecture entry and add user-facing feature.
replace_once(
    "CHANGELOG.md",
    "## 未發佈\n\n### 架構\n",
    """## 未發佈

### 新功能

- 新增 EX Lv.1–5 稀疏成長差分：同一隻小豬可按玩家既有 `count - 1` EX 等級替換圖片、描述或完整文案，各欄位獨立向下繼承；EX 5 以上沿用最後有效差分。
- AstrBot Resource Protocol v1 增加可選 `pig_ex_variants.json`／`variant_images`，仍沿用大小、SHA-256、圖片解碼、128 MiB 預算、staging 與原子切換；舊 v1／私人來源不需要修改。
- 本地小豬 override 仍高於遠端／內置 EX 差分；`/明日小豬` 預測不套用玩家已擁有的 EX 成長，避免把收藏狀態洩漏到未來結果。
- 群聊本人重複抽取可寫入去重的 `ex_level_up` Gameplay Event，為後續日報與成就統計提供資料，不改變收藏權威狀態。
- 新增 [`docs/EX-VARIANTS.md`](docs/EX-VARIANTS.md) 說明格式、繼承、安全邊界與目前尚未包含的管理面板 EX 編輯／投稿範圍。

### 架構
""",
)
