from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual < count:
        raise SystemExit(f"{path}: expected at least {count} marker(s), found {actual}: {old[:80]!r}")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


# Storage contract.
replace(
    "storage/base.py",
    """    def consume_roast_cooldown(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n""",
    """    def consume_roast_cooldown(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n    def consume_roast_charge(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n""",
)

# SQLite imports and schema/projection/compatibility round-trip.
replace(
    "storage/sqlite_storage.py",
    """from .base import StorageBackend\nfrom .json_storage import JSONStorage\n""",
    """from .base import StorageBackend\nfrom .json_storage import JSONStorage\n\ntry:\n    from ..roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\nexcept ImportError:  # pragma: no cover - direct module loading compatibility\n    from roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\n""",
)
replace(
    "storage/sqlite_storage.py",
    """                CREATE TABLE IF NOT EXISTS roast_cooldowns (\n                    cooldown_key TEXT PRIMARY KEY,\n                    group_id TEXT NOT NULL,\n                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),\n                    last_used_at REAL NOT NULL\n                );\n""",
    """                CREATE TABLE IF NOT EXISTS roast_cooldowns (\n                    cooldown_key TEXT PRIMARY KEY,\n                    group_id TEXT NOT NULL,\n                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),\n                    last_used_at REAL NOT NULL,\n                    charges INTEGER NOT NULL DEFAULT -1,\n                    refill_anchor REAL NOT NULL DEFAULT 0\n                );\n""",
)
replace(
    "storage/sqlite_storage.py",
    """                draw_columns = {\n                    str(row[1]) for row in connection.execute(\"PRAGMA table_info(daily_draws)\")\n                }\n""",
    """                cooldown_columns = {\n                    str(row[1])\n                    for row in connection.execute(\"PRAGMA table_info(roast_cooldowns)\")\n                }\n                if \"charges\" not in cooldown_columns:\n                    connection.execute(\n                        \"ALTER TABLE roast_cooldowns ADD COLUMN charges INTEGER NOT NULL DEFAULT -1\"\n                    )\n                if \"refill_anchor\" not in cooldown_columns:\n                    connection.execute(\n                        \"ALTER TABLE roast_cooldowns ADD COLUMN refill_anchor REAL NOT NULL DEFAULT 0\"\n                    )\n                draw_columns = {\n                    str(row[1]) for row in connection.execute(\"PRAGMA table_info(daily_draws)\")\n                }\n""",
)
replace(
    "storage/sqlite_storage.py",
    """            connection.execute(\n                \"INSERT INTO roast_cooldowns VALUES (?, ?, ?, ?)\",\n                (str(cooldown_key), group_id, actor_id, float(used_at or 0)),\n            )\n\n        counts = state.get(\"daily_roast_counts\") if isinstance(state.get(\"daily_roast_counts\"), dict) else {}\n""",
    """            connection.execute(\n                \"INSERT INTO roast_cooldowns(\"\n                \"cooldown_key, group_id, actor_id, last_used_at, charges, refill_anchor\"\n                \") VALUES (?, ?, ?, ?, -1, 0)\",\n                (str(cooldown_key), group_id, actor_id, float(used_at or 0)),\n            )\n\n        charge_states = (\n            state.get(\"roast_charges\")\n            if isinstance(state.get(\"roast_charges\"), dict)\n            else {}\n        )\n        for charge_key, entry in charge_states.items():\n            if not isinstance(entry, dict):\n                continue\n            group_id, separator, actor_id = str(charge_key).rpartition(\":\")\n            if not separator:\n                group_id, actor_id = \"\", str(charge_key)\n            self._remember_identity(connection, actor_id)\n            try:\n                charges = int(entry.get(\"charges\", -1))\n                refill_anchor = float(entry.get(\"refill_anchor\", 0) or 0)\n            except (TypeError, ValueError):\n                continue\n            legacy_last_used = float(cooldowns.get(charge_key, 0) or 0)\n            connection.execute(\n                \"INSERT INTO roast_cooldowns(\"\n                \"cooldown_key, group_id, actor_id, last_used_at, charges, refill_anchor\"\n                \") VALUES (?, ?, ?, ?, ?, ?) \"\n                \"ON CONFLICT(cooldown_key) DO UPDATE SET \"\n                \"group_id = excluded.group_id, actor_id = excluded.actor_id, \"\n                \"charges = excluded.charges, refill_anchor = excluded.refill_anchor\",\n                (\n                    str(charge_key),\n                    group_id,\n                    actor_id,\n                    legacy_last_used,\n                    charges,\n                    refill_anchor,\n                ),\n            )\n\n        counts = state.get(\"daily_roast_counts\") if isinstance(state.get(\"daily_roast_counts\"), dict) else {}\n""",
)
replace(
    "storage/sqlite_storage.py",
    """            \"cooldowns\": {},\n            \"daily_backdoors\": {},\n""",
    """            \"cooldowns\": {},\n            \"roast_charges\": {},\n            \"daily_backdoors\": {},\n""",
)
replace(
    "storage/sqlite_storage.py",
    """        roast[\"cooldowns\"] = {\n            str(row[\"cooldown_key\"]): float(row[\"last_used_at\"])\n            for row in connection.execute(\n                \"SELECT cooldown_key, last_used_at FROM roast_cooldowns \"\n                \"ORDER BY cooldown_key\"\n            ).fetchall()\n        }\n        roast[\"daily_roast_counts\"] = {\n""",
    """        roast[\"cooldowns\"] = {\n            str(row[\"cooldown_key\"]): float(row[\"last_used_at\"])\n            for row in connection.execute(\n                \"SELECT cooldown_key, last_used_at FROM roast_cooldowns \"\n                \"ORDER BY cooldown_key\"\n            ).fetchall()\n        }\n        roast[\"roast_charges\"] = {\n            str(row[\"cooldown_key\"]): {\n                \"charges\": int(row[\"charges\"]),\n                \"refill_anchor\": float(row[\"refill_anchor\"]),\n            }\n            for row in connection.execute(\n                \"SELECT cooldown_key, charges, refill_anchor FROM roast_cooldowns \"\n                \"WHERE charges >= 0 ORDER BY cooldown_key\"\n            ).fetchall()\n        }\n        roast[\"daily_roast_counts\"] = {\n""",
)
# Avoid implicit VALUES arity assumptions now that roast_cooldowns has six columns.
replace(
    "storage/sqlite_storage.py",
    """                \"INSERT INTO roast_cooldowns(\n                    cooldown_key, group_id, actor_id, last_used_at\n                ) VALUES (?, ?, ?, ?)\n""",
    """                \"INSERT INTO roast_cooldowns(\n                    cooldown_key, group_id, actor_id, last_used_at\n                ) VALUES (?, ?, ?, ?)\n""",
)

# Insert one shared transactional token-bucket implementation before legacy cooldown API.
sqlite_marker = """    def consume_roast_cooldown(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        cooldown_seconds: int,\n    ) -> dict[str, Any]:\n"""
sqlite_insert = """    def _consume_roast_charge_tx(\n        self,\n        connection: sqlite3.Connection,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n        group_id = str(group_id)\n        actor_id = str(actor_id)\n        charge_key = f\"{group_id}:{actor_id}\"\n        now_value = float(now)\n        row = connection.execute(\n            \"SELECT last_used_at, charges, refill_anchor FROM roast_cooldowns \"\n            \"WHERE cooldown_key = ?\",\n            (charge_key,),\n        ).fetchone()\n        if row and int(row[\"charges\"]) >= 0:\n            state = {\n                \"charges\": int(row[\"charges\"]),\n                \"refill_anchor\": float(row[\"refill_anchor\"]),\n            }\n        else:\n            state = bootstrap_legacy_cooldown(\n                float(row[\"last_used_at\"]) if row else 0,\n                now=now_value,\n                max_charges=max_charges,\n                recovery_seconds=recovery_seconds,\n            )\n        result = consume_roast_charge_state(\n            state,\n            now=now_value,\n            max_charges=max_charges,\n            recovery_seconds=recovery_seconds,\n        )\n        if not result.get(\"consumed\"):\n            return result\n        self._remember_identity(connection, actor_id)\n        connection.execute(\n            \"\"\"\n            INSERT INTO roast_cooldowns(\n                cooldown_key, group_id, actor_id, last_used_at, charges, refill_anchor\n            ) VALUES (?, ?, ?, ?, ?, ?)\n            ON CONFLICT(cooldown_key) DO UPDATE SET\n                group_id = excluded.group_id,\n                actor_id = excluded.actor_id,\n                last_used_at = excluded.last_used_at,\n                charges = excluded.charges,\n                refill_anchor = excluded.refill_anchor\n            \"\"\",\n            (\n                charge_key,\n                group_id,\n                actor_id,\n                now_value,\n                int(result[\"charges\"]),\n                float(result[\"refill_anchor\"]),\n            ),\n        )\n        return result\n\n    def consume_roast_charge(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n        \"\"\"Consume one user × group charge and persist its refill queue.\"\"\"\n        with self.transaction() as connection:\n            result = self._consume_roast_charge_tx(\n                connection,\n                group_id=group_id,\n                actor_id=actor_id,\n                now=now,\n                max_charges=max_charges,\n                recovery_seconds=recovery_seconds,\n            )\n            if result.get(\"consumed\"):\n                roast = self._roast_document_from_sql(connection)\n                self._write_document_tx(connection, \"roast_state.json\", roast)\n                self._set_write_authority(connection)\n                result[\"roast_state\"] = roast\n            return result\n\n"""
replace("storage/sqlite_storage.py", sqlite_marker, sqlite_insert + sqlite_marker)

# SQL-primary avoids compatibility document writes on hot paths.
primary_marker = """    def consume_roast_cooldown(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        cooldown_seconds: int,\n    ) -> dict[str, Any]:\n"""
primary_insert = """    def consume_roast_charge(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n        with self.transaction() as connection:\n            result = self._consume_roast_charge_tx(\n                connection,\n                group_id=group_id,\n                actor_id=actor_id,\n                now=now,\n                max_charges=max_charges,\n                recovery_seconds=recovery_seconds,\n            )\n            if result.get(\"consumed\"):\n                self._mark_primary_write_tx(connection)\n            return result\n\n"""
replace("storage/sqlite_primary.py", primary_marker, primary_insert + primary_marker)

# Plugin imports/config/default state and orchestration.
replace(
    "legacy_main.py",
    """    from .rollpig_core import consecutive_duplicate_day_streak\n""",
    """    from .rollpig_core import consecutive_duplicate_day_streak\n    from .roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\n""",
)
replace(
    "legacy_main.py",
    """    from rollpig_core import consecutive_duplicate_day_streak\n""",
    """    from rollpig_core import consecutive_duplicate_day_streak\n    from roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\n""",
)
replace(
    "legacy_main.py",
    """        self.group_roast_cooldown_seconds = int(\n            min(72, max(1, cooldown_hours)) * 60 * 60\n        )\n        image_theme = str(self.config.get(\"image_theme\", \"auto\") or \"auto\").lower()\n""",
    """        self.group_roast_cooldown_seconds = int(\n            min(72, max(1, cooldown_hours)) * 60 * 60\n        )\n        try:\n            max_roast_charges = int(self.config.get(\"group_roast_max_charges\", 2))\n        except (TypeError, ValueError):\n            max_roast_charges = 2\n        self.group_roast_max_charges = min(5, max(1, max_roast_charges))\n        image_theme = str(self.config.get(\"image_theme\", \"auto\") or \"auto\").lower()\n""",
)
replace(
    "legacy_main.py",
    """            \"cooldowns\": {},\n            \"daily_backdoors\": {},\n""",
    """            \"cooldowns\": {},\n            \"roast_charges\": {},\n            \"daily_backdoors\": {},\n""",
)
old_consume = """    async def _consume_group_roast_cooldown(\n        self, group_id: str, actor_id: str\n    ) -> int:\n        \"\"\"记录一次普通烤群友，返回剩余冷却秒数；0 表示已成功占用。\"\"\"\n        storage_actor = self._storage_user_key(str(actor_id))\n        if getattr(self.storage, \"supports_domain_writes\", False):\n            result = await asyncio.to_thread(\n                self.storage.consume_roast_cooldown,\n                group_id=str(group_id),\n                actor_id=storage_actor,\n                now=time.time(),\n                cooldown_seconds=self.group_roast_cooldown_seconds,\n            )\n            roast_state = result.get(\"roast_state\")\n            if isinstance(roast_state, dict):\n                self.roast_state = roast_state\n            return int(result.get(\"remaining\", 0) or 0)\n        key = f\"{group_id}:{storage_actor}\"\n        now = time.time()\n        with self._data_lock:\n            cooldowns = self.roast_state.setdefault(\"cooldowns\", {})\n            previous = float(cooldowns.get(key, 0) or 0)\n            remaining = int(previous + self.group_roast_cooldown_seconds - now)\n            if remaining > 0:\n                return remaining\n            cooldowns[key] = now\n            self._save_roast_state()\n        return 0\n\n"""
new_consume = """    async def _consume_group_roast_charge(\n        self, group_id: str, actor_id: str\n    ) -> dict[str, object]:\n        \"\"\"Consume one user × group oven charge using one shared token policy.\"\"\"\n        storage_actor = self._storage_user_key(str(actor_id))\n        now_value = time.time()\n        if getattr(self.storage, \"supports_domain_writes\", False):\n            result = await asyncio.to_thread(\n                self.storage.consume_roast_charge,\n                group_id=str(group_id),\n                actor_id=storage_actor,\n                now=now_value,\n                max_charges=self.group_roast_max_charges,\n                recovery_seconds=self.group_roast_cooldown_seconds,\n            )\n            roast_state = result.get(\"roast_state\")\n            if isinstance(roast_state, dict):\n                self.roast_state = roast_state\n            return dict(result)\n\n        key = f\"{group_id}:{storage_actor}\"\n        with self._data_lock:\n            charge_states = self.roast_state.setdefault(\"roast_charges\", {})\n            if not isinstance(charge_states, dict):\n                charge_states = {}\n                self.roast_state[\"roast_charges\"] = charge_states\n            entry = charge_states.get(key)\n            if not isinstance(entry, dict):\n                cooldowns = self.roast_state.setdefault(\"cooldowns\", {})\n                legacy_last_used = (\n                    float(cooldowns.get(key, 0) or 0)\n                    if isinstance(cooldowns, dict)\n                    else 0\n                )\n                entry = bootstrap_legacy_cooldown(\n                    legacy_last_used,\n                    now=now_value,\n                    max_charges=self.group_roast_max_charges,\n                    recovery_seconds=self.group_roast_cooldown_seconds,\n                )\n            result = consume_roast_charge_state(\n                entry,\n                now=now_value,\n                max_charges=self.group_roast_max_charges,\n                recovery_seconds=self.group_roast_cooldown_seconds,\n            )\n            charge_states[key] = {\n                \"charges\": int(result.get(\"charges\", 0) or 0),\n                \"refill_anchor\": float(result.get(\"refill_anchor\", now_value) or now_value),\n            }\n            if result.get(\"consumed\"):\n                self.roast_state.setdefault(\"cooldowns\", {})[key] = now_value\n            self._save_roast_state()\n        return dict(result)\n\n    async def _consume_group_roast_cooldown(\n        self, group_id: str, actor_id: str\n    ) -> int:\n        \"\"\"Deprecated compatibility facade over the charge system.\"\"\"\n        status = await self._consume_group_roast_charge(group_id, actor_id)\n        return (\n            0\n            if status.get(\"consumed\")\n            else int(status.get(\"next_refill_seconds\", 0) or 0)\n        )\n\n    @staticmethod\n    def _roast_charge_note(status: dict[str, object] | None) -> str:\n        if not status:\n            return \"\"\n        return (\n            f\"\\n🔥 烤箱能量：{int(status.get('charges', 0) or 0)}/\"\n            f\"{int(status.get('max_charges', 0) or 0)}\"\n        )\n\n"""
replace("legacy_main.py", old_consume, new_consume)
replace(
    "legacy_main.py",
    """        if not bypass:\n            remaining = await self._consume_group_roast_cooldown(\n                group_id, actor_id\n            )\n            if remaining:\n                await event.send(\n                    event.plain_result(\n                        f\"烤架还在降温，请 {self._format_cooldown(remaining)} 后再试。\"\n                    )\n                )\n                return\n\n        result = self.roast_service.choose_group_roast_outcome(bypass=bypass)\n""",
    """        charge_status: dict[str, object] | None = None\n        if not bypass:\n            charge_status = await self._consume_group_roast_charge(group_id, actor_id)\n            if not charge_status.get(\"consumed\"):\n                remaining = int(charge_status.get(\"next_refill_seconds\", 0) or 0)\n                await event.send(\n                    event.plain_result(\n                        \"🔥 烤箱能量已耗尽（\"\n                        f\"0/{self.group_roast_max_charges}）；下一格将在 \"\n                        f\"{self._format_cooldown(remaining)} 后恢复。\"\n                    )\n                )\n                return\n\n        charge_note = self._roast_charge_note(charge_status)\n        result = self.roast_service.choose_group_roast_outcome(bypass=bypass)\n""",
)
replace(
    "legacy_main.py",
    """event.plain_result(\"💨 对方一溜烟逃走了，烤架上只剩一阵风。\")""",
    """event.plain_result(\"💨 对方一溜烟逃走了，烤架上只剩一阵风。\" + charge_note)""",
)
replace(
    "legacy_main.py",
    """\"🔥 烤架反噬了！但你今天没有可料理的小猪，侥幸躲过一劫。\"\n                    )""",
    """\"🔥 烤架反噬了！但你今天没有可料理的小猪，侥幸躲过一劫。\"\n                        + charge_note\n                    )""",
)
replace(
    "legacy_main.py",
    """event.plain_result(\"🔥 烤架反噬！这次轮到你的今日小猪上桌。\")""",
    """event.plain_result(\"🔥 烤架反噬！这次轮到你的今日小猪上桌。\" + charge_note)""",
)
replace(
    "legacy_main.py",
    """event.plain_result(f\"{prefix}对方今天的小猪已被端上料理台。\")""",
    """event.plain_result(f\"{prefix}对方今天的小猪已被端上料理台。\" + charge_note)""",
)

# Reservation creator consumes one charge; joiners remain free and trigger never consumes again.
replace(
    "roast_reservation_feature.py",
    """        \"\"\"Reserve an absent target; creator pays cooldown, later users join free.\"\"\"\n""",
    """        \"\"\"Reserve an absent target; creator pays one charge, later users join free.\"\"\"\n""",
)
replace(
    "roast_reservation_feature.py",
    """            remaining = await self._consume_group_roast_cooldown(group_id, actor_id)\n            if remaining:\n                await event.send(\n                    event.plain_result(\n                        f\"烤架还在降温，请 {self._format_cooldown(remaining)} 后再来埋伏。\"\n                    )\n                )\n                return True\n""",
    """            charge_status = await self._consume_group_roast_charge(group_id, actor_id)\n            if not charge_status.get(\"consumed\"):\n                remaining = int(charge_status.get(\"next_refill_seconds\", 0) or 0)\n                await event.send(\n                    event.plain_result(\n                        \"🔥 烤箱能量已耗尽（\"\n                        f\"0/{self.group_roast_max_charges}）；下一格将在 \"\n                        f\"{self._format_cooldown(remaining)} 后恢复，暂时不能创建预约。\"\n                    )\n                )\n                return True\n""",
)
replace(
    "roast_reservation_feature.py",
    """                \" 🔥 今天还没抽猪，烤箱已被提前预热；等你在本群现身抽猪后自动结算。\"\n                f\"主厨已就位，最多可有 {self.roast_reservation_max_participants} 人添柴。\",\n""",
    """                \" 🔥 今天还没抽猪，烤箱已被提前预热；等你在本群现身抽猪后自动结算。\"\n                f\"主厨已就位，最多可有 {self.roast_reservation_max_participants} 人添柴。\"\n                + self._roast_charge_note(charge_status),\n""",
)

# Config schema: existing cooldown key becomes recharge interval; add configurable capacity.
replace(
    "_conf_schema.json",
    """    \"group_roast_cooldown_hours\": {\n        \"description\": \"烤群友冷却时间（小时）\",\n        \"hint\": \"普通烤群友按发起者与群组分别冷却，范围 1-72，默认 8；创建预约也会消耗一次，后续添柴不消耗；后门口令会绕过此限制\",\n        \"type\": \"float\",\n        \"default\": 8\n    },\n""",
    """    \"group_roast_cooldown_hours\": {\n        \"description\": \"烤箱每格能量恢复时间（小时）\",\n        \"hint\": \"沿用旧冷却配置作为每格能量的恢复周期，范围 1-72，默认 8；缺失能量按队列逐格恢复，后门口令不消耗能量\",\n        \"type\": \"float\",\n        \"default\": 8\n    },\n    \"group_roast_max_charges\": {\n        \"description\": \"烤箱最大能量格数\",\n        \"hint\": \"按发起者 × 群组独立储存，范围 1-5，默认 2；普通烤群友与创建预约各消耗 1 格，后续添柴和预约触发不重复消耗\",\n        \"type\": \"int\",\n        \"default\": 2\n    },\n""",
)
replace(
    "_conf_schema.json",
    """\"hint\": \"明确 /烤群友 @尚未抽猪的群友时建立本群当天预约；第一位主厨消耗正常冷却，后续群友可免费添柴，目标在本群抽猪后自动按 60/30/10 结算\"""",
    """\"hint\": \"明确 /烤群友 @尚未抽猪的群友时建立本群当天预约；第一位主厨消耗 1 格烤箱能量，后续群友可免费添柴，目标在本群抽猪后自动按 60/30/10 结算\"""",
)

print("Phase 3A roast charge patch applied")
