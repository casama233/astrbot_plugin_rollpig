from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    source = target.read_text(encoding="utf-8")
    actual = source.count(old)
    if actual < count:
        raise SystemExit(f"{path}: marker missing ({actual} < {count}): {old[:120]!r}")
    target.write_text(source.replace(old, new, count), encoding="utf-8")


# Charge + refill design document.
path = ROOT / "docs" / "ROAST-CHARGES.md"
source = path.read_text(encoding="utf-8")
source = source.replace("# 烤箱 Charge（Phase 3A）", "# 烤箱 Charge 與群體補貨（Phase 3A–3B）", 1)
old_phase3b = '''## Phase 3B

本階段 **不包含** `/烤箱補貨` 與 `/添煤`。

Phase 3B 會建立群體補貨事件，成功時為符合條件的本群玩家恢復 **+1 格**，而不是直接補滿，並寫入已預留的 Gameplay Event：

- `oven_refill_started`
- `oven_refill_supported`
- `oven_refill_succeeded`
- `oven_refill_failed`

在 Phase 3A 的 charge/storage contract 穩定後再接入，避免同一個 PR 同時重寫冷卻、預約與群體補貨。
'''
new_phase3b = '''## Phase 3B：群體補貨

Phase 3B 已在 Phase 3A 的 charge/storage contract 上加入：

- `/烤箱補貨`：由本群今天已參與 RollPig 的玩家發起；發起者自動計入第 1 份支持。
- `/添煤`：同一玩家每輪只計一次；只有本群今日活躍玩家可參與。
- 首輪預設門檻為 `max(3, ceil(今日活躍 × 30%))`；若只有 2 位活躍玩家則必須 2 人全部支持。
- 每成功一次，下一輪門檻預設再增加 2 人，但永遠不會高於本群今日活躍人數。
- 每群每日預設最多成功補貨 2 次。
- 達標時為本群今日活躍玩家各恢復 **+1 格**，不直接補滿；已滿能量者不會溢出。
- 若達標時所有符合資格玩家都已自行恢復滿格，本輪作廢，不消耗每日成功次數。

SQLite 使用正規化 `oven_refill_groups` / `oven_refill_supporters`；達標狀態切換與逐人 +1 charge 在同一 transaction 完成。JSON fallback 使用 `roast_state.json -> oven_refills`，並共用相同 charge policy。

Gameplay Event：

- `oven_refill_started`
- `oven_refill_supported`
- `oven_refill_succeeded`
- `oven_refill_failed`

豬圈日報只讀 Gameplay Event，顯示「補貨發起 / 添煤人次 / 補貨成功」，不直接讀補貨資料表。
'''
if old_phase3b not in source:
    raise SystemExit("ROAST-CHARGES Phase 3B marker missing")
path.write_text(source.replace(old_phase3b, new_phase3b, 1), encoding="utf-8")

# Command guide: old cooldown prose -> charge model + cooperative commands.
replace(
    "docs/COMMANDS.md",
    "普通烤群友按「發起者 + 群組」計算冷卻，預設 8 小時，可由 `group_roast_cooldown_hours` 調整。",
    "普通烤群友按「發起者 + 群組」使用烤箱能量，預設 `2 / 2` 格；每次消耗 1 格。`group_roast_cooldown_hours` 現表示每格缺失能量的恢復時間（預設 8 小時），`group_roast_max_charges` 控制最大格數（預設 2）。",
)
replace(
    "docs/COMMANDS.md",
    "- 第一位玩家成為固定主廚，必須先抽到自己可料理的小豬，並立即消耗一次普通烤架冷卻。\n- 後續其他群友對同一目標再使用 `/烤群友` 會免費「添柴」，不消耗自己的冷卻；同一人不重複計數。",
    "- 第一位玩家成為固定主廚，必須先抽到自己可料理的小豬，並立即消耗 1 格烤箱能量。\n- 後續其他群友對同一目標再使用 `/烤群友` 會免費「添柴」，不消耗自己的烤箱能量；同一人不重複計數。",
)
replace(
    "docs/COMMANDS.md",
    "- 觸發時不再次扣主廚冷卻，仍使用原本 60% / 30% / 10% 結果。",
    "- 觸發時不再次扣主廚能量，仍使用原本 60% / 30% / 10% 結果。",
)
insert_marker = "### `/隨機烤群友`\n"
insert_text = '''## 烤箱補貨

### `/烤箱補貨`

只可在群聊中使用。發起者必須是本群今天已參與 RollPig 的活躍玩家；發起成功後自動計入第 1 份支持。

預設首輪需要 `max(3, ceil(今日活躍 × 30%))` 人支持；只有 2 位活躍玩家時需要兩人全部支持。當天每成功一次，下一輪預設再增加 2 人需求，且不會超過今日活躍人數。每群每日預設最多成功補貨 2 次。

### `/添煤`

支持本群目前進行中的補貨。只有今天在本群參與過 RollPig 的玩家可添煤，同一玩家同一輪只計一次。

達標後，本群今日活躍玩家各恢復 **+1 格** 烤箱能量，不會直接補滿，也不會超過 `group_roast_max_charges`。若達標時所有符合資格玩家都已滿格，本輪作廢且不計入每日成功上限。

補貨流程會產生 Gameplay Event，豬圈日報統計「補貨發起 / 添煤人次 / 補貨成功」。

'''
replace("docs/COMMANDS.md", insert_marker, insert_text + insert_marker)

# Config guide.
replace(
    "docs/CONFIGURATION.md",
    "| `roast_reservation_max_participants` | int | `12` | `2-20` | 每張預約包含固定主廚在內的最大參與人數；後續添柴不消耗自己的普通冷卻。 |",
    "| `roast_reservation_max_participants` | int | `12` | `2-20` | 每張預約包含固定主廚在內的最大參與人數；後續添柴不消耗自己的烤箱能量。 |",
)
replace(
    "docs/CONFIGURATION.md",
    "| `group_roast_cooldown_hours` | float | `8` | `1-72` | 普通烤群友按「發起者 + 群組」計算冷卻；第一位主廚建立預約時消耗一次，添柴與預約觸發不重複扣除。後門可繞過。 |",
    "| `group_roast_cooldown_hours` | float | `8` | `1-72` | 每格缺失烤箱能量的恢復時間；沿用舊冷卻配置。 |\n| `group_roast_max_charges` | int | `2` | `1-5` | 每位玩家在每個群組可儲存的最大烤箱能量；普通烤群友與建立預約各消耗 1 格。 |\n| `enable_oven_refill` | bool | `true` | `true` / `false` | 是否啟用 `/烤箱補貨` 與 `/添煤`。 |\n| `oven_refill_daily_limit` | int | `2` | `1-5` | 每群每天成功補貨次數上限；作廢輪次不計。 |\n| `oven_refill_support_ratio_percent` | int | `30` | `1-100` | 首輪補貨需要的本群今日活躍玩家比例。 |\n| `oven_refill_min_supporters` | int | `3` | `2-20` | 補貨的最少支持人數；僅 2 位活躍玩家時固定需要 2 人。 |\n| `oven_refill_extra_supporters_per_success` | int | `2` | `0-10` | 當天每成功補貨一次，下一輪增加的支持人數。 |",
)
replace(
    "docs/CONFIGURATION.md",
    "預約只在明確指定未抽豬目標時建立。主廚先支付普通冷卻，目標在同群顯示自己的今日小豬時才結算；添柴不增加成功率。詳細行為見 [`ROAST-RESERVATIONS.md`](ROAST-RESERVATIONS.md)。",
    "預約只在明確指定未抽豬目標時建立。主廚先支付 1 格烤箱能量，目標在同群顯示自己的今日小豬時才結算；添柴不增加成功率。詳細行為見 [`ROAST-RESERVATIONS.md`](ROAST-RESERVATIONS.md)。",
)
replace(
    "docs/CONFIGURATION.md",
    '  "group_roast_cooldown_hours": 8,\n  "enable_roast_protection": true,',
    '  "group_roast_cooldown_hours": 8,\n  "group_roast_max_charges": 2,\n  "enable_oven_refill": true,\n  "oven_refill_daily_limit": 2,\n  "enable_roast_protection": true,',
)

# Daily report guide gets a gameplay-event note.
daily = ROOT / "docs" / "DAILY-REPORT.md"
text = daily.read_text(encoding="utf-8")
addition = '''\n## 烤箱補貨指標\n\nPhase 3B 後，日報從 Gameplay Event 聚合並額外顯示：\n\n- 補貨發起：`oven_refill_started`。\n- 添煤人次：發起者自動支持 + `oven_refill_supported`。\n- 補貨成功：`oven_refill_succeeded`。\n\n`oven_refill_failed` 仍會保留在事件流中供後續統計／管理面板使用，但不佔主海報的核心指標卡。日報不直接查詢 `oven_refill_groups` 或 `oven_refill_supporters`，保持「玩法寫事件、日報只讀事件」的邊界。\n'''
if "## 烤箱補貨指標" not in text:
    text += addition
daily.write_text(text, encoding="utf-8")

# Unreleased changelog.
changelog = ROOT / "CHANGELOG.md"
text = changelog.read_text(encoding="utf-8")
marker = "## 未發佈\n\n"
addition = '''## 未發佈\n\n### Added\n- Phase 3B 群體烤箱補貨：新增 `/烤箱補貨` 與 `/添煤`；本群今日活躍玩家協作達標後各恢復 +1 格烤箱能量，首輪預設門檻為 `max(3, ceil(活躍 × 30%))`，成功後下一輪預設 +2 人，每群每日預設最多成功 2 次。\n- 新增正規化 `oven_refill_groups` / `oven_refill_supporters` SQL 狀態，達標狀態與逐人 +1 charge 在同一 transaction 完成；JSON fallback 使用相同狀態語義。\n- Gameplay Event 正式接入 `oven_refill_started/supported/succeeded/failed`，豬圈日報新增「補貨發起 / 添煤人次 / 補貨成功」三個指標。\n\n'''
if marker not in text:
    raise SystemExit("CHANGELOG Unreleased marker missing")
if "Phase 3B 群體烤箱補貨" not in text:
    text = text.replace(marker, addition, 1)
changelog.write_text(text, encoding="utf-8")

print("Phase 3B docs updated")
