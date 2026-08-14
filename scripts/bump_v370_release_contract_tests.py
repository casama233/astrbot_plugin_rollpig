from pathlib import Path

TARGETS = (
    "tests/test_identity_migration_plus.py",
    "tests/test_source_regressions.py",
    "tests/test_v312_release_contract.py",
)

old = "assert 'version: \"3.6.5\"' in metadata"
new = "assert 'version: \"3.7.0\"' in metadata"

for filename in TARGETS:
    path = Path(filename)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{filename}: expected exactly one old release assertion, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")
