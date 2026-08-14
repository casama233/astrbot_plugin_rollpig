from pathlib import Path

feature = Path("oven_refill_feature.py")
text = feature.read_text(encoding="utf-8")
marker = '''    def _init_oven_refill_feature(self) -> None:\n'''
helper = '''    @staticmethod\n    def _oven_refill_bool(value: Any, default: bool) -> bool:\n        if isinstance(value, bool):\n            return value\n        if value is None:\n            return bool(default)\n        text = str(value).strip().lower()\n        if text in {"1", "true", "yes", "on"}:\n            return True\n        if text in {"0", "false", "no", "off"}:\n            return False\n        return bool(default)\n\n    def _init_oven_refill_feature(self) -> None:\n'''
if text.count(marker) != 1:
    raise SystemExit(f"unexpected init marker count: {text.count(marker)}")
text = text.replace(marker, helper, 1)
old = '''        self.enable_oven_refill = self._config_bool(\n            config.get("enable_oven_refill", True), True\n        )\n'''
new = '''        self.enable_oven_refill = self._oven_refill_bool(\n            config.get("enable_oven_refill", True), True\n        )\n'''
if text.count(old) != 1:
    raise SystemExit("unexpected enable_oven_refill parser block")
feature.write_text(text.replace(old, new, 1), encoding="utf-8")

contract = Path("tests/test_oven_refill_feature_contract.py")
nt = contract.read_text(encoding="utf-8")
if "test_refill_init_owns_its_bool_parser" not in nt:
    nt += '''\n\ndef test_refill_init_owns_its_bool_parser_and_does_not_depend_on_base_helper():\n    source = Path("oven_refill_feature.py").read_text(encoding="utf-8")\n    assert "def _oven_refill_bool(" in source\n    assert "self._oven_refill_bool(" in source\n    assert "self._config_bool(" not in source\n'''
    contract.write_text(nt, encoding="utf-8")
