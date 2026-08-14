from __future__ import annotations

import json
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one marker, found {text.count(old)}")
    file.write_text(text.replace(old, new), encoding="utf-8")


# Charge policy: group refill grants at most one cell after applying lazy recovery.
roast = Path("roast_charges.py")
text = roast.read_text(encoding="utf-8")
if "def add_roast_charge_state(" not in text:
    text += '''\n\ndef add_roast_charge_state(\n    state: Mapping[str, Any] | None,\n    *,\n    now: float,\n    max_charges: int,\n    recovery_seconds: int,\n) -> dict[str, Any]:\n    """Refresh first, then grant at most one charge without exceeding capacity."""\n    refreshed = refresh_roast_charge_state(\n        state,\n        now=now,\n        max_charges=max_charges,\n        recovery_seconds=recovery_seconds,\n    )\n    before = int(refreshed["charges"])\n    capacity = int(refreshed["max_charges"])\n    after = min(capacity, before + 1)\n    anchor = float(refreshed["refill_anchor"])\n    now_value = float(now)\n    if after >= capacity:\n        anchor = now_value\n        next_refill = 0\n    else:\n        next_refill = int(refreshed.get("next_refill_seconds", 0) or 0)\n    return {\n        "charges": after,\n        "max_charges": capacity,\n        "refill_anchor": anchor,\n        "next_refill_seconds": next_refill,\n        "increased": after > before,\n    }\n'''
roast.write_text(text, encoding="utf-8")

# SQLite legacy authority gets one transactional grant primitive.
sql = Path("storage/sqlite_storage.py")
s = sql.read_text(encoding="utf-8")
s = s.replace(
    "from ..roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state",
    "from ..roast_charges import add_roast_charge_state, bootstrap_legacy_cooldown, consume_roast_charge_state",
)
s = s.replace(
    "from roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state",
    "from roast_charges import add_roast_charge_state, bootstrap_legacy_cooldown, consume_roast_charge_state",
)
marker = '''    def consume_roast_charge(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n'''
if "def _grant_roast_charge_tx(" not in s:
    if s.count(marker) != 1:
        raise SystemExit("sqlite_storage: consume_roast_charge marker missing")
    helper = '''    def _grant_roast_charge_tx(\n        self,\n        connection: sqlite3.Connection,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n        group_id = str(group_id)\n        actor_id = str(actor_id)\n        charge_key = f"{group_id}:{actor_id}"\n        now_value = float(now)\n        row = connection.execute(\n            "SELECT last_used_at, charges, refill_anchor FROM roast_cooldowns "\n            "WHERE cooldown_key = ?",\n            (charge_key,),\n        ).fetchone()\n        if row and int(row["charges"]) >= 0:\n            state = {\n                "charges": int(row["charges"]),\n                "refill_anchor": float(row["refill_anchor"]),\n            }\n        else:\n            state = bootstrap_legacy_cooldown(\n                float(row["last_used_at"]) if row else 0,\n                now=now_value,\n                max_charges=max_charges,\n                recovery_seconds=recovery_seconds,\n            )\n        result = add_roast_charge_state(\n            state,\n            now=now_value,\n            max_charges=max_charges,\n            recovery_seconds=recovery_seconds,\n        )\n        self._remember_identity(connection, actor_id)\n        last_used_at = float(row["last_used_at"]) if row else 0.0\n        connection.execute(\n            """\n            INSERT INTO roast_cooldowns(\n                cooldown_key, group_id, actor_id, last_used_at, charges, refill_anchor\n            ) VALUES (?, ?, ?, ?, ?, ?)\n            ON CONFLICT(cooldown_key) DO UPDATE SET\n                group_id = excluded.group_id,\n                actor_id = excluded.actor_id,\n                charges = excluded.charges,\n                refill_anchor = excluded.refill_anchor\n            """,\n            (\n                charge_key, group_id, actor_id, last_used_at,\n                int(result["charges"]), float(result["refill_anchor"]),\n            ),\n        )\n        return result\n\n'''
    s = s.replace(marker, helper + marker)
public_marker = '''    def consume_roast_cooldown(\n        self,\n        *,\n        group_id: str,\n'''
if "def grant_roast_charge(" not in s:
    if s.count(public_marker) != 1:
        raise SystemExit("sqlite_storage: cooldown marker missing")
    public = '''    def grant_roast_charge(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n        """Grant at most one user × group charge through normalized SQL."""\n        with self.transaction() as connection:\n            result = self._grant_roast_charge_tx(\n                connection,\n                group_id=group_id, actor_id=actor_id, now=now,\n                max_charges=max_charges, recovery_seconds=recovery_seconds,\n            )\n            roast = self._roast_document_from_sql(connection)\n            self._write_document_tx(connection, "roast_state.json", roast)\n            self._set_write_authority(connection)\n            result["roast_state"] = roast\n            return result\n\n'''
    s = s.replace(public_marker, public + public_marker)
sql.write_text(s, encoding="utf-8")

# SQLite v3 overrides the legacy compatibility-document behavior.
primary = Path("storage/sqlite_primary.py")
p = primary.read_text(encoding="utf-8")
primary_marker = '''    def consume_roast_cooldown(\n        self,\n        *,\n        group_id: str,\n'''
if "def grant_roast_charge(" not in p:
    if p.count(primary_marker) != 1:
        raise SystemExit("sqlite_primary: cooldown marker missing")
    method = '''    def grant_roast_charge(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n        with self.transaction() as connection:\n            result = self._grant_roast_charge_tx(\n                connection,\n                group_id=group_id, actor_id=actor_id, now=now,\n                max_charges=max_charges, recovery_seconds=recovery_seconds,\n            )\n            self._mark_primary_write_tx(connection)\n            return result\n\n'''
    p = p.replace(primary_marker, method + primary_marker)
primary.write_text(p, encoding="utf-8")

# AstrBot config surface.
conf_path = Path("_conf_schema.json")
conf = json.loads(conf_path.read_text(encoding="utf-8"))
conf.setdefault("enable_oven_refill", {
    "description": "开启群体烤箱补货",
    "hint": "允许今日在本群参与过 RollPig 的群友发起 /烤箱补货 并通过 /添煤 协作恢复烤箱能量",
    "type": "bool", "default": True,
})
conf.setdefault("oven_refill_daily_limit", {
    "description": "每日每群补货成功上限",
    "hint": "范围 1-5，默认 2；失败或全员已满的作废轮次不计入",
    "type": "int", "default": 2,
})
conf.setdefault("oven_refill_support_ratio_percent", {
    "description": "补货基础参与比例（百分比）",
    "hint": "按今日活跃人数计算第一轮需要的支持者，默认 30%",
    "type": "int", "default": 30,
})
conf.setdefault("oven_refill_min_supporters", {
    "description": "补货最低支持人数",
    "hint": "范围 2-20，默认 3；2 人小群固定需要 2 人",
    "type": "int", "default": 3,
})
conf.setdefault("oven_refill_max_base_supporters", {
    "description": "首轮基础支持人数上限",
    "hint": "范围 3-50，默认 8；后续成功轮次仍会继续增加难度",
    "type": "int", "default": 8,
})
conf.setdefault("oven_refill_extra_supporters_per_success", {
    "description": "每次成功后额外支持人数",
    "hint": "同群同日每成功一次，下一轮额外需要的人数；默认 +2",
    "type": "int", "default": 2,
})
conf_path.write_text(json.dumps(conf, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

# Dynamic help follows the feature flag and command surface.
replace_once(
    "help_system.py",
    "    enable_roast_reservation: bool = True\n    enable_group_eat: bool = True\n",
    "    enable_roast_reservation: bool = True\n    enable_oven_refill: bool = True\n    enable_group_eat: bool = True\n",
)
replace_once(
    "help_system.py",
    '''        group_entries.extend(\n            [\n                HelpEntry("/烤群友 @某人", detail),\n                HelpEntry("/随机烤群友", "从今天在本群抽过猪的可料理群友中随机挑选"),\n                HelpEntry("/打点后厨 @某人", "后门别名每日一次；超管可用 /强行点火"),\n            ]\n        )\n''',
    '''        group_entries.extend(\n            [\n                HelpEntry("/烤群友 @某人", detail),\n                HelpEntry("/随机烤群友", "从今天在本群抽过猪的可料理群友中随机挑选"),\n                HelpEntry("/打点后厨 @某人", "后门别名每日一次；超管可用 /强行点火"),\n            ]\n        )\n        if state.enable_oven_refill:\n            group_entries.extend(\n                [\n                    HelpEntry("/烤箱补货", "发起本群今日协作补货；发起者自动贡献第一份煤"),\n                    HelpEntry("/添煤", "今日在本群参与过 RollPig 的群友每轮可支持一次"),\n                ]\n            )\n''',
)
replace_once(
    "help_system.py",
    '''    if group_roast_enabled and state.enable_roast_reservation:\n''',
    '''    if group_roast_enabled and state.enable_oven_refill:\n        mechanics.append(\n            HelpEntry("群体补货", "达成群体支持门槛后，今日活跃玩家统一恢复 +1 格能量", kind="feature")\n        )\n    if group_roast_enabled and state.enable_roast_reservation:\n''',
)
replace_once(
    "help_feature.py",
    '''            enable_roast_reservation=bool(\n                getattr(self, "enable_roast_reservation", True)\n            ),\n            enable_group_eat=bool(getattr(self, "enable_group_eat", True)),\n''',
    '''            enable_roast_reservation=bool(\n                getattr(self, "enable_roast_reservation", True)\n            ),\n            enable_oven_refill=bool(getattr(self, "enable_oven_refill", True)),\n            enable_group_eat=bool(getattr(self, "enable_group_eat", True)),\n''',
)

# Daily report consumes the shared gameplay events.
report = Path("daily_report_core.py")
r = report.read_text(encoding="utf-8")
old_import = '''        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n'''
new_import = '''        EVENT_OVEN_REFILL_SUCCEEDED,\n        EVENT_OVEN_REFILL_SUPPORTED,\n        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n'''
if r.count(old_import) != 2:
    raise SystemExit(f"daily_report_core import markers: {r.count(old_import)}")
r = r.replace(old_import, new_import)
r = r.replace(
    "    backlashes = 0\n\n    for raw in events:\n",
    "    backlashes = 0\n    oven_refill_supports = 0\n    oven_refills = 0\n\n    for raw in events:\n",
    1,
)
r = r.replace(
    '''        elif kind == EVENT_ROAST_BACKLASH:\n            backlashes += 1\n            if target:\n                backlash_king[target] += 1\n            if victim:\n                miserable[victim] += 1\n                event_roasts += 1\n''',
    '''        elif kind == EVENT_ROAST_BACKLASH:\n            backlashes += 1\n            if target:\n                backlash_king[target] += 1\n            if victim:\n                miserable[victim] += 1\n                event_roasts += 1\n        elif kind == EVENT_OVEN_REFILL_SUPPORTED:\n            oven_refill_supports += 1\n        elif kind == EVENT_OVEN_REFILL_SUCCEEDED:\n            oven_refills += 1\n''',
    1,
)
r = r.replace(
    '        "backlashes": backlashes,\n        "popular_pigs": popular_items,\n',
    '        "backlashes": backlashes,\n        "oven_refill_supports": oven_refill_supports,\n        "oven_refills": oven_refills,\n        "popular_pigs": popular_items,\n',
    1,
)
report.write_text(r, encoding="utf-8")

# Render a compact refill line without changing the report layout architecture.
replace_once(
    "daily_report_feature.py",
    "        pop_y = 558\n",
    '''        draw.text(\n            (58, 531),\n            f"⛽ 烤箱补货 {int(report.get('oven_refills', 0) or 0)} 次 · 添煤 {int(report.get('oven_refill_supports', 0) or 0)} 人次",\n            font=small_font,\n            fill=palette["secondary"],\n        )\n\n        pop_y = 558\n''',
)

# Command-registration safety contracts include the focused mixin and new commands.
cmd = Path("tests/test_command_registration_boundary.py")
c = cmd.read_text(encoding="utf-8")
c = c.replace(
    "'roast_reservation_feature.py', 'help_feature.py'",
    "'roast_reservation_feature.py', 'help_feature.py', 'oven_refill_feature.py'",
)
if '"oven_refill"' not in c:
    c = c.replace('    "my_pigsty",\n', '    "my_pigsty",\n    "oven_refill",\n    "oven_refill_support",\n', 1)
cmd.write_text(c, encoding="utf-8")

hotfix = Path("tests/test_v361_hotfix_contract.py")
h = hotfix.read_text(encoding="utf-8")
if '"oven_refill_feature.py"' not in h:
    h = h.replace(
        '    "roast_reservation_feature.py",\n',
        '    "roast_reservation_feature.py",\n    "oven_refill_feature.py",\n',
        1,
    )
hotfix.write_text(h, encoding="utf-8")

# Add direct policy tests for +1 behavior.
charge_test = Path("tests/test_roast_charges.py")
if charge_test.exists():
    t = charge_test.read_text(encoding="utf-8")
    if "test_group_refill_adds_only_one_charge" not in t:
        t += '''\n\ndef test_group_refill_adds_only_one_charge():\n    from roast_charges import add_roast_charge_state\n\n    result = add_roast_charge_state(\n        {"charges": 0, "refill_anchor": 1000},\n        now=1200, max_charges=2, recovery_seconds=800,\n    )\n    assert result["charges"] == 1\n    assert result["increased"] is True\n    assert result["refill_anchor"] == 1000\n\n\ndef test_group_refill_never_overbanks_and_stops_recovery_when_full():\n    from roast_charges import add_roast_charge_state\n\n    result = add_roast_charge_state(\n        {"charges": 1, "refill_anchor": 1000},\n        now=1200, max_charges=2, recovery_seconds=800,\n    )\n    assert result["charges"] == 2\n    assert result["refill_anchor"] == 1200\n    assert result["next_refill_seconds"] == 0\n'''
        charge_test.write_text(t, encoding="utf-8")

# Existing dynamic-help tests should explicitly verify the new capability.
dynamic = Path("tests/test_dynamic_help_system.py")
d = dynamic.read_text(encoding="utf-8")
if 'assert "/烤箱补货" in commands' not in d:
    d = d.replace(
        '    assert "/猪圈日报 状态" in commands\n',
        '    assert "/猪圈日报 状态" in commands\n    assert "/烤箱补货" in commands\n    assert "/添煤" in commands\n',
        1,
    )
dynamic.write_text(d, encoding="utf-8")

# Daily-report aggregation regression.
daily_test = Path("tests/test_daily_report.py")
if daily_test.exists():
    dt = daily_test.read_text(encoding="utf-8")
    if "test_daily_report_counts_oven_refill_events" not in dt:
        dt += '''\n\ndef test_daily_report_counts_oven_refill_events():\n    from daily_report_core import aggregate_daily_report\n\n    result = aggregate_daily_report(\n        [],\n        [\n            {"kind": "oven_refill_supported", "actor_id": "u1"},\n            {"kind": "oven_refill_supported", "actor_id": "u2"},\n            {"kind": "oven_refill_succeeded", "actor_id": "u2"},\n        ],\n        [],\n    )\n    assert result["oven_refill_supports"] == 2\n    assert result["oven_refills"] == 1\n'''
        daily_test.write_text(dt, encoding="utf-8")

# CI compile surface includes the new feature module.
ci = Path(".github/workflows/ci.yml")
ci_text = ci.read_text(encoding="utf-8")
if "oven_refill_feature.py" not in ci_text:
    ci_text = ci_text.replace(
        "roast_reservations.py roast_reservation_feature.py rollpig_core.py",
        "roast_reservations.py roast_reservation_feature.py oven_refill_feature.py rollpig_core.py",
    )
ci.write_text(ci_text, encoding="utf-8")

# Repair accidental path typo from branch integration if present.
main = Path("main.py")
m = main.read_text(encoding="utf-8").replace(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
main.write_text(m, encoding="utf-8")
