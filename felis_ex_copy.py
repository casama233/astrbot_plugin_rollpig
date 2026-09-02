from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

try:
    from .ex_variants import validate_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import validate_ex_variants


FELIS_DIRECT_EX_COPY_FILENAME = "felis_direct_ex_copy.json"
FELIS_DIRECT_EX_COPY_SCOPE = "felis-direct-text-only"
FELIS_DIRECT_EX_COPY_SCHEMA_VERSION = 3
FELIS_DIRECT_EX_COPY_AUTHORING_MODE = "explicit-ex1-ex5"
_EXPLICIT_SPEC_FIELDS = {"levels"}
_REQUIRED_LEVELS = {"1", "2", "3", "4", "5"}
_REQUIRED_COPY_FIELDS = {"description", "analysis"}


def _normalize_explicit_levels(
    pig_id: str,
    raw_levels: object,
) -> dict[str, dict[str, str]]:
    if not isinstance(raw_levels, dict) or set(map(str, raw_levels)) != _REQUIRED_LEVELS:
        raise ValueError(f"{pig_id} 的 Felis EX 手写文案必须完整提供 EX1-EX5")

    levels: dict[str, dict[str, str]] = {}
    for raw_level, raw_item in raw_levels.items():
        level = str(raw_level)
        if not isinstance(raw_item, dict) or set(raw_item) != _REQUIRED_COPY_FIELDS:
            raise ValueError(f"{pig_id} EX{level} 的手写文案字段不完整")
        values = {
            key: str(raw_item.get(key) or "").strip()
            for key in _REQUIRED_COPY_FIELDS
        }
        if not all(values.values()):
            raise ValueError(f"{pig_id} EX{level} 的手写文案存在空字段")
        levels[level] = values
    return levels


def _expand_spec_copy(raw_specs: dict[str, object]) -> dict[str, object]:
    """Normalize the all-explicit Felis EX authoring document.

    Legacy ``name/theme/progress/lesson`` semantic seeds are intentionally no
    longer accepted. Every allowlisted pig must carry five reviewable, explicit
    description/analysis pairs in the repository.
    """

    pigs: dict[str, dict[str, dict[str, str]]] = {}
    for raw_pig_id, raw_spec in raw_specs.items():
        pig_id = str(raw_pig_id or "").strip()
        if not isinstance(raw_spec, dict) or set(raw_spec) != _EXPLICIT_SPEC_FIELDS:
            raise ValueError(f"{pig_id} 的 Felis EX 手写规格字段不完整")
        pigs[pig_id] = _normalize_explicit_levels(pig_id, raw_spec.get("levels"))

    return {"schema_version": 1, "pigs": pigs}


def load_felis_direct_ex_copy(
    resource_dir: Path,
    pig_ids: Iterable[str],
    allowed_ids: Iterable[str],
    *,
    image_extensions: set[str] | tuple[str, ...],
) -> dict[str, dict[int, dict[str, str]]]:
    """Load repository-owned EX1-EX5 text for the Felis direct allowlist.

    Schema v3 requires explicit per-level copy for every allowlisted ID. The
    runtime no longer expands semantic seeds, so generic templates cannot hide a
    missing handwritten review. Felis upstream EX text and EX images remain out
    of scope.
    """

    path = Path(resource_dir) / FELIS_DIRECT_EX_COPY_FILENAME
    if not path.is_file():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Felis EX 手写文案规格必须是 JSON 对象")
    if payload.get("schema_version") != FELIS_DIRECT_EX_COPY_SCHEMA_VERSION:
        raise ValueError(
            "Felis EX 手写文案规格 schema_version 必须为 "
            f"{FELIS_DIRECT_EX_COPY_SCHEMA_VERSION}"
        )

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("Felis EX 手写文案规格缺少 provenance")
    if str(provenance.get("scope") or "") != FELIS_DIRECT_EX_COPY_SCOPE:
        raise ValueError("Felis EX 手写文案规格 provenance scope 不匹配")
    if provenance.get("upstream_ex_used") is not False:
        raise ValueError("Felis EX 手写文案规格必须声明 upstream_ex_used=false")
    if not str(provenance.get("source_basis") or "").strip():
        raise ValueError("Felis EX 手写文案规格必须声明非空 source_basis")
    if (
        str(provenance.get("authoring_mode") or "")
        != FELIS_DIRECT_EX_COPY_AUTHORING_MODE
    ):
        raise ValueError(
            "Felis EX 手写文案规格 authoring_mode 必须为 "
            f"{FELIS_DIRECT_EX_COPY_AUTHORING_MODE}"
        )

    allowlist = {str(item) for item in allowed_ids if str(item)}
    if not allowlist:
        raise ValueError("Felis EX 手写文案规格缺少运行时 allowlist")
    try:
        declared_count = int(provenance.get("handwritten_id_count"))
    except (TypeError, ValueError):
        declared_count = -1
    if declared_count != len(allowlist):
        raise ValueError(
            "Felis EX 手写文案规格 handwritten_id_count 与 allowlist 不一致"
        )

    raw_specs = payload.get("pigs")
    if not isinstance(raw_specs, dict):
        raise ValueError("Felis EX 手写文案规格 pigs 必须是对象")
    if set(map(str, raw_specs)) != allowlist:
        missing = sorted(allowlist.difference(map(str, raw_specs)))
        extras = sorted(set(map(str, raw_specs)).difference(allowlist))
        detail = []
        if missing:
            detail.append("缺少：" + ", ".join(missing))
        if extras:
            detail.append("多出：" + ", ".join(extras))
        raise ValueError("Felis EX 手写文案规格必须完整覆盖 allowlist；" + "；".join(detail))

    variants = validate_ex_variants(
        _expand_spec_copy(raw_specs),
        allowlist,
        image_extensions=image_extensions,
    )
    for pig_id, levels in variants.items():
        if set(levels) != {1, 2, 3, 4, 5}:
            raise ValueError(f"{pig_id} 必须完整提供 EX1-EX5 文案")
        if any("image" in item for item in levels.values()):
            raise ValueError(f"{pig_id} 的 Felis EX 手写层不得包含 image")
        if len({item["description"] for item in levels.values()}) != 5:
            raise ValueError(f"{pig_id} EX1-EX5 description 必须逐级不同")
        if len({item["analysis"] for item in levels.values()}) != 5:
            raise ValueError(f"{pig_id} EX1-EX5 analysis 必须逐级不同")

    active_ids = {str(item) for item in pig_ids if str(item)}
    return {pig_id: levels for pig_id, levels in variants.items() if pig_id in active_ids}
