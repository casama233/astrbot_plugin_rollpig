from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    source = target.read_text(encoding="utf-8")
    actual = source.count(old)
    if actual < count:
        raise SystemExit(f"{path}: marker missing ({actual} < {count}): {old[:100]!r}")
    target.write_text(source.replace(old, new, count), encoding="utf-8")


# Storage public contract.
replace(
    "storage/base.py",
    """    def consume_roast_charge(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n""",
    """    def consume_roast_charge(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n    def start_oven_refill(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n    def support_oven_refill(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n""",
)

# SQLite imports, schema and migration marker.
replace(
    "storage/sqlite_storage.py",
    """try:\n    from ..roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\nexcept ImportError:  # pragma: no cover - direct module loading compatibility\n    from roast_charges import bootstrap_legacy_cooldown, consume_roast_charge_state\n""",
    """try:\n    from ..roast_charges import (\n        add_roast_charge_state,\n        bootstrap_legacy_cooldown,\n        consume_roast_charge_state,\n    )\n    from ..services.oven_refill_service import OvenRefillService\nexcept ImportError:  # pragma: no cover - direct module loading compatibility\n    from roast_charges import (\n        add_roast_charge_state,\n        bootstrap_legacy_cooldown,\n        consume_roast_charge_state,\n    )\n    from services.oven_refill_service import OvenRefillService\n""",
)
replace("storage/sqlite_storage.py", "    schema_version = 5\n", "    schema_version = 7\n")
replace(
    "storage/sqlite_storage.py",
    """                CREATE TABLE IF NOT EXISTS roast_cooldowns (\n                    cooldown_key TEXT PRIMARY KEY,\n                    group_id TEXT NOT NULL,\n                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),\n                    last_used_at REAL NOT NULL,\n                    charges INTEGER NOT NULL DEFAULT -1,\n                    refill_anchor REAL NOT NULL DEFAULT 0\n                );\n                CREATE TABLE IF NOT EXISTS daily_roast_counts (\n""",
    """                CREATE TABLE IF NOT EXISTS roast_cooldowns (\n                    cooldown_key TEXT PRIMARY KEY,\n                    group_id TEXT NOT NULL,\n                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),\n                    last_used_at REAL NOT NULL,\n                    charges INTEGER NOT NULL DEFAULT -1,\n                    refill_anchor REAL NOT NULL DEFAULT 0\n                );\n                CREATE TABLE IF NOT EXISTS oven_refill_groups (\n                    draw_date TEXT NOT NULL,\n                    group_id TEXT NOT NULL,\n                    successes INTEGER NOT NULL DEFAULT 0,\n                    round_no INTEGER NOT NULL DEFAULT 0,\n                    active INTEGER NOT NULL DEFAULT 0,\n                    required_supporters INTEGER NOT NULL DEFAULT 0,\n                    active_count INTEGER NOT NULL DEFAULT 0,\n                    started_by TEXT NOT NULL DEFAULT '',\n                    status TEXT NOT NULL DEFAULT 'idle',\n                    started_at REAL NOT NULL DEFAULT 0,\n                    completed_at REAL NOT NULL DEFAULT 0,\n                    PRIMARY KEY (draw_date, group_id),\n                    CHECK (status IN ('idle', 'active', 'succeeded', 'failed'))\n                );\n                CREATE TABLE IF NOT EXISTS oven_refill_supporters (\n                    draw_date TEXT NOT NULL,\n                    group_id TEXT NOT NULL,\n                    round_no INTEGER NOT NULL,\n                    supporter_id TEXT NOT NULL REFERENCES identities(identity_key),\n                    supported_at REAL NOT NULL DEFAULT 0,\n                    PRIMARY KEY (draw_date, group_id, round_no, supporter_id)\n                );\n                CREATE INDEX IF NOT EXISTS idx_oven_refill_supporters_group_date\n                    ON oven_refill_supporters(group_id, draw_date, round_no);\n                CREATE TABLE IF NOT EXISTS daily_roast_counts (\n""",
)
replace(
    "storage/sqlite_storage.py",
    """                if 5 not in migrated:\n                    connection.execute(\n                        \"INSERT OR IGNORE INTO schema_migrations(version, applied_at) \"\n                        \"VALUES (5, unixepoch())\"\n                    )\n                connection.execute(\"COMMIT\")\n""",
    """                if 5 not in migrated:\n                    connection.execute(\n                        \"INSERT OR IGNORE INTO schema_migrations(version, applied_at) \"\n                        \"VALUES (5, unixepoch())\"\n                    )\n                if 7 not in migrated:\n                    connection.execute(\n                        \"INSERT OR IGNORE INTO schema_migrations(version, applied_at) \"\n                        \"VALUES (7, unixepoch())\"\n                    )\n                connection.execute(\"COMMIT\")\n""",
)

# Compatibility projection now includes the refill state summary.
replace(
    "storage/sqlite_storage.py",
    """        for table in (\n            \"eaten_penalties\",\n            \"eaten_events\",\n            \"roast_cooldowns\",\n            \"daily_roast_counts\",\n            \"daily_backdoors\",\n        ):\n""",
    """        for table in (\n            \"oven_refill_supporters\",\n            \"oven_refill_groups\",\n            \"eaten_penalties\",\n            \"eaten_events\",\n            \"roast_cooldowns\",\n            \"daily_roast_counts\",\n            \"daily_backdoors\",\n        ):\n""",
)
projection_marker = """        counts = state.get(\"daily_roast_counts\") if isinstance(state.get(\"daily_roast_counts\"), dict) else {}\n"""
projection_insert = """        refill_root = (\n            state.get(\"oven_refills\")\n            if isinstance(state.get(\"oven_refills\"), dict)\n            else {}\n        )\n        for draw_date, groups in refill_root.items():\n            if not isinstance(groups, dict):\n                continue\n            for group_id, row in groups.items():\n                if not isinstance(row, dict):\n                    continue\n                round_no = int(row.get(\"round\", 0) or 0)\n                successes = int(row.get(\"successes\", 0) or 0)\n                active = int(bool(row.get(\"active\")))\n                required = int(row.get(\"required\", 0) or 0)\n                active_count = int(row.get(\"active_count\", 0) or 0)\n                started_by = str(row.get(\"started_by\") or \"\")\n                status = str(row.get(\"status\") or (\"active\" if active else \"idle\"))\n                if status not in {\"idle\", \"active\", \"succeeded\", \"failed\"}:\n                    status = \"active\" if active else \"idle\"\n                connection.execute(\n                    \"INSERT INTO oven_refill_groups VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\",\n                    (\n                        str(draw_date),\n                        str(group_id),\n                        successes,\n                        round_no,\n                        active,\n                        required,\n                        active_count,\n                        started_by,\n                        status,\n                        float(row.get(\"started_at\", 0) or 0),\n                        float(row.get(\"completed_at\", 0) or 0),\n                    ),\n                )\n                for supporter in row.get(\"supporters\", []) if isinstance(row.get(\"supporters\"), list) else []:\n                    supporter_id = str(supporter)\n                    if not supporter_id or round_no <= 0:\n                        continue\n                    self._remember_identity(connection, supporter_id)\n                    connection.execute(\n                        \"INSERT OR IGNORE INTO oven_refill_supporters VALUES (?, ?, ?, ?, ?)\",\n                        (str(draw_date), str(group_id), round_no, supporter_id, 0),\n                    )\n\n"""
replace("storage/sqlite_storage.py", projection_marker, projection_insert + projection_marker)

# Compatibility document round-trip.
replace(
    "storage/sqlite_storage.py",
    """            \"roast_charges\": {},\n            \"daily_backdoors\": {},\n""",
    """            \"roast_charges\": {},\n            \"oven_refills\": {},\n            \"daily_backdoors\": {},\n""",
)
roast_doc_marker = """        roast[\"daily_roast_counts\"] = {\n"""
roast_doc_insert = """        refill_root: dict[str, dict[str, Any]] = {}\n        for row in connection.execute(\n            \"SELECT draw_date, group_id, successes, round_no, active, \"\n            \"required_supporters, active_count, started_by, status, started_at, completed_at \"\n            \"FROM oven_refill_groups ORDER BY draw_date, group_id\"\n        ).fetchall():\n            draw_date = str(row[\"draw_date\"])\n            group_id = str(row[\"group_id\"])\n            round_no = int(row[\"round_no\"])\n            supporters = [\n                str(item[\"supporter_id\"])\n                for item in connection.execute(\n                    \"SELECT supporter_id FROM oven_refill_supporters \"\n                    \"WHERE draw_date = ? AND group_id = ? AND round_no = ? \"\n                    \"ORDER BY supported_at, supporter_id\",\n                    (draw_date, group_id, round_no),\n                ).fetchall()\n            ]\n            refill_root.setdefault(draw_date, {})[group_id] = {\n                \"successes\": int(row[\"successes\"]),\n                \"round\": round_no,\n                \"active\": bool(row[\"active\"]),\n                \"required\": int(row[\"required_supporters\"]),\n                \"active_count\": int(row[\"active_count\"]),\n                \"started_by\": str(row[\"started_by\"]),\n                \"status\": str(row[\"status\"]),\n                \"started_at\": float(row[\"started_at\"]),\n                \"completed_at\": float(row[\"completed_at\"]),\n                \"supporters\": supporters,\n            }\n        roast[\"oven_refills\"] = refill_root\n"""
replace("storage/sqlite_storage.py", roast_doc_marker, roast_doc_insert + roast_doc_marker)

# Transaction helpers + public SQL APIs inserted before consume_roast_charge.
storage_marker = """    def consume_roast_charge(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n"""
storage_insert = r'''    def _add_roast_charge_tx(
        self,
        connection: sqlite3.Connection,
        *,
        group_id: str,
        actor_id: str,
        now: float,
        max_charges: int,
        recovery_seconds: int,
    ) -> dict[str, Any]:
        group_id = str(group_id)
        actor_id = str(actor_id)
        key = f"{group_id}:{actor_id}"
        row = connection.execute(
            "SELECT last_used_at, charges, refill_anchor FROM roast_cooldowns "
            "WHERE cooldown_key = ?",
            (key,),
        ).fetchone()
        if row and int(row["charges"]) >= 0:
            state = {
                "charges": int(row["charges"]),
                "refill_anchor": float(row["refill_anchor"]),
            }
        else:
            state = bootstrap_legacy_cooldown(
                float(row["last_used_at"]) if row else 0,
                now=float(now),
                max_charges=max_charges,
                recovery_seconds=recovery_seconds,
            )
        updated = add_roast_charge_state(
            state,
            now=float(now),
            max_charges=max_charges,
            recovery_seconds=recovery_seconds,
        )
        if row is not None or updated.get("increased"):
            self._remember_identity(connection, actor_id)
            last_used_at = float(row["last_used_at"]) if row else 0.0
            connection.execute(
                """
                INSERT INTO roast_cooldowns(
                    cooldown_key, group_id, actor_id, last_used_at, charges, refill_anchor
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cooldown_key) DO UPDATE SET
                    group_id = excluded.group_id,
                    actor_id = excluded.actor_id,
                    charges = excluded.charges,
                    refill_anchor = excluded.refill_anchor
                """,
                (
                    key,
                    group_id,
                    actor_id,
                    last_used_at,
                    int(updated["charges"]),
                    float(updated["refill_anchor"]),
                ),
            )
        return updated

    def _start_oven_refill_tx(
        self,
        connection: sqlite3.Connection,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_count: int,
        now: float,
        daily_limit: int,
        ratio_percent: int,
        minimum_supporters: int,
        extra_per_success: int,
        cutoff_date: str,
    ) -> dict[str, Any]:
        draw_date = str(draw_date)
        group_id = str(group_id)
        actor_id = str(actor_id)
        connection.execute(
            "DELETE FROM oven_refill_supporters WHERE draw_date < ?", (str(cutoff_date),)
        )
        connection.execute(
            "DELETE FROM oven_refill_groups WHERE draw_date < ?", (str(cutoff_date),)
        )
        row = connection.execute(
            "SELECT * FROM oven_refill_groups WHERE draw_date = ? AND group_id = ?",
            (draw_date, group_id),
        ).fetchone()
        successes = int(row["successes"]) if row else 0
        if successes >= max(1, int(daily_limit)):
            return {"state": "limit", "successes": successes}
        if row and bool(row["active"]):
            round_no = int(row["round_no"])
            supporters = [
                str(item["supporter_id"])
                for item in connection.execute(
                    "SELECT supporter_id FROM oven_refill_supporters "
                    "WHERE draw_date = ? AND group_id = ? AND round_no = ? "
                    "ORDER BY supported_at, supporter_id",
                    (draw_date, group_id, round_no),
                ).fetchall()
            ]
            return {
                "state": "active",
                "successes": successes,
                "round": round_no,
                "required": int(row["required_supporters"]),
                "supporters": supporters,
            }
        required = OvenRefillService.refill_requirement(
            active_count,
            successes,
            ratio_percent=ratio_percent,
            minimum_supporters=minimum_supporters,
            extra_per_success=extra_per_success,
        )
        round_no = int(row["round_no"]) + 1 if row else 1
        self._remember_identity(connection, actor_id)
        connection.execute(
            """
            INSERT INTO oven_refill_groups(
                draw_date, group_id, successes, round_no, active,
                required_supporters, active_count, started_by, status,
                started_at, completed_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, 'active', ?, 0)
            ON CONFLICT(draw_date, group_id) DO UPDATE SET
                successes = excluded.successes,
                round_no = excluded.round_no,
                active = 1,
                required_supporters = excluded.required_supporters,
                active_count = excluded.active_count,
                started_by = excluded.started_by,
                status = 'active',
                started_at = excluded.started_at,
                completed_at = 0
            """,
            (
                draw_date,
                group_id,
                successes,
                round_no,
                int(required),
                int(active_count),
                actor_id,
                float(now),
            ),
        )
        connection.execute(
            "INSERT OR IGNORE INTO oven_refill_supporters VALUES (?, ?, ?, ?, ?)",
            (draw_date, group_id, round_no, actor_id, float(now)),
        )
        return {
            "state": "started",
            "successes": successes,
            "round": round_no,
            "required": int(required),
            "supporters": [actor_id],
        }

    def _support_oven_refill_tx(
        self,
        connection: sqlite3.Connection,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_actor_ids: list[str] | tuple[str, ...],
        now: float,
        max_charges: int,
        recovery_seconds: int,
        cutoff_date: str,
    ) -> dict[str, Any]:
        draw_date = str(draw_date)
        group_id = str(group_id)
        actor_id = str(actor_id)
        connection.execute(
            "DELETE FROM oven_refill_supporters WHERE draw_date < ?", (str(cutoff_date),)
        )
        connection.execute(
            "DELETE FROM oven_refill_groups WHERE draw_date < ?", (str(cutoff_date),)
        )
        row = connection.execute(
            "SELECT * FROM oven_refill_groups "
            "WHERE draw_date = ? AND group_id = ? AND active = 1",
            (draw_date, group_id),
        ).fetchone()
        if not row:
            return {"state": "inactive"}
        round_no = int(row["round_no"])
        required = int(row["required_supporters"])
        self._remember_identity(connection, actor_id)
        cursor = connection.execute(
            "INSERT OR IGNORE INTO oven_refill_supporters VALUES (?, ?, ?, ?, ?)",
            (draw_date, group_id, round_no, actor_id, float(now)),
        )
        supporters = [
            str(item["supporter_id"])
            for item in connection.execute(
                "SELECT supporter_id FROM oven_refill_supporters "
                "WHERE draw_date = ? AND group_id = ? AND round_no = ? "
                "ORDER BY supported_at, supporter_id",
                (draw_date, group_id, round_no),
            ).fetchall()
        ]
        if cursor.rowcount == 0:
            return {
                "state": "duplicate",
                "round": round_no,
                "required": required,
                "supporters": supporters,
            }
        if len(supporters) < required:
            return {
                "state": "supported",
                "round": round_no,
                "required": required,
                "supporters": supporters,
            }

        restored = 0
        recipients = list(dict.fromkeys(str(item) for item in active_actor_ids if str(item)))
        for recipient in recipients:
            updated = self._add_roast_charge_tx(
                connection,
                group_id=group_id,
                actor_id=recipient,
                now=float(now),
                max_charges=max_charges,
                recovery_seconds=recovery_seconds,
            )
            if updated.get("increased"):
                restored += 1
        if restored > 0:
            status = "succeeded"
            successes = int(row["successes"]) + 1
        else:
            status = "failed"
            successes = int(row["successes"])
        connection.execute(
            "UPDATE oven_refill_groups SET successes = ?, active = 0, status = ?, "
            "completed_at = ? WHERE draw_date = ? AND group_id = ?",
            (successes, status, float(now), draw_date, group_id),
        )
        return {
            "state": status,
            "round": round_no,
            "required": required,
            "supporters": supporters,
            "restored_users": restored,
            "active_users": len(recipients),
        }

    def start_oven_refill(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_count: int,
        now: float,
        daily_limit: int,
        ratio_percent: int,
        minimum_supporters: int,
        extra_per_success: int,
        cutoff_date: str,
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            result = self._start_oven_refill_tx(
                connection,
                draw_date=draw_date,
                group_id=group_id,
                actor_id=actor_id,
                active_count=active_count,
                now=now,
                daily_limit=daily_limit,
                ratio_percent=ratio_percent,
                minimum_supporters=minimum_supporters,
                extra_per_success=extra_per_success,
                cutoff_date=cutoff_date,
            )
            if result.get("state") == "started":
                roast = self._roast_document_from_sql(connection)
                self._write_document_tx(connection, "roast_state.json", roast)
                self._set_write_authority(connection)
                result["roast_state"] = roast
            return result

    def support_oven_refill(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_actor_ids: list[str] | tuple[str, ...],
        now: float,
        max_charges: int,
        recovery_seconds: int,
        cutoff_date: str,
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            result = self._support_oven_refill_tx(
                connection,
                draw_date=draw_date,
                group_id=group_id,
                actor_id=actor_id,
                active_actor_ids=active_actor_ids,
                now=now,
                max_charges=max_charges,
                recovery_seconds=recovery_seconds,
                cutoff_date=cutoff_date,
            )
            if result.get("state") in {"supported", "succeeded", "failed"}:
                roast = self._roast_document_from_sql(connection)
                self._write_document_tx(connection, "roast_state.json", roast)
                self._set_write_authority(connection)
                result["roast_state"] = roast
            return result

'''
replace("storage/sqlite_storage.py", storage_marker, storage_insert + storage_marker)

# SQL-primary uses the same transaction helpers but does not persist compatibility docs.
replace("storage/sqlite_primary.py", "    schema_version = 6\n", "    schema_version = 7\n")
primary_marker = """    def consume_roast_charge(\n        self,\n        *,\n        group_id: str,\n        actor_id: str,\n        now: float,\n        max_charges: int,\n        recovery_seconds: int,\n    ) -> dict[str, Any]:\n"""
primary_insert = r'''    def start_oven_refill(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_count: int,
        now: float,
        daily_limit: int,
        ratio_percent: int,
        minimum_supporters: int,
        extra_per_success: int,
        cutoff_date: str,
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            result = self._start_oven_refill_tx(
                connection,
                draw_date=draw_date,
                group_id=group_id,
                actor_id=actor_id,
                active_count=active_count,
                now=now,
                daily_limit=daily_limit,
                ratio_percent=ratio_percent,
                minimum_supporters=minimum_supporters,
                extra_per_success=extra_per_success,
                cutoff_date=cutoff_date,
            )
            if result.get("state") == "started":
                self._mark_primary_write_tx(connection)
            return result

    def support_oven_refill(
        self,
        *,
        draw_date: str,
        group_id: str,
        actor_id: str,
        active_actor_ids: list[str] | tuple[str, ...],
        now: float,
        max_charges: int,
        recovery_seconds: int,
        cutoff_date: str,
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            result = self._support_oven_refill_tx(
                connection,
                draw_date=draw_date,
                group_id=group_id,
                actor_id=actor_id,
                active_actor_ids=active_actor_ids,
                now=now,
                max_charges=max_charges,
                recovery_seconds=recovery_seconds,
                cutoff_date=cutoff_date,
            )
            if result.get("state") in {"supported", "succeeded", "failed"}:
                self._mark_primary_write_tx(connection)
            return result

'''
replace("storage/sqlite_primary.py", primary_marker, primary_insert + primary_marker)

# Main feature integration and command registration.
replace(
    "main.py",
    """    from .roast_reservation_feature import RoastReservationMixin\n    from .persistent_collection_feature import PermanentCollectionMixin\n""",
    """    from .roast_reservation_feature import RoastReservationMixin\n    from .oven_refill_feature import OvenRefillMixin\n    from .persistent_collection_feature import PermanentCollectionMixin\n""",
)
replace(
    "main.py",
    """    from roast_reservation_feature import RoastReservationMixin\n    from persistent_collection_feature import PermanentCollectionMixin\n""",
    """    from roast_reservation_feature import RoastReservationMixin\n    from oven_refill_feature import OvenRefillMixin\n    from persistent_collection_feature import PermanentCollectionMixin\n""",
)
replace(
    "main.py",
    """class RollPigPlugin(\n    PermanentCollectionMixin,\n    RoastReservationMixin,\n""",
    """class RollPigPlugin(\n    OvenRefillMixin,\n    PermanentCollectionMixin,\n    RoastReservationMixin,\n""",
)
main_marker = """    @filter.command(\n        \"烤群友\",\n        alias={\"烤群友\", \"烤群友 \"},\n        priority=ROLLPIG_COMMAND_PRIORITY,\n    )\n"""
main_insert = """    @filter.command(\n        \"烤箱补货\",\n        alias={\"烤箱補貨\"},\n        priority=ROLLPIG_COMMAND_PRIORITY,\n    )\n    async def oven_refill(self, event: AstrMessageEvent):\n        return await super().oven_refill(event)\n\n    @filter.command(\n        \"添煤\",\n        priority=ROLLPIG_COMMAND_PRIORITY,\n    )\n    async def oven_refill_support(self, event: AstrMessageEvent):\n        return await super().oven_refill_support(event)\n\n"""
replace("main.py", main_marker, main_insert + main_marker)

# Configuration.
config_marker = """    \"enable_roast_protection\": {\n"""
config_insert = """    \"enable_oven_refill\": {\n        \"description\": \"开启群体烤箱补货\",\n        \"hint\": \"允许本群今日活跃玩家使用 /烤箱补货 发起补货、/添煤 参与；达标后为本群今日活跃玩家恢复 +1 格烤箱能量\",\n        \"type\": \"bool\",\n        \"default\": true\n    },\n    \"oven_refill_daily_limit\": {\n        \"description\": \"每群每日成功补货上限\",\n        \"hint\": \"范围 1-5，默认 2；失败或因所有人已满而作废的轮次不计入成功次数\",\n        \"type\": \"int\",\n        \"default\": 2\n    },\n    \"oven_refill_support_ratio_percent\": {\n        \"description\": \"首次补货活跃人数支持比例（百分比）\",\n        \"hint\": \"默认 30%；例如今日活跃 16 人时首次需要 5 人支持，仍受最少支持人数约束\",\n        \"type\": \"int\",\n        \"default\": 30\n    },\n    \"oven_refill_min_supporters\": {\n        \"description\": \"补货最少支持人数\",\n        \"hint\": \"范围 2-20，默认 3；若本群今日只有 2 位活跃玩家，则需要两人全部支持\",\n        \"type\": \"int\",\n        \"default\": 3\n    },\n    \"oven_refill_extra_supporters_per_success\": {\n        \"description\": \"当天每成功补货一次后增加的支持人数\",\n        \"hint\": \"范围 0-10，默认 2；第二轮及以后逐步提高门槛，但不会超过本群今日活跃人数\",\n        \"type\": \"int\",\n        \"default\": 2\n    },\n"""
replace("_conf_schema.json", config_marker, config_insert + config_marker)

print("Phase 3B oven refill patch applied")
