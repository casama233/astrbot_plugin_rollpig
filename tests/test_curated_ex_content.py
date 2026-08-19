from __future__ import annotations

import json
from pathlib import Path

from ex_variants import build_effective_ex_variants


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "resource"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_authored_bundled_ex_material_is_quarantined():
    assert not (RESOURCE / "pig_ex_variants.json").exists()
    assert not (RESOURCE / "ex_curated").exists()


def test_deterministic_baseline_still_covers_the_bundled_catalog():
    primary = _load(RESOURCE / "pig.json")
    ids = {str(item["id"]) for item in primary}
    effective = build_effective_ex_variants(primary, {})

    assert set(effective) == ids
    for pig_id, levels in effective.items():
        assert set(levels) == {1, 2, 3, 4, 5}, pig_id
        descriptions = [str(levels[level].get("description") or "") for level in range(1, 6)]
        analyses = [str(levels[level].get("analysis") or "") for level in range(1, 6)]
        assert all(descriptions), pig_id
        assert all(analyses), pig_id
        assert len(set(descriptions)) == 5, pig_id
        assert len(set(analyses)) == 5, pig_id


def test_no_compatibility_floor_ids_are_required_by_bundled_ex_ci():
    source = (ROOT / "tests" / "test_curated_ex_content.py").read_text(encoding="utf-8")
    assert "17ac1586a91c33995883803a55e2f755047f6e1f" not in source
    assert "201_official_pigs" not in source
    assert "RESTORED_COMPAT_IDS" not in source
