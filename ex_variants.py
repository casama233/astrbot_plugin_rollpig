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
    ('混个脸熟', '熟客驾到', '老友返场', '猪圈台柱', '究极形态'),
    ('默契值 +1', '羁绊加深', '熟门熟路', '常驻嘉宾', '满级老铁'),
    ('初露锋芒', '渐入佳境', '火候十足', '招牌亮相', '终极觉醒'),
    ('二度碰面', '熟面孔了', '元老席位', '每日必看', '传说常客'),
)
_ANALYSIS_TAILS = (
    (
        '头一回在群里重逢，这只小猪总算从擦肩而过的路人变成你的熟面孔啦。',
        '又来报到了，这股子味儿算是彻底焊死在猪圈，成了你的专属名片。',
        '迈入三阶段，大伙闭着眼都能闻出这股派头，正式晋升猪圈老江湖。',
        '四度蜕变把招牌立得稳稳当当，如今你一探头，全猪圈都知道好戏要开锣了。',
        '解锁 EX5 后，这人设算是彻底铁板钉钉：不是偶尔神似，大伙早认定你打娘胎里就长这样。',
    ),
    (
        '头一回返场看着还有些生分，不过你的招牌小动作已经悄悄挂上号了。',
        '二刷这股劲儿，默契瞬间拉满，不用吭声就已经是老熟人的排场了。',
        '三阶段省去自我介绍，你往那一戳，本身就是猪圈的活体二维码。',
        '四阶段正式转正成常驻嘉宾，当年那点小性子，硬生生盘成了金字招牌。',
        'EX5 是熟络度的终点站：几轮返场摸爬滚打下来，你活成了猪圈的标准答案。',
    ),
    (
        '初次进阶没改人设，只是把原本的亮点擦得锃亮，叫人一眼就能认出。',
        '二阶段明显舒展开了，熟稔绝非复制粘贴，而是把骨子里的个性越养越醇厚。',
        '三阶段踏入资深老炮儿地界，核心设定稳如磐石，连背影都透着老练。',
        '四阶段基本成了个人图腾，猪圈里但凡提起这茬，大伙准第一个扭头望向你。',
        '终极阶段直接修成完全体：底色丝毫未变，可每回返场攒下的资历全写在了脸上。',
    ),
    (
        '首轮返场先打个样儿：你还是原来的你，只是大伙开始记住你的固定戏码了。',
        '返场成了家常便饭后，老设定自带熟客滤镜，再也不是当初的一锤子买卖。',
        '三阶段稳坐资深席位，你的独门梗和架势，已经能稳稳兜住每一次亮相。',
        '四阶段彻底成了保留曲目，刷屏毫不腻歪，反倒把个人特色越盘越润、越盘越亮。',
        '到了 EX5，你直接从常驻封神为传说——猪圈流水的猪，铁打的你。',
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
        raise ValueError('pig_ex_variants.json 的根节点必须为 JSON 对象')
    if "pigs" in payload or "schema_version" in payload:
        schema = payload.get("schema_version", EX_VARIANT_SCHEMA_VERSION)
        if schema not in (EX_VARIANT_SCHEMA_VERSION, str(EX_VARIANT_SCHEMA_VERSION)):
            raise ValueError('当前 EX 差分协议版本不受支持')
        raw_pigs = payload.get("pigs", {})
    else:
        raw_pigs = payload
    if not isinstance(raw_pigs, Mapping):
        raise ValueError('EX 差分配置中的 pigs 字段必须是对象')

    allowed_ext = {str(item).lower().lstrip(".") for item in image_extensions}
    known = {str(item) for item in pig_ids} if pig_ids is not None else None
    result: dict[str, dict[int, dict[str, str]]] = {}
    for raw_pig_id, raw_levels in raw_pigs.items():
        pig_id = str(raw_pig_id or "").strip()
        if not _PIG_ID.fullmatch(pig_id):
            raise ValueError(f'EX 差分中存在无效的小猪 ID：{pig_id}')
        if known is not None and pig_id not in known:
            raise ValueError(f'EX 差分引用了不存在的小猪：{pig_id}')
        if not isinstance(raw_levels, Mapping) or not raw_levels:
            raise ValueError(f'{pig_id} 的 EX 差分配置必须为非空对象')
        levels: dict[int, dict[str, str]] = {}
        for raw_level, raw_variant in raw_levels.items():
            try:
                level = int(str(raw_level))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{pig_id} 的 EX 等级无效：{raw_level}") from exc
            if not 1 <= level <= MAX_EX_VARIANT_LEVEL:
                raise ValueError(
                    f'{pig_id} 的 EX 等级须落在 1 至 {MAX_EX_VARIANT_LEVEL} 范围内'
                )
            if level in levels:
                raise ValueError(f'{pig_id} 的 EX Lv.{level} 配置出现重复')
            if not isinstance(raw_variant, Mapping):
                raise ValueError(f'{pig_id} 的 EX Lv.{level} 必须是对象')
            extras = set(map(str, raw_variant)).difference(_ALLOWED_FIELDS)
            if extras:
                raise ValueError(
                    f"{pig_id} EX Lv.{level} 包含未允许的字段：{', '.join(sorted(extras))}"
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
                    raise ValueError(f'{pig_id} EX Lv.{level} 的图片文件名无效：{image}')
                item["image"] = image
            description = simplify_display_text(raw_variant.get("description")).strip()
            if description:
                if len(description) > 120:
                    raise ValueError(f'{pig_id} EX Lv.{level} 的描述超出 120 字上限')
                item["description"] = description
            analysis = simplify_display_text(raw_variant.get("analysis")).strip()
            if analysis:
                if len(analysis) > 800:
                    raise ValueError(f'{pig_id} EX Lv.{level} 的文案超出 800 字上限')
                item["analysis"] = analysis
            if not item:
                raise ValueError(f'{pig_id} EX Lv.{level} 至少需要覆写一项内容')
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
            raise ValueError(f'{pig_id} 的 {source} 手写文案必须完整提供 EX1 到 EX5')
        levels: dict[str, dict[str, str]] = {}
        for raw_level, raw_item in raw_levels.items():
            level = str(raw_level)
            if not isinstance(raw_item, dict) or set(raw_item) != required_fields:
                raise ValueError(f"{pig_id} EX{level} 的 {source} 手写文案字段不完整")
            item = {field: str(raw_item.get(field) or "").strip() for field in required_fields}
            if not all(item.values()):
                raise ValueError(f'{pig_id} EX{level} 的 {source} 手写文案包含空字段')
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
                raise ValueError(f'{pig_id} EX1 到 EX5 的 {field} 必须逐级区分，不可雷同')
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
