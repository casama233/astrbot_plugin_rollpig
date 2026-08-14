from __future__ import annotations

import random

from services.catalog_service import CatalogService


def _pig(pig_id: str, **extra):
    return {"id": pig_id, "name": pig_id, **extra}


def test_merge_layers_preserves_base_order_and_appends_new_overrides():
    service = CatalogService()
    base = [_pig("a", description="base-a"), _pig("b"), _pig("c")]
    overrides = [_pig("b", description="override-b"), _pig("d")]

    merged = service.merge_layers(base, overrides, {"c"})

    assert [pig["id"] for pig in merged] == ["a", "b", "d"]
    assert merged[1]["description"] == "override-b"


def test_merge_layers_tombstone_wins_over_local_override():
    merged = CatalogService.merge_layers([_pig("a")], [_pig("a", name="local")], {"a"})
    assert merged == []


def test_find_and_collection_order_preserve_catalog_objects_and_partition_order():
    service = CatalogService()
    catalog = [_pig("a"), _pig("b"), _pig("c"), _pig("d")]

    assert service.find(catalog, "c") is catalog[2]
    ordered = service.ordered_for_collection(catalog, {"c": {}, "a": {}})
    assert [pig["id"] for pig in ordered] == ["a", "c", "b", "d"]


def test_page_count_matches_existing_catalog_contract():
    service = CatalogService(page_size=12)
    assert service.page_count([]) == 1
    assert service.page_count([_pig(str(i)) for i in range(12)]) == 1
    assert service.page_count([_pig(str(i)) for i in range(13)]) == 2


def test_search_matches_all_existing_text_fields_case_insensitively_in_catalog_order():
    catalog = [
        _pig("alpha", description="Sleepy"),
        _pig("beta", analysis="PLAYFUL"),
        _pig("toy-pig", name="玩偶猪"),
    ]
    service = CatalogService()

    assert [pig["id"] for pig in service.search(catalog, "play")] == ["beta"]
    assert [pig["id"] for pig in service.search(catalog, "toy") ] == ["toy-pig"]
    assert service.search(catalog, "   ") == []


def test_sample_caps_at_catalog_size_and_does_not_mutate_catalog():
    catalog = [_pig("a"), _pig("b"), _pig("c")]
    before = list(catalog)
    result = CatalogService.sample(catalog, 9, rng=random.Random(7))

    assert sorted(pig["id"] for pig in result) == ["a", "b", "c"]
    assert catalog == before
