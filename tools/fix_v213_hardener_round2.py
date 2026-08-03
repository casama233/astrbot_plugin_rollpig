from pathlib import Path

path = Path(__file__).with_name("harden_v213_sql_authority.py")
text = path.read_text(encoding="utf-8")

old = '''            for key, expected_value in authoritative.items():
                actual_value = documents.get(key)
                if key in decode_errors or actual_value != expected_value:
                    document_mismatches[f"document:{key}"] = {
'''
new = '''            for key, expected_value in authoritative.items():
                actual_value = documents.get(key)
                expected_compare = self._clone(expected_value)
                actual_compare = self._clone(actual_value)
                if isinstance(expected_compare, dict):
                    expected_compare.pop("version", None)
                if isinstance(actual_compare, dict):
                    actual_compare.pop("version", None)
                if key in decode_errors or actual_compare != expected_compare:
                    document_mismatches[f"document:{key}"] = {
'''
if text.count(old) != 1:
    raise RuntimeError("semantic comparison block not found exactly once")
text = text.replace(old, new, 1)

old = '''    def export_documents(self) -> dict[str, Any]:
        with self.transaction() as connection:
            if self._write_authority(connection).startswith("sql-primary-"):
                self._repair_compatibility_documents_tx(connection)
                self._set_write_authority(connection)
            rows = connection.execute(
'''
new = '''    def export_documents(self) -> dict[str, Any]:
        with self.transaction() as connection:
            health = self._projection_health(connection)
            if (
                self._write_authority(connection).startswith("sql-primary-")
                and not health["projection_ok"]
            ):
                self._repair_compatibility_documents_tx(connection)
                self._set_write_authority(connection)
            rows = connection.execute(
'''
if text.count(old) != 1:
    raise RuntimeError("export repair block not found exactly once")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
