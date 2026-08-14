from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


# metadata
p = "metadata.yaml"
s = read(p)
s = replace_once(s, 'version: "3.6.4"', 'version: "3.6.5"', "metadata version")
write(p, s)

# runtime/update user agents
p = "legacy_main.py"
s = read(p)
s = replace_once(s, "AstrBot-RollPig/3.6.4", "AstrBot-RollPig/3.6.5", "runtime UA")
write(p, s)

p = "updater.py"
s = read(p)
s = replace_once(
    s,
    "AstrBot-RollPig-Safe-Updater/3.6.4",
    "AstrBot-RollPig-Safe-Updater/3.6.5",
    "updater UA",
)
write(p, s)

# README version badge/highlights
p = "README.md"
s = read(p)
s = replace_once(s, "current-3.6.4-ef5d82", "current-3.6.5-ef5d82", "README badge")
start = s.index("## 3.6.4 版本亮點")
end = s.index("\n## 為什麼選擇增強版", start)
new_block = '''## 3.6.5 版本亮點

| 修復／加固 | 說明 |
| --- | --- |
| 🔔 群日報改為 opt-in | 群組自動推送預設關閉；只有群主、群管理員或 AstrBot 管理員使用 `/豬圈日報 開啟` 後才會在自然日結束前推送，並提供 `關閉` / `狀態` |
| 📊 日報資料更可解釋 | 所有豬都只出現一次時不再硬選「最熱門」；歷史只有總量、缺少人物事件明細的烤豬資料會明確標註，避免名人堂看起來與總數矛盾 |
| 🛡️ 公共源審核加固 | 修復審核圖片只顯示 🐽 fallback；加入名稱近似與 dHash 圖片疑似重複提示、敏感審核代理 CSRF、全局待審上限與 review service systemd sandbox |
| 🧩 收藏身份邊界 | 新增 claim-aware `CollectionService`；只合併已證明屬於同一 logical user 的收藏 ownership，pig count 取 `max`，不把舊 fragment 的保底／總抽取統計算回目前狀態 |

完整變更請閱讀 [CHANGELOG](CHANGELOG.md)；EX 成長格式見 [EX 差分手冊](docs/EX-VARIANTS.md)，資源使用方式見 [資源管理手冊](docs/RESOURCE-MANAGEMENT.md)，發佈與回退流程見 [豬源維護手冊](docs/RESOURCE-SOURCE-MAINTENANCE.md)。
'''
s = s[:start] + new_block + s[end:]
write(p, s)

# CHANGELOG: reset Unreleased and publish current entries as 3.6.5
p = "CHANGELOG.md"
s = read(p)
idx = s.index("## v3.6.4 (2026-08-14)")
rest = s[idx:]
head = '''# 更新

## 未發佈

- 暫無。

## v3.6.5 (2026-08-15)

### 版本主題：群日報 opt-in、收藏身份安全與公共源審核加固

### 修復

- 豬圈日報自動推送改為 **per-group opt-in**：新群與既有未標記群一律默認關閉；只有群主、群管理員或 AstrBot 管理員使用 `/豬圈日報 開啟` 後才會自動推送，並提供 `/豬圈日報 關閉`、`/豬圈日報 狀態`。全局 `daily_report_auto_send` 僅保留為 master switch。
- scheduler 只遍歷顯式啟用群，`auto_enabled_since` 阻止新開啟群補發更早日期；23:50 + 隨機延遲被限制在報告自然日內，不再跨午夜。
- 修正日報「熱門豬」誤導：當所有豬都只出現一次時，不再任選一隻標成最熱門，改為明確顯示形態分散；若烤豬 storage 總量包含缺少 Gameplay Event 人物明細的舊記錄，保留真實總量並標註缺失明細，人物稱號只按可追溯事件計算。
- 修復公共源審核圖片代理使用錯誤 GET query API 導致管理頁只顯示 🐽 fallback；改用 AstrBot `request.query`，並為 review list/image 敏感 GET 加 same-origin + CSRF。
- 公共源審核新增現役 catalog 的正規化名稱近似與 64-bit dHash 圖片感知相似提示；提示只輔助人工審核，不會自動拒絕合理變體，同 ID／待審完全相同 SHA-256 仍為硬拒絕。

### 資料與身份安全

- 完成 claim-aware Collection Identity Boundary：`CollectionService` 只讀取目前 namespaced identity 與已由 `identity_claims` 證明屬於同一 logical user 的舊 fragment，不自動合併 sibling Bot instance，也不把其他平台同 raw ID 的資料串入。
- 永久 ownership 可跨安全 fragment 聯集；`first_unlocked` 取最早、`last_drawn` 取最晚、同豬 `count` 取 `max` 而不是相加，避免 migration copy 虛增 EX Lv.。
- `duplicate_streak`、`total_draws`、`active_days` 不跨 fragment 算術合併；目前 gameplay state 仍以最高優先級 fragment 為權威，舊資料不會把已失效保底重新帶回。

### 公共源安全

- 明確區分協議門檻與身份認證：`User-Agent` / `X-RollPig-*` 可被開源客戶端模擬，只作 protocol gate；公開投稿安全依賴內容驗證、來源 HMAC 指紋節流、人工審核與服務端管理 token。
- 新增全局待審上限 200，duplicate index 依 canonical `pig.json` revision cache，避免每次刷新重算全 catalog 圖片。
- review service systemd sandbox 增加 `PrivateDevices`、`ProtectHome`、`ProtectKernel*`、`ProtectControlGroups`、`LockPersonality`、`MemoryDenyWriteExecute`、`RestrictAddressFamilies`；管理 Bearer token 仍只存在維護者主機，不進插件配置或瀏覽器。

### 相容性

- 可由 **v3.6.4 直接升級**；不修改 SQLite schema、玩家抽取權威、EX 算法、保底概率、烤豬概率或 Resource Protocol。
- 本版不包含烤箱 charge/refill 新玩法。
- 公共源審核的服務端 duplicate/security 加固需要維護者主機同步新版 `source_service/app.py` 與 systemd unit；一般插件使用者只需正常更新插件。

'''
write(p, head + rest)

# Release notes
release_notes = '''# 今日小豬 · 增強版 v3.6.5

這是一個穩定性與安全性 patch，重點收口群組日報的 opt-in 行為、收藏身份 fragment 的安全讀取，以及公共源人工審核的圖片／重複提示／服務端防護。

## 修復與加固

- 群組自動日報預設關閉；僅群主、群管理員或 AstrBot 管理員在群內 `/豬圈日報 開啟` 後才會自動推送，並提供 `關閉` / `狀態`。
- 自動日報不再跨自然日；今天才 opt-in 的群不補發更早日期。
- 修正 16 種豬各出現 1 次時硬選「最熱門」的誤導；歷史只有總量、缺人物事件明細的烤豬統計會明確披露。
- 修復公共源審核圖片只顯示 🐽 fallback；review list/image 增加 same-origin + CSRF。
- 審核頁新增名稱近似與 dHash 圖片疑似重複提示；模糊相似只供人審，不自動拒絕。
- 公共投稿增加全局 pending 200 上限，review service 增加更嚴格 systemd sandbox。
- 新增 claim-aware `CollectionService`：只合併已證明屬於同一 logical user 的 ownership；同豬 count 取 max，舊 fragment 不回灌 duplicate streak／總抽取／活躍天數，避免虛增 EX 或保底。

## 升級

可由 v3.6.4 直接更新。無 SQLite migration，無 EX／保底／烤豬概率／Resource Protocol 變更。

> 維護公共源審核服務的主機還需同步新版 `source_service/app.py` 與 `deploy/rollpig-source-review.service` 才能啟用服務端 duplicate/security hardening；一般插件安裝不需要做此步驟。
'''
write(".github/release-v3.6.5.md", release_notes)

# Release contract tests
for p in (
    "tests/test_v312_release_contract.py",
    "tests/test_identity_migration_plus.py",
    "tests/test_source_regressions.py",
):
    s = read(p)
    if "3.6.4" in s:
        s = s.replace("3.6.4", "3.6.5")
    write(p, s)

print("prepared v3.6.5")
