from __future__ import annotations

import json
from pathlib import Path

from ex_variants import resolve_ex_variant, validate_ex_variants


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_bundled_ex_pack_is_non_empty_valid_and_resolves_visible_growth():
    pigs = _load_json(RESOURCE_DIR / "pig.json")
    variants_payload = _load_json(RESOURCE_DIR / "pig_ex_variants.json")

    pig_by_id = {
        str(item.get("id") or ""): item
        for item in pigs
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    variants = validate_ex_variants(
        variants_payload,
        set(pig_by_id),
        image_extensions={"png", "jpg", "jpeg", "gif", "webp"},
    )

    # The bundled pack is a product feature, not an optional empty placeholder.
    assert len(variants) >= 10

    for pig_id, levels in variants.items():
        assert levels
        base = pig_by_id[pig_id]
        highest_level = max(levels)
        resolved = resolve_ex_variant(base, variants, highest_level)

        assert resolved["_ex_level"] == highest_level
        assert resolved["_ex_variant_level"] == highest_level
        assert (
            resolved.get("description") != base.get("description")
            or resolved.get("analysis") != base.get("analysis")
            or resolved.get("_ex_image")
        ), pig_id


def test_bundled_ex_pack_keeps_sparse_and_lv5_plus_inheritance_contract():
    pigs = _load_json(RESOURCE_DIR / "pig.json")
    pig_by_id = {str(item["id"]): item for item in pigs if isinstance(item, dict)}
    variants = validate_ex_variants(
        _load_json(RESOURCE_DIR / "pig_ex_variants.json"),
        set(pig_by_id),
        image_extensions={"png", "jpg", "jpeg", "gif", "webp"},
    )

    # `pig` intentionally skips EX2/EX4. Sparse levels must continue inheriting
    # prior fields, and numeric EX can grow beyond the last configured variant.
    base = pig_by_id["pig"]
    ex4 = resolve_ex_variant(base, variants, 4)
    assert ex4["description"] == "标准猪，但已经被你养熟一点了"
    assert "老员工的从容" in ex4["analysis"]

    ex9 = resolve_ex_variant(base, variants, 9)
    assert ex9["_ex_level"] == 9
    assert ex9["_ex_variant_level"] == 5
    assert ex9["description"] == "默认款？现在是资深标准猪"
    assert "老员工的从容" in ex9["analysis"]
