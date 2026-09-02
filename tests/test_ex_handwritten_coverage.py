from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_ex_handwritten_coverage import (
    CoverageError,
    check_handwritten_coverage,
    main,
)


ROOT = Path(__file__).resolve().parents[1]


def _levels(prefix: str) -> dict[str, dict[str, str]]:
    return {
        str(level): {
            "description": f"{prefix} description {level}",
            "analysis": f"{prefix} analysis {level}",
        }
        for level in range(1, 6)
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _fixture_repo(
    root: Path,
    *,
    bundled_ids: tuple[str, ...] = ("bundled-a", "bundled-b"),
    felis_ids: tuple[str, ...] = ("felis-a", "felis-b"),
) -> Path:
    resource = root / "resource"
    resource.mkdir(parents=True)
    _write_json(
        resource / "pig.json",
        [
            {
                "id": pig_id,
                "name": pig_id,
                "description": f"{pig_id} base",
                "analysis": f"{pig_id} base analysis",
            }
            for pig_id in bundled_ids
        ],
    )
    _write_json(
        resource / "bundled_ex_copy.json",
        {
            "schema_version": 1,
            "provenance": {
                "scope": "bundled-lineage-text-only",
                "quarantined_ex_used": False,
            },
            "pigs": {
                pig_id: {"levels": _levels(pig_id)} for pig_id in bundled_ids
            },
        },
    )
    (root / "felis_direct_feature.py").write_text(
        "FELIS_DIRECT_IDS = " + repr(felis_ids) + "\n",
        encoding="utf-8",
    )
    _write_json(
        resource / "felis_direct_ex_copy.json",
        {
            "schema_version": 3,
            "provenance": {
                "scope": "felis-direct-text-only",
                "source_basis": "fixture-authored base semantics",
                "upstream_ex_used": False,
                "authoring_mode": "explicit-ex1-ex5",
                "handwritten_id_count": len(felis_ids),
            },
            "pigs": {
                pig_id: {"levels": _levels(pig_id)} for pig_id in felis_ids
            },
        },
    )
    return root


def test_repository_has_full_canonical_handwritten_coverage():
    report = check_handwritten_coverage(ROOT)
    assert report.bundled_handwritten_count == report.bundled_catalog_count == 99
    assert report.felis_handwritten_count == report.felis_allowlist_count == 34
    assert report.total_handwritten_count == 133
    assert report.authored_level_count == 665


def test_cli_prints_independent_authoring_summary(tmp_path: Path, capsys):
    repo = _fixture_repo(tmp_path)
    assert main(["--root", str(repo)]) == 0
    assert capsys.readouterr().out.strip() == (
        "handwritten EX coverage: bundled 2/2; Felis 2/2; "
        "total 4 pigs / 20 authored EX levels"
    )


def test_generated_materialization_cannot_mask_missing_bundled_authoring(
    tmp_path: Path,
):
    repo = _fixture_repo(tmp_path)
    path = repo / "resource/bundled_ex_copy.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pigs"].pop("bundled-b")
    _write_json(path, payload)

    # A complete generated artifact must be irrelevant to the canonical audit.
    _write_json(
        repo / "dist/astrbot-rollpig-source/pig_ex_variants.json",
        {
            "schema_version": 1,
            "pigs": {
                "bundled-a": _levels("generated-a"),
                "bundled-b": _levels("generated-b"),
            },
        },
    )

    with pytest.raises(CoverageError, match="缺少 catalog ID：bundled-b"):
        check_handwritten_coverage(repo)


def test_duplicate_bundled_authoring_across_shards_is_rejected(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    _write_json(
        repo / "resource/bundled_ex_copy_phase99.json",
        {
            "schema_version": 1,
            "provenance": {
                "scope": "bundled-lineage-text-only",
                "quarantined_ex_used": False,
            },
            "pigs": {"bundled-a": {"levels": _levels("duplicate")}},
        },
    )

    with pytest.raises(CoverageError, match="重复定义：bundled-a"):
        check_handwritten_coverage(repo)


def test_legacy_felis_semantic_seed_is_rejected(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    path = repo / "resource/felis_direct_ex_copy.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pigs"]["felis-a"] = {
        "name": "旧种子",
        "theme": "模板成长",
        "progress": "自动扩写",
        "lesson": "不能冒充手写",
    }
    _write_json(path, payload)

    with pytest.raises(CoverageError, match="felis-a 必须只提供显式 levels"):
        check_handwritten_coverage(repo)


def test_felis_provenance_count_must_match_static_allowlist(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    path = repo / "resource/felis_direct_ex_copy.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provenance"]["handwritten_id_count"] = 1
    _write_json(path, payload)

    with pytest.raises(CoverageError, match="handwritten_id_count"):
        check_handwritten_coverage(repo)


def test_unknown_bundled_authoring_id_is_rejected(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    path = repo / "resource/bundled_ex_copy.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pigs"]["not-in-catalog"] = {"levels": _levels("unknown")}
    _write_json(path, payload)

    with pytest.raises(CoverageError, match="含未知 ID：not-in-catalog"):
        check_handwritten_coverage(repo)
