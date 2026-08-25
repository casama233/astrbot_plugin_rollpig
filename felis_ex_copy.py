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
_REQUIRED_LEVELS = {1, 2, 3, 4, 5}


def load_felis_direct_ex_copy(
    resource_dir: Path,
    pig_ids: Iterable[str],
    allowed_ids: Iterable[str],
    *,
    image_extensions: set[str] | tuple[str, ...],
) -> dict[str, dict[int, dict[str, str]]]:
    """Load the repository-owned text-only EX layer for Felis direct IDs.

    This layer is intentionally independent from the Felis upstream resource
    protocol.  It may override ``description`` and ``analysis`` only; EX images
    and upstream EX/variant payloads remain outside the direct-read boundary.
    The complete file is validated against the audited 34-ID allowlist before
    being filtered to IDs that are present in the current runtime catalog.
    """

    path = Path(resource_dir) / FELIS_DIRECT_EX_COPY_FILENAME
    if not path.is_file():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Felis EX 原创文案包必须是 JSON 对象")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("Felis EX 原创文案包缺少 provenance")
    if str(provenance.get("scope") or "") != FELIS_DIRECT_EX_COPY_SCOPE:
        raise ValueError("Felis EX 原创文案包 provenance scope 不匹配")
    if provenance.get("upstream_ex_used") is not False:
        raise ValueError("Felis EX 原创文案包必须声明 upstream_ex_used=false")

    allowlist = {str(item) for item in allowed_ids if str(item)}
    if not allowlist:
        raise ValueError("Felis EX 原创文案包缺少运行时 allowlist")

    variants = validate_ex_variants(
        payload,
        allowlist,
        image_extensions=image_extensions,
    )
    if set(variants) != allowlist:
        missing = sorted(allowlist.difference(variants))
        extras = sorted(set(variants).difference(allowlist))
        detail = []
        if missing:
            detail.append("缺少：" + ", ".join(missing))
        if extras:
            detail.append("多出：" + ", ".join(extras))
        raise ValueError("Felis EX 原创文案包必须完整覆盖 allowlist；" + "；".join(detail))

    for pig_id, levels in variants.items():
        if set(levels) != _REQUIRED_LEVELS:
            raise ValueError(f"{pig_id} 必须完整提供 EX1-EX5 文案")
        descriptions: set[str] = set()
        analyses: set[str] = set()
        for level, item in levels.items():
            if "image" in item:
                raise ValueError(f"{pig_id} EX Lv.{level} 不允许携带 image")
            if set(item) != {"description", "analysis"}:
                raise ValueError(
                    f"{pig_id} EX Lv.{level} 只允许完整 description/analysis 文案"
                )
            descriptions.add(item["description"])
            analyses.add(item["analysis"])
        if len(descriptions) != 5 or len(analyses) != 5:
            raise ValueError(f"{pig_id} EX1-EX5 文案必须逐级不同")

    active_ids = {str(item) for item in pig_ids if str(item)}
    return {
        pig_id: levels
        for pig_id, levels in variants.items()
        if pig_id in active_ids
    }
