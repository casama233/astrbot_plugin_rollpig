from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    source = target.read_text(encoding="utf-8")
    actual = source.count(old)
    if actual < count:
        raise SystemExit(f"{path}: marker missing ({actual} < {count}): {old[:120]!r}")
    target.write_text(source.replace(old, new, count), encoding="utf-8")


# Daily report aggregation consumes Gameplay Events only.
replace(
    "daily_report_core.py",
    """        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n""",
    """        EVENT_OVEN_REFILL_FAILED,\n        EVENT_OVEN_REFILL_STARTED,\n        EVENT_OVEN_REFILL_SUCCEEDED,\n        EVENT_OVEN_REFILL_SUPPORTED,\n        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n""",
    count=2,
)
replace(
    "daily_report_core.py",
    """    event_roasts = 0\n    escapes = 0\n    backlashes = 0\n\n    for raw in events:\n""",
    """    event_roasts = 0\n    escapes = 0\n    backlashes = 0\n    oven_refill_started = 0\n    oven_refill_supports = 0\n    oven_refill_successes = 0\n    oven_refill_failures = 0\n\n    for raw in events:\n""",
)
replace(
    "daily_report_core.py",
    """        elif kind == EVENT_ROAST_BACKLASH:\n            backlashes += 1\n            if target:\n                backlash_king[target] += 1\n            if victim:\n                miserable[victim] += 1\n                event_roasts += 1\n\n    popular = top_tied(pig_counts)\n""",
    """        elif kind == EVENT_ROAST_BACKLASH:\n            backlashes += 1\n            if target:\n                backlash_king[target] += 1\n            if victim:\n                miserable[victim] += 1\n                event_roasts += 1\n        elif kind == EVENT_OVEN_REFILL_STARTED:\n            oven_refill_started += 1\n            # 发起者会自动贡献本轮第 1 份煤。\n            oven_refill_supports += 1\n        elif kind == EVENT_OVEN_REFILL_SUPPORTED:\n            oven_refill_supports += 1\n        elif kind == EVENT_OVEN_REFILL_SUCCEEDED:\n            oven_refill_successes += 1\n        elif kind == EVENT_OVEN_REFILL_FAILED:\n            oven_refill_failures += 1\n\n    popular = top_tied(pig_counts)\n""",
)
replace(
    "daily_report_core.py",
    """        \"backlashes\": backlashes,\n        \"popular_pigs\": popular_items,\n""",
    """        \"backlashes\": backlashes,\n        \"oven_refill_started\": oven_refill_started,\n        \"oven_refill_supports\": oven_refill_supports,\n        \"oven_refill_successes\": oven_refill_successes,\n        \"oven_refill_failures\": oven_refill_failures,\n        \"popular_pigs\": popular_items,\n""",
)

# 9 metric cards: third row is the Phase 3B group loop.
replace(
    "daily_report_feature.py",
    """        height = 1680 + (285 if sacrifice_id else 0)\n""",
    """        height = 1820 + (285 if sacrifice_id else 0)\n""",
)
replace(
    "daily_report_feature.py",
    """            (\"触发反噬\", report.get(\"backlashes\", 0)),\n        ]\n""",
    """            (\"触发反噬\", report.get(\"backlashes\", 0)),\n            (\"补货发起\", report.get(\"oven_refill_started\", 0)),\n            (\"添煤人次\", report.get(\"oven_refill_supports\", 0)),\n            (\"补货成功\", report.get(\"oven_refill_successes\", 0)),\n        ]\n""",
)
replace("daily_report_feature.py", "        pop_y = 558\n", "        pop_y = 698\n")
replace("daily_report_feature.py", "        awards_y = 846\n", "        awards_y = 986\n")
replace("daily_report_feature.py", "        footer_y = 1512\n", "        footer_y = 1652\n")
replace("daily_report_feature.py", "            sac_y = 1490\n", "            sac_y = 1630\n")
replace("daily_report_feature.py", "            footer_y = 1800\n", "            footer_y = 1940\n")

# Existing report test gains explicit oven-event coverage.
path = ROOT / "tests" / "test_daily_report.py"
source = path.read_text(encoding="utf-8")
addition = '''\n\ndef test_daily_report_aggregates_oven_refill_gameplay_events():\n    events = [\n        {"kind": "oven_refill_started", "actor_id": "a"},\n        {"kind": "oven_refill_supported", "actor_id": "b"},\n        {"kind": "oven_refill_supported", "actor_id": "c"},\n        {"kind": "oven_refill_succeeded", "actor_id": "c"},\n        {"kind": "oven_refill_started", "actor_id": "d"},\n        {"kind": "oven_refill_supported", "actor_id": "e"},\n        {"kind": "oven_refill_failed", "actor_id": "e"},\n    ]\n    report = aggregate_daily_report([], events, [], roast_total=0)\n\n    assert report["oven_refill_started"] == 2\n    # 两位发起者各自动贡献 1 份煤，再加 3 条显式 supported 事件。\n    assert report["oven_refill_supports"] == 5\n    assert report["oven_refill_successes"] == 1\n    assert report["oven_refill_failures"] == 1\n'''
if "test_daily_report_aggregates_oven_refill_gameplay_events" not in source:
    source += addition
path.write_text(source, encoding="utf-8")

print("Phase 3B daily report patch applied")
