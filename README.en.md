# RollPig Plus — Today's Pig for AstrBot (今日小豬 · 增強版)

[简体中文](README.zh-CN.md) · [繁體中文](README.md) · **English**

`astrbot_plugin_rollpig_plus`: daily pig draws, persistent collections, EX progression and cooperative group-chat roasting.

Current source version **v3.12.4**. **Only a published stable Release with matching tag, ZIP and SHA256SUMS is considered update-ready; merging into main does not publish an update.** [Stable Releases](https://github.com/casama233/astrbot_plugin_rollpig/releases/latest) · [Full wiki](docs/index.md).

> [!CAUTION]
> This plugin contains AI-generated code reviewed by humans. Defects, security flaws or compatibility problems may remain. Review and test it before using sensitive accounts or production environments.

> [!IMPORTANT]
> **Upstream provenance:** Direct parent [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig), earlier [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig). Later features also referenced or adapted work from [Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus). See [ATTRIBUTION.md](ATTRIBUTION.md) for MIT notices and the separate rights boundaries for code, mechanics, images, copy and data. Unverified third-party art/text is not automatically redistributable.

## Features

| System | What it does |
| --- | --- |
| Daily pig | One stable draw per user per day, no reroll on repeat; yesterday, tomorrow and weekly views |
| Persistent collection | `/我的豬圈` records unlocked species, appearances, favorites, EX and retirement history |
| EX growth | Repeated appearances begin EX from the second draw; official pigs offer levels 1–5 with distinct text/art |
| New-pig pity | Repetition plus multi-day fatigue can raise conditional new-pig redraw probability up to **80%** |
| Group roasting | Roast yourself, others or a random member, group eating, next-day protection and backlash |
| Roast Charge | Per user and group, default **2 stored charges**, independently regenerated |
| Reservations | Reserve an unavailable target; `/添柴 @target` joins a specific reservation |
| Oven refills | `/烤箱補貨` starts cooperative refill; qualified depleted participants recover up to one charge |
| Daily report | Poster of roasting, escape, backlash, food and titles; manual view read-only, auto-push per-group opt-in |
| Creator workbench | Local pigs, EX variants, private sources and manually reviewed public submissions |

## Installation

| Requirement | Value |
| --- | --- |
| AstrBot | **4.26.0+** |
| Python | **3.10+** |
| Python packages | `Pillow >=10.0.0`, `httpx >=0.27.0,<1.0.0` |
| Plugin identity | **`astrbot_plugin_rollpig_plus`** |

Install “今日小豬 · 增強版” from the AstrBot marketplace or clone manually:

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

Restart AstrBot and verify the loaded plugin ID. **Since v3.2.0 this enhanced edition uses a separate code/config/data namespace; do not overwrite the old `astrbot_plugin_rollpig` directory.** See [migration and recovery](docs/OPERATIONS.md).

## Main commands

| Original command | Meaning |
| --- | --- |
| `/今日小豬` | Draw today's pig |
| `/豬豬幫助` | Show features actually enabled in this installation |
| `/我的豬圈 [頁碼]` | View persistent pig collection |
| `/找豬 關鍵詞` | Search ID, name, description or full lore |
| `/烤群友 @某人` | Attempt to roast a group member |
| `/烤箱補貨` | Initiate a group oven refill |
| `/添柴` | Participate in current refill or unambiguous reservation |
| `/添柴 @某人` | Join a reservation for that user |
| `/豬圈日報` | Read the daily report |

Some commands have Simplified/Traditional Chinese aliases. **Only [COMMANDS.md](docs/COMMANDS.md) and runtime `/豬豬幫助` are authoritative for current aliases and limits.** This README does not add new commands.

## Collection, EX and pity

`/我的豬圈` records what players have **actually owned**, not merely what the currently available resource pool contains. Retired pigs with historical ownership can remain listed; explicitly tombstoned content still respects blocking rules. Cards show current progress, historical holdings, most-returned pig, highest EX and undiscovered variants. See [collection/pity](docs/gameplay/collection-pity.md) and [EX growth](docs/gameplay/ex-growth.md).

## Roast Charge and outcomes

1. **Charge gates whether a roast can start.** Each player has 2 charges per group by default. `group_roast_cooldown_hours` is the recovery time **for each missing charge**, default **8 hours**, not a single global cooldown.
2. **The shared outcome weights are 70/20/10:** **70% success, 20% escape, 10% backlash**, confirmed by the current `services/roast_service.py` policy and tests. Reservations and firewood do not increase success odds.
3. **`/添柴` is contextual.** It joins an active refill, or a single unambiguous reservation if no refill exists. `/添柴 @target` explicitly joins that target. Multiple reservations require a target.

Older `/添煤`, `/加煤`, `/烤箱添煤`, `/烤箱添柴` remain compatibility-only refill aliases. See [Charge](docs/gameplay/roast-charge.md), [outcomes](docs/gameplay/roast-outcomes.md) and [reservations](docs/ROAST-RESERVATIONS.md).

## Daily reports

Manual `/豬圈日報` is read-only. Automatic reports have a global master switch but still require **explicit group-by-group opt-in**. They do not start merely because someone used the plugin. Optional “Today's Sacrifice” is disabled by default and may only run in the automatic report path. See [daily reports](docs/gameplay/daily-report.md).

## Administration, sources and security

The AstrBot Plugin Page workbench covers statistics, pig entries, EX 1–5 text/art, local assets, public contribution review, source synchronization, SQLite/JSON maintenance and validated stable-Release updates.

Source layers: **built-in / AstrBot v1 / private manifest → local additions and overrides → delete/tombstone masks → final draw pool**. Syncing the base layer must not erase local creations. Default manifest: `https://curryudon.top/astrbot-rollpig/v1/manifest.json`. A 403 may reflect a client-protocol check, **not cryptographically strong authentication**; real private sources need your own Token/mTLS boundary.

Public submissions are sent only after explicit admin approval and include pig ID, names, descriptions, full lore, artwork and EX variants. **They do not include original group chats, group IDs, SQLite databases, backups or plugin configuration.** Third-party art and prose retain their separate rights.

Core data is normalized in SQLite; JSON is for export/disaster recovery. Downloads switch atomically only after manifest, size, SHA-256 and image checks, keeping last good data on failure. Identity migration uses **Copy → Verify → Atomic Commit**, and unproven cross-group identities are not silently merged. See [OPERATIONS.md](docs/OPERATIONS.md) and [COLLECTION-IDENTITY.md](docs/COLLECTION-IDENTITY.md).

## Configuration

Common keys: `enable_new_pig_pity`, `pity_step_percent`, `enable_daily_duplicate_pity`, `group_roast_max_charges` (default 2), `group_roast_cooldown_hours` (per-charge recovery, default 8 hours), `enable_roast_reservation`, `roast_reservation_max_participants`, `enable_oven_refill`, `oven_refill_*`, `enable_daily_report`, `daily_report_*`, `resource_sync_enabled`, `resource_manifest_url`, `storage_backend`. Complete values: [CONFIGURATION.md](docs/CONFIGURATION.md).

## Documentation, development and license

[Quick start](docs/getting-started/index.md) · [Gameplay](docs/gameplay/index.md) · [Commands](docs/COMMANDS.md) · [Creators](docs/creators/index.md) · [Sources](docs/RESOURCE-MANAGEMENT.md) · [Operations](docs/OPERATIONS.md) · [Architecture](docs/ARCHITECTURE.md).

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py legacy_main.py storage services renderers
pytest -q
pre-commit run --all-files --show-diff-on-failure
```

Release gates additionally verify real AstrBot loading, marketplace packaging, strict wiki builds and resource source validity. Code uses [MIT](LICENSE); **third-party images, prose and data do not automatically carry the same redistribution rights**. See [ATTRIBUTION.md](ATTRIBUTION.md).
