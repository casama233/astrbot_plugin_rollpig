from __future__ import annotations

import ast
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "main.py"
text = path.read_text(encoding="utf-8")
old = '''                self.save_json(self.local_overrides_path, overrides)
                self.save_json(self.tombstones_path, sorted(tombstones))
'''
new = '''                self.save_json_batch(
                    {
                        self.local_overrides_path: overrides,
                        self.tombstones_path: sorted(tombstones),
                    }
                )
'''
count = text.count(old)
if count != 2:
    raise RuntimeError(f"expected save and delete metadata pairs, got {count}")
text = text.replace(old, new)
ast.parse(text)
path.write_text(text, encoding="utf-8")
print("catalog transactions finalized")
