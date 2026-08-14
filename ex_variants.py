from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

EX_VARIANT_SCHEMA_VERSION = 1
MAX_EX_VARIANT_LEVEL = 5
DEFAULT_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
_PIG_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_IMAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}")
_ALLOWED_FIELDS = {"image", "description", "analysis"}


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
            description = str(raw_variant.get("description") or "").strip()
            if description:
                if len(description) > 120:
                    raise ValueError(f"{pig_id} EX Lv.{level} 描述超过 120 字")
                item["description"] = description
            analysis = str(raw_variant.get("analysis") or "").strip()
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
