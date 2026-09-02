from __future__ import annotations

import json
from pathlib import Path


ROOT = Path.cwd()


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one replacement, found {count}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


resource_path = ROOT / "resource/felis_direct_ex_copy.json"
payload = json.loads(resource_path.read_text(encoding="utf-8-sig"))
pigs = payload.get("pigs")
if not isinstance(pigs, dict) or len(pigs) != 34:
    raise SystemExit("Felis authoring pack must contain exactly 34 pigs")
for pig_id, spec in pigs.items():
    if not isinstance(spec, dict) or set(spec) != {"levels"}:
        raise SystemExit(f"{pig_id}: legacy/non-explicit Felis authoring remains")
    levels = spec.get("levels")
    if not isinstance(levels, dict) or set(map(str, levels)) != {"1", "2", "3", "4", "5"}:
        raise SystemExit(f"{pig_id}: incomplete EX1-EX5 authoring")
    for level, item in levels.items():
        if not isinstance(item, dict) or set(item) != {"description", "analysis"}:
            raise SystemExit(f"{pig_id} EX{level}: invalid explicit fields")
        if not all(str(value).strip() for value in item.values()):
            raise SystemExit(f"{pig_id} EX{level}: blank explicit copy")

payload["schema_version"] = 3
provenance = payload.get("provenance")
if not isinstance(provenance, dict):
    raise SystemExit("Felis authoring pack missing provenance")
provenance["authoring_mode"] = "explicit-ex1-ex5"
provenance["handwritten_id_count"] = len(pigs)
resource_path.write_text(
    json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
    encoding="utf-8",
)

replace_once(
    "docs/EX-VARIANTS.md",
    "| Felis 直讀精修文案 | **22 / 34** | 34 個固定 Felis 直讀 ID 中，22 個已逐圖、逐原義與逐梗精修；其餘 12 個仍使用本倉庫語義種子生成 |",
    "| Felis 直讀手寫文案 | **34 / 34** | 34 個固定 Felis 直讀 ID 均已逐圖、逐原義與逐梗審查，完整顯式提供 EX1～EX5 `description`／`analysis`；運行時不再接受語義種子模板 |",
)
replace_once(
    "docs/EX-VARIANTS.md",
    "以目前互不重疊的 bundled 與 Felis 直讀範圍計算，已逐隻人工精修的有效總數為 **121**。這個數字不包括 deterministic baseline，也不等於公共豬源全部 ID 的手寫覆蓋率。",
    "以目前互不重疊的 bundled 與 Felis 直讀範圍計算，已逐隻人工精修的有效總數為 **133**（99 + 34），共 **665** 組 EX1～EX5 `description`／`analysis`。這個數字不包括 deterministic baseline，也不等於公共豬源全部 ID 的手寫覆蓋率。",
)
replace_once(
    "docs/EX-VARIANTS.md",
    "- 「bundled 99/99 手寫、Felis 22/34 精修」描述**人工內容覆蓋**；",
    "- 「bundled 99/99 手寫、Felis 34/34 手寫」描述**人工內容覆蓋**；",
)
replace_once(
    "docs/EX-VARIANTS.md",
    "├─ felis_direct_ex_copy.json        # 34 個 Felis 直讀 ID 的專案自有文字層",
    "├─ felis_direct_ex_copy.json        # Felis 34/34 顯式手寫 EX1～EX5 文字層",
)
replace_once(
    "docs/EX-VARIANTS.md",
    "- 不允許不同分片重複定義同一 ID。\n\n以下是 builder 為相容舊輸入仍可理解、但 canonical 倉庫與 Resource Source workflow **禁止提交**的生成／舊 authoring 路徑：",
    "- 不允許不同分片重複定義同一 ID。\n\n`felis_direct_ex_copy.json` 由 `felis_ex_copy.py` 驗證，採用 schema v3，並額外要求：\n\n- `pigs` 的 ID 集合與固定 `FELIS_DIRECT_IDS` 完全一致；\n- 34 隻全部以 `levels` 顯式提供 EX1～EX5，不接受 `name/theme/progress/lesson` 語義種子；\n- provenance 必須聲明 `authoring_mode=explicit-ex1-ex5`、`handwritten_id_count=34` 與 `upstream_ex_used=false`；\n- 只保存本倉庫撰寫的文字，不讀取或攜帶 Felis 上游 EX／variant 文案與圖片。\n\n以下是 builder 為相容舊輸入仍可理解、但 canonical 倉庫與 Resource Source workflow **禁止提交**的生成／舊 authoring 路徑：",
)
replace_once(
    "docs/EX-VARIANTS.md",
    "- Felis 直讀層只使用本倉庫維護的文字規格，不讀取 Felis 上游 EX／variant 文案或圖片。",
    "- Felis 直讀層只使用本倉庫維護的 34/34 顯式五級手寫文字，不接受語義種子模板，也不讀取 Felis 上游 EX／variant 文案或圖片。",
)
replace_once(
    "docs/EX-VARIANTS.md",
    "- `ex_level_up` 去重。",
    "- `ex_level_up` 去重；\n- Felis 34/34 顯式五級集合、schema v3 provenance 與舊語義種子拒絕。",
)

replace_once(
    "CHANGELOG.md",
    "- EX 覆蓋率文件契約修正：重寫 `docs/EX-VARIANTS.md`，明確區分所有有效小豬可物化的 EX1～EX5 運行覆蓋、bundled 99/99 手寫文案與 Felis 22/34 精修文案；同步移除已刪除／禁止提交的舊 authoring 路徑與 `201/201 全手寫` 說法，改為現行 `scripts/build_resource_source.py` 及 Resource Source workflow 契約。",
    "- EX 覆蓋率文件契約修正：重寫 `docs/EX-VARIANTS.md`，明確區分所有有效小豬可物化的 EX1～EX5 運行覆蓋、bundled 99/99 手寫文案與 Felis 34/34 顯式五級手寫文案；同步移除已刪除／禁止提交的舊 authoring 路徑與 `201/201 全手寫` 說法，改為現行 `scripts/build_resource_source.py` 及 Resource Source workflow 契約。",
)
replace_once(
    "CHANGELOG.md",
    "- Felis 34 項直讀資源的專案自有 EX1–EX5 文案層已完成前三批逐豬精修：目前 22 隻按基礎圖片、原始語義與實際網路梗逐級手寫，其餘 12 隻繼續由本倉庫語義種子生成；不讀取 Felis EX/variant 文案或圖片，固定 allowlist、provenance 與 text-only 合約維持不變。",
    "- Felis 34 項直讀資源的專案自有 EX1–EX5 文案層已完成全量逐豬精修：34/34 均按基礎圖片、原始語義與實際網路梗顯式手寫五級 `description`／`analysis`；schema 升至 v3，移除 `name/theme/progress/lesson` 語義種子生成通道，並以 `authoring_mode=explicit-ex1-ex5`、`handwritten_id_count=34`、固定 allowlist、provenance 與 text-only 回歸合約防止模板回退。",
)
replace_once(
    "CHANGELOG.md",
    "## 未發佈\n\n- 今日小豬新增一次性 EX 成長提示：",
    "## 未發佈\n\n- Felis 直讀 EX 文案契約收斂為 34/34 顯式手寫：補正過期的 22/34 文件口徑，將 `felis_direct_ex_copy.json` 升為 schema v3，並在運行時拒絕舊語義種子模板，避免 generated fallback 再被誤算為人工精修。\n\n- 今日小豬新增一次性 EX 成長提示：",
)
