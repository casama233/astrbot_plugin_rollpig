from pathlib import Path
import json


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one marker, found {text.count(old)}")
    file.write_text(text.replace(old, new), encoding="utf-8")


# User-facing cooldown language now reflects the charge model.
replace_once(
    "legacy_main.py",
    '''                await event.send(\n                    event.plain_result(\n                        f"烤架还在降温，请 {self._format_cooldown(remaining)} 后再试。"\n                    )\n                )\n''',
    '''                await event.send(\n                    event.plain_result(self._group_roast_unavailable_message(remaining))\n                )\n''',
)
replace_once(
    "roast_reservation_feature.py",
    '''                await event.send(\n                    event.plain_result(\n                        f"烤架还在降温，请 {self._format_cooldown(remaining)} 后再来埋伏。"\n                    )\n                )\n''',
    '''                await event.send(\n                    event.plain_result(self._group_roast_unavailable_message(remaining))\n                )\n''',
)

# Keep the old cooldown setting as a compatibility fallback while exposing the
# real charge/refill settings to AstrBot's config UI.
conf_path = Path("_conf_schema.json")
conf = json.loads(conf_path.read_text(encoding="utf-8"))
old = conf.get("group_roast_cooldown_hours", {})
old["description"] = "旧版烤群友冷却时间（兼容）"
old["hint"] = (
    "v3.6.4 及更早版本的兼容配置；Phase 3 默认仍把此值作为充能恢复小时数的后备值。"
    "新配置请使用 group_roast_charge_recovery_hours。"
)
conf["group_roast_cooldown_hours"] = old
items = list(conf.items())
rebuilt = {}
for key, value in items:
    rebuilt[key] = value
    if key == "group_roast_cooldown_hours":
        rebuilt["group_roast_max_charges"] = {
            "description": "烤箱最大能量格",
            "hint": "按发起者 × 群组独立计算；范围 1-5，默认 2。普通烤群友和创建预约各消耗 1 格，后门与后续添柴不消耗。",
            "type": "int",
            "default": 2,
        }
        rebuilt["group_roast_charge_recovery_hours"] = {
            "description": "烤箱每格恢复时间（小时）",
            "hint": "每隔多少小时自然恢复 1 格能量，范围 1-72，默认 8；恢复不会超过最大能量格。",
            "type": "float",
            "default": 8,
        }
        rebuilt["oven_refill_daily_limit"] = {
            "description": "每日烤箱补货成功上限",
            "hint": "每群每天最多成功补货几次，范围 1-5，默认 2；每次成功仅为今日活跃玩家恢复 +1 格，不会直接回满。",
            "type": "int",
            "default": 2,
        }
conf_path.write_text(json.dumps(rebuilt, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

# Compile the new feature explicitly in CI.
replace_once(
    ".github/workflows/ci.yml",
    "daily_report_core.py daily_report_feature.py gameplay_events.py ex_variants.py ex_variant_feature.py roast_reservations.py roast_reservation_feature.py rollpig_core.py updater.py storage services",
    "daily_report_core.py daily_report_feature.py gameplay_events.py ex_variants.py ex_variant_feature.py roast_reservations.py roast_reservation_feature.py oven_charge_feature.py rollpig_core.py updater.py storage services",
)

# Daily report consumes refill events without owning refill state.
replace_once(
    "daily_report_core.py",
    '''        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n''',
    '''        EVENT_OVEN_REFILL_SUCCEEDED,\n        EVENT_OVEN_REFILL_SUPPORTED,\n        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n''',
)
# Same import exists in direct-load fallback.
text = Path("daily_report_core.py").read_text(encoding="utf-8")
old_fallback = '''        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n'''
if text.count(old_fallback) != 1:
    raise SystemExit("daily_report_core fallback import marker missing")
text = text.replace(
    old_fallback,
    '''        EVENT_OVEN_REFILL_SUCCEEDED,\n        EVENT_OVEN_REFILL_SUPPORTED,\n        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n''',
)
Path("daily_report_core.py").write_text(text, encoding="utf-8")

replace_once(
    "daily_report_core.py",
    '''    event_roasts = 0\n    escapes = 0\n    backlashes = 0\n''',
    '''    event_roasts = 0\n    escapes = 0\n    backlashes = 0\n    oven_refill_supports = 0\n    oven_refills = 0\n''',
)
replace_once(
    "daily_report_core.py",
    '''        elif kind == EVENT_ROAST_BACKLASH:\n            backlashes += 1\n            if target:\n                backlash_king[target] += 1\n            if victim:\n                miserable[victim] += 1\n                event_roasts += 1\n''',
    '''        elif kind == EVENT_ROAST_BACKLASH:\n            backlashes += 1\n            if target:\n                backlash_king[target] += 1\n            if victim:\n                miserable[victim] += 1\n                event_roasts += 1\n        elif kind == EVENT_OVEN_REFILL_SUPPORTED:\n            oven_refill_supports += 1\n        elif kind == EVENT_OVEN_REFILL_SUCCEEDED:\n            oven_refills += 1\n''',
)
replace_once(
    "daily_report_core.py",
    '''        "backlashes": backlashes,\n        "popular_pigs": popular_items,\n''',
    '''        "backlashes": backlashes,\n        "oven_refill_supports": oven_refill_supports,\n        "oven_refills": oven_refills,\n        "popular_pigs": popular_items,\n''',
)

# Compact report line fits in the existing gap below the six metric cards.
replace_once(
    "daily_report_feature.py",
    '''        pop_y = 558\n''',
    '''        draw.text(\n            (58, 531),\n            f"⛽ 烤箱补货 {int(report.get('oven_refills', 0) or 0)} 次 · 添煤 {int(report.get('oven_refill_supports', 0) or 0)} 人次",\n            font=small_font,\n            fill=palette["secondary"],\n        )\n\n        pop_y = 558\n''',
)

# Extend aggregation tests with the new event namespace.
test_path = Path("tests/test_daily_report.py")
if test_path.exists():
    source = test_path.read_text(encoding="utf-8")
    if "test_daily_report_counts_oven_refill_events" not in source:
        source += '''\n\ndef test_daily_report_counts_oven_refill_events():\n    from daily_report_core import aggregate_daily_report\n\n    result = aggregate_daily_report(\n        [],\n        [\n            {"kind": "oven_refill_supported", "actor_id": "u1"},\n            {"kind": "oven_refill_supported", "actor_id": "u2"},\n            {"kind": "oven_refill_succeeded", "actor_id": "u2"},\n        ],\n        [],\n    )\n    assert result["oven_refill_supports"] == 2\n    assert result["oven_refills"] == 1\n'''
        test_path.write_text(source, encoding="utf-8")
