from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v214_release_contract_and_clean_workflows():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    storage = (ROOT / "storage" / "sqlite_storage.py").read_text(encoding="utf-8")
    assert 'version: "2.14.0"' in metadata
    assert "schema_version = 5" in storage
    assert "sql-primary-v2.14" in storage
    assert not (ROOT / ".github" / "workflows" / "apply-v214.yml").exists()
    assert not (
        ROOT / ".github" / "workflows" / "apply-v214-observability.yml"
    ).exists()
