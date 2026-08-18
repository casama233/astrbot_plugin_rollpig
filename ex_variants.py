from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

try:
    from .display_copy import simplify_display_text
except ImportError:  # pragma: no cover - direct module loading compatibility
    from display_copy import simplify_display_text

EX_VARIANT_SCHEMA_VERSION = 1
MAX_EX_VARIANT_LEVEL = 5
DEFAULT_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
_PIG_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_IMAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}")
_ALLOWED_FIELDS = {"image", "description", "analysis"}

# Every official pig receives a deterministic five-level copy baseline. Explicit
# EX resources remain sparse overrides layered on top, so creator-authored image
# and copy inheritance keeps the existing protocol semantics.
_DESCRIPTION_PHASES = (
    ("开始养熟", "熟客上线", "资深返场", "招牌常驻", "完全体"),
    ("熟悉度 +1", "默契升温", "老熟人模式", "猪圈常驻", "终极熟客"),
    ("初次进阶", "状态渐熟", "资历已深", "招牌阶段", "最终形态"),
    ("返场一回", "返场成习惯", "资深席位", "固定节目", "传奇常驻"),
)
_ANALYSIS_TAILS = (
    (
        "第一次重复遇见后，这份设定开始从偶遇变成你的专属熟悉感。",
        "再次返场后，原本的特点已经不只是设定，而是逐渐成了你在猪圈里的固定印象。",
        "到了第三阶段，大家已经不用看名字也能认出这套气质，熟练度正式进入资深区。",
        "第四次成长把招牌特征彻底坐实，现在只要你出现，猪圈就知道这段固定节目又来了。",
        "来到 EX5 后，这套设定已经被你养成完全体：不是偶尔像，而是大家默认你就该是这个样子。",
    ),
    (
        "第一次返场只是有点眼熟，但属于你的细节已经开始被记住。",
        "第二阶段的默契明显上来了，同样的气质再次出现时，已经有了老熟人的味道。",
        "第三阶段不再需要自我介绍，你的特点已经稳定到足以成为猪圈识别码。",
        "第四阶段进入常驻状态，原本的小特点被重复养成了非常稳定的个人招牌。",
        "EX5 是熟悉度的终点站：经历一次次返场后，你已经把自己的风格活成了猪圈标准答案。",
    ),
    (
        "第一次进阶没有改变本质，只是让原本的特点更容易被一眼认出来。",
        "第二阶段开始有了明显成长感，熟悉不是复制，而是把原本的个性一点点养深。",
        "第三阶段已经进入资深版本，同样的核心设定开始呈现出更稳定、更成熟的状态。",
        "第四阶段几乎成了招牌版本，猪圈里只要提起这项特点，大家就会自然想到你。",
        "最终阶段把成长收束成完整形态：核心没变，但每次返场累积出的资历已经写在气质里。",
    ),
    (
        "第一次返场先留下一个记号：你还是你，只是大家开始记住你的固定节目。",
        "返场渐渐变成习惯后，原本的设定也有了更多熟客感，不再像一次性的偶遇。",
        "第三阶段拿到了资深席位，属于你的梗和气质已经可以稳定接住每一次出场。",
        "第四阶段正式成为固定节目，重复出现不再稀释新鲜感，反而把个人特色越养越明显。",
        "到了 EX5，你已经从常驻升级成传奇常驻——猪圈可能会换新猪，但这套招牌气质不会下线。",
    ),
)


def _compact_copy(value: object, limit: int) -> str:
    text = " ".join(simplify_display_text(value).split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def _growth_style(pig_id: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(pig_id)) % len(
        _DESCRIPTION_PHASES
    )


def generate_official_ex_baseline(
    pigs: Iterable[Mapping[str, Any]],
) -> dict[str, dict[int, dict[str, str]]]:
    """Generate deterministic EX1-EX5 copy for every catalog pig.

    The baseline is deliberately presentation-only and is derived from the
    existing name/description/analysis fields. It never changes IDs, gameplay,
    rarity, pity or collection state. Every level has distinct description and
    analysis copy, so a pig without bespoke EX assets still visibly grows.
    """
    result: dict[str, dict[int, dict[str, str]]] = {}
    for raw in pigs:
        if not isinstance(raw, Mapping):
            continue
        pig_id = str(raw.get("id") or "").strip()
        if not _PIG_ID.fullmatch(pig_id):
            continue
        name = _compact_copy(raw.get("name") or pig_id, 48)
        description = _compact_copy(raw.get("description") or name, 76)
        analysis = _compact_copy(raw.get("analysis") or description, 610)
        style = _growth_style(pig_id)
        phases = _DESCRIPTION_PHASES[style]
        tails = _ANALYSIS_TAILS[style]
        levels: dict[int, dict[str, str]] = {}
        for level in range(1, MAX_EX_VARIANT_LEVEL + 1):
            phase = phases[level - 1]
            levels[level] = {
                "description": _compact_copy(f"{description} · {phase}", 120),
                "analysis": _compact_copy(
                    f"{analysis} {tails[level - 1]}",
                    800,
                ),
            }
        result[pig_id] = levels
    return result


def merge_ex_variant_layers(
    baseline: Mapping[str, Mapping[int, Mapping[str, str]]],
    overrides: Mapping[str, Mapping[int, Mapping[str, str]]],
) -> dict[str, dict[int, dict[str, str]]]:
    """Apply sparse EX overrides over a complete baseline with inheritance.

    Explicit fields keep the historic per-field inheritance contract: once an
    override appears at a level it remains in force for higher levels until the
    same field is overridden again. Baseline copy fills everything else.
    """
    result: dict[str, dict[int, dict[str, str]]] = {
        str(pig_id): {
            int(level): {str(key): str(value) for key, value in item.items()}
            for level, item in levels.items()
        }
        for pig_id, levels in baseline.items()
    }
    for raw_pig_id, raw_levels in overrides.items():
        pig_id = str(raw_pig_id)
        target = result.setdefault(pig_id, {})
        inherited: dict[str, str] = {}
        for level in range(1, MAX_EX_VARIANT_LEVEL + 1):
            raw_item = raw_levels.get(level, {})
            if isinstance(raw_item, Mapping):
                for field in _ALLOWED_FIELDS:
                    value = str(raw_item.get(field) or "").strip()
                    if value:
                        inherited[field] = value
            item = dict(target.get(level, {}))
            item.update(inherited)
            target[level] = item
    return result


def build_effective_ex_variants(
    pigs: Iterable[Mapping[str, Any]],
    overrides: Mapping[str, Mapping[int, Mapping[str, str]]] | None = None,
) -> dict[str, dict[int, dict[str, str]]]:
    """Return the complete official baseline with optional sparse overrides."""
    baseline = generate_official_ex_baseline(pigs)
    return merge_ex_variant_layers(baseline, overrides or {})


def validate_ex_variants(
    payload: Any,
    pig_ids: set[str] | None = None,
    *,
    image_extensions: set[str] | tuple[str, ...] = DEFAULT_IMAGE_EXTENSIONS,
) -> dict[str, dict[int, dict[str, str]]]:
    """Validate EX Lv.1-5 sparse variants and return a normalized mapping.

    Accepted JSON shape::

        {"schema_version": 1, "pigs": {"pig-id": {"2": {...}}}}

    For backwards-friendly local authoring a plain ``{"pig-id": ...}`` mapping is
    also accepted. A variant may override image, description and analysis only;
    ID/name/gameplay fields can never be changed by EX growth.
    """
    if not isinstance(payload, Mapping):
        raise ValueError("pig_ex_variants.json 必须是 JSON 对象")
    if "pigs" in payload or "schema_version" in payload:
        schema = payload.get("schema_version", EX_VARIANT_SCHEMA_VERSION)
        if schema not in (EX_VARIANT_SCHEMA_VERSION, str(EX_VARIANT_SCHEMA_VERSION)):
            raise ValueError("EX 差分协议版本不受支持")
        raw_pigs = payload.get("pigs", {})
    else:
        raw_pigs = payload
    if not isinstance(raw_pigs, Mapping):
        raise ValueError("EX 差分 pigs 必须是对象")

    allowed_ext = {str(item).lower().lstrip(".") for item in image_extensions}
    known = {str(item) for item in pig_ids} if pig_ids is not None else None
    result: dict[str, dict[int, dict[str, str]]] = {}
    for raw_pig_id, raw_levels in raw_pigs.items():
        pig_id = str(raw_pig_id or "").strip()
        if not _PIG_ID.fullmatch(pig_id):
            raise ValueError(f"EX 差分小猪 ID 无效：{pig_id}")
        if known is not None and pig_id not in known:
            raise ValueError(f"EX 差分引用不存在的小猪：{pig_id}")
        if not isinstance(raw_levels, Mapping) or not raw_levels:
            raise ValueError(f"{pig_id} 的 EX 差分必须是非空对象")
        levels: dict[int, dict[str, str]] = {}
        for raw_level, raw_variant in raw_levels.items():
            try:
                level = int(str(raw_level))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{pig_id} 的 EX 等级无效：{raw_level}") from exc
            if not 1 <= level <= MAX_EX_VARIANT_LEVEL:
                raise ValueError(
                    f"{pig_id} 的 EX 等级必须在 1-{MAX_EX_VARIANT_LEVEL}"
                )
            if level in levels:
                raise ValueError(f"{pig_id} 的 EX Lv.{level} 重复")
            if not isinstance(raw_variant, Mapping):
                raise ValueError(f"{pig_id} EX Lv.{level} 必须是对象")
            extras = set(map(str, raw_variant)).difference(_ALLOWED_FIELDS)
            if extras:
                raise ValueError(
                    f"{pig_id} EX Lv.{level} 含不允许字段：{', '.join(sorted(extras))}"
                )
            item: dict[str, str] = {}
            image = str(raw_variant.get("image") or "").strip()
            if image:
                if (
                    not _IMAGE_NAME.fullmatch(image)
                    or "/" in image
                    or "\\" in image
                    or "." not in image
                    or image.rsplit(".", 1)[-1].lower() not in allowed_ext
                ):
                    raise ValueError(f"{pig_id} EX Lv.{level} 图片文件名无效：{image}")
                item["image"] = image
            description = simplify_display_text(raw_variant.get("description")).strip()
            if description:
                if len(description) > 120:
                    raise ValueError(f"{pig_id} EX Lv.{level} 描述超过 120 字")
                item["description"] = description
            analysis = simplify_display_text(raw_variant.get("analysis")).strip()
            if analysis:
                if len(analysis) > 800:
                    raise ValueError(f"{pig_id} EX Lv.{level} 文案超过 800 字")
                item["analysis"] = analysis
            if not item:
                raise ValueError(f"{pig_id} EX Lv.{level} 至少要覆盖一项内容")
            levels[level] = item
        result[pig_id] = dict(sorted(levels.items()))
    return result


def serialize_ex_variants(
    variants: Mapping[str, Mapping[int, Mapping[str, str]]]
) -> dict[str, Any]:
    """Convert normalized variants into the canonical resource JSON shape."""
    return {
        "schema_version": EX_VARIANT_SCHEMA_VERSION,
        "pigs": {
            str(pig_id): {
                str(int(level)): {str(key): str(value) for key, value in item.items()}
                for level, item in sorted(levels.items(), key=lambda pair: int(pair[0]))
            }
            for pig_id, levels in sorted(variants.items())
        },
    }


def resolve_ex_variant(
    pig: Mapping[str, Any] | None,
    variants: Mapping[str, Mapping[int, Mapping[str, str]]],
    ex_level: int,
) -> dict[str, Any] | None:
    """Apply sparse EX overrides up to ``ex_level`` with per-field inheritance."""
    if not isinstance(pig, Mapping):
        return None
    result = dict(pig)
    pig_id = str(result.get("id") or "")
    level = max(0, int(ex_level or 0))
    result["_ex_level"] = level
    levels = variants.get(pig_id, {}) if isinstance(variants, Mapping) else {}
    applied_level = 0
    image_name = ""
    for variant_level in sorted(int(item) for item in levels):
        if variant_level > level:
            break
        item = levels.get(variant_level, {})
        if not isinstance(item, Mapping):
            continue
        for field in ("description", "analysis"):
            value = str(item.get(field) or "").strip()
            if value:
                result[field] = value
        value = str(item.get("image") or "").strip()
        if value:
            image_name = value
        applied_level = max(applied_level, variant_level)
    if applied_level:
        result["_ex_variant_level"] = applied_level
    if image_name:
        result["_ex_image"] = image_name
    return result
