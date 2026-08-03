from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


base = read("storage/base.py")
base = replace_once(
    base,
    '''    def replace_daily_pig_with_eaten(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

''',
    '''    def replace_daily_pig_with_eaten(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def claim_legacy_identity(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def remember_identity_alias(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

''',
    "base metadata methods",
)
write("storage/base.py", base)

sqlite = read("storage/sqlite_storage.py")
sqlite = replace_once(
    sqlite,
    '''    @staticmethod
    def _event_key(event_date: str, group_id: str, user_id: str) -> str:
        return json.dumps(
            [str(event_date), str(group_id), str(user_id)], ensure_ascii=False
        )

''',
    '''    @staticmethod
    def _event_key(event_date: str, group_id: str, user_id: str) -> str:
        return json.dumps(
            [str(event_date), str(group_id), str(user_id)], ensure_ascii=False
        )

    @staticmethod
    def _event_key_date(value: Any) -> str:
        try:
            parsed = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""
        return str(parsed[0]) if isinstance(parsed, list) and len(parsed) == 3 else ""

''',
    "safe event date helper",
)
metadata_anchor = '''    def create_daily_draw(
        self,
        *,
'''
metadata_methods = r'''    def claim_legacy_identity(
        self,
        *,
        namespaced: str,
        legacy: str,
        kind: str,
        accepted_claims: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Atomically claim one ambiguous legacy key without rewriting projections."""
        namespaced = str(namespaced)
        legacy = str(legacy)
        accepted = {str(item) for item in accepted_claims if str(item)}
        accepted.add(namespaced)
        with self.transaction() as connection:
            history = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "pig_history.json",
                    {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}},
                )
            )
            claims_root = history.get("identity_claims")
            if not isinstance(claims_root, dict):
                claims_root = {}
                history["identity_claims"] = claims_root
            claims = claims_root.get(str(kind))
            if not isinstance(claims, dict):
                claims = {}
                claims_root[str(kind)] = claims
            claimed_by = str(claims.get(legacy) or "")
            claimed = not claimed_by or claimed_by in accepted
            changed = claimed and claimed_by != namespaced
            if changed:
                claims[legacy] = namespaced
                self._write_document_tx(connection, "pig_history.json", history)
            return {
                "claimed": claimed,
                "storage_key": legacy if claimed else namespaced,
                "history": history,
            }

    def remember_identity_alias(
        self,
        *,
        namespace: str,
        canonical_id: str,
        username: str,
    ) -> dict[str, Any]:
        """Merge one Telegram alias into the latest history document atomically."""
        namespace = str(namespace)
        canonical_id = str(canonical_id)
        username = str(username).lstrip("@")
        alias_key = username.lower()
        with self.transaction() as connection:
            history = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "pig_history.json",
                    {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}},
                )
            )
            aliases_root = history.get("identity_aliases")
            if not isinstance(aliases_root, dict):
                aliases_root = {}
                history["identity_aliases"] = aliases_root
            bucket = aliases_root.get(namespace)
            if not isinstance(bucket, dict):
                bucket = {"by_alias": {}, "by_user": {}}
                aliases_root[namespace] = bucket
            by_alias = bucket.get("by_alias")
            if not isinstance(by_alias, dict):
                by_alias = {}
                bucket["by_alias"] = by_alias
            by_user = bucket.get("by_user")
            if not isinstance(by_user, dict):
                by_user = {}
                bucket["by_user"] = by_user
            changed = not (
                by_alias.get(alias_key) == canonical_id
                and by_user.get(canonical_id) == username
            )
            if changed:
                previous_user = str(by_alias.get(alias_key) or "")
                if previous_user and previous_user != canonical_id:
                    by_user.pop(previous_user, None)
                previous_alias = str(by_user.get(canonical_id) or "").lower()
                if previous_alias and previous_alias != alias_key:
                    by_alias.pop(previous_alias, None)
                by_alias[alias_key] = canonical_id
                by_user[canonical_id] = username
                self._write_document_tx(connection, "pig_history.json", history)
            return {"changed": changed, "history": history}

'''
sqlite = replace_once(
    sqlite, metadata_anchor, metadata_methods + metadata_anchor, "metadata domain methods"
)
old_prune = '''            roast["eaten_events"] = {
                key: value
                for key, value in events_doc.items()
                if isinstance(value, dict)
                and (
                    (lambda parsed: isinstance(parsed, list) and len(parsed) == 3 and str(parsed[0]) >= str(cutoff_date))(
                        json.loads(key)
                    )
                    if isinstance(key, str)
                    else False
                )
            }
'''
new_prune = '''            roast["eaten_events"] = {
                key: value
                for key, value in events_doc.items()
                if isinstance(value, dict)
                and self._event_key_date(key) >= str(cutoff_date)
            }
'''
sqlite = replace_once(sqlite, old_prune, new_prune, "safe event pruning")
write("storage/sqlite_storage.py", sqlite)

main = read("main.py")
claim_anchor = '''        if namespaced == legacy or not legacy_exists:
            return namespaced
        with self._data_lock:
'''
claim_sql = '''        if namespaced == legacy or not legacy_exists:
            return namespaced
        if getattr(self.storage, "supports_domain_writes", False):
            result = self.storage.claim_legacy_identity(
                namespaced=namespaced,
                legacy=legacy,
                kind=kind,
                accepted_claims=self._identity_candidates(namespaced),
            )
            history = result.get("history")
            if isinstance(history, dict):
                self.history = history
            return str(result.get("storage_key") or namespaced)
        with self._data_lock:
'''
main = replace_once(main, claim_anchor, claim_sql, "main atomic claim")
alias_anchor = '''        username = self._telegram_username(sender_name)
        if not username:
            return
        with self._data_lock:
'''
alias_sql = '''        username = self._telegram_username(sender_name)
        if not username:
            return
        if getattr(self.storage, "supports_domain_writes", False):
            result = self.storage.remember_identity_alias(
                namespace=self._platform_namespace(event),
                canonical_id=canonical_id,
                username=username,
            )
            history = result.get("history")
            if isinstance(history, dict):
                self.history = history
            return
        with self._data_lock:
'''
main = replace_once(main, alias_anchor, alias_sql, "main atomic alias")
write("main.py", main)

tests = read("tests/test_sqlite_storage.py")
if "test_sql_primary_metadata_merges_do_not_rebuild_or_erase_draws" not in tests:
    tests += r'''


def test_sql_primary_metadata_merges_do_not_rebuild_or_erase_draws(
    tmp_path, monkeypatch
):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    first.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|telegram@one|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|telegram@one|group|9",
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("metadata merge must not rebuild projections")

    monkeypatch.setattr(second, "_project_history", forbidden)
    claim = second.claim_legacy_identity(
        namespaced="v2|telegram@one|user|1",
        legacy="1",
        kind="users",
        accepted_claims=("v2|telegram@one|user|1", "v2|telegram|user|1", "1"),
    )
    alias = second.remember_identity_alias(
        namespace="telegram@one",
        canonical_id="v2|telegram@one|user|1",
        username="ExampleUser",
    )
    assert claim["storage_key"] == "1"
    assert alias["changed"] is True
    with first._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM user_stats").fetchone()[0] == 1
    history = first.export_documents()["pig_history.json"]
    assert history["identity_claims"]["users"]["1"] == "v2|telegram@one|user|1"
    assert history["identity_aliases"]["telegram@one"]["by_alias"]["exampleuser"] == "v2|telegram@one|user|1"


def test_sql_primary_legacy_claim_is_atomic_across_platforms(tmp_path):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    one = first.claim_legacy_identity(
        namespaced="v2|qq@one|user|1",
        legacy="1",
        kind="users",
        accepted_claims=("v2|qq@one|user|1", "1"),
    )
    two = second.claim_legacy_identity(
        namespaced="v2|discord@one|user|1",
        legacy="1",
        kind="users",
        accepted_claims=("v2|discord@one|user|1", "1"),
    )
    assert one["storage_key"] == "1"
    assert two["storage_key"] == "v2|discord@one|user|1"


def test_sql_primary_eat_drops_malformed_legacy_event_keys(tmp_path):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_events"] = {
        "not-json": {"actor_id": "broken", "outcome": "legacy", "at": 1}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    result = storage.replace_daily_pig_with_eaten(
        draw_date="2026-08-04",
        due_date="2026-08-05",
        cutoff_date="2026-08-02",
        user_id="v2|qq|user|1",
        group_id="v2|qq|group|9",
        actor_id="v2|qq|user|2",
        outcome="eat_success",
        eaten_pig={"id": "eaten", "name": "吃掉了"},
    )
    assert result["status"] == "updated"
    assert "not-json" not in storage.export_documents()["roast_state.json"]["eaten_events"]
'''
write("tests/test_sqlite_storage.py", tests)

regression = read("tests/test_source_regressions.py")
if "test_identity_metadata_uses_sql_merge_in_sqlite_mode" not in regression:
    regression += r'''


def test_identity_metadata_uses_sql_merge_in_sqlite_mode():
    claim = ast.get_source_segment(SOURCE, _method("_claim_legacy_identity")) or ""
    alias = ast.get_source_segment(SOURCE, _method("_remember_sender_alias")) or ""
    assert "self.storage.claim_legacy_identity" in claim
    assert "self.storage.remember_identity_alias" in alias
'''
write("tests/test_source_regressions.py", regression)
