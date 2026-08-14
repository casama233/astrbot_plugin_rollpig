from pathlib import Path

path = Path(__file__).with_name("_apply_phase3a_roast_charge.py")
source = path.read_text(encoding="utf-8")
start = source.index(
    "# Avoid implicit VALUES arity assumptions now that roast_cooldowns has six columns."
)
end = source.index(
    "# Insert one shared transactional token-bucket implementation before legacy cooldown API."
)
source = source[:start] + source[end:]
exec(compile(source, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})
