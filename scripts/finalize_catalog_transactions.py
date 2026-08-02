from __future__ import annotations

import ast
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "main.py"
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

(root / "tests" / "conftest.py").write_text(
    '''from __future__ import annotations\n\nimport sys\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nif str(ROOT) not in sys.path:\n    sys.path.insert(0, str(ROOT))\n''',
    encoding="utf-8",
)
print("catalog transactions and test path finalized")
