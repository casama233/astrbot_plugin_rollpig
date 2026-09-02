#!/usr/bin/env python3
"""Audit handwritten EX coverage before deterministic materialization runs."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
_REQUIRED_LEVELS = {"1", "2", "3", "4", "5"}
_REQUIRED_COPY_FIELDS = {"description", "analysis"}
_BUNDLED_COPY_GLOB = "bundled_ex_copy*.json"
_BUNDLED_COPY_SCOPE = "bundled-lineage-text-only"
_FELIS_COPY_FILENAME = "felis_direct_ex_copy.json"
_FELIS_COPY_SCOPE = "felis-direct-text-only"
_FELIS_SCHEMA_VERSION = 3
_FELIS_AUTHORING_MODE = "explicit-ex1-ex5"


class CoverageError(ValueError):
    """Raised when canonical authoring does not prove handwritten coverage."""


@dataclass(frozen=True)
class CoverageReport:
    bundled_catalog_count: int
    bundled_handwritten_count: int
    felis_allowlist_count: int
    felis_handwritten_count: int

    @property
    def total_handwritten_count(self) -> int:
        return self.bundled_handwritten_count + self.felis_handwritten_count

    @property
    def authored_level_count(self) -> int:
        return self.total_handwritten_count * len(_REQUIRED_LEVELS)

    def summary(self) -> str:
        return (
            "handwritten EX coverage: "
            f"bundled {self.bundled_handwritten_count}/{self.bundled_catalog_count}; "
            f"Felis {self.felis_handwritten_count}/{self.felis_allowlist_count}; "
            f"total {self.total_handwritten_count} pigs / "
            f"{self.authored_level_count} authored EX levels"
        )


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise CoverageError(f"无法读取 {path}: {exc}") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CoverageError(f"{path} 不是有效 UTF-8 JSON：{exc}") from exc


def _load_catalog_ids(path: Path) -> set[str]:
    payload = _load_json(path)
    if not isinstance(payload, list) or not payload:
        raise CoverageError("resource/pig.json 必须是非空数组")

    ids: list[str] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise CoverageError(f"resource/pig.json 第 {index + 1} 项不是对象")
        pig_id = str(item.get("id") or "").strip()
        if not pig_id:
            raise CoverageError(f"resource/pig.json 第 {index + 1} 项缺少 ID")
        ids.append(pig_id)
    if len(set(ids)) != len(ids):
        duplicates = sorted({pig_id for pig_id in ids if ids.count(pig_id) > 1})
        raise CoverageError("resource/pig.json 存在重复 ID：" + ", ".join(duplicates))
    return set(ids)


def _validate_explicit_levels(pig_id: str, spec: object, *, source: str) -> None:
    if not isinstance(spec, dict) or set(spec) != {"levels"}:
        raise CoverageError(f"{source}: {pig_id} 必须只提供显式 levels")
    raw_levels = spec.get("levels")
    if not isinstance(raw_levels, dict) or set(map(str, raw_levels)) != _REQUIRED_LEVELS:
        raise CoverageError(f"{source}: {pig_id} 必须完整手写 EX1-EX5")

    descriptions: list[str] = []
    analyses: list[str] = []
    for level in sorted(_REQUIRED_LEVELS):
        item = raw_levels.get(level)
        if not isinstance(item, dict) or set(item) != _REQUIRED_COPY_FIELDS:
            raise CoverageError(
                f"{source}: {pig_id} EX{level} 必须且只能提供 description/analysis"
            )
        description = str(item.get("description") or "").strip()
        analysis = str(item.get("analysis") or "").strip()
        if not description or not analysis:
            raise CoverageError(f"{source}: {pig_id} EX{level} 存在空白文案")
        descriptions.append(description)
        analyses.append(analysis)

    if len(set(descriptions)) != len(_REQUIRED_LEVELS):
        raise CoverageError(f"{source}: {pig_id} 的五级 description 存在重复")
    if len(set(analyses)) != len(_REQUIRED_LEVELS):
        raise CoverageError(f"{source}: {pig_id} 的五级 analysis 存在重复")


def _load_bundled_handwritten_ids(resource_dir: Path, catalog_ids: set[str]) -> set[str]:
    paths = sorted(
        resource_dir.glob(_BUNDLED_COPY_GLOB),
        key=lambda path: (path.name != "bundled_ex_copy.json", path.name),
    )
    if not paths:
        raise CoverageError("缺少 resource/bundled_ex_copy*.json 手写文案")

    specs: dict[str, object] = {}
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, dict):
            raise CoverageError(f"{path.name} 必须是 JSON 对象")
        provenance = payload.get("provenance")
        if not isinstance(provenance, dict):
            raise CoverageError(f"{path.name} 缺少 provenance")
        if str(provenance.get("scope") or "") != _BUNDLED_COPY_SCOPE:
            raise CoverageError(f"{path.name} provenance scope 不匹配")
        if provenance.get("quarantined_ex_used") is not False:
            raise CoverageError(
                f"{path.name} 必须声明 quarantined_ex_used=false"
            )
        pigs = payload.get("pigs")
        if not isinstance(pigs, dict) or not pigs:
            raise CoverageError(f"{path.name} pigs 必须是非空对象")
        for raw_pig_id, spec in pigs.items():
            pig_id = str(raw_pig_id or "").strip()
            if not pig_id:
                raise CoverageError(f"{path.name} 含空白小猪 ID")
            if pig_id in specs:
                raise CoverageError(f"Bundled 手写分片重复定义：{pig_id}")
            _validate_explicit_levels(pig_id, spec, source=path.name)
            specs[pig_id] = spec

    authored_ids = set(specs)
    missing = sorted(catalog_ids - authored_ids)
    extras = sorted(authored_ids - catalog_ids)
    if missing:
        raise CoverageError(
            "Bundled canonical authoring 缺少 catalog ID：" + ", ".join(missing)
        )
    if extras:
        raise CoverageError(
            "Bundled canonical authoring 含未知 ID：" + ", ".join(extras)
        )
    return authored_ids


def _load_python_string_ids(path: Path, variable_name: str) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError as exc:
        raise CoverageError(f"无法读取 {path}: {exc}") from exc
    except (UnicodeError, SyntaxError) as exc:
        raise CoverageError(f"无法解析 {path}: {exc}") from exc

    value_node: ast.AST | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == variable_name
            for target in node.targets
        ):
            value_node = node.value
            break
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == variable_name
        ):
            value_node = node.value
            break
    if value_node is None:
        raise CoverageError(f"{path} 缺少 {variable_name}")

    try:
        raw_value = ast.literal_eval(value_node)
    except (ValueError, TypeError) as exc:
        raise CoverageError(f"{variable_name} 必须是静态字符串序列") from exc
    if not isinstance(raw_value, (tuple, list, set, frozenset)) or not raw_value:
        raise CoverageError(f"{variable_name} 必须是非空字符串序列")

    values = [str(item or "").strip() for item in raw_value]
    if not all(values):
        raise CoverageError(f"{variable_name} 含空白 ID")
    if len(set(values)) != len(values):
        raise CoverageError(f"{variable_name} 含重复 ID")
    return set(values)


def _load_felis_handwritten_ids(
    resource_dir: Path,
    allowlist_ids: set[str],
) -> set[str]:
    path = resource_dir / _FELIS_COPY_FILENAME
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise CoverageError(f"{_FELIS_COPY_FILENAME} 必须是 JSON 对象")
    if payload.get("schema_version") != _FELIS_SCHEMA_VERSION:
        raise CoverageError(
            f"{_FELIS_COPY_FILENAME} schema_version 必须为 {_FELIS_SCHEMA_VERSION}"
        )

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise CoverageError(f"{_FELIS_COPY_FILENAME} 缺少 provenance")
    if str(provenance.get("scope") or "") != _FELIS_COPY_SCOPE:
        raise CoverageError(f"{_FELIS_COPY_FILENAME} provenance scope 不匹配")
    if provenance.get("upstream_ex_used") is not False:
        raise CoverageError(
            f"{_FELIS_COPY_FILENAME} 必须声明 upstream_ex_used=false"
        )
    if not str(provenance.get("source_basis") or "").strip():
        raise CoverageError(f"{_FELIS_COPY_FILENAME} source_basis 不能为空")
    if str(provenance.get("authoring_mode") or "") != _FELIS_AUTHORING_MODE:
        raise CoverageError(
            f"{_FELIS_COPY_FILENAME} authoring_mode 必须为 {_FELIS_AUTHORING_MODE}"
        )
    try:
        declared_count = int(provenance.get("handwritten_id_count"))
    except (TypeError, ValueError):
        declared_count = -1
    if declared_count != len(allowlist_ids):
        raise CoverageError(
            f"{_FELIS_COPY_FILENAME} handwritten_id_count 与 allowlist 不一致"
        )

    pigs = payload.get("pigs")
    if not isinstance(pigs, dict):
        raise CoverageError(f"{_FELIS_COPY_FILENAME} pigs 必须是对象")
    authored_ids = {str(pig_id) for pig_id in pigs}
    missing = sorted(allowlist_ids - authored_ids)
    extras = sorted(authored_ids - allowlist_ids)
    if missing:
        raise CoverageError("Felis canonical authoring 缺少 allowlist ID：" + ", ".join(missing))
    if extras:
        raise CoverageError("Felis canonical authoring 含未知 ID：" + ", ".join(extras))

    for raw_pig_id, spec in pigs.items():
        _validate_explicit_levels(
            str(raw_pig_id),
            spec,
            source=_FELIS_COPY_FILENAME,
        )
    return authored_ids


def check_handwritten_coverage(root: Path = ROOT) -> CoverageReport:
    """Validate canonical authoring without consulting generated artifacts."""

    root = Path(root).resolve()
    resource_dir = root / "resource"
    bundled_catalog_ids = _load_catalog_ids(resource_dir / "pig.json")
    bundled_handwritten_ids = _load_bundled_handwritten_ids(
        resource_dir,
        bundled_catalog_ids,
    )
    felis_allowlist_ids = _load_python_string_ids(
        root / "felis_direct_feature.py",
        "FELIS_DIRECT_IDS",
    )
    felis_handwritten_ids = _load_felis_handwritten_ids(
        resource_dir,
        felis_allowlist_ids,
    )

    return CoverageReport(
        bundled_catalog_count=len(bundled_catalog_ids),
        bundled_handwritten_count=len(bundled_handwritten_ids),
        felis_allowlist_count=len(felis_allowlist_ids),
        felis_handwritten_count=len(felis_handwritten_ids),
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate explicit handwritten bundled/Felis EX authoring before "
            "deterministic materialization."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root (default: detected from this script)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = check_handwritten_coverage(args.root)
    except CoverageError as exc:
        print(f"handwritten EX coverage check failed: {exc}", file=sys.stderr)
        return 1
    print(report.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
