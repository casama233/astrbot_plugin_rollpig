from __future__ import annotations

import re
from pathlib import Path

path = Path(__file__).with_name("apply_audit_fixes.py")
text = path.read_text(encoding="utf-8")

# The streaming replacement already performs image validation. Remove the earlier
# overlapping replacement so the guarded source matcher still sees the original block.
pattern = re.compile(
    r'''main = replace_once\(\n\s+main,\n\s+"                        try:\\\n.*?\n\s+"cloud image dimension validation",\n\)\n''',
    re.DOTALL,
)
text, count = pattern.subn("", text, count=1)
if count != 1:
    raise RuntimeError(f"could not remove overlapping cloud validation patch: {count}")

path.write_text(text, encoding="utf-8")
print("audit patcher prepared")
