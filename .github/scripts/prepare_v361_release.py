from __future__ import annotations

import re
from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor in {path}: {old!r}; got {count}")
    write(path, text.replace(old, new, 1))


replace_once("metadata.yaml", 'version: "3.6.0"', 'version: "3.6.1"')
replace_once("legacy_main.py", "AstrBot-RollPig/3.6.0", "AstrBot-RollPig/3.6.1")
replace_once(
    "legacy_main.py",
    '"X-RollPig-Version": "3.6.0"',
    '"X-RollPig-Version": "3.6.1"',
)
replace_once(
    "updater.py",
    "AstrBot-RollPig-Safe-Updater/3.6.0",
    "AstrBot-RollPig-Safe-Updater/3.6.1",
)

for path in (
    "tests/test_v312_release_contract.py",
    "tests/test_identity_migration_plus.py",
    "tests/test_source_regressions.py",
):
    text = read(path)
    if path == "tests/test_v312_release_contract.py":
        text = text.replace('version: "3.6.0"', 'version: "3.6.1"')
        text = text.replace("AstrBot-RollPig/3.6.0", "AstrBot-RollPig/3.6.1")
        text = text.replace(
            "AstrBot-RollPig-Safe-Updater/3.6.0",
            "AstrBot-RollPig-Safe-Updater/3.6.1",
        )
    elif path == "tests/test_identity_migration_plus.py":
        text = text.replace('version: "3.6.0"', 'version: "3.6.1"')
    else:
        text = text.replace('version: "3.6.0"', 'version: "3.6.1"')
        text = text.replace("AstrBot-RollPig/3.6.0", "AstrBot-RollPig/3.6.1")
    write(path, text)

replace_once(
    "docs/COMMANDS.md",
    "本文以 v3.6.0 的 `main.py` 實作為準。",
    "本文以 v3.6.1 的 `main.py` 實作為準。",
)
replace_once(
    "docs/CONFIGURATION.md",
    "本文對應 v3.6.0 的 `_conf_schema.json`。",
    "本文對應 v3.6.1 的 `_conf_schema.json`。",
)
replace_once(
    "docs/OPERATIONS.md",
    "本文面向插件管理員與維護者，說明 v3.6.0 的",
    "本文面向插件管理員與維護者，說明 v3.6.1 的",
)
replace_once(
    "docs/RESOURCE-MANAGEMENT.md",
    "本文對應 v3.6.0，面向需要維護",
    "本文對應 v3.6.1，面向需要維護",
)

readme = read("README.md")
if readme.count("current-3.6.0-ef5d82") != 1:
    raise RuntimeError("README current-version badge anchor changed")
readme = readme.replace("current-3.6.0-ef5d82", "current-3.6.1-ef5d82", 1)
readme = readme.replace(
    "- **v3.2.0+ → v3.6.0**：直接更新；現有 SQLite、本地小豬、自訂圖片和屏蔽記錄會保留。",
    "- **v3.2.0+ → v3.6.1**：直接更新；現有 SQLite、本地小豬、自訂圖片和屏蔽記錄會保留。",
    1,
)
readme = readme.replace(
    "- **v3.1.4 或更早增強版 → v3.6.0**：先完成獨立身份遷移，再確認新資料正常。",
    "- **v3.1.4 或更早增強版 → v3.6.1**：先完成獨立身份遷移，再確認新資料正常。",
    1,
)
highlights = re.compile(r"## 3\.6\.0 版本亮點\n\n.*?\n完整變更請閱讀", re.S)
replacement = '''## 3.6.1 版本亮點

| 修復 | 改進 |
| --- | --- |
| 🧭 指令事件隔離 | RollPig 指令匹配後會停止繼續傳播，避免 `/今日小豬` 完成後又落入其他插件或 LLM |
| 📊 日報衝突修復 | 移除 legacy `豬圈日報` 重複註冊，只保留完整統計海報實作 |
| 🖼️ PigHub 缺圖自癒 | 歷史／本地 PigHub metadata 尚在但圖片遺失時，可由可信來源安全恢復圖片 |
| 🔤 繁體字體修復 | AI 料理與繁體文案優先使用正式包內完整 CJK 字體，不再誤用 Pillow 預設字體 |
| ☁️ Cloud cache 修復 | 已版本化但不完整的雲資源快取會在重啟後提前進行完整原子重同步 |

完整變更請閱讀'''
readme, count = highlights.subn(replacement, readme, count=1)
if count != 1:
    raise RuntimeError("README 3.6.0 highlights block changed")
write("README.md", readme)

changelog = read("CHANGELOG.md")
unreleased = "## 未發佈\n\n### 修復\n"
released = '''## 未發佈

- 暫無。

## v3.6.1 (2026-08-14)

### 版本主題：指令隔離與資源自癒 Hotfix

### 修復
'''
if not changelog.startswith("# 更新\n\n" + unreleased):
    raise RuntimeError("CHANGELOG v3.6.1 unreleased block changed")
changelog = changelog.replace(unreleased, released, 1)
write("CHANGELOG.md", changelog)

release_notes = '''## 🐷 今日小豬 · 增強版 v3.6.1

v3.6.1 是針對 v3.6.0 實機回報的 **hotfix patch release**，不新增玩法、不改資料格式，集中修復指令衝突、事件穿透、繁體字體 fallback 與缺圖恢復。

### 修復

- **豬圈日報指令衝突**：移除 `legacy_main` 的舊 `豬圈日報` 註冊，只保留 `DailyReportMixin` 的完整統計海報版本；AstrBot 指令管理器不應再顯示 RollPig 自身的兩條同名日報衝突。
- **RollPig 指令穿透到 LLM／其他插件**：所有 RollPig 聊天指令在匹配後會安全呼叫 `event.stop_event()`；`/今日小豬` 等命令完成後不再繼續被其他插件或 LLM 當成普通訊息處理。
- **繁體／AI 文案字體**：優先使用正式包已包含的 `荆南麦圆体.otf`，修復舊獨立繁體字體不存在時 Pillow default 被誤當有效 CJK 字體的問題。
- **PigHub 歷史／本地缺圖自癒**：若小豬 metadata 仍保留通過既有 PigHub URL 安全校驗的 `source_url`，發送前會嘗試重新下載、做大小限制與圖片解碼／標準化，再恢復本地圖片；修復失敗仍維持原有無圖降級，不會阻塞每日抽取。
- **損壞 cloud cache 提前修復**：已有 resource version、但 `_load_cloud_pigs()` 判定本地 cache 不完整時，重啟後會提前觸發 `force=True` 的完整原子同步，不必等待正常同步週期。

### 相容性

- 可由 **v3.6.0 直接升級**；SQLite／JSON、永久圖鑑、本地 override、歷史記錄、EX 差分、日報及預約烤豬資料均不需要 migration。
- PigHub 自癒只接受既有安全校驗允許的 PigHub 圖片 URL，不會把歷史 metadata 中的任意外部 URL 當作下載來源。
- 本版沒有 Repository Security Advisory；按實際內容標示為穩定性 hotfix。

### 驗證

- Python 3.10 / 3.12 全量測試
- pre-commit / pre-commit.ci
- Marketplace Package
- AstrBot 官方 Market Smoke
- v3.6.1 專用 AST/source regression contracts
'''
write(".github/release-v3.6.1.md", release_notes)

# Guard current release references. Historical release notes/changelog are intentionally allowed.
checks = {
    "metadata.yaml": ['version: "3.6.1"'],
    "legacy_main.py": ["AstrBot-RollPig/3.6.1", '"X-RollPig-Version": "3.6.1"'],
    "updater.py": ["AstrBot-RollPig-Safe-Updater/3.6.1"],
    "README.md": ["current-3.6.1-ef5d82", "## 3.6.1 版本亮點"],
    "CHANGELOG.md": ["## v3.6.1 (2026-08-14)"],
}
for path, needles in checks.items():
    text = read(path)
    for needle in needles:
        if needle not in text:
            raise RuntimeError(f"release contract missing {needle!r} in {path}")
