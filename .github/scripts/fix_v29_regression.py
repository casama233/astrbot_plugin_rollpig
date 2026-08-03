from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "tests" / "test_source_regressions.py"
text = path.read_text(encoding="utf-8")
old = '    assert "self.storage = JSONStorage" in init\n'
new = (
    '    assert "self.storage_manager = StorageManager" in init\n'
    '    assert "self.storage = self.storage_manager.backend" in init\n'
)
if text.count(old) != 1:
    raise RuntimeError(f"storage regression anchor count: {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
Path(__file__).unlink()
