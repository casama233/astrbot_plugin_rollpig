from pathlib import Path

path = Path(__file__).with_name("harden_v213_sql_authority.py")
text = path.read_text(encoding="utf-8")

old = '''        valid_backdoors = sum(
            1
            for raw_key in backdoors if isinstance(backdoors, dict)
            if ":" in str(raw_key) and str(raw_key).partition(":")[2]
        )
'''
new = '''        valid_backdoors = sum(
            1
            for raw_key in (backdoors if isinstance(backdoors, dict) else {})
            if ":" in str(raw_key) and str(raw_key).partition(":")[2]
        )
'''
if text.count(old) != 1:
    raise RuntimeError("backdoor iterable block not found exactly once")
text = text.replace(old, new, 1)

old = '''        authority = self._write_authority(connection)
        document_mismatches: dict[str, Any] = {}
        if authority.startswith("sql-primary-"):
'''
new = '''        authority = self._write_authority(connection)
        document_mismatches: dict[str, Any] = {}

        def semantic_value(value: Any) -> Any:
            if isinstance(value, dict):
                normalized: dict[str, Any] = {}
                for item_key, item_value in value.items():
                    if str(item_key) == "version":
                        continue
                    normalized_value = semantic_value(item_value)
                    if normalized_value in ({}, [], None):
                        continue
                    normalized[str(item_key)] = normalized_value
                return normalized
            if isinstance(value, list):
                return [semantic_value(item) for item in value]
            return value

        if authority.startswith("sql-primary-"):
'''
if text.count(old) != 1:
    raise RuntimeError("projection semantic helper insertion point not found")
text = text.replace(old, new, 1)

old = '''                expected_compare = self._clone(expected_value)
                actual_compare = self._clone(actual_value)
                if isinstance(expected_compare, dict):
                    expected_compare.pop("version", None)
                if isinstance(actual_compare, dict):
                    actual_compare.pop("version", None)
                if key in decode_errors or actual_compare != expected_compare:
'''
new = '''                expected_compare = semantic_value(expected_value)
                actual_compare = semantic_value(actual_value)
                if key in decode_errors or actual_compare != expected_compare:
'''
if text.count(old) != 1:
    raise RuntimeError("projection semantic comparison block not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
