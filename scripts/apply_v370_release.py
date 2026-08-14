from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one marker, found {count}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


# Canonical version surfaces.
replace_once("metadata.yaml", 'version: "3.6.5"', 'version: "3.7.0"')
replace_once(
    "legacy_main.py",
    "AstrBot-RollPig/3.6.5 (+https://github.com/casama233/astrbot_plugin_rollpig)",
    "AstrBot-RollPig/3.7.0 (+https://github.com/casama233/astrbot_plugin_rollpig)",
)

# README release headline and product story.
readme = Path("README.md")
r = readme.read_text(encoding="utf-8")
r = r.replace(
    "![Current Version](https://img.shields.io/badge/current-3.6.5-ef5d82)",
    "![Current Version](https://img.shields.io/badge/current-3.7.0-ef5d82)",
    1,
)
start = r.index("## 3.6.5 版本亮點")
end_marker = "完整變更請閱讀 [CHANGELOG](CHANGELOG.md)"
end = r.index(end_marker, start)
end = r.index("\n", end) if "\n" in r[end:] else len(r)
new_highlights = '''## 3.7.0 版本亮點

| 新玩法／整合 | 說明 |
| --- | --- |
| 🔥 烤箱 Charge 2/2 | `/烤群友` 與建立預約改為「使用者 × 群組」可儲存能量；預設 2 格、每 8 小時自然恢復 1 格，舊 8 小時 cooldown 會安全 lazy 遷移，不重置既有進度 |
| ⛽ 群體烤箱補貨 | 新增 `/烤箱補貨` 與 `/添煤`；今日活躍群友達成可配置參與門檻後，全體今日活躍玩家各恢復 +1 格，並有每日成功上限與逐輪加難機制 |
| ⚡ 渲染與落盤性能整合 | 圖片 decode／縮放快取、成品豬卡與資源路徑快取、全局 render backpressure，以及豬圈日報狀態 debounce，大幅降低高併發時 CPU、I/O 與重複工作 |
| 🧭 動態幫助與管理契約 | `/豬豬幫助` 依目前配置動態生成並以內容指紋快取；豬圈日報自動推送開關只允許 AstrBot 管理員修改，手動日報永不觸發祭品 |

完整變更請閱讀 [CHANGELOG](CHANGELOG.md)；EX 成長格式見 [EX 差分手冊](docs/EX-VARIANTS.md)，資源使用方式見 [資源管理手冊](docs/RESOURCE-MANAGEMENT.md)，發佈與回退流程見 [豬源維護手冊](docs/RESOURCE-SOURCE-MAINTENANCE.md)。'''
r = r[:start] + new_highlights + r[end:]
r = r.replace(
    "今日烤豬、烤群友、預約埋伏、吃群友與豬圈日報，兼顧異步互動、冷卻、保護與失敗回退。",
    "今日烤豬、Charge 烤群友、預約埋伏、群體補貨、吃群友與豬圈日報，兼顧異步互動、能量恢復、保護與失敗回退。",
    1,
)
r = r.replace(
    "- **群聊互動**：烤自己、烤群友、預約未抽目標與群友添柴、隨機烤、吃群友及群聊日報。",
    "- **群聊互動**：烤自己、Charge 烤群友、預約未抽目標與群友添柴、群體烤箱補貨、隨機烤、吃群友及群聊日報。",
    1,
)
r = r.replace(
    "| `/烤群友 @某人` / `/吃群友 @某人` | 群聊互動玩法 |\n| `/豬圈日報` | 查看本群今日概況 |",
    "| `/烤群友 @某人` / `/吃群友 @某人` | 群聊互動玩法 |\n| `/烤箱補貨` / `/添煤` | 今日活躍群友協作恢復烤箱 Charge |\n| `/豬圈日報` | 查看本群今日概況；管理員可用 `開啟` / `關閉` / `狀態` 管理自動推送 |",
    1,
)
readme.write_text(r, encoding="utf-8")

# Command manual: release baseline + Charge/refill semantics.
commands = Path("docs/COMMANDS.md")
c = commands.read_text(encoding="utf-8")
c = c.replace(
    "本文以 v3.6.3 的 `main.py` 實作為準。",
    "本文以 v3.7.0 的 `main.py` 實作為準。",
    1,
)
c = c.replace(
    "普通烤群友按「發起者 + 群組」計算冷卻，預設 8 小時，可由 `group_roast_cooldown_hours` 調整。",
    "普通烤群友按「發起者 × 群組」消耗烤箱 Charge；預設最多 2 格，每次普通烤群友消耗 1 格，每隔 8 小時自然恢復 1 格。容量由 `group_roast_max_charges` 調整，恢復週期沿用 `group_roast_cooldown_hours`。",
    1,
)
c = c.replace(
    "- 第一位玩家成為固定主廚，必須先抽到自己可料理的小豬，並立即消耗一次普通烤架冷卻。",
    "- 第一位玩家成為固定主廚，必須先抽到自己可料理的小豬，並立即消耗 1 格目前群組的烤箱 Charge。",
    1,
)
c = c.replace(
    "- 後續其他群友對同一目標再使用 `/烤群友` 會免費「添柴」，不消耗自己的冷卻；同一人不重複計數。",
    "- 後續其他群友對同一目標再使用 `/烤群友` 會免費「添柴」，不消耗自己的 Charge；同一人不重複計數。",
    1,
)
c = c.replace(
    "- 觸發時不再次扣主廚冷卻，仍使用原本 60% / 30% / 10% 結果。",
    "- 觸發時不再次扣主廚 Charge，仍使用原本 60% / 30% / 10% 結果。",
    1,
)
insert_marker = '''### `/隨機烤群友`\n\n別名：`/随机烤群友`。\n\n從今天在當前群聊抽過小豬、且目前符合烤豬資格的其他成員中隨機選一位，再套用正常的烤群友流程。\n'''
refill_section = insert_marker + '''\n## 烤箱補貨\n\n需要 `enable_roast=true`、`enable_group_roast=true` 與 `enable_oven_refill=true`。只有**今天在目前群聊參與過 RollPig** 的玩家可以發起或支持。\n\n### `/烤箱補貨`\n\n別名包括 `/烤箱补货`、`/烤箱補給`、`/烤箱补给`。\n\n- 發起者自動貢獻第一份支持。\n- 第一輪預設需要今日活躍人數的 30%，最低 3 人、基礎上限 8 人；只有 2 位活躍玩家時固定需要 2 人。\n- 同群同日每成功一輪，下一輪預設再增加 2 名支持者。\n- 每群每日預設最多成功 2 次，可由 `oven_refill_daily_limit` 調整。\n\n### `/添煤`\n\n別名包括 `/加煤`、`/烤箱添煤`。\n\n- 同一玩家每輪只可支持一次。\n- 達標後，今天在本群活躍的玩家各恢復 **+1 格 Charge**，但不會超過自己的最大容量。\n- 如果結算時所有活躍玩家都已因自然恢復回滿，本輪作廢，不計入每日成功次數。\n- 補貨只操作既有 Charge authority；不改變 60% / 30% / 10% 烤群友結果，也不跨群共享能量。\n'''
if c.count(insert_marker) != 1:
    raise SystemExit(f"COMMANDS random-roast marker count={c.count(insert_marker)}")
c = c.replace(insert_marker, refill_section, 1)
commands.write_text(c, encoding="utf-8")

# Changelog: roll current Unreleased changes and the full integration batch into v3.7.0.
changelog = Path("CHANGELOG.md")
ch = changelog.read_text(encoding="utf-8")
start = ch.index("## 未發佈")
next_release = ch.index("## v3.6.5", start)
release_entry = '''## 未發佈\n\n- 暫無。\n\n## v3.7.0 (2026-08-15)\n\n### 版本主題：烤箱能量、群體補貨、動態幫助與性能大整合\n\n### 新玩法\n\n- **Phase 3A 烤箱 Charge**：普通 `/烤群友` 與建立預約由單次 8 小時硬冷卻升級為「使用者 × 群組」可儲存能量；預設 2 格，每 `group_roast_cooldown_hours` 自然恢復 1 格，容量可由 `group_roast_max_charges`（1–5）配置。\n- SQLite／JSON 共用同一 token-bucket policy；舊 `roast_cooldowns.last_used_at` lazy 遷移為 Charge state，仍在舊冷卻中的玩家視為已消耗 1 格並保留原恢復進度，不因升級清空或重罰。\n- 預約主廚建立預約消耗 1 格；後續添柴與日後觸發不重複消耗；後門 bypass 與原本 60% / 30% / 10% outcome policy 保持不變。\n- **Phase 3B 群體烤箱補貨**：新增 `/烤箱補貨` 與 `/添煤`。今日在本群活躍的玩家達成可配置支持門檻後，全體今日活躍玩家各恢復 +1 格 Charge；第一輪預設 30% 活躍人口、最低 3、基礎上限 8，後續每成功一輪預設 +2 人，每群每日預設最多成功 2 次。\n- 群體補貨只寫入既有 Charge authority；SQLite 提供原子 `grant_roast_charge`，SQLite v3 仍維持 normalized SQL single-authority。補貨 campaign 使用獨立輔助狀態並支援 crash-interrupted round 恢復，避免重複結算。\n- Gameplay Event、動態 Help 與豬圈日報同步接入補貨事件；日報可顯示補貨成功次數與添煤人次。\n\n### 性能與架構\n\n- 合入 renderer CPU／圖片 decode 熱路徑優化（#74）：減少重複圖片解碼、縮放及字型／版面計算。\n- 合入成品豬卡與資源路徑 probe 快取（#77），降低熱門指令反覆查檔與重渲染成本。\n- 新增共享 renderer backpressure（#75）：CPU 密集圖片工作以可配置 bounded semaphore 限制同時執行數，避免高併發把 thread pool 與 CPU 打滿。\n- 豬圈日報輔助狀態改為 debounce snapshot writer（#76），高頻 profile／event 更新不再每次同步整份 JSON；插件卸載前強制 flush 最新快照。\n- `/豬豬幫助` 升級為配置感知、響應式動態卡片（#81）：按目前啟用玩法與數值生成內容，以實際可見內容 + 主題 + 字型建立指紋快取；渲染仍共用全局 backpressure。\n\n### 日報與權限\n\n- 豬圈日報群組自動推送的開啟／關閉權限收緊為**僅 AstrBot 管理員**（#82）；原生群主／群管理員不再具備修改權限。\n- 固化祭品契約：`daily_report_random_eat_enabled` 預設關閉，且只允許定時自動日報流程觸發；手動 `/豬圈日報` 永不改變任何人的祭品狀態。\n\n### 升級與相容性\n\n- 可由 **v3.6.5 直接升級**。Charge 所需 SQLite 欄位與舊 cooldown 資料由插件自動遷移／lazy bootstrap，無需手工修改資料庫或 JSON。\n- 不修改永久收藏 identity boundary、EX 計數語義、保底概率、資源協議或烤群友 60/30/10 結果。\n- 本版繼續沿用 v3.6.5 已完成的 claim-aware Collection Identity Boundary；補貨參與者與 Charge 仍使用 canonical、claim-safe user × group identity，不枚舉 sibling Bot instance。\n\n'''
changelog.write_text(ch[:start] + release_entry + ch[next_release:], encoding="utf-8")

# Release workflow consumes this file verbatim when metadata reaches main.
release_notes = Path(".github/release-v3.7.0.md")
release_notes.write_text('''# 今日小豬 · 增強版 v3.7.0\n\n這是一個把近期玩法、性能與可維護性工作一次收口的大版本。核心主題是：**烤群友從硬冷卻升級為 2/2 Charge，並加入真正的群體烤箱補貨；同時把高併發渲染、日報落盤與動態幫助一起整理到正式架構。**\n\n## 🔥 烤箱 Charge 2/2\n\n- `/烤群友` 與建立預約按「使用者 × 群組」消耗 Charge，預設 2 格。\n- 每 8 小時自然恢復 1 格（沿用 `group_roast_cooldown_hours`），容量由 `group_roast_max_charges` 配置。\n- v3.6.x 舊 cooldown 會安全 lazy 遷移：活動中的舊冷卻視為已花 1 格，保留剩餘恢復時間。\n- 預約建立只扣主廚 1 格；添柴與觸發不重複扣；原 60/30/10 結果不變。\n\n## ⛽ 群體烤箱補貨\n\n- 新增 `/烤箱補貨` 與 `/添煤`。\n- 今日在本群參與 RollPig 的玩家才能發起／支持；發起者自動算第一份。\n- 第一輪預設門檻為活躍玩家 30%，最低 3 人、基礎上限 8 人；2 人小群固定 2 人。\n- 每成功一輪，下一輪預設再需要 +2 人；每群每日預設最多成功 2 次。\n- 達標後，今日活躍玩家各恢復 +1 Charge，不會超過容量；若結算時全員已自然回滿，本輪直接作廢且不吃每日次數。\n- 補貨事件已進 Gameplay Event 與豬圈日報。\n\n## ⚡ 性能整合\n\n- #74：renderer CPU / image decode 熱路徑優化。\n- #77：成品豬卡與資源 path probe 快取。\n- #75：全局圖片 renderer backpressure，避免高併發把 CPU / thread pool 打滿。\n- #76：豬圈日報狀態 debounce 落盤，卸載前保證 flush 最新快照。\n\n## 🧭 動態幫助與日報契約\n\n- #81：`/豬豬幫助` 改為依目前配置與數值動態生成；內容指紋、主題與字型共同決定快取，不再顯示已關閉玩法。\n- #82：群日報自動推送開關只允許 AstrBot 管理員修改；手動 `/豬圈日報` 永遠不會觸發祭品。\n\n## 🛡️ 資料與升級安全\n\n- SQLite / JSON 使用同一 Charge policy；SQLite v3 仍保持 normalized SQL single-authority。\n- 由 v3.6.5 可直接升級，Charge / cooldown 遷移自動完成。\n- 永久收藏仍沿用 v3.6.5 的 claim-aware Collection Identity Boundary；EX、保底、資源協議與烤群友 60/30/10 不因本版改寫。\n\n## ✅ 發佈門檻\n\n本版本在合併前要求同一 release head 通過 Python 3.10 / 3.12 全測試、pre-commit、Marketplace package 與 AstrBot 官方 PluginManager checked-out revision load。\n''', encoding="utf-8")
