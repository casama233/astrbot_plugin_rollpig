from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _method_source(name: str) -> str:
    source = _source("legacy_main.py")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(source, node) or ""
    raise AssertionError(f"missing method: {name}")


def test_legacy_catalog_reads_delegate_to_services():
    source = _source("legacy_main.py")
    assert "CatalogService" in source
    assert "ResourceReadService" in source
    assert "self.catalog_service = CatalogService" in source
    assert "self.resource_read_service = ResourceReadService" in source

    assert "self.catalog_service.merge_layers(" in _method_source("_reload_catalog_layers")
    assert "self.catalog_service.find(" in _method_source("_find_catalog_pig")
    assert "self.catalog_service.ordered_for_collection(" in _method_source("_ordered_pigsty_pigs")
    assert "self.resource_read_service.find_image(" in _method_source("find_image_file")
    assert "self.catalog_service.sample(" in _method_source("random_pigs")
    assert "self.catalog_service.search(" in _method_source("find_pigs")


def test_legacy_does_not_reimplement_catalog_merge_or_search_policy():
    reload_source = _method_source("_reload_catalog_layers")
    assert "override_map =" not in reload_source
    assert "merged.append" not in reload_source

    search_source = _method_source("find_pigs")
    assert "for key in (\"id\", \"name\", \"description\", \"analysis\")" not in search_source


def test_resource_read_precedence_is_documented_in_service():
    source = _source("services/resource_read_service.py")
    assert "local override -> optional EX variant -> cloud base -> bundled base" in source
