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
_LEGACY_SPEC_FIELDS = {"name", "theme", "progress", "lesson"}
_EXPLICIT_SPEC_FIELDS = {"levels"}
_REQUIRED_LEVELS = {"1", "2", "3", "4", "5"}
_REQUIRED_COPY_FIELDS = {"description", "analysis"}

_DESCRIPTION_PATTERNS = (
    "{name} EX1：第一次把{theme}从本能反应变成有意识的练习",
    "{name} EX2：{progress}，开始形成自己的节奏",
    "{name} EX3：{theme}进入稳定期，遇到状况也不再立刻乱套",
    "{name} EX4：这套{theme}已经成了招牌，别人一看就知道你熟了",
    "{name} EX5：{theme}完全体——{lesson}",
)
_ANALYSIS_PATTERNS = (
    "第一次进阶没有让你突然变成另一只猪。你只是开始认真观察自己的{theme}：什么时候有用，什么时候会添乱。最明显的变化，是你愿意先停半拍再行动。",
    "第二阶段的你已经会复盘。你把旧习惯拆开来看，试着{progress}。少一点条件反射，多一点选择，结果反而更稳，也更像真正属于你的成长。",
    "到了 EX3，熟练度不再靠声势证明。即使现场突然变化，你也能围绕{theme}重新判断，而不是照着旧套路硬冲。稳定感来自知道自己为什么这么做。",
    "EX4 以后，这套{theme}成了你的个人招牌，但你没有把招牌变成固定动作。会根据别人和环境调整，才让同一套本事每次出现都还有分寸。",
    "EX5 把成长收在一句话里：{lesson}。你保留了最初的特点，却不再被它牵着走；现在是你在使用这份特质，而不是这份特质替你做决定。",
)


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
    pigs: dict[str, dict[str, dict[str, str]]] = {}
    for raw_pig_id, raw_spec in raw_specs.items():
        pig_id = str(raw_pig_id or "").strip()
        if not isinstance(raw_spec, dict):
            raise ValueError(f"{pig_id} 的 Felis EX 原创规格字段不完整")

        fields = set(raw_spec)
        if fields == _EXPLICIT_SPEC_FIELDS:
            pigs[pig_id] = _normalize_explicit_levels(pig_id, raw_spec.get("levels"))
            continue

        if fields != _LEGACY_SPEC_FIELDS:
            raise ValueError(f"{pig_id} 的 Felis EX 原创规格字段不完整")

        values = {
            key: str(raw_spec.get(key) or "").strip()
            for key in _LEGACY_SPEC_FIELDS
        }
        if not all(values.values()):
            raise ValueError(f"{pig_id} 的 Felis EX 原创规格存在空字段")

        levels: dict[str, dict[str, str]] = {}
        for index in range(5):
            levels[str(index + 1)] = {
                "description": _DESCRIPTION_PATTERNS[index].format(**values),
                "analysis": _ANALYSIS_PATTERNS[index].format(**values),
            }
        pigs[pig_id] = levels

    return {"schema_version": 1, "pigs": pigs}


def load_felis_direct_ex_copy(
    resource_dir: Path,
    pig_ids: Iterable[str],
    allowed_ids: Iterable[str],
    *,
    image_extensions: set[str] | tuple[str, ...],
) -> dict[str, dict[int, dict[str, str]]]:
    """Load repository-owned EX1-EX5 text for the Felis direct allowlist.

    The authoring file supports both the earlier four-field semantic seed format
    and explicit per-level handwritten copy. This lets the project migrate pigs
    to fully authored EX1-EX5 prose in reviewable batches without ever importing
    Felis upstream EX text or EX images.
    """

    path = Path(resource_dir) / FELIS_DIRECT_EX_COPY_FILENAME
    if not path.is_file():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Felis EX 原创文案规格必须是 JSON 对象")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("Felis EX 原创文案规格缺少 provenance")
    if str(provenance.get("scope") or "") != FELIS_DIRECT_EX_COPY_SCOPE:
        raise ValueError("Felis EX 原创文案规格 provenance scope 不匹配")
    if provenance.get("upstream_ex_used") is not False:
        raise ValueError("Felis EX 原创文案规格必须声明 upstream_ex_used=false")

    allowlist = {str(item) for item in allowed_ids if str(item)}
    if not allowlist:
        raise ValueError("Felis EX 原创文案规格缺少运行时 allowlist")
    raw_specs = payload.get("pigs")
    if not isinstance(raw_specs, dict):
        raise ValueError("Felis EX 原创文案规格 pigs 必须是对象")
    if set(map(str, raw_specs)) != allowlist:
        missing = sorted(allowlist.difference(map(str, raw_specs)))
        extras = sorted(set(map(str, raw_specs)).difference(allowlist))
        detail = []
        if missing:
            detail.append("缺少：" + ", ".join(missing))
        if extras:
            detail.append("多出：" + ", ".join(extras))
        raise ValueError("Felis EX 原创文案规格必须完整覆盖 allowlist；" + "；".join(detail))

    variants = validate_ex_variants(
        _expand_spec_copy(raw_specs),
        allowlist,
        image_extensions=image_extensions,
    )
    for pig_id, levels in variants.items():
        if set(levels) != {1, 2, 3, 4, 5}:
            raise ValueError(f"{pig_id} 必须完整提供 EX1-EX5 文案")
        if any("image" in item for item in levels.values()):
            raise ValueError(f"{pig_id} 的 Felis EX 原创层不得包含 image")
        if len({item["description"] for item in levels.values()}) != 5:
            raise ValueError(f"{pig_id} EX1-EX5 description 必须逐级不同")
        if len({item["analysis"] for item in levels.values()}) != 5:
            raise ValueError(f"{pig_id} EX1-EX5 analysis 必须逐级不同")

    active_ids = {str(item) for item in pig_ids if str(item)}
    return {pig_id: levels for pig_id, levels in variants.items() if pig_id in active_ids}
