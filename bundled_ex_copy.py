from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

try:
    from .ex_variants import validate_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import validate_ex_variants


BUNDLED_EX_COPY_FILENAME = "bundled_ex_copy.json"
BUNDLED_EX_COPY_GLOB = "bundled_ex_copy*.json"
BUNDLED_EX_COPY_SCOPE = "bundled-lineage-text-only"
_REQUIRED_LEVELS = {"1", "2", "3", "4", "5"}
_REQUIRED_COPY_FIELDS = {"description", "analysis"}


def _normalize_specs(raw_specs: object) -> dict[str, dict[str, dict[str, str]]]:
    if not isinstance(raw_specs, dict) or not raw_specs:
        raise ValueError("Bundled EX 手写文案 pigs 必须是非空对象")

    pigs: dict[str, dict[str, dict[str, str]]] = {}
    for raw_pig_id, raw_spec in raw_specs.items():
        pig_id = str(raw_pig_id or "").strip()
        if not pig_id or not isinstance(raw_spec, dict) or set(raw_spec) != {"levels"}:
            raise ValueError(f"{pig_id} 的 Bundled EX 手写文案规格字段不完整")
        raw_levels = raw_spec.get("levels")
        if not isinstance(raw_levels, dict) or set(map(str, raw_levels)) != _REQUIRED_LEVELS:
            raise ValueError(f"{pig_id} 的 Bundled EX 手写文案必须完整提供 EX1-EX5")

        levels: dict[str, dict[str, str]] = {}
        for raw_level, raw_item in raw_levels.items():
            level = str(raw_level)
            if not isinstance(raw_item, dict) or set(raw_item) != _REQUIRED_COPY_FIELDS:
                raise ValueError(f"{pig_id} EX{level} 的 Bundled EX 手写文案字段不完整")
            item = {key: str(raw_item.get(key) or "").strip() for key in _REQUIRED_COPY_FIELDS}
            if not all(item.values()):
                raise ValueError(f"{pig_id} EX{level} 的 Bundled EX 手写文案存在空字段")
            levels[level] = item
        pigs[pig_id] = levels
    return pigs


def _load_specs(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} 的 Bundled EX 手写文案规格必须是 JSON 对象")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError(f"{path.name} 的 Bundled EX 手写文案规格缺少 provenance")
    if str(provenance.get("scope") or "") != BUNDLED_EX_COPY_SCOPE:
        raise ValueError(f"{path.name} 的 Bundled EX 手写文案 provenance scope 不匹配")
    if provenance.get("quarantined_ex_used") is not False:
        raise ValueError(f"{path.name} 的 Bundled EX 手写文案必须声明 quarantined_ex_used=false")

    return _normalize_specs(payload.get("pigs"))


def _copy_paths(resource_dir: Path) -> list[Path]:
    paths = list(Path(resource_dir).glob(BUNDLED_EX_COPY_GLOB))
    return sorted(paths, key=lambda path: (path.name != BUNDLED_EX_COPY_FILENAME, path.name))


def load_bundled_ex_copy(
    resource_dir: Path,
    pig_ids: Iterable[str],
    bundled_ids: Iterable[str],
    *,
    image_extensions: set[str] | tuple[str, ...],
) -> dict[str, dict[int, dict[str, str]]]:
    """Load phased project-owned EX copy for bundled/base-lineage pigs."""
    paths = _copy_paths(Path(resource_dir))
    if not paths:
        return {}

    specs: dict[str, dict[str, dict[str, str]]] = {}
    for path in paths:
        shard_specs = _load_specs(path)
        duplicates = sorted(set(specs).intersection(shard_specs))
        if duplicates:
            raise ValueError(
                "Bundled EX 手写文案分片重复定义小猪：" + ", ".join(duplicates)
            )
        specs.update(shard_specs)

    allowlist = {str(item) for item in bundled_ids if str(item)}
    unknown = sorted(set(specs).difference(allowlist))
    if unknown:
        raise ValueError("Bundled EX 手写文案只能引用 resource/pig.json 中的小猪：" + ", ".join(unknown))

    variants = validate_ex_variants(
        {"schema_version": 1, "pigs": specs},
        allowlist,
        image_extensions=image_extensions,
    )
    for pig_id, levels in variants.items():
        if set(levels) != {1, 2, 3, 4, 5}:
            raise ValueError(f"{pig_id} 必须完整提供 EX1-EX5 文案")
        if any("image" in item for item in levels.values()):
            raise ValueError(f"{pig_id} 的 Bundled EX 手写层不得包含 image")
        if len({item["description"] for item in levels.values()}) != 5:
            raise ValueError(f"{pig_id} EX1-EX5 description 必须逐级不同")
        if len({item["analysis"] for item in levels.values()}) != 5:
            raise ValueError(f"{pig_id} EX1-EX5 analysis 必须逐级不同")

    active_ids = {str(item) for item in pig_ids if str(item)}
    return {pig_id: levels for pig_id, levels in variants.items() if pig_id in active_ids}
