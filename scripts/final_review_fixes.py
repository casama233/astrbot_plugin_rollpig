from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
TEST = ROOT / "tests" / "test_source_regressions.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


main = MAIN.read_text(encoding="utf-8")

anchor = '''    def _identity_candidates(self, value: str) -> tuple[str, ...]:
        value = str(value or "").strip()
        legacy = self._legacy_identity(value)
        return (value,) if legacy == value else (value, legacy)

'''
replacement = anchor + '''    def _user_read_candidates(self, user_id: str) -> tuple[str, ...]:
        """Return only identity keys that belong to the current platform claim."""
        candidates = self._identity_candidates(str(user_id))
        if len(candidates) == 1:
            return candidates
        namespaced, legacy = candidates
        storage_key = self._storage_user_key(namespaced)
        claims = self.history.get("identity_claims", {}).get("users", {})
        claimed_by = str(claims.get(legacy) or "") if isinstance(claims, dict) else ""
        if storage_key == legacy or claimed_by == namespaced:
            return (namespaced, legacy)
        return (namespaced,)

'''
main = replace_once(main, anchor, replacement, "claim-aware read candidates")

main = replace_once(
    main,
    '''    def _get_user_collection(self, user_id: str) -> dict:
        users = self.history.get("users", {})
        for candidate in self._identity_candidates(str(user_id)):
            user = users.get(candidate, {})
            if isinstance(user, dict) and user:
                return user
        return {}
''',
    '''    def _get_user_collection(self, user_id: str) -> dict:
        users = self.history.get("users", {})
        for candidate in self._user_read_candidates(str(user_id)):
            user = users.get(candidate, {})
            if isinstance(user, dict) and user:
                return user
        return {}
''',
    "collection claim isolation",
)

main = replace_once(
    main,
    '''        for candidate in self._identity_candidates(str(user_id)):
            pig_id = str(records.get(candidate, ""))
            if pig_id:
                break
''',
    '''        for candidate in self._user_read_candidates(str(user_id)):
            pig_id = str(records.get(candidate, ""))
            if pig_id:
                break
''',
    "daily claim isolation",
)

old_weekly = '''        day = self.history.get("daily", {}).get(date_value.isoformat(), {})
        user_key = str(user_id)
        pig_id = str(day.get("records", {}).get(user_key, ""))
        original_id = str(day.get("eaten_originals", {}).get(user_key, ""))
        if pig_id == "eaten" and original_id:
'''
new_weekly = '''        day = self.history.get("daily", {}).get(date_value.isoformat(), {})
        user_key = str(user_id)
        records = day.get("records", {})
        originals = day.get("eaten_originals", {})
        pig_id = ""
        original_id = ""
        for candidate in self._user_read_candidates(user_key):
            if not pig_id:
                pig_id = str(records.get(candidate, ""))
            if not original_id:
                original_id = str(originals.get(candidate, ""))
        if pig_id == "eaten" and original_id:
'''
main = replace_once(main, old_weekly, new_weekly, "weekly claim isolation")

main = replace_once(
    main,
    '''                    for candidate in self._identity_candidates(target_id)
                    if candidate in user_records
''',
    '''                    for candidate in self._user_read_candidates(target_id)
                    if candidate in user_records
''',
    "today cache claim isolation",
)

main = replace_once(
    main,
    '''                for path in reversed(replaced):
                    backup = backups.get(path)
                    if backup and backup.exists():
                        shutil.copy2(backup, path)
                raise
''',
    '''                for path in reversed(replaced):
                    backup = backups.get(path)
                    if backup and backup.exists():
                        shutil.copy2(backup, path)
                    else:
                        path.unlink(missing_ok=True)
                raise
''',
    "new-file rollback",
)

ast.parse(main)
MAIN.write_text(main, encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
test += '''\n\ndef test_claim_aware_reads_do_not_use_raw_candidates_directly():\n    for name in ("_get_user_collection", "_get_daily_pig", "_get_weekly_pig", "roll_pig"):\n        method = ast.get_source_segment(SOURCE, _method(name)) or ""\n        assert "_user_read_candidates" in method\n\n\ndef test_batch_rollback_removes_newly_created_files():\n    method = ast.get_source_segment(SOURCE, _method("save_json_batch")) or ""\n    assert "path.unlink(missing_ok=True)" in method\n'''
TEST.write_text(test, encoding="utf-8")
print("final review fixes applied")
