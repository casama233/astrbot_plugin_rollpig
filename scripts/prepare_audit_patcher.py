from __future__ import annotations

from pathlib import Path

path = Path(__file__).with_name("apply_audit_fixes.py")
text = path.read_text(encoding="utf-8")


def remove_replace_block(source: str, label_text: str) -> str:
    label = f'"{label_text}"'
    label_pos = source.find(label)
    if label_pos < 0:
        raise RuntimeError(f"patch label was not found: {label_text}")
    start = source.rfind("main = replace_once(", 0, label_pos)
    end = source.find("\n)\n", label_pos)
    if start < 0 or end < 0:
        raise RuntimeError(f"patch boundaries were not found: {label_text}")
    return source[:start] + source[end + 3 :]


# The streaming replacement already validates every image.
text = remove_replace_block(text, "cloud image dimension validation")

# Keep the existing data-lock indentation in catalog writes. The postprocessor
# will replace both pairs of JSON writes with save_json_batch without inserting
# another nested block, avoiding fragile source re-indentation.
start_label = '"page save lock"'
end_label = '"page delete batch"'
start_pos = text.find(start_label)
end_label_pos = text.find(end_label)
if start_pos < 0 or end_label_pos < 0:
    raise RuntimeError("catalog transaction patch range was not found")
start = text.rfind("main = replace_once(", 0, start_pos)
end = text.find("\n)\n", end_label_pos)
if start < 0 or end < 0:
    raise RuntimeError("catalog transaction patch boundaries were not found")
text = text[:start] + text[end + 3 :]

path.write_text(text, encoding="utf-8")
print("audit patcher prepared")
