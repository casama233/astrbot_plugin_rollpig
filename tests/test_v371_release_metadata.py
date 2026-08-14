from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_v371_metadata_declares_current_stable_version():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    assert re.search(r'^version:\s*"3\.7\.1"\s*$', metadata, re.MULTILINE)
