from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_updater_uses_hmac_compare_digest():
    source = (ROOT / "updater.py").read_text(encoding="utf-8")
    assert "import hmac" in source
    assert "hmac.compare_digest(" in source
    assert "hashlib.compare_digest(" not in source
