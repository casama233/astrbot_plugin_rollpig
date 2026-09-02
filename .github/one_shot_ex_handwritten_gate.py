from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def replace_exact(path: str, old: str, new: str, *, expected: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(
            f"{path}: expected {expected} replacements, found {count}: {old[:120]!r}"
        )
    target.write_text(text.replace(old, new), encoding="utf-8")


replace_exact(
    "docs/EX-VARIANTS.md",
    "Resource Source workflow 目前保證：\n\n"
    "- canonical `resource/` 不提交 `pig_ex_variants.json` 或 `ex_curated/`；",
    "Resource Source workflow 目前保證：\n\n"
    "- builder 啟動前先執行 `scripts/check_ex_handwritten_coverage.py`，直接核對 canonical authoring，不讀取 `dist/` 或任何物化輸出；\n"
    "- merged `bundled_ex_copy*.json` 必須與 `resource/pig.json` 達成 99/99 精確覆蓋，缺 ID、未知 ID 或跨分片重複均失敗；\n"
    "- `felis_direct_ex_copy.json` 必須與靜態 `FELIS_DIRECT_IDS` 達成 34/34 精確覆蓋，並維持 schema v3、顯式五級及 provenance 契約；\n"
    "- canonical `resource/` 不提交 `pig_ex_variants.json` 或 `ex_curated/`；",
)
replace_exact(
    "docs/EX-VARIANTS.md",
    "這些 gate 證明的是「生成後完整可用」，**不會單憑物化輸出證明每個 ID 都由人工撰寫**。人工覆蓋必須另外由 `bundled_ex_copy*.json`、Felis 精修清單及公共源審查記錄統計。",
    "生成物校驗證明的是「生成後完整可用」；獨立的 handwritten gate 則只承認 `bundled_ex_copy*.json`、`felis_direct_ex_copy.json` 與靜態 allowlist 等 canonical 輸入。即使 deterministic baseline 能把發布物補成 100%，只要 canonical authoring 少一隻、混入舊語義種子或 provenance／分片不一致，CI 仍會在 builder 前失敗，因此 generated fallback 不得再被計入人工覆蓋。公共豬源獨有項仍須另按 provenance 與文案審查記錄統計。",
)

replace_exact(
    "CHANGELOG.md",
    "## 未發佈\n\n- Felis 直讀 EX 文案契約收斂為 34/34 顯式手寫：",
    "## 未發佈\n\n"
    "- 新增 canonical EX 手寫覆蓋閘門 `scripts/check_ex_handwritten_coverage.py`：一般 CI 與 Resource Source 均直接比對 bundled 99/99、Felis 34/34 的顯式 authoring、固定 allowlist、分片與 provenance，且必須在 deterministic baseline 物化前通過；另以反例測試證明即使 `dist/pig_ex_variants.json` 完整，canonical 少一隻仍會失敗。\n\n"
    "- Felis 直讀 EX 文案契約收斂為 34/34 顯式手寫：",
)
