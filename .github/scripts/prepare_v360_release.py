from pathlib import Path
import re


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor in {path}: {old!r}; got {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once("metadata.yaml", 'version: "3.5.0"', 'version: "3.6.0"')
replace_once("legacy_main.py", "AstrBot-RollPig/3.5.0", "AstrBot-RollPig/3.6.0")
replace_once(
    "updater.py",
    "AstrBot-RollPig-Safe-Updater/3.5.0",
    "AstrBot-RollPig-Safe-Updater/3.6.0",
)
replace_once(
    "tests/test_v312_release_contract.py",
    'assert \'version: "3.5.0"\' in metadata',
    'assert \'version: "3.6.0"\' in metadata',
)
replace_once(
    "tests/test_v312_release_contract.py",
    'assert "AstrBot-RollPig/3.5.0" in main',
    'assert "AstrBot-RollPig/3.6.0" in main',
)
replace_once(
    "tests/test_v312_release_contract.py",
    'assert "AstrBot-RollPig-Safe-Updater/3.5.0" in updater',
    'assert "AstrBot-RollPig-Safe-Updater/3.6.0" in updater',
)
replace_once(
    "docs/COMMANDS.md",
    "本文以 v3.5.0 的 `main.py` 實作為準。",
    "本文以 v3.6.0 的 `main.py` 實作為準。",
)
replace_once(
    "docs/CONFIGURATION.md",
    "本文對應 v3.5.0 的 `_conf_schema.json`。",
    "本文對應 v3.6.0 的 `_conf_schema.json`。",
)

readme = Path("README.md")
text = readme.read_text(encoding="utf-8")
if "current-3.5.0-ef5d82" not in text:
    raise RuntimeError("README current-version badge anchor missing")
text = text.replace("current-3.5.0-ef5d82", "current-3.6.0-ef5d82", 1)
pattern = re.compile(r"## 3\.5\.0 版本亮點\n\n.*?\n完整變更請閱讀", re.S)
replacement = """## 3.6.0 版本亮點

| 能力 | 帶來的改進 |
| --- | --- |
| 📊 完整豬圈日報 | 可配置每日自動推送統計海報，支援真實並列稱號、頭像、跨午夜鎖定、重啟補發與可選今日祭品 |
| 🧬 EX Lv. 成長差分 | EX Lv.1–5 可按既有收藏次數替換立繪、描述或完整文案，欄位可獨立向下繼承 |
| 🔥 預約烤豬 | 明確指定尚未抽豬的群友可建立同群當日埋伏，其他群友免費添柴，目標出現後一次性按原 60/30/10 結算 |
| 🧱 Gameplay Event v1 | 日報、EX 成長與預約玩法共用可去重事件層，避免新玩法各自建立孤立歷史 |
| 🛠️ 投稿按鈕修復 | 修復管理面板「投稿公共源」在 sandbox 環境下點擊無反應，改為頁面內二次確認與明確成功／失敗反饋 |
| 🔤 CJK 發行修復 | Release 與 Marketplace 包重新包含首選中文字體，Linux 標題不再因回退 DejaVu 而顯示方框 |

完整變更請閱讀"""
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError("README v3.5.0 highlight block not found")
readme.write_text(text, encoding="utf-8")

changelog = Path("CHANGELOG.md")
text = changelog.read_text(encoding="utf-8")
header = "# 更新\n\n## 未發佈\n\n### 新功能\n"
new_header = """# 更新

## 未發佈

- 暫無。

## v3.6.0 (2026-08-14)

### 版本主題：群聊成長、完整日報與發行穩定性

### 新功能

- 豬圈日報升級為可配置統計海報與自動推送系統：加入真實並列稱號、平台頭像、跨午夜日期鎖定、重啟補發與可選「今日祭品」；手動查看不觸發祭品。
"""
if not text.startswith(header):
    raise RuntimeError("CHANGELOG unreleased header changed unexpectedly")
text = text.replace(header, new_header, 1)
architecture = "\n### 架構\n"
fixes = """

### 修復

- 修復管理面板「投稿公共源」在 sandbox 中依賴原生 `window.confirm` 導致點擊無反應；改用頁面內二次點擊確認並補齊成功／失敗反饋與回歸測試。
- 修復 v3.5.0 發行包排除 `resource/font/荆南麦圆体.otf` 導致 Linux 中文標題可能回退 DejaVu 顯示方框；Release／Marketplace 現在強制打包並在 CI 中斷言字體存在。

### 架構
"""
if architecture not in text:
    raise RuntimeError("CHANGELOG architecture section missing")
text = text.replace(architecture, fixes, 1)
changelog.write_text(text, encoding="utf-8")

release_notes = """## 🐷 今日小豬 · 增強版 v3.6.0

這一版把 v3.5.0 之後已合併的群聊成長功能正式收成一個穩定版本，同時優先帶上兩個影響實際使用與發行包的修復。

### 新增

- **完整豬圈日報**：每天可自動推送統計海報，包含熱門豬、燒烤狂人、最慘食材、逃脫大師、反噬之王等真實並列稱號，並支援頭像、隨機延遲、跨午夜與重啟補發。
- **EX Lv.1–5 成長差分**：同一隻小豬可隨收藏成長替換圖片、描述或完整文案；舊資源包與私人 v1 manifest 保持相容。
- **預約烤豬／添柴**：明確烤尚未抽豬的群友時建立同群當日埋伏；第一位主廚支付既有冷卻，後續群友可免費添柴，目標本人出現後一次性按原 60% 成功／30% 逃脫／10% 反噬結算。
- **Gameplay Event v1**：日報、EX 與預約玩法共用去重事件入口，為後續群聊玩法提供統一統計基線。

### 修復

- 修復管理面板「投稿公共源」按鈕在 sandbox 環境中點擊無反應，改用頁面內二次確認並提供明確結果反饋。
- 修復 v3.5.0 正式 ZIP 排除首選 CJK 標題字體的問題；Release 與 Marketplace 包現在強制包含 `荆南麦圆体.otf`，Linux 中文小豬名稱不再因回退 DejaVu 而顯示方框。

### 升級與相容性

- 可由 v3.5.0 直接升級；既有 SQLite／JSON 資料、永久圖鑑、本地 override、屏蔽記錄與資源快取均保留。
- 本版沒有新增破壞性資料庫 migration；新增日報／預約狀態使用輔助資料，核心收藏與群聊計數權威保持原有存儲語義。
- EX 差分是 Resource Protocol v1 的可選擴充，舊 v1／私人來源不需要立即修改。

> GitHub 上目前沒有公開或私密 Repository Security Advisory 對應本次發版；本版的緊急修補屬功能／發行穩定性修復，不虛標安全公告。

完整細節見 [CHANGELOG](../CHANGELOG.md)、[豬圈日報](../docs/DAILY-REPORT.md)、[EX 差分](../docs/EX-VARIANTS.md) 與 [預約烤豬](../docs/ROAST-RESERVATIONS.md)。
"""
Path(".github/release-v3.6.0.md").write_text(release_notes, encoding="utf-8")
