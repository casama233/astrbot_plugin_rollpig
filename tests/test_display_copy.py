from __future__ import annotations

from display_copy import simplify_display_text, simplify_pig_display_copy
from ex_variants import validate_ex_variants
from roast_copy import decode_ai_candidates
from services.catalog_service import CatalogService


def test_simplify_display_text_converts_traditional_copy():
    assert simplify_display_text("豬圈後廚開飯") == "猪圈后厨开饭"


def test_pig_display_normalization_preserves_identity_and_extra_fields():
    raw = {
        "id": "demo-pig",
        "name": "測試豬",
        "description": "今天很適合發呆",
        "analysis": "後廚不開火",
        "image": "demo.png",
    }
    result = simplify_pig_display_copy(raw)
    assert result == {
        "id": "demo-pig",
        "name": "测试猪",
        "description": "今天很适合发呆",
        "analysis": "后厨不开火",
        "image": "demo.png",
    }
    assert raw["name"] == "測試豬"


def test_catalog_ingress_normalizes_public_or_local_display_copy():
    merged = CatalogService.merge_layers(
        [{"id": "p", "name": "小豬", "description": "後廚", "analysis": "開飯"}],
        [],
        frozenset(),
    )
    assert merged[0]["id"] == "p"
    assert merged[0]["name"] == "小猪"
    assert merged[0]["description"] == "后厨"
    assert merged[0]["analysis"] == "开饭"


def test_ex_override_copy_is_normalized_without_touching_image_or_id():
    result = validate_ex_variants(
        {"pigs": {"demo-pig": {"1": {"description": "返場", "analysis": "繼續成長", "image": "demo.png"}}}},
        {"demo-pig"},
    )
    item = result["demo-pig"][1]
    assert item["description"] == "返场"
    assert item["analysis"] == "继续成长"
    assert item["image"] == "demo.png"


def test_ai_roast_candidates_are_normalized_before_selection_or_storage():
    assert decode_ai_candidates('["後廚開飯", "豬圈限定"]') == ["后厨开饭", "猪圈限定"]
