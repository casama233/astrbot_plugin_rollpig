from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tests/test_source_regressions.py"
text = path.read_text(encoding="utf-8")
old = "assert 'version: \"3.0.4\"' in metadata"
new = "assert 'version: \"3.0.5\"' in metadata"
if old not in text:
    raise SystemExit("v3 release version assertion not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
Path(__file__).unlink(missing_ok=True)
print("v3.0.5 source regression contract patched")
