from pathlib import Path

path = Path(__file__).with_name("harden_v213_sql_authority.py")
text = path.read_text(encoding="utf-8")
old = '    "    def document_hashes(\\n",\n'
new = '    "    def document_hashes(self) -> dict[str, str]:\\n",\n'
if text.count(old) != 1:
    raise RuntimeError("hardener marker not found exactly once")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
