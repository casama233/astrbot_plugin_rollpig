from __future__ import annotations

import re
import textwrap
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label}: expected one anchor, found {text.count(old)}")
    return text.replace(old, new, 1)


def class_block(text: str) -> str:
    return textwrap.indent(textwrap.dedent(text).strip() + "\n", "    ")


storage_path = Path("storage/sqlite_storage.py")
source = storage_path.read_text(encoding="utf-8")

expected_method = class_block(
    '''
    @staticmethod
    def _expected_projection_counts(documents: dict[str, Any]) -> dict[str, int]:
        history = documents.get("pig_history.json")
        history = history if isinstance(history, dict) else {}
        users = history.get("users") if isinstance(history.get("users"), dict) else {}
        daily = history.get("daily") if isinstance(history.get("daily"), dict) else {}
        snapshots = (
            history.get("pig_snapshots")
            if isinstance(history.get("pig_snapshots"), dict)
            else {}
        )
        valid_users = {
            str(user_id): value
            for user_id, value in users.items()
            if isinstance(value, dict)
        }
        user_pigs = sum(
            sum(
                1
                for value in raw_user.get("pigs", {}).values()
                if isinstance(value, dict)
            )
            for raw_user in valid_users.values()
            if isinstance(raw_user.get("pigs"), dict)
        )
        daily_draws = 0
        daily_groups = 0
        for day in daily.values():
            if not isinstance(day, dict):
                continue
            records = day.get("records") if isinstance(day.get("records"), dict) else {}
            groups = day.get("groups") if isinstance(day.get("groups"), dict) else {}
            daily_draws += len(records)
            membership: dict[str, set[str]] = {}
            for group_id, members in groups.items():
                if not isinstance(members, list):
                    continue
                for user_id in members:
                    membership.setdefault(str(user_id), set()).add(str(group_id))
            daily_groups += sum(
                len(membership.get(str(user_id), set())) for user_id in records
            )

        roast = documents.get("roast_state.json")
        roast = roast if isinstance(roast, dict) else {}
        counts = roast.get("daily_roast_counts")
        valid_roast_counts = 0
        for raw_key in counts if isinstance(counts, dict) else {}:
            try:
                parsed = json.loads(str(raw_key))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            valid_roast_counts += int(isinstance(parsed, list) and len(parsed) == 3)

        events = roast.get("eaten_events")
        valid_events = 0
        for raw_key, entry in events.items() if isinstance(events, dict) else ():
            if not isinstance(entry, dict):
                continue
            try:
                parsed = json.loads(str(raw_key))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            valid_events += int(isinstance(parsed, list) and len(parsed) == 3)

        backdoors = roast.get("daily_backdoors")
        valid_backdoors = sum(
            1
            for raw_key in backdoors if isinstance(backdoors, dict)
            if ":" in str(raw_key) and str(raw_key).partition(":")[2]
        )

        ai = documents.get("ai_roast_copies.json")
        ai = ai if isinstance(ai, dict) else {}
        copies = ai.get("copies") if isinstance(ai.get("copies"), dict) else {}
        ai_count = sum(
            sum(1 for content in value.values() if str(content or "").strip())
            for value in copies.values()
            if isinstance(value, dict)
        )
        overrides = documents.get("local_overrides.json")
        tombstones = documents.get("deleted_pigs.json")
        penalties = roast.get("eaten_penalties")
        cooldowns = roast.get("cooldowns")
        return {
            "user_stats": len(valid_users),
            "user_pigs": user_pigs,
            "daily_draws": daily_draws,
            "daily_draw_groups": daily_groups,
            "pig_snapshots": sum(
                1 for value in snapshots.values() if isinstance(value, dict)
            ),
            "eaten_penalties": sum(
                1 for value in penalties.values() if isinstance(value, dict)
            )
            if isinstance(penalties, dict)
            else 0,
            "eaten_events": valid_events,
            "roast_cooldowns": len(cooldowns) if isinstance(cooldowns, dict) else 0,
            "daily_roast_counts": valid_roast_counts,
            "daily_backdoors": valid_backdoors,
            "ai_roast_copies": ai_count,
            "catalog_overrides": sum(
                1
                for value in overrides
                if isinstance(value, dict) and str(value.get("id") or "")
            )
            if isinstance(overrides, list)
            else 0,
            "catalog_tombstones": sum(1 for value in tombstones if str(value))
            if isinstance(tombstones, list)
            else 0,
        }
    '''
)
pattern = re.compile(
    r"^    @staticmethod\n    def _expected_projection_counts\(.*?(?=^    def _projection_health)",
    re.MULTILINE | re.DOTALL,
)
source, count = pattern.subn(expected_method + "\n", source, count=1)
if count != 1:
    raise SystemExit("expected projection method anchor mismatch")

verify_method = class_block(
    '''
    def verify(self, *, deep: bool = True) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            foreign_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
            schema_row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
            ).fetchone()
            documents = int(
                connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            )
            daily_draws = int(
                connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0]
            )
            users = int(
                connection.execute("SELECT COUNT(*) FROM user_stats").fetchone()[0]
            )
            projection = (
                self._projection_health(connection)
                if deep
                else {
                    "projection_ok": None,
                    "projection_mismatches": {},
                    "projection_expected": {},
                    "projection_actual": {},
                }
            )
        return {
            "ok": (
                integrity == "ok"
                and not foreign_rows
                and projection["projection_ok"] is not False
            ),
            "integrity": integrity,
            "foreign_key_errors": len(foreign_rows),
            "schema_version": int(schema_row[0] if schema_row else 0),
            "documents": documents,
            "daily_draws": daily_draws,
            "users": users,
            "deep_verified": deep,
            **projection,
        }
    '''
)
pattern = re.compile(
    r"^    def verify\(self.*?(?=^    def health\()",
    re.MULTILINE | re.DOTALL,
)
source, count = pattern.subn(verify_method + "\n", source, count=1)
if count != 1:
    raise SystemExit("verify method anchor mismatch")
source = replace_once(
    source,
    "verification = self.verify()",
    "verification = self.verify(deep=False)",
    "lightweight health",
)
storage_path.write_text(source, encoding="utf-8")

source_tests_path = Path("tests/test_source_regressions.py")
tests = source_tests_path.read_text(encoding="utf-8")
insert_before = '    assert "_eat_actor_block_reason(actor_pig)" in eat\n'
tests = replace_once(
    tests,
    insert_before,
    '    service_source = (ROOT / "services" / "roast_service.py").read_text(encoding="utf-8")\n\n'
    + insert_before,
    "service source test",
)
tests = replace_once(
    tests,
    '    assert "你今天是" in actor_rules\n',
    '    assert "self.roast_service.eat_actor_block_reason" in actor_rules\n'
    '    assert "你今天是" in service_source\n',
    "actor delegation test",
)
tests = replace_once(
    tests,
    '    assert \'state in {"normal", "cooked"}\' in target_rules\n',
    '    assert "self.roast_service.eat_target_block_reason" in target_rules\n'
    '    assert \'state in {"normal", "cooked"}\' in service_source\n',
    "target delegation test",
)
tests = replace_once(
    tests,
    '    assert "开袋即食成功" in success_copy\n',
    '    assert "self.roast_service.eat_success_message" in success_copy\n'
    '    assert "开袋即食成功" in service_source\n',
    "success copy delegation test",
)
source_tests_path.write_text(tests, encoding="utf-8")

sqlite_tests_path = Path("tests/test_sqlite_storage.py")
sqlite_tests = sqlite_tests_path.read_text(encoding="utf-8")
marker = "def test_projection_verification_ignores_unprojectable_legacy_garbage"
if marker not in sqlite_tests:
    sqlite_tests += textwrap.dedent(
        '''

        def test_projection_verification_ignores_unprojectable_legacy_garbage(tmp_path):
            values = _documents(tmp_path)
            roast = values["roast_state.json"]
            roast["daily_roast_counts"]["broken"] = 1
            roast["eaten_events"]["broken"] = {"actor_id": "x"}
            roast["daily_backdoors"]["broken"] = True
            values["ai_roast_copies.json"]["copies"]["pink-pig"]["bad"] = ""
            values["local_overrides.json"].append({})
            values["deleted_pigs.json"].append("")
            storage = SQLiteStorage(
                tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
            )
            storage.save_json_batch(
                {tmp_path / key: value for key, value in values.items()}
            )
            assert storage.verify()["projection_ok"] is True


        def test_dashboard_health_avoids_deep_document_projection_scan(
            tmp_path, monkeypatch
        ):
            values = _documents(tmp_path)
            storage = SQLiteStorage(
                tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
            )
            storage.save_json_batch(
                {tmp_path / key: value for key, value in values.items()}
            )
            monkeypatch.setattr(
                storage,
                "_projection_health",
                lambda connection: (_ for _ in ()).throw(AssertionError("deep scan")),
            )
            health = storage.health()
            assert health["ok"] is True
            assert health["deep_verified"] is False
        '''
    )
sqlite_tests_path.write_text(sqlite_tests, encoding="utf-8")
