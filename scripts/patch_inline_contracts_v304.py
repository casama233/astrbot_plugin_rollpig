from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

contract_path = ROOT / "tests/test_v304_release_contract.py"
contract = contract_path.read_text(encoding="utf-8")
old = "    assert './ui-feedback.js?v=3.0.4' in page\n"
new = (
    '    assert "data-rollpig-feedback-core" in page\n'
    '    assert "data-rollpig-enterprise-ui" in page\n'
    '    assert "data-rollpig-analytics-ui" in page\n'
    '    assert \'src="./ui-feedback.js\' not in page\n'
)
if old not in contract:
    raise SystemExit("release contract external-loader assertion not found")
contract_path.write_text(contract.replace(old, new, 1), encoding="utf-8")

cache_path = ROOT / "tests/test_ui_cache_busting.py"
cache = cache_path.read_text(encoding="utf-8")
cache = cache.replace(
    'payload = payload.replace("</script", "<\\/script")',
    'payload = payload.replace("</script", r"<\\/script")',
)
cache_path.write_text(cache, encoding="utf-8")

Path(__file__).unlink(missing_ok=True)
print("v3.0.4 inline asset contracts patched")
