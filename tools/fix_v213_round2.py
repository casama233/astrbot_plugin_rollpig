from pathlib import Path

root = Path(__file__).resolve().parents[1]

path = root / "tests" / "test_source_regressions.py"
text = path.read_text(encoding="utf-8")
old = '    assert "get_ai_roast_copies" in ai and "store_ai_roast_copy" in ai\n'
new = '    assert "claim_ai_roast_generation" in ai and "complete_ai_roast_generation" in ai\n'
if text.count(old) != 1:
    raise RuntimeError("v2.12 AI regression assertion not found exactly once")
path.write_text(text.replace(old, new, 1), encoding="utf-8")

path = root / "tests" / "test_sqlite_storage.py"
text = path.read_text(encoding="utf-8")
old = "    assert version == 2\n"
new = "    assert version == 3\n"
if text.count(old) != 1:
    raise RuntimeError("schema version assertion not found exactly once")
path.write_text(text.replace(old, new, 1), encoding="utf-8")

print("v2.13 round-two test expectations updated")
