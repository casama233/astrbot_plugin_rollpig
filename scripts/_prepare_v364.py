from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, count: int | None = None) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    actual = text.count(old)
    expected = actual if count is None else count
    if actual != expected or actual == 0:
        raise SystemExit(f"{path}: expected {expected} matches for {old!r}, got {actual}")
    target.write_text(text.replace(old, new), encoding="utf-8")


replace("metadata.yaml", 'version: "3.6.3"', 'version: "3.6.4"', count=1)
replace(
    "legacy_main.py",
    "AstrBot-RollPig/3.6.3 (+https://github.com/casama233/astrbot_plugin_rollpig)",
    "AstrBot-RollPig/3.6.4 (+https://github.com/casama233/astrbot_plugin_rollpig)",
    count=1,
)
replace(
    "legacy_main.py",
    '"X-RollPig-Version": "3.6.3"',
    '"X-RollPig-Version": "3.6.4"',
    count=1,
)
replace(
    "updater.py",
    "AstrBot-RollPig-Safe-Updater/3.6.3",
    "AstrBot-RollPig-Safe-Updater/3.6.4",
    count=1,
)
replace(
    "tests/test_v312_release_contract.py",
    'assert \'version: "3.6.3"\' in metadata',
    'assert \'version: "3.6.4"\' in metadata',
    count=1,
)
replace(
    "tests/test_v312_release_contract.py",
    'assert "AstrBot-RollPig/3.6.3" in main',
    'assert "AstrBot-RollPig/3.6.4" in main',
    count=1,
)
replace(
    "tests/test_v312_release_contract.py",
    'assert "AstrBot-RollPig-Safe-Updater/3.6.3" in updater',
    'assert "AstrBot-RollPig-Safe-Updater/3.6.4" in updater',
    count=1,
)
replace(
    "tests/test_identity_migration_plus.py",
    'assert \'version: "3.6.3"\' in metadata',
    'assert \'version: "3.6.4"\' in metadata',
    count=1,
)
replace(
    "tests/test_source_regressions.py",
    'assert \'version: "3.6.3"\' in metadata',
    'assert \'version: "3.6.4"\' in metadata',
    count=1,
)
replace(
    "tests/test_source_regressions.py",
    'assert "AstrBot-RollPig/3.6.3" in SOURCE',
    'assert "AstrBot-RollPig/3.6.4" in SOURCE',
    count=1,
)

readme = ROOT / "README.md"
text = readme.read_text(encoding="utf-8")
text = text.replace("current-3.6.3-ef5d82", "current-3.6.4-ef5d82", 1)
start = text.index("## 3.6.3 版本亮點")
end = text.index("\n完整變更請閱讀", start)
new_highlight = """## 3.6.4 版本亮點

| 修復 | 說明 |
| --- | --- |
| 🐷 公共豬源兼容恢復 | 修復 v3.4 切換預設資源源時只帶入 99 隻小豬的內容縮水；官方源現在以切源前固定 199-ID 快照作兼容下限，再疊加 AstrBot 現有內容 |
| 🖼️ QQ 圖鑑投遞修復 | NapCat/NTQQ 已把 `/我的豬圈` 圖片送達、但 `sendMsg` ACK 超時返回 retcode=1200 時，不再誤報「圖鑑生成失敗」或重試造成重複圖片 |
| 📚 永久頁碼修復 | `/我的豬圈` 頁數校驗改以永久 display catalog 為準，歷史保留卡存在時最後頁不會被 active catalog 頁數提前擋掉 |
"""
text = text[:start] + new_highlight + text[end:]
text = text.replace("**v3.2.0+ → v3.6.3**", "**v3.2.0+ → v3.6.4**", 1)
text = text.replace("**v3.1.4 或更早增強版 → v3.6.3**", "**v3.1.4 或更早增強版 → v3.6.4**", 1)
readme.write_text(text, encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
text = changelog.read_text(encoding="utf-8")
needle = "## 未發佈\n\n- 暫無。\n\n## v3.6.3"
section = """## 未發佈

- 暫無。

## v3.6.4 (2026-08-14)

### 版本主題：公共豬源兼容與 QQ 圖鑑投遞修復

### 修復

- 修復 v3.4.0 將舊 Felis 預設資源源切換到 AstrBot 專用源時，只以內置 99 隻小豬建立首版來源造成的內容縮水；固定 v3.4 cut-over 前最後一個 Felis RollPig 快照（199 IDs）作 compatibility floor，官方源必須保持其超集，同 ID 仍以目前 AstrBot canonical 資料與圖片為準。
- 新增公共源兼容建構與 live canonical 原子遷移工具；CI 固定舊快照 commit / resource version / pig.json SHA-256，禁止跟隨可變 Felis main，並以 `miku-pig`、`wechat-pig`、`duke-pig` 作回歸哨兵。
- 修復 QQ/NapCat/NTQQ 已實際送達 `/我的豬圈` 圖片，但等待 `NodeIKernelMsgService/sendMsg` 回執超時返回 `retcode=1200` 時，被誤報為「圖鑑圖片生成失敗」；此類 ACK timeout 現在視為投遞結果不確定，只記 warning、不重試、不發失敗提示，避免重複圖片。
- `/我的豬圈` 將圖片渲染與消息投遞錯誤分離；真正 render error 與真正 send error 使用不同提示，且頁碼範圍改按永久 display catalog 計算。

### 相容性

- 可由 **v3.6.3 直接升級**；不修改 SQLite schema、玩家 ownership、EX count、保底、烤豬概率或 Resource Protocol 版本。
- PR #68 identity-fragment merge 仍未包含；本版不引入烤箱 charge/refill 等新玩法。

## v3.6.3"""
if needle not in text:
    raise SystemExit("CHANGELOG release insertion point missing")
changelog.write_text(text.replace(needle, section, 1), encoding="utf-8")

notes = ROOT / ".github" / "release-v3.6.4.md"
notes.write_text(
    """# 今日小豬 · 增強版 v3.6.4

這是一個穩定性 patch，集中修復公共豬源切換造成的歷史內容縮水，以及 QQ/NapCat/NTQQ 圖片已送達後 ACK timeout 被誤判失敗的問題。

## 修復

- 恢復 v3.4 切源前完整兼容下限：固定 Felis `17ac1586a91c33995883803a55e2f755047f6e1f` 快照的 199 個 ID 作為官方源最低兼容集合；目前 AstrBot canonical 同 ID 內容優先。
- 官方 Resource Source CI 現在會拒絕任何低於固定 compatibility floor 的發布，並驗證 `miku-pig`、`wechat-pig`、`duke-pig` 等回歸哨兵。
- `/我的豬圈` 對 NTQQ `retcode=1200`、`NodeIKernelMsgService/sendMsg` ACK timeout 不再重試或誤報「生成失敗」；圖片可能已經投遞時只記錄 warning。
- 真正的圖鑑渲染失敗與真正的圖片發送失敗分開處理；永久圖鑑頁碼按完整 display catalog 校驗。

## 升級

可由 v3.6.3 直接更新。無 SQLite migration，無玩家收藏重建，無 EX / 保底 / 烤豬概率變更。

本版仍不包含 PR #68 identity-fragment merge，也不包含烤箱 charge/refill 新玩法。
""",
    encoding="utf-8",
)

print("v3.6.4 release files prepared")
