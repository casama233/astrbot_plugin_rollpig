from pathlib import Path

path = Path("storage/sqlite_storage.py")
text = path.read_text(encoding="utf-8")
old = '''            connection.execute(
                "DELETE FROM daily_roast_counts WHERE draw_date < ?",
                (str(cutoff_date),),
            )
            total = int(
                connection.execute(
                    "SELECT roast_count FROM daily_roast_counts "
                    "WHERE draw_date = ? AND group_id = ? AND user_id = ?",
                    (draw_date, group_id, user_id),
                ).fetchone()[0]
            )
'''
new = '''            total = int(
                connection.execute(
                    "SELECT roast_count FROM daily_roast_counts "
                    "WHERE draw_date = ? AND group_id = ? AND user_id = ?",
                    (draw_date, group_id, user_id),
                ).fetchone()[0]
            )
            connection.execute(
                "DELETE FROM daily_roast_counts WHERE draw_date < ?",
                (str(cutoff_date),),
            )
'''
if text.count(old) != 1:
    raise RuntimeError(f"roast pruning anchor count={text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
