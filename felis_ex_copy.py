from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

try:
    from .ex_variants import validate_handwritten_ex_copy
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import validate_handwritten_ex_copy


FELIS_DIRECT_EX_COPY_FILENAME = "felis_direct_ex_copy.json"
FELIS_DIRECT_EX_COPY_SCOPE = "felis-direct-text-only"
FELIS_DIRECT_EX_COPY_SCHEMA_VERSION = 3
FELIS_DIRECT_EX_COPY_AUTHORING_MODE = "explicit-ex1-ex5"
_EXPLICIT_SPEC_FIELDS = {"levels"}


def _read_explicit_specs(raw_specs: dict[str, object]) -> dict[str, object]:
    """Read explicit Felis level specs for the shared handwriting validator.

    Legacy ``name/theme/progress/lesson`` semantic seeds are intentionally no
    longer accepted. Every allowlisted pig must carry five reviewable, explicit
    description/analysis pairs in the repository.
    """

    pigs: dict[str, object] = {}
    for raw_pig_id, raw_spec in raw_specs.items():
        pig_id = str(raw_pig_id or "").strip()
        if not isinstance(raw_spec, dict) or set(raw_spec) != _EXPLICIT_SPEC_FIELDS:
            raise ValueError(f"{pig_id} 的 Felis EX 手写规格字段不完整")
        pigs[pig_id] = raw_spec.get("levels")

    return pigs


def _load_felis_copy_payload(resource_dir: Path, allowed_ids: Iterable[str]) -> dict | None:
    path = Path(resource_dir) / FELIS_DIRECT_EX_COPY_FILENAME
    if not path.is_file():
        return None

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Felis EX 手写文案规格必须是 JSON 对象")
    if payload.get("schema_version") != FELIS_DIRECT_EX_COPY_SCHEMA_VERSION:
        raise ValueError(
            f'Felis EX 手写文案规格的 schema_version 必须为 {FELIS_DIRECT_EX_COPY_SCHEMA_VERSION}'
        )

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError('Felis EX 手写文案规格缺少 provenance 字段')
    if str(provenance.get("scope") or "") != FELIS_DIRECT_EX_COPY_SCOPE:
        raise ValueError('Felis EX 手写文案规格的 provenance scope 不匹配')
    if provenance.get("upstream_ex_used") is not False:
        raise ValueError("Felis EX 手写文案规格必须声明 upstream_ex_used=false")
    if not str(provenance.get("source_basis") or "").strip():
        raise ValueError('Felis EX 手写文案规格必须声明非空的 source_basis')
    if (
        str(provenance.get("authoring_mode") or "")
        != FELIS_DIRECT_EX_COPY_AUTHORING_MODE
    ):
        raise ValueError(
            f'Felis EX 手写文案规格的 authoring_mode 必须为 {FELIS_DIRECT_EX_COPY_AUTHORING_MODE}'
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
            'Felis EX 手写文案规格中的 handwritten_id_count 与 allowlist 数量对不上'
        )

    raw_specs = payload.get("pigs")
    if not isinstance(raw_specs, dict):
        raise ValueError('Felis EX 手写文案规格的 pigs 字段必须是字典对象')
    if set(map(str, raw_specs)) != allowlist:
        missing = sorted(allowlist.difference(map(str, raw_specs)))
        extras = sorted(set(map(str, raw_specs)).difference(allowlist))
        detail = []
        if missing:
            detail.append('漏掉了以下项目：' + ", ".join(missing))
        if extras:
            detail.append('多出了以下项目：' + ", ".join(extras))
        raise ValueError('Felis EX 手写文案规格必须把 allowlist 里的条目全部涵盖：' + "；".join(detail))

    return payload


def load_felis_direct_base_copy(
    resource_dir: Path, allowed_ids: Iterable[str]
) -> dict[str, dict[str, str]]:
    """Read optional project-owned base text without changing upstream cache."""
    allowlist = set(allowed_ids)
    payload = _load_felis_copy_payload(resource_dir, allowlist)
    if payload is None or "base_pigs" not in payload:
        return {}
    base = payload["base_pigs"]
    if not isinstance(base, dict) or set(base) != allowlist:
        raise ValueError('Felis 基础文案必须把 allowlist 里的条目全部涵盖')
    for pig_id, copy in base.items():
        if not isinstance(copy, dict) or set(copy) != {"description", "analysis"}:
            raise ValueError(f'{pig_id} 的 Felis 基础文案只允许包含 description/analysis')
        for field, limit in (("description", 80), ("analysis", 500)):
            value = copy[field]
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f'{pig_id} 的 Felis 基础文案中 {field} 格式有误或无效')
    return base


def load_felis_direct_ex_copy(
    resource_dir: Path,
    pig_ids: Iterable[str],
    allowed_ids: Iterable[str],
    *,
    image_extensions: set[str] | tuple[str, ...],
) -> dict[str, dict[int, dict[str, str]]]:
    """Load explicit, project-owned EX1–EX5 text for the direct allowlist."""
    allowlist = set(allowed_ids)
    payload = _load_felis_copy_payload(resource_dir, allowlist)
    if payload is None:
        return {}
    raw_specs = payload["pigs"]
    variants = validate_handwritten_ex_copy(
        _read_explicit_specs(raw_specs),
        allowlist,
        source="Felis EX",
        image_extensions=image_extensions,
    )

    active_ids = {str(item) for item in pig_ids if str(item)}
    return {pig_id: levels for pig_id, levels in variants.items() if pig_id in active_ids}
