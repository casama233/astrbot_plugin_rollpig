from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"anchor not found in {path}: {old[:90]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Help card in the historical implementation.
replace_once(
    "legacy_main.py",
    '("/烤群友 @某人", "60/30/10·8h冷却；昨日过度被烤会受保护"),',
    '("/烤群友 @某人", "60/30/10·8h冷却；未抽目标可预约，群友可添柴"),',
)

# README player-facing summary.
replace_once(
    "README.md",
    "今日烤豬、烤群友、吃群友、隨機互動與豬圈日報，兼顧趣味、冷卻、保護與失敗回退。",
    "今日烤豬、烤群友、預約埋伏、吃群友與豬圈日報，兼顧異步互動、冷卻、保護與失敗回退。",
)
replace_once(
    "README.md",
    "- **群聊互動**：烤自己、烤群友、隨機烤、吃群友與群聊日報。",
    "- **群聊互動**：烤自己、烤群友、預約未抽目標與群友添柴、隨機烤、吃群友及群聊日報。",
)

# Commands: replace the existing direct-roast section with reservation semantics.
old_roast = '''### `/烤群友 @某人`

需要：

- 群聊環境。
- `enable_roast=true`。
- `enable_group_roast=true`。
- 目標今天已抽取且仍是可料理的小豬。
- 不能對自己使用；想烤自己請用 `/今日烤豬`。

可以直接 @ 目標，也可以回覆對方訊息後使用。

普通烤群友的隨機結果為：

- 60%：成功，目標上桌。
- 30%：目標逃脫。
- 10%：烤架反噬，改為發起者自己的今日小豬上桌；若發起者當前不可料理則幸免。

普通烤群友按「發起者 + 群組」計算冷卻，預設 8 小時，可由 `group_roast_cooldown_hours` 調整。
'''
new_roast = '''### `/烤群友 @某人`

需要：

- 群聊環境。
- `enable_roast=true`。
- `enable_group_roast=true`。
- 不能對自己使用；想烤自己請用 `/今日烤豬`。

可以直接 @ 目標，也可以回覆對方訊息後使用。若目標今天已抽取且仍可料理，直接按普通流程結算：

- 60%：成功，目標上桌。
- 30%：目標逃脫。
- 10%：烤架反噬，改為發起者自己的今日小豬上桌；若發起者當前不可料理則幸免。

普通烤群友按「發起者 + 群組」計算冷卻，預設 8 小時，可由 `group_roast_cooldown_hours` 調整。

#### 目標尚未抽豬：預約烤豬

當 `enable_roast_reservation=true` 時，明確指定一位今天尚未抽豬的目標不再直接失敗，而會建立本群當日預約：

- 第一位玩家成為固定主廚，必須先抽到自己可料理的小豬，並立即消耗一次普通烤架冷卻。
- 後續其他群友對同一目標再使用 `/烤群友` 會免費「添柴」，不消耗自己的冷卻；同一人不重複計數。
- 預約包含主廚在內預設最多 12 人，可由 `roast_reservation_max_participants` 設為 2–20。
- 目標本人在**同一群**顯示自己的今日小豬時一次性觸發；不會因 `/今日小豬 @某人` 只讀查看而觸發。
- 觸發時不再次扣主廚冷卻，仍使用原本 60% / 30% / 10% 結果。
- 添柴目前不提高成功率，只形成群聊參與與 Gameplay Event，避免多人堆疊至必定成功。
- 建立預約同樣尊重昨日被烤保護；隨機烤群友與後門口令不建立預約。
- 預約只屬於當天與當前群，不跨日、不跨群投遞。

完整狀態與一次性結算語義見 [`ROAST-RESERVATIONS.md`](ROAST-RESERVATIONS.md)。
'''
replace_once("docs/COMMANDS.md", old_roast, new_roast)

# Correct the stale pre-PR51 daily report description while touching commands.
old_report = '''只可在群聊中使用，輸出：

- 本群今日抽豬人數。
- 本群今日被吃人數。
- 若存在被吃成員，隨機點名一位獲得「可憐被吃」稱號。
'''
new_report = '''只可在群聊中使用，生成當天卡片化統計海報，包括活躍／抽豬、成功燒烤、被吃、逃脫、反噬、熱門豬，以及「燒烤狂人」「最慘食材」「逃脫大師」「反噬之王」等真實並列稱號。手動查看不觸發可選「今日祭品」。完整自動推送與補發語義見 [`DAILY-REPORT.md`](DAILY-REPORT.md)。
'''
replace_once("docs/COMMANDS.md", old_report, new_report)
replace_once(
    "docs/COMMANDS.md",
    "| `enable_group_roast` | 烤群友、隨機烤群友、後門口令 |",
    "| `enable_group_roast` | 烤群友、隨機烤群友、預約烤豬、後門口令 |\n| `enable_roast_reservation` | 明確指定尚未抽豬目標時建立／加入預約 |\n| `roast_reservation_max_participants` | 每張預約可參與的主廚 + 添柴人數上限 |",
)

# Configuration table.
replace_once(
    "docs/CONFIGURATION.md",
    "| `enable_group_roast` | bool | `true` | `true` / `false` | 群聊烤群友玩法開關，包括普通、隨機與後門口令。 |",
    "| `enable_group_roast` | bool | `true` | `true` / `false` | 群聊烤群友玩法開關，包括普通、預約、隨機與後門口令。 |\n| `enable_roast_reservation` | bool | `true` | `true` / `false` | 明確 `/烤群友 @尚未抽豬目標` 時建立同群當日預約；隨機／後門不建立。 |\n| `roast_reservation_max_participants` | int | `12` | `2-20` | 每張預約包含固定主廚在內的最大參與人數；後續添柴不消耗自己的普通冷卻。 |",
)
replace_once(
    "docs/CONFIGURATION.md",
    "| `group_roast_cooldown_hours` | float | `8` | `1-72` | 普通烤群友按「發起者 + 群組」計算的冷卻時間。後門口令可繞過。 |",
    "| `group_roast_cooldown_hours` | float | `8` | `1-72` | 普通烤群友按「發起者 + 群組」計算冷卻；第一位主廚建立預約時消耗一次，添柴與預約觸發不重複扣除。後門可繞過。 |",
)
replace_once(
    "docs/CONFIGURATION.md",
    "AI 烤豬文案預設關閉。啟用後，同一隻小豬同一天最多實際進行一次模型生成嘗試；成功文案會保留並在近七個自然日窗口內供後續復用。這可以避免熱門小豬被多人重複烤時反覆消耗模型 Token。",
    "### 預約烤豬建議\n\n預約只在明確指定未抽豬目標時建立。主廚先支付普通冷卻，目標在同群顯示自己的今日小豬時才結算；添柴不增加成功率。詳細行為見 [`ROAST-RESERVATIONS.md`](ROAST-RESERVATIONS.md)。\n\n### AI 文案成本與節流\n\nAI 烤豬文案預設關閉。啟用後，同一隻小豬同一天最多實際進行一次模型生成嘗試；成功文案會保留並在近七個自然日窗口內供後續復用。這可以避免熱門小豬被多人重複烤時反覆消耗模型 Token。",
)
# The previous replacement leaves the old heading immediately before our inserted heading.
replace_once(
    "docs/CONFIGURATION.md",
    "### AI 文案成本與節流\n\n### 預約烤豬建議",
    "### 預約烤豬建議",
)

# Docs index.
replace_once(
    "docs/README.md",
    "| [`DAILY-REPORT.md`](DAILY-REPORT.md) | 豬圈日報統計、稱號、自動推送、補發與可選祭品 |",
    "| [`DAILY-REPORT.md`](DAILY-REPORT.md) | 豬圈日報統計、稱號、自動推送、補發與可選祭品 |\n| [`ROAST-RESERVATIONS.md`](ROAST-RESERVATIONS.md) | 預約烤豬、添柴、一次性觸發與 Gameplay Event |",
)

# Architecture: reservation event names are no longer merely reserved.
replace_once(
    "docs/ARCHITECTURE.md",
    "- 預約烤豬：`roast_reservation_created/joined/triggered/cancelled`；",
    "- 預約烤豬：已啟用 `roast_reservation_created/joined/triggered`；`roast_reservation_cancelled` 保留給未來顯式取消流程；",
)

# Changelog.
replace_once(
    "CHANGELOG.md",
    "### 新功能\n\n- 新增 EX Lv.1–5 稀疏成長差分",
    "### 新功能\n\n- 新增可配置預約烤豬：明確指定尚未抽豬的目標時，第一位主廚支付普通冷卻建立同群當日預約，後續群友可免費添柴；目標本人在同群顯示今日小豬後一次性按原 60/30/10 結算。\n- 預約預設最多 12 人（可配置 2–20），建立時尊重昨日被烤保護；隨機烤與後門不建立預約，添柴不直接提高成功率。\n- 預約狀態在消息投遞前先標記 resolved，避免適配器超時造成重複結算；流程接入 `roast_reservation_created/joined/triggered` 與既有燒烤 outcome Gameplay Event，因此日報可沿用原統計。\n- 新增 [`docs/ROAST-RESERVATIONS.md`](docs/ROAST-RESERVATIONS.md) 說明群／日隔離、冷卻支付與一次性語義。\n- 新增 EX Lv.1–5 稀疏成長差分",
)
