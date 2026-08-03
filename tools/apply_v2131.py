from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one marker, found {count}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "storage/sqlite_storage.py",
    "    schema_version = 3\n",
    "    schema_version = 4\n",
)

replace_once(
    "storage/sqlite_storage.py",
    '''                    connection.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) "
                        "VALUES (3, unixepoch())"
                    )
                connection.execute("COMMIT")
''',
    '''                    connection.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) "
                        "VALUES (3, unixepoch())"
                    )
                if 4 not in migrated:
                    connection.execute(
                        """
                        UPDATE daily_draws
                        SET was_new_unlock = CASE WHEN EXISTS (
                            SELECT 1
                            FROM user_pigs
                            WHERE user_pigs.user_id = daily_draws.user_id
                              AND user_pigs.pig_id = COALESCE(
                                  NULLIF(daily_draws.original_pig_id, ''),
                                  daily_draws.pig_id
                              )
                              AND user_pigs.first_unlocked = daily_draws.draw_date
                        ) THEN 1 ELSE 0 END
                        """
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) "
                        "VALUES (4, unixepoch())"
                    )
                connection.execute("COMMIT")
''',
)

replace_once(
    "storage/sqlite_storage.py",
    '''                group_ids = sorted(set(memberships.get(user_key, [])))
                connection.execute(
                    """
                    INSERT INTO daily_draws(
                        draw_date, user_id, pig_id, original_pig_id, group_ids_json,
                        created_at, was_new_unlock
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(draw_date),
                        user_key,
                        str(pig_id or ""),
                        str(originals.get(user_id) or ""),
                        json.dumps(group_ids, ensure_ascii=False),
                        int(time.time()),
                        0,
                    ),
                )
''',
    '''                group_ids = sorted(set(memberships.get(user_key, [])))
                original_pig_id = str(originals.get(user_id) or "")
                effective_pig_id = original_pig_id or str(pig_id or "")
                was_new_unlock = (
                    connection.execute(
                        "SELECT 1 FROM user_pigs "
                        "WHERE user_id = ? AND pig_id = ? AND first_unlocked = ?",
                        (user_key, effective_pig_id, str(draw_date)),
                    ).fetchone()
                    is not None
                )
                connection.execute(
                    """
                    INSERT INTO daily_draws(
                        draw_date, user_id, pig_id, original_pig_id, group_ids_json,
                        created_at, was_new_unlock
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(draw_date),
                        user_key,
                        str(pig_id or ""),
                        original_pig_id,
                        json.dumps(group_ids, ensure_ascii=False),
                        int(time.time()),
                        int(was_new_unlock),
                    ),
                )
''',
)

replace_once(
    "main.py",
    '"AstrBot-RollPig/2.13.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
    '"AstrBot-RollPig/2.13.1 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
)

replace_once(
    "metadata.yaml",
    'version: "2.13.0"',
    'version: "2.13.1"',
)

replace_once(
    "CHANGELOG.md",
    "# 更新\n",
    "# 更新\n## v2.13.1 (2026-08-04)\n### 新解锁趋势修复\n- 修复 JSON→SQLite 迁移与投影重建把历史抽取的 `was_new_unlock` 全部写成 0，导致管理面板「新解锁」曲线长期贴地的问题。\n- schema 4 会根据每位用户图鉴的 `first_unlocked` 日期自动回填历史抽取；被吃掉的记录使用 `original_pig_id` 还原当天真正解锁的小猪。\n- 今后的 JSON 投影会在写入 `daily_draws` 时直接计算新解锁标记，不会再次丢失统计。\n\n",
)

replace_once(
    "tests/test_sqlite_storage.py",
    "    assert version == 3\n",
    "    assert version == 4\n",
)

print("v2.13.1 unlock trend patch applied")
