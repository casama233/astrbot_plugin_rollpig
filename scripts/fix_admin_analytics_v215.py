from pathlib import Path

path = Path(__file__).with_name("apply_admin_analytics_v215.py")
text = path.read_text(encoding="utf-8")
old = '"WHERE d.draw_date BETWEEN ? AND ? GROUP BY pig_id",'
new = (
    '"WHERE d.draw_date BETWEEN ? AND ? "\n'
    '                    "GROUP BY COALESCE(NULLIF(d.original_pig_id, \'\'), d.pig_id)",'
)
if text.count(old) != 1:
    raise SystemExit(f"expected one ambiguous GROUP BY anchor, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("qualified rising pig grouping")
