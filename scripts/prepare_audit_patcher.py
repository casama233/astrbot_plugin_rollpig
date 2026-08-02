from __future__ import annotations

from pathlib import Path

path = Path(__file__).with_name("apply_audit_fixes.py")
text = path.read_text(encoding="utf-8")

# The streaming replacement already validates every image. Remove the earlier
# overlapping replacement by its unique guard label, not by matching its large
# escaped source literal.
label = '"cloud image dimension validation"'
label_pos = text.find(label)
if label_pos < 0:
    raise RuntimeError("cloud validation patch label was not found")
start = text.rfind("main = replace_once(", 0, label_pos)
end = text.find("\n)\n", label_pos)
if start < 0 or end < 0:
    raise RuntimeError("cloud validation patch boundaries were not found")
text = text[:start] + text[end + 3 :]

path.write_text(text, encoding="utf-8")
print("audit patcher prepared")
