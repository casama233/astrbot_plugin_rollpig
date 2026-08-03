from pathlib import Path

path = Path('.github/scripts/apply_v210.py')
text = path.read_text(encoding='utf-8')
old = '''                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS daily_draw_groups (
                        draw_date TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        PRIMARY KEY (draw_date, user_id, group_id),
                        FOREIGN KEY (draw_date, user_id)
                            REFERENCES daily_draws(draw_date, user_id)
                            ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_identities_namespace_raw
                        ON identities(namespace, raw_id);
                    CREATE INDEX IF NOT EXISTS idx_daily_draw_groups_group_date
                        ON daily_draw_groups(group_id, draw_date);
                    """
                )
'''
new = '''                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_draw_groups (
                        draw_date TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        group_id TEXT NOT NULL,
                        PRIMARY KEY (draw_date, user_id, group_id),
                        FOREIGN KEY (draw_date, user_id)
                            REFERENCES daily_draws(draw_date, user_id)
                            ON DELETE CASCADE
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_identities_namespace_raw "
                    "ON identities(namespace, raw_id)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_daily_draw_groups_group_date "
                    "ON daily_draw_groups(group_id, draw_date)"
                )
'''
if text.count(old) != 1:
    raise SystemExit('atomic migration anchor mismatch')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
