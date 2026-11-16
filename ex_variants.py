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
        '头一回重逢，这副面孔总算从路人甲混成了你的熟人。',
        '又一次返场，这股劲儿已经焊死成了你在猪圈里的独家印象。',
        '第三阶段一到，大伙闭着眼都能认出这股气质，正式迈入老江湖行列。',
        '第四次蜕变把招牌彻底立住，现在你一露面，全猪圈都知道好戏又要开场了。',
        '解锁 EX5 后，这套人设算是彻底焊死了：不是偶尔像，大伙早默认你本尊就长这样。',
    ),
    (
        '头一回返场看着还有点面生，但你的专属小动作已经悄悄挂上号了。',
        '二刷这气质，默契直接拉满，不用开口就已经是老熟人排面了。',
        '三阶段免去自我介绍，你的路数往那一站，就是猪圈活体识别码。',
        '四阶段正式转正成常驻，当年那点小脾气，硬是盘成了金字招牌。',
        'EX5 是熟悉度终点站：多轮返场下来，你已经把自己活成了猪圈标准答案。',
    ),
    (
        '头一回进阶没换人设，只是把原本的特点擦得更亮，让人一眼就认出来。',
        '二阶段明显长开了，熟悉可不是复制粘贴，是把原本的个性越养越醇。',
        '三阶段迈入资深老炮区，核心设定稳如泰山，连气质都透着老练。',
        '四阶段基本成了个人招牌，猪圈里一提这茬，大伙第一个就扭头看你。',
        '最终阶段直接修成完全体：底色没变，但每次返场攒下的资历全写在脸上。',
    ),
    (
        '头回返场先打个样：你还是那个你，只是大伙开始记住你的固定节目了。',
        '返场成了日常后，老设定自带熟客滤镜，再也不是当初的一锤子偶遇。',
        '三阶段稳坐资深席位，你的专属梗和派头，已经能稳稳接住每次出场。',
        '四阶段彻底成了保留节目，刷屏不腻味，反倒把个人特色越盘越包浆。',
        '到了 EX5，你直接从常驻封神成传说——猪圈流水的猪，铁打的你。',
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


def validate_handwritten_ex_copy(
    raw_pigs: Mapping[str, object],
    pig_ids: set[str],
    *,
    source: str,
    image_extensions: set[str] | tuple[str, ...],
) -> dict[str, dict[int, dict[str, str]]]:
    """Validate full text-only authoring after the caller checks source rights.

    Unlike sparse creator variants, handwritten packs require both text fields
    at all five levels. Compare uniqueness after display-text normalization.
    """
    required_levels = {str(level) for level in range(1, MAX_EX_VARIANT_LEVEL + 1)}
    required_fields = {"description", "analysis"}
    pigs: dict[str, dict[str, dict[str, str]]] = {}
    for pig_id, raw_levels in raw_pigs.items():
        if not isinstance(raw_levels, dict) or set(map(str, raw_levels)) != required_levels:
            raise ValueError(f"{pig_id} 的 {source} 手写文案必须完整提供 EX1-EX5")
        levels: dict[str, dict[str, str]] = {}
        for raw_level, raw_item in raw_levels.items():
            level = str(raw_level)
            if not isinstance(raw_item, dict) or set(raw_item) != required_fields:
                raise ValueError(f"{pig_id} EX{level} 的 {source} 手写文案字段不完整")
            item = {field: str(raw_item.get(field) or "").strip() for field in required_fields}
            if not all(item.values()):
                raise ValueError(f"{pig_id} EX{level} 的 {source} 手写文案存在空字段")
            levels[level] = item
        pigs[pig_id] = levels

    variants = validate_ex_variants(
        {"schema_version": EX_VARIANT_SCHEMA_VERSION, "pigs": pigs},
        pig_ids,
        image_extensions=image_extensions,
    )
    for pig_id, levels in variants.items():
        for field in ("description", "analysis"):
            if len({item[field] for item in levels.values()}) != MAX_EX_VARIANT_LEVEL:
                raise ValueError(f"{pig_id} EX1-EX5 {field} 必须逐级不同")
    return variants


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
