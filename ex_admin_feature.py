from __future__ import annotations

import asyncio
import base64
import copy
import re
import tempfile
from pathlib import Path

from astrbot.api import logger
from astrbot.api.web import request

try:
    from .ex_variants import resolve_ex_variant, serialize_ex_variants, validate_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import resolve_ex_variant, serialize_ex_variants, validate_ex_variants


class ExAdminMixin:
    """Local EX authoring layer and admin-page API.

    Local EX variants are stored separately from the base pig override layer. A
    local EX definition has the highest presentation priority. When an
    administrator overrides the base pig but has not authored local EX, the
    existing safety rule remains intact: remote/bundled EX is blocked.
    """

    LOCAL_EX_IMAGE_MAX_SIZE = 10 * 1024 * 1024

    def __init__(self, context, config):
        self._local_ex_variants: dict[str, dict[int, dict[str, str]]] = {}
        self.local_ex_variants_path: Path | None = None
        self.local_ex_variant_image_dir: Path | None = None
        super().__init__(context, config)

        self.local_ex_variants_path = self.plugin_data_dir / "local_ex_variants.json"
        self.local_ex_variant_image_dir = self.plugin_data_dir / "local_ex_variants"
        self.local_ex_variant_image_dir.mkdir(parents=True, exist_ok=True)
        self._reload_local_ex_variants()

        context.register_web_api(
            f"/{self.PLUGIN_NAME}/ex/variants",
            self.page_ex_variants,
            ["GET"],
            "查看本地 EX 差分与实际生效预览",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/ex/variants/save",
            self.page_ex_variant_save,
            ["POST"],
            "新增或编辑本地 EX 差分",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/ex/variants/delete",
            self.page_ex_variant_delete,
            ["POST"],
            "删除本地 EX 差分",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/ex/variants/image",
            self.page_ex_variant_image,
            ["POST"],
            "预览本地或实际生效 EX 图片",
        )

    def _reload_catalog_layers(self):
        result = super()._reload_catalog_layers()
        if getattr(self, "local_ex_variants_path", None):
            self._reload_local_ex_variants()
        return result

    def _local_ex_payload(self) -> dict:
        return serialize_ex_variants(self._local_ex_variants)

    def _reload_local_ex_variants(self) -> None:
        path = getattr(self, "local_ex_variants_path", None)
        image_root = getattr(self, "local_ex_variant_image_dir", None)
        if not isinstance(path, Path) or not path.is_file():
            self._local_ex_variants = {}
            return
        try:
            payload = self.load_json(path, {})
            pig_ids = {
                str(item.get("id") or "")
                for item in getattr(self, "pig_list", [])
                if isinstance(item, dict)
            }
            variants = validate_ex_variants(
                payload,
                pig_ids,
                image_extensions=set(getattr(self, "IMAGE_EXTENSIONS", ("png",))),
            )
            if isinstance(image_root, Path):
                for pig_id, levels in variants.items():
                    for level, item in levels.items():
                        image = str(item.get("image") or "")
                        if image and not (image_root / image).is_file():
                            raise ValueError(
                                f"本地 EX 差分缺少图片：{pig_id} EX Lv.{level} -> {image}"
                            )
            self._local_ex_variants = variants
        except Exception as exc:
            self._local_ex_variants = {}
            logger.warning(f"本地 EX 差分资源无效，已暂时跳过：{exc}")

    def _local_ex_levels(self, pig_id: str) -> dict[int, dict[str, str]]:
        levels = self._local_ex_variants.get(str(pig_id), {})
        return levels if isinstance(levels, dict) else {}

    def _decorate_ex_variant(self, pig: dict | None, user_id: str) -> dict | None:
        if not isinstance(pig, dict):
            return pig
        pig_id = str(pig.get("id") or "")
        if not pig_id or pig_id == "eaten":
            return dict(pig)
        local_levels = self._local_ex_levels(pig_id)
        if local_levels:
            ex_level = self._ex_level_for_user(str(user_id), pig_id)
            return resolve_ex_variant(pig, {pig_id: local_levels}, ex_level)
        return super()._decorate_ex_variant(pig, user_id)

    def _ex_variant_image_path(self, pig_id: str, ex_level: int) -> Path | None:
        local_levels = self._local_ex_levels(str(pig_id))
        image_root = getattr(self, "local_ex_variant_image_dir", None)
        if local_levels and isinstance(image_root, Path) and ex_level > 0:
            base = self._find_catalog_pig(str(pig_id))
            if not base:
                return None
            resolved = resolve_ex_variant(
                base, {str(pig_id): local_levels}, int(ex_level)
            )
            image = str((resolved or {}).get("_ex_image") or "")
            if not image:
                return None
            candidate = image_root / image
            return candidate if candidate.is_file() else None
        return super()._ex_variant_image_path(pig_id, ex_level)

    def _effective_ex_preview(self, pig: dict, ex_level: int) -> dict:
        pig_id = str(pig.get("id") or "")
        local_levels = self._local_ex_levels(pig_id)
        if local_levels:
            resolved = resolve_ex_variant(pig, {pig_id: local_levels}, ex_level)
            source = "local"
        elif self._has_local_pig_override(pig_id):
            resolved = dict(pig)
            resolved["_ex_level"] = max(0, int(ex_level))
            source = "local-base-block"
        else:
            resolved = resolve_ex_variant(pig, self._ex_variants, ex_level)
            source = (
                self._ex_variant_source
                if pig_id in getattr(self, "_ex_variants", {})
                else "base"
            )
        return {
            "level": max(0, int(ex_level)),
            "source": source,
            "description": str(resolved.get("description") or ""),
            "analysis": str(resolved.get("analysis") or ""),
            "image": str(resolved.get("_ex_image") or ""),
            "variant_level": int(resolved.get("_ex_variant_level", 0) or 0),
        }

    @staticmethod
    def _effective_image_level(
        levels: dict[int, dict[str, str]], ex_level: int, image_name: str
    ) -> int:
        """Return the first sparse level that introduced the effective image."""
        target = str(image_name or "")
        if not target:
            return 0
        for level in sorted(int(item) for item in levels):
            if level > int(ex_level):
                break
            item = levels.get(level, {})
            if isinstance(item, dict) and str(item.get("image") or "") == target:
                return level
        return 0

    def _effective_ex_image_preview_path(
        self,
        pig_id: str,
        ex_level: int,
        *,
        remove_local_image: bool = False,
    ) -> tuple[Path | None, str, int]:
        """Resolve the image the runtime would show, without mutating EX state.

        ``remove_local_image`` simulates the editor's pending "remove image"
        checkbox. This lets the browser preview the exact inheritance/fallback
        result before the administrator presses Save.
        """
        pig_id = str(pig_id)
        level = max(1, int(ex_level))
        pig = self._find_catalog_pig(pig_id)
        if not isinstance(pig, dict):
            return None, "base", 0

        local_levels = copy.deepcopy(self._local_ex_levels(pig_id))
        if remove_local_image:
            current = dict(local_levels.get(level, {}))
            current.pop("image", None)
            if current:
                local_levels[level] = current
            else:
                local_levels.pop(level, None)

        local_root = getattr(self, "local_ex_variant_image_dir", None)
        if local_levels:
            resolved = resolve_ex_variant(pig, {pig_id: local_levels}, level) or {}
            image = str(resolved.get("_ex_image") or "")
            if image and isinstance(local_root, Path):
                candidate = local_root / image
                if candidate.is_file():
                    return (
                        candidate,
                        "local",
                        self._effective_image_level(local_levels, level, image),
                    )
            # Any local EX definition blocks public/bundled EX. If its sparse
            # image chain resolves to nothing, the real runtime falls back to
            # the pig's base image rather than borrowing a public EX image.
            base = self.find_image_file(pig_id)
            return base, "base", 0

        if self._has_local_pig_override(pig_id):
            return self.find_image_file(pig_id), "base", 0

        upstream_levels = getattr(self, "_ex_variants", {})
        upstream = (
            upstream_levels.get(pig_id, {})
            if isinstance(upstream_levels, dict)
            else {}
        )
        resolved = resolve_ex_variant(pig, upstream_levels, level) or {}
        image = str(resolved.get("_ex_image") or "")
        upstream_root = getattr(self, "_ex_variant_image_root", None)
        if image and isinstance(upstream_root, Path):
            candidate = upstream_root / image
            if candidate.is_file():
                return (
                    candidate,
                    str(getattr(self, "_ex_variant_source", "") or "base"),
                    self._effective_image_level(upstream, level, image)
                    if isinstance(upstream, dict)
                    else 0,
                )

        return self.find_image_file(pig_id), "base", 0

    def _admin_ex_snapshot(self) -> dict:
        items = []
        for pig in getattr(self, "pig_list", []):
            if not isinstance(pig, dict):
                continue
            pig_id = str(pig.get("id") or "")
            if not pig_id or pig_id == "eaten":
                continue
            local_levels = self._local_ex_levels(pig_id)
            items.append(
                {
                    "id": pig_id,
                    "name": str(pig.get("name") or pig_id),
                    "description": str(pig.get("description") or ""),
                    "analysis": str(pig.get("analysis") or ""),
                    "base_overridden": bool(self._has_local_pig_override(pig_id)),
                    "local_levels": {
                        str(level): dict(value)
                        for level, value in sorted(local_levels.items())
                    },
                    "effective": [
                        self._effective_ex_preview(pig, level) for level in range(1, 6)
                    ],
                }
            )
        return {
            "items": items,
            "local_variant_pigs": len(self._local_ex_variants),
            "local_variant_levels": sum(
                len(levels) for levels in self._local_ex_variants.values()
            ),
        }

    def _validated_local_variant_state(
        self, variants: dict[str, dict[int, dict[str, str]]]
    ) -> dict[str, dict[int, dict[str, str]]]:
        pig_ids = {
            str(item.get("id") or "")
            for item in getattr(self, "pig_list", [])
            if isinstance(item, dict)
        }
        return validate_ex_variants(
            serialize_ex_variants(variants),
            pig_ids,
            image_extensions=set(getattr(self, "IMAGE_EXTENSIONS", ("png",))),
        )

    def _write_local_ex_image(self, filename: str, data: bytes) -> None:
        root = self.local_ex_variant_image_dir
        if not isinstance(root, Path):
            raise ValueError("本地 EX 图片目录尚未初始化")
        if len(data) > self.LOCAL_EX_IMAGE_MAX_SIZE:
            raise ValueError("EX 图片超过 10MB")
        root.mkdir(parents=True, exist_ok=True)
        target = root / filename
        with tempfile.NamedTemporaryFile(dir=root, delete=False, suffix=".tmp") as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)

    def _persist_local_ex_state(
        self, variants: dict[str, dict[int, dict[str, str]]]
    ) -> None:
        normalized = self._validated_local_variant_state(variants)
        path = self.local_ex_variants_path
        if not isinstance(path, Path):
            raise ValueError("本地 EX 存储尚未初始化")
        self.save_json(path, serialize_ex_variants(normalized))
        self._local_ex_variants = normalized

    def _parse_ex_target(self, payload: dict) -> tuple[str, int]:
        pig_id = str(payload.get("id") or "").strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
            raise ValueError("小猪 ID 无效")
        if not self._find_catalog_pig(pig_id):
            raise ValueError("小猪不存在")
        try:
            level = int(payload.get("level"))
        except (TypeError, ValueError) as exc:
            raise ValueError("EX 等级无效") from exc
        if level < 1 or level > 5:
            raise ValueError("EX 等级必须在 1-5")
        return pig_id, level

    async def page_ex_variants(self):
        try:
            return self._jsonify({"status": "ok", "data": self._admin_ex_snapshot()})
        except Exception as exc:
            logger.error(f"读取 EX 管理数据失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "读取 EX 管理数据失败"})

    async def page_ex_variant_save(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")
            pig_id, level = self._parse_ex_target(payload)

            image_content = str(payload.get("image") or "")
            normalized_image = None
            if image_content:
                normalized_image = await asyncio.to_thread(
                    self._normalise_uploaded_image, image_content
                )
                if len(normalized_image) > self.LOCAL_EX_IMAGE_MAX_SIZE:
                    raise ValueError("EX 图片超过 10MB")

            with self._data_lock:
                variants = copy.deepcopy(self._local_ex_variants)
                levels = variants.setdefault(pig_id, {})
                item = dict(levels.get(level, {}))

                for field in ("description", "analysis"):
                    if field not in payload:
                        continue
                    value = str(payload.get(field) or "").strip()
                    if value:
                        item[field] = value
                    else:
                        item.pop(field, None)

                filename = f"{pig_id}-ex{level}.png"
                if normalized_image is not None:
                    self._write_local_ex_image(filename, normalized_image)
                    item["image"] = filename
                elif payload.get("remove_image") is True:
                    item.pop("image", None)

                if item:
                    levels[level] = item
                else:
                    levels.pop(level, None)
                if not levels:
                    variants.pop(pig_id, None)

                self._persist_local_ex_state(variants)
                if payload.get("remove_image") is True and normalized_image is None:
                    root = self.local_ex_variant_image_dir
                    if isinstance(root, Path):
                        try:
                            (root / filename).unlink(missing_ok=True)
                        except OSError as exc:
                            logger.warning(f"清理未引用 EX 图片失败：{exc}")

            return self._jsonify(
                {
                    "status": "ok",
                    "message": f"已保存 {pig_id} EX Lv.{level}",
                    "data": self._admin_ex_snapshot(),
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"保存本地 EX 差分失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "保存本地 EX 差分失败"})

    async def page_ex_variant_delete(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")
            pig_id, level = self._parse_ex_target(payload)
            with self._data_lock:
                variants = copy.deepcopy(self._local_ex_variants)
                levels = variants.get(pig_id, {})
                removed = dict(levels.pop(level, {})) if isinstance(levels, dict) else {}
                if not levels:
                    variants.pop(pig_id, None)
                self._persist_local_ex_state(variants)
                image = str(removed.get("image") or "")
                if image and isinstance(self.local_ex_variant_image_dir, Path):
                    try:
                        (self.local_ex_variant_image_dir / image).unlink(missing_ok=True)
                    except OSError as exc:
                        logger.warning(f"清理 EX 图片失败：{exc}")
            return self._jsonify(
                {
                    "status": "ok",
                    "message": f"已重置 {pig_id} EX Lv.{level}",
                    "data": self._admin_ex_snapshot(),
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"删除本地 EX 差分失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "删除本地 EX 差分失败"})

    async def page_ex_variant_image(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")
            pig_id, level = self._parse_ex_target(payload)

            if payload.get("base") is True:
                path = self.find_image_file(pig_id)
                source = "base"
                image_level = 0
            elif payload.get("effective") is True:
                path, source, image_level = self._effective_ex_image_preview_path(
                    pig_id,
                    level,
                    remove_local_image=payload.get("remove_image") is True,
                )
            else:
                item = self._local_ex_levels(pig_id).get(level, {})
                image = str(item.get("image") or "")
                root = self.local_ex_variant_image_dir
                path = root / image if image and isinstance(root, Path) else None
                source = "local"
                image_level = level if path and path.is_file() else 0

            if not path or not path.is_file():
                raise ValueError("这一等级没有可预览的图片")
            raw = path.read_bytes()
            if len(raw) > self.LOCAL_EX_IMAGE_MAX_SIZE:
                raise ValueError("EX 图片超过读取上限")
            ext = path.suffix.lower().lstrip(".")
            mime_types = getattr(self, "IMAGE_MIME_TYPES", {})
            mime_type = (
                str(mime_types.get(ext) or "")
                if isinstance(mime_types, dict)
                else ""
            ) or ("image/png" if ext == "png" else "application/octet-stream")
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "mime_type": mime_type,
                        "base64": base64.b64encode(raw).decode("ascii"),
                        "source": source,
                        "variant_level": int(image_level or 0),
                        "filename": path.name,
                    },
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"读取 EX 图片失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "读取 EX 图片失败"})
