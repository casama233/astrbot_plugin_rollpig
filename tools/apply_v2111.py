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


sqlite = read("storage/sqlite_storage.py")
sqlite = replace_once(
    sqlite,
    '''                elif due_date == draw_date:
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )
                    penalties_doc.pop(penalty_user, None)
                    roast_changed = True

            if not isinstance(pig, dict) or not str(pig.get("id") or "").strip():
''',
    '''                elif due_date == draw_date and isinstance(pig, dict) and str(
                    pig.get("id") or ""
                ).strip():
                    # A successful penalty is consumed only in the same transaction
                    # that inserts the daily draw. Probe calls must leave it intact.
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )
                    penalties_doc.pop(penalty_user, None)
                    roast_changed = True

            if not isinstance(pig, dict) or not str(pig.get("id") or "").strip():
''',
    "defer successful penalty consumption",
)
sqlite = sqlite.replace(
    '''        A probe call with ``pig=None`` returns an existing draw, consumes/blocks a
        due penalty, or returns ``needs-pig``. The caller can then choose a pig and
''',
    '''        A probe call with ``pig=None`` returns an existing draw, blocks a failed
        penalty, or returns ``needs-pig`` without consuming a successful penalty.
        The caller can then choose a pig and
''',
)
write("storage/sqlite_storage.py", sqlite)

main = read("main.py").replace("2.11.0", "2.11.1")
write("main.py", main)
updater = read("updater.py").replace("2.11.0", "2.11.1")
write("updater.py", updater)
metadata = read("metadata.yaml").replace('version: "2.11.0"', 'version: "2.11.1"')
write("metadata.yaml", metadata)

changelog = read("CHANGELOG.md")
entry = '''# 更新\n## v2.11.1 (2026-08-04)\n### 被吃惩罚与每日抽取原子性热修复\n- 修复 SQL 主写路径在“探测今日状态”阶段提前消费成功惩罚的问题；探测现在只判断失败或返回待选猪状态。\n- 成功消费次日惩罚只会与 `daily_draws`、图鉴和统计写入在同一个 `BEGIN IMMEDIATE` 事务中提交。\n- 若抽取写入、兼容文档同步或进程在提交前失败，惩罚与所有抽取记录会一起回滚，不会出现“惩罚消失但没有抽到猪”。\n\n'''
if not changelog.startswith("# 更新\n"):
    raise RuntimeError("unexpected changelog header")
changelog = entry + changelog[len("# 更新\n"):]
write("CHANGELOG.md", changelog)

tests = read("tests/test_sqlite_storage.py")
if "test_sql_primary_successful_penalty_is_not_consumed_by_probe" not in tests:
    tests += r'''


def test_sql_primary_successful_penalty_is_not_consumed_by_probe(tmp_path):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_penalties"] = {
        "v2|qq|user|1": {"due_date": "2026-08-04", "failed": False}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)

    probe = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig=None,
        penalty_should_fail=False,
    )
    assert probe["status"] == "needs-pig"
    with storage._connection() as connection:
        assert connection.execute(
            "SELECT due_date, failed FROM eaten_penalties "
            "WHERE user_id = 'v2|qq|user|1'"
        ).fetchone() == ("2026-08-04", 0)

    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        penalty_should_fail=False,
    )
    assert result["status"] == "created"
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM eaten_penalties").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 1


def test_sql_primary_successful_penalty_rolls_back_with_failed_draw(
    tmp_path, monkeypatch
):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_penalties"] = {
        "v2|qq|user|1": {"due_date": "2026-08-04", "failed": False}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)
    original_writer = storage._write_document_tx

    def fail_on_history(connection, key, value, **kwargs):
        if key == "pig_history.json":
            raise RuntimeError("draw fault injection")
        return original_writer(connection, key, value, **kwargs)

    monkeypatch.setattr(storage, "_write_document_tx", fail_on_history)
    with pytest.raises(RuntimeError, match="draw fault injection"):
        storage.create_daily_draw(
            draw_date="2026-08-04",
            user_id="v2|qq|user|1",
            pig={"id": "pig-a", "name": "A"},
            penalty_should_fail=False,
        )
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 0
        assert connection.execute(
            "SELECT due_date, failed FROM eaten_penalties "
            "WHERE user_id = 'v2|qq|user|1'"
        ).fetchone() == ("2026-08-04", 0)
    documents = storage.export_documents()
    assert documents["roast_state.json"]["eaten_penalties"]["v2|qq|user|1"] == {
        "due_date": "2026-08-04",
        "failed": False,
    }
'''
write("tests/test_sqlite_storage.py", tests)
