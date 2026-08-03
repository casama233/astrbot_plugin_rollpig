from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


path = ROOT / "storage" / "sqlite_storage.py"
text = path.read_text(encoding="utf-8")
replacements = [
    (
        '''                CREATE TABLE IF NOT EXISTS daily_draws (
                    draw_date TEXT NOT NULL,
                    user_id TEXT NOT NULL,
''',
        '''                CREATE TABLE IF NOT EXISTS daily_draws (
                    draw_date TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
''',
        "daily draws identity foreign key",
    ),
    (
        '''                CREATE TABLE IF NOT EXISTS user_pigs (
                    user_id TEXT NOT NULL,
''',
        '''                CREATE TABLE IF NOT EXISTS user_pigs (
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
''',
        "user pigs identity foreign key",
    ),
    (
        '''                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY,
''',
        '''                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY REFERENCES identities(identity_key),
''',
        "user stats identity foreign key",
    ),
    (
        '''                CREATE TABLE IF NOT EXISTS eaten_penalties (
                    user_id TEXT PRIMARY KEY,
''',
        '''                CREATE TABLE IF NOT EXISTS eaten_penalties (
                    user_id TEXT PRIMARY KEY REFERENCES identities(identity_key),
''',
        "penalty identity foreign key",
    ),
    (
        '''                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
''',
        '''                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
                    actor_id TEXT NOT NULL,
''',
        "eaten event target foreign key",
    ),
    (
        '''                CREATE TABLE IF NOT EXISTS roast_cooldowns (
                    cooldown_key TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
''',
        '''                CREATE TABLE IF NOT EXISTS roast_cooldowns (
                    cooldown_key TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),
''',
        "cooldown actor foreign key",
    ),
    (
        '''                CREATE TABLE IF NOT EXISTS daily_roast_counts (
                    draw_date TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
''',
        '''                CREATE TABLE IF NOT EXISTS daily_roast_counts (
                    draw_date TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL REFERENCES identities(identity_key),
''',
        "roast count identity foreign key",
    ),
    (
        '''                CREATE TABLE IF NOT EXISTS daily_backdoors (
                    backdoor_key TEXT PRIMARY KEY,
                    draw_date TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
''',
        '''                CREATE TABLE IF NOT EXISTS daily_backdoors (
                    backdoor_key TEXT PRIMARY KEY,
                    draw_date TEXT NOT NULL,
                    actor_id TEXT NOT NULL REFERENCES identities(identity_key),
''',
        "backdoor actor foreign key",
    ),
]
for old, new, label in replacements:
    text = replace_once(text, old, new, label)

backdoor_anchor = '''        for backdoor_key, used in backdoors.items():
            draw_date, separator, actor_id = str(backdoor_key).partition(":")
            if not separator:
                actor_id = ""
            self._remember_identity(connection, actor_id)
'''
backdoor_replacement = '''        for backdoor_key, used in backdoors.items():
            draw_date, separator, actor_id = str(backdoor_key).partition(":")
            if not separator or not actor_id:
                continue
            self._remember_identity(connection, actor_id)
'''
text = replace_once(
    text, backdoor_anchor, backdoor_replacement, "skip malformed backdoor keys"
)
path.write_text(text, encoding="utf-8", newline="\n")

tests_path = ROOT / "tests" / "test_sqlite_storage.py"
tests = tests_path.read_text(encoding="utf-8")
tests += '''


def test_projection_tables_enforce_identity_foreign_keys(tmp_path):
    storage = SQLiteStorage(
        tmp_path / "rollpig.db",
        tmp_path,
        StorageManager.MANAGED_PATHS,
    )
    expected = {
        "daily_draws",
        "user_pigs",
        "user_stats",
        "eaten_penalties",
        "eaten_events",
        "roast_cooldowns",
        "daily_roast_counts",
        "daily_backdoors",
    }
    with storage._connection() as connection:
        constrained = {
            table
            for table in expected
            if any(
                row[2] == "identities"
                for row in connection.execute(
                    f"PRAGMA foreign_key_list({table})"
                ).fetchall()
            )
        }
        assert constrained == expected
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO user_stats("
                "user_id, total_draws, active_days, duplicate_streak, payload_json"
                ") VALUES ('missing-identity', 0, 0, 0, '{}')"
            )
'''
tests_path.write_text(tests, encoding="utf-8", newline="\n")

Path(__file__).unlink()
