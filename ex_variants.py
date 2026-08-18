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
        "第一次进阶让设定从平面文字长出了层次，同一只猪开始有了属于你的版本。",
        "第二阶段继续把细节堆厚，基础设定还在，但已经明显多了个人痕迹。",
        "第三阶段把原本的气质推到成熟区，重复不再只是重复，而是在持续升级。",
        "第四阶段几乎把这套特征练成职业技能，猪圈里一眼就知道这只已经养得很深。",
        "EX5 把所有成长线收束到完全体：原设定仍看得见，但你已经把它养出了最终版本。",
    ),
    (
        "第一次返场给这只猪盖上了你的印章，从今天起它不再只是图鉴里的一条记录。",
        "第二次返场开始形成固定节目，看到这个名字时，大家已经知道熟悉的剧情要来了。",
        "第三阶段进入资深席位，这只猪和你的绑定感已经远高于普通偶遇。",
        "第四阶段基本坐稳常驻嘉宾，连重复都开始有了节目效果。",
        "第五次成长直接把返场做成传奇常驻：别人是在抽猪，你是在维护自己的招牌角色。",
    ),
)


def _default_ex_copy(pig_id: str, level: int, base_name: str = "") -> dict[str, str]:
    normalized_id = str(pig_id or "").strip().lower()
    safe_level = max(1, min(MAX_EX_VARIANT_LEVEL, int(level)))
    variant = sum(ord(ch) for ch in normalized_id) % len(_DESCRIPTION_PHASES)
    name = str(base_name or "").strip()
    subject = name or "这只猪"
    return {
        "description": _DESCRIPTION_PHASES[variant][safe_level - 1],
        "analysis": f"{subject}{_ANALYSIS_TAILS[variant][safe_level - 1]}",
    }


def build_default_ex_variants(
    pig_ids: Iterable[str], *, base_names: Mapping[str, str] | None = None
) -> dict[str, dict[int, dict[str, str]]]:
    names = {str(key): str(value) for key, value in (base_names or {}).items()}
    result: dict[str, dict[int, dict[str, str]]] = {}
    for pig_id in sorted({str(item or "").strip() for item in pig_ids if str(item or "").strip()}):
        result[pig_id] = {
            level: _default_ex_copy(pig_id, level, names.get(pig_id, ""))
            for level in range(1, MAX_EX_VARIANT_LEVEL + 1)
        }
    return result


def _normalize_text(value: object) -> str:
    text = " ".join(simplify_display_text(value).split()).strip()
    return text[:400]


def _normalize_image(value: object) -> str:
    image = str(value or "").strip()
    if not image:
        return ""
    name = image.replace("\\", "/").split("/")[-1]
    if not _IMAGE_NAME.fullmatch(name):
        return ""
    if "." not in name or name.rsplit(".", 1)[-1].lower() not in DEFAULT_IMAGE_EXTENSIONS:
        return ""
    return name


def validate_ex_variants(
    raw: object,
    valid_pig_ids: Iterable[str],
) -> dict[str, dict[int, dict[str, str]]]:
    allowed = {str(item) for item in valid_pig_ids}
    if not isinstance(raw, Mapping):
        return {}
    pigs = raw.get("pigs") if "pigs" in raw else raw
    if not isinstance(pigs, Mapping):
        return {}
    result: dict[str, dict[int, dict[str, str]]] = {}
    for raw_pig_id, raw_levels in pigs.items():
        pig_id = str(raw_pig_id or "").strip()
        if pig_id not in allowed or not _PIG_ID.fullmatch(pig_id) or not isinstance(raw_levels, Mapping):
            continue
        levels: dict[int, dict[str, str]] = {}
        for raw_level, raw_variant in raw_levels.items():
            try:
                level = int(raw_level)
            except (TypeError, ValueError):
                continue
            if level < 1 or level > MAX_EX_VARIANT_LEVEL or not isinstance(raw_variant, Mapping):
                continue
            variant: dict[str, str] = {}
            image = _normalize_image(raw_variant.get("image"))
            description = simplify_display_text(raw_variant.get("description")).strip()
            analysis = simplify_display_text(raw_variant.get("analysis")).strip()
            if image:
                variant["image"] = image
            if description:
                variant["description"] = _normalize_text(description)
            if analysis:
                variant["analysis"] = _normalize_text(analysis)
            if variant:
                levels[level] = variant
        if levels:
            result[pig_id] = levels
    return result


def resolve_ex_variant(
    variants: Mapping[str, Mapping[int, Mapping[str, str]]],
    pig_id: str,
    level: int,
    *,
    field: str | None = None,
) -> dict[str, str] | str | None:
    pig_levels = variants.get(str(pig_id), {})
    if not pig_levels:
        return None if field else {}
    safe_level = max(0, min(MAX_EX_VARIANT_LEVEL, int(level)))
    if field:
        for current in range(safe_level, 0, -1):
            value = str(pig_levels.get(current, {}).get(field) or "").strip()
            if value:
                return value
        return None
    result: dict[str, str] = {}
    for current in range(1, safe_level + 1):
        variant = pig_levels.get(current, {})
        for key in _ALLOWED_FIELDS:
            value = str(variant.get(key) or "").strip()
            if value:
                result[key] = value
    return result


def serialize_ex_variants(
    variants: Mapping[str, Mapping[int, Mapping[str, str]]]
) -> dict[str, object]:
    pigs: dict[str, dict[str, dict[str, str]]] = {}
    for pig_id in sorted(variants):
        levels: dict[str, dict[str, str]] = {}
        for level in sorted(variants[pig_id]):
            variant = {
                key: str(value)
                for key, value in variants[pig_id][level].items()
                if key in _ALLOWED_FIELDS and str(value or "").strip()
            }
            if variant:
                levels[str(level)] = variant
        if levels:
            pigs[pig_id] = levels
    return {"schema_version": EX_VARIANT_SCHEMA_VERSION, "pigs": pigs}
