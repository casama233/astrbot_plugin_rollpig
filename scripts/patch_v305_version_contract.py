from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tests/test_source_regressions.py"
text = path.read_text(encoding="utf-8")
replacements = {
    "assert 'version: \"3.0.4\"' in metadata": "assert 'version: \"3.0.5\"' in metadata",
    'assert "AstrBot-RollPig/3.0.4" in SOURCE': 'assert "AstrBot-RollPig/3.0.5" in SOURCE',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"v3 release assertion not found: {old}")
    text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
Path(__file__).unlink(missing_ok=True)
print("v3.0.5 source regression contract patched")
