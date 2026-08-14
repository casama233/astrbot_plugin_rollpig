from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
original = ROOT / "scripts" / "_apply_phase3b_oven_refill.py"
source = original.read_text(encoding="utf-8")

# Execute only the storage portion of the verified v1 patcher. Its main.py
# marker assumed a different import ordering than the real Star entry module.
cut = source.index("# Main feature integration and command registration.")
exec(compile(source[:cut], str(original), "exec"), {"__name__": "__main__", "__file__": str(original)})


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual < count:
        raise SystemExit(f"{path}: marker missing ({actual} < {count}): {old[:100]!r}")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


# Real main.py entry-point ordering.
replace(
    "main.py",
    "    from .permanent_collection_feature import PermanentCollectionMixin\n    from .roast_reservation_feature import RoastReservationMixin\n",
    "    from .permanent_collection_feature import PermanentCollectionMixin\n    from .roast_reservation_feature import RoastReservationMixin\n    from .oven_refill_feature import OvenRefillMixin\n",
)
replace(
    "main.py",
    "    from permanent_collection_feature import PermanentCollectionMixin\n    from roast_reservation_feature import RoastReservationMixin\n",
    "    from permanent_collection_feature import PermanentCollectionMixin\n    from roast_reservation_feature import RoastReservationMixin\n    from oven_refill_feature import OvenRefillMixin\n",
)
replace(
    "main.py",
    "class RollPigPlugin(\n    RoastReservationMixin,\n",
    "class RollPigPlugin(\n    OvenRefillMixin,\n    RoastReservationMixin,\n",
)
command_marker = """    @filter.command('烤群友', alias={'烤群友'}, priority=1000)\n"""
command_insert = """    @filter.command('烤箱补货', alias={'烤箱補貨'}, priority=1000)\n    async def oven_refill(self, event: AstrMessageEvent):\n        \"\"\"发起本群今日活跃玩家的协作补货。\"\"\"\n        return await super().oven_refill(event)\n\n    @filter.command('添煤', priority=1000)\n    async def oven_refill_support(self, event: AstrMessageEvent):\n        \"\"\"为本群当前补货轮次添加一次唯一支持。\"\"\"\n        return await super().oven_refill_support(event)\n\n"""
replace("main.py", command_marker, command_insert + command_marker)

# Config additions.
config_marker = "    \"enable_roast_protection\": {\n"
config_insert = """    \"enable_oven_refill\": {\n        \"description\": \"开启群体烤箱补货\",\n        \"hint\": \"允许本群今日活跃玩家使用 /烤箱补货 发起补货、/添煤 参与；达标后为本群今日活跃玩家恢复 +1 格烤箱能量\",\n        \"type\": \"bool\",\n        \"default\": true\n    },\n    \"oven_refill_daily_limit\": {\n        \"description\": \"每群每日成功补货上限\",\n        \"hint\": \"范围 1-5，默认 2；失败或因所有人已满而作废的轮次不计入成功次数\",\n        \"type\": \"int\",\n        \"default\": 2\n    },\n    \"oven_refill_support_ratio_percent\": {\n        \"description\": \"首次补货活跃人数支持比例（百分比）\",\n        \"hint\": \"默认 30%；例如今日活跃 16 人时首次需要 5 人支持，仍受最少支持人数约束\",\n        \"type\": \"int\",\n        \"default\": 30\n    },\n    \"oven_refill_min_supporters\": {\n        \"description\": \"补货最少支持人数\",\n        \"hint\": \"范围 2-20，默认 3；若本群今日只有 2 位活跃玩家，则需要两人全部支持\",\n        \"type\": \"int\",\n        \"default\": 3\n    },\n    \"oven_refill_extra_supporters_per_success\": {\n        \"description\": \"当天每成功补货一次后增加的支持人数\",\n        \"hint\": \"范围 0-10，默认 2；第二轮及以后逐步提高门槛，但不会超过本群今日活跃人数\",\n        \"type\": \"int\",\n        \"default\": 2\n    },\n"""
replace("_conf_schema.json", config_marker, config_insert + config_marker)

# Domain calls prune refill rows at the current daily boundary.
feature = ROOT / "oven_refill_feature.py"
text = feature.read_text(encoding="utf-8")
text = text.replace(
    "                extra_per_success=self.oven_refill_extra_supporters_per_success,\n            )",
    "                extra_per_success=self.oven_refill_extra_supporters_per_success,\n                cutoff_date=draw_date,\n            )",
    1,
)
text = text.replace(
    "                recovery_seconds=self.group_roast_cooldown_seconds,\n            )",
    "                recovery_seconds=self.group_roast_cooldown_seconds,\n                cutoff_date=draw_date,\n            )",
    1,
)
feature.write_text(text, encoding="utf-8")

print("Phase 3B v2 patch applied")
