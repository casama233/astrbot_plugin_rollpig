from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

try:
    from .ex_variants import validate_handwritten_ex_copy
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import validate_handwritten_ex_copy


BUNDLED_EX_COPY_FILENAME = "bundled_ex_copy.json"
BUNDLED_EX_COPY_GLOB = "bundled_ex_copy*.json"
BUNDLED_EX_COPY_SCOPE = "bundled-lineage-text-only"


def _read_specs(raw_specs: object) -> dict[str, object]:
    if not isinstance(raw_specs, dict) or not raw_specs:
        raise ValueError("Bundled EX 手写文案 pigs 必须是非空对象")

    pigs: dict[str, object] = {}
    for raw_pig_id, raw_spec in raw_specs.items():
        pig_id = str(raw_pig_id or "").strip()
        if not pig_id or not isinstance(raw_spec, dict) or set(raw_spec) != {"levels"}:
            raise ValueError(f"{pig_id} 的 Bundled EX 手写文案规格字段不完整")
        pigs[pig_id] = raw_spec.get("levels")
    return pigs


def _load_specs(path: Path) -> dict[str, object]:
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

    return _read_specs(payload.get("pigs"))


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

    specs: dict[str, object] = {}
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

    variants = validate_handwritten_ex_copy(
        specs,
        allowlist,
        source="Bundled EX",
        image_extensions=image_extensions,
    )

    active_ids = {str(item) for item in pig_ids if str(item)}
    return {pig_id: levels for pig_id, levels in variants.items() if pig_id in active_ids}
