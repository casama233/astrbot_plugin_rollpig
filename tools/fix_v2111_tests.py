from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tests/test_sqlite_storage.py"
text = path.read_text(encoding="utf-8")
old = '''        assert connection.execute(
            "SELECT due_date, failed FROM eaten_penalties "
            "WHERE user_id = 'v2|qq|user|1'"
        ).fetchone() == ("2026-08-04", 0)
'''
new = '''        penalty = connection.execute(
            "SELECT due_date, failed FROM eaten_penalties "
            "WHERE user_id = 'v2|qq|user|1'"
        ).fetchone()
        assert tuple(penalty) == ("2026-08-04", 0)
'''
if text.count(old) != 2:
    raise RuntimeError(f"expected two SQLite row assertions, found {text.count(old)}")
path.write_text(text.replace(old, new), encoding="utf-8")
