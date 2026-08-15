from __future__ import annotations

import json
from pathlib import Path

from astrbot.api import logger

try:
    from .ex_variants import (
        build_effective_ex_variants,
        resolve_ex_variant,
        validate_ex_variants,
    )
    from .gameplay_events import EVENT_EX_LEVEL_UP
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import (
        build_effective_ex_variants,
        resolve_ex_variant,
        validate_ex_variants,
    )
    from gameplay_events import EVENT_EX_LEVEL_UP


class ExVariantMixin:
    """Render collection-owned pigs with sparse EX Lv.1-5 resource variants.

    The mixin deliberately does not change draw IDs, rarity, pity, roast rules or
    permanent collection data. EX growth remains derived from the existing
    ``count`` field; variants are a presentation layer over that stable state.
    """

    def __init__(self, context, config):
        self._ex_variants: dict[str, dict[int, dict[str, str]]] = {}
        self._ex_variant_image_root: Path | None = None
        self._ex_variant_source = "none"
        super().__init__(context, config)
        self._reload_ex_variants()

    def _reload_catalog_layers(self):
        result = super()._reload_catalog_layers()
        if hasattr(self, "res_dir") and hasattr(self, "resource_active_dir"):
            self._reload_ex_variants()
        return result

    def _read_ex_variant_source(
        self, path: Path, image_root: Path, source: str
    ) -> tuple[dict[str, dict[int, dict[str, str]]], Path, str]:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        pigs = [
            item
            for item in getattr(self, "pig_list", [])
            if isinstance(item, dict)
        ]
        pig_ids = {str(item.get("id") or "") for item in pigs}
        variants = validate_ex_variants(
            payload,
            pig_ids,
            image_extensions=set(getattr(self, "IMAGE_EXTENSIONS", ("png",))),
        )
        for pig_id, levels in variants.items():
            for level, item in levels.items():
                image = str(item.get("image") or "")
                if image and not (image_root / image).is_file():
                    raise ValueError(
                        f"{source} EX 差分缺少图片：{pig_id} EX Lv.{level} -> {image}"
                    )
        # Explicit resources stay sparse authoring layers. The active catalog is
        # completed underneath them so every current/compatibility pig has
        # distinct EX1-EX5 copy even when it has no bespoke asset yet.
        effective = build_effective_ex_variants(pigs, variants)
        return effective, image_root, source

    def _reload_ex_variants(self) -> None:
        """Prefer the active cloud snapshot, falling back to bundled variants."""
        candidates = (
            (
                self.resource_active_dir / "pig_ex_variants.json",
                self.resource_active_dir / "ex_variants",
                "cloud",
            ),
            (
                self.res_dir / "pig_ex_variants.json",
                self.res_dir / "ex_variants",
                "bundled",
            ),
        )
        for path, image_root, source in candidates:
            if not path.is_file():
                continue
            try:
                variants, root, resolved_source = self._read_ex_variant_source(
                    path, image_root, source
                )
            except Exception as exc:
                logger.warning(f"{source} EX 差分资源无效，已跳过：{exc}")
                continue
            self._ex_variants = variants
            self._ex_variant_image_root = root
            self._ex_variant_source = resolved_source
            logger.info(
                f"已加载 {resolved_source} EX 差分：{len(variants)} 只小猪（含官方五级文案基线）"
            )
            return

        pigs = [
            item
            for item in getattr(self, "pig_list", [])
            if isinstance(item, dict)
        ]
        self._ex_variants = build_effective_ex_variants(pigs)
        self._ex_variant_image_root = None
        self._ex_variant_source = "baseline"
        logger.info(f"已加载官方 EX 五级文案基线：{len(self._ex_variants)} 只小猪")

    def _has_local_pig_override(self, pig_id: str) -> bool:
        """Remote/bundled variants never override an administrator's local pig."""
        try:
            overrides = self._runtime_document(
                "catalog_overrides", self.local_overrides_path, []
            )
        except Exception:
            return False
        return any(
            isinstance(item, dict) and str(item.get("id") or "") == str(pig_id)
            for item in (overrides if isinstance(overrides, list) else [])
        )

    def _ex_level_for_user(self, user_id: str, pig_id: str) -> int:
        user = self._get_user_collection(str(user_id))
        pigs = user.get("pigs", {}) if isinstance(user, dict) else {}
        record = pigs.get(str(pig_id), {}) if isinstance(pigs, dict) else {}
        try:
            return max(0, int(record.get("count", 0) or 0) - 1)
        except (TypeError, ValueError, AttributeError):
            return 0

    def _decorate_ex_variant(self, pig: dict | None, user_id: str) -> dict | None:
        if not isinstance(pig, dict):
            return pig
        pig_id = str(pig.get("id") or "")
        if not pig_id or pig_id == "eaten":
            return dict(pig)
        ex_level = self._ex_level_for_user(user_id, pig_id)
        if self._has_local_pig_override(pig_id):
            result = dict(pig)
            result["_ex_level"] = ex_level
            return result
        return resolve_ex_variant(pig, self._ex_variants, ex_level)

    def _ex_variant_image_path(self, pig_id: str, ex_level: int) -> Path | None:
        root = self._ex_variant_image_root
        if not root or ex_level <= 0 or self._has_local_pig_override(pig_id):
            return None
        base = self._find_catalog_pig(str(pig_id))
        if not base:
            return None
        resolved = resolve_ex_variant(base, self._ex_variants, ex_level)
        image = str((resolved or {}).get("_ex_image") or "")
        if not image:
            return None
        path = root / image
        return path if path.is_file() else None

    def _get_daily_pig(self, user_id, date_value):
        return self._decorate_ex_variant(
            super()._get_daily_pig(user_id, date_value), str(user_id)
        )

    def _get_weekly_pig(self, user_id, date_value):
        pig, eaten = super()._get_weekly_pig(user_id, date_value)
        return self._decorate_ex_variant(pig, str(user_id)), eaten

    def _maybe_record_ex_level_event(
        self, event, pig: dict | None, user_id: str, fallback_title: str
    ) -> None:
        """Record today's duplicate growth once, without changing draw state."""
        if fallback_title != "今日小猪" or not isinstance(pig, dict):
            return
        try:
            sender_id = str(self._event_sender_id(event))
        except Exception:
            return
        if sender_id != str(user_id):
            return
        group_id = str(self._event_group_id(event) or "")
        if not group_id:
            return
        pig_id = str(pig.get("id") or "")
        ex_level = self._ex_level_for_user(user_id, pig_id)
        if ex_level <= 0:
            return
        user = self._get_user_collection(str(user_id))
        pigs = user.get("pigs", {}) if isinstance(user, dict) else {}
        record = pigs.get(pig_id, {}) if isinstance(pigs, dict) else {}
        if str(record.get("last_drawn") or "") != self._today().isoformat():
            return
        writer = getattr(self, "_record_gameplay_event", None)
        if not callable(writer):
            return
        writer(
            group_id,
            EVENT_EX_LEVEL_UP,
            actor_id=str(user_id),
            pig_id=pig_id,
            metadata={"from": ex_level - 1, "to": ex_level},
            draw_date=self._today().isoformat(),
            event_id=(
                f"ex:{self._today().isoformat()}:{user_id}:{pig_id}:{ex_level}"
            ),
        )

    async def send_rendered_pig(
        self,
        event,
        pig_data: dict,
        user_id: str,
        intro: str = ". 这是你的今日小猪：",
        fallback_title: str = "今日小猪",
    ):
        # Tomorrow is a preview rather than an owned draw; do not leak collection
        # growth into the future prediction card.
        display = (
            dict(pig_data)
            if fallback_title == "明日小猪预测"
            else self._decorate_ex_variant(pig_data, str(user_id)) or dict(pig_data)
        )
        self._maybe_record_ex_level_event(event, display, str(user_id), fallback_title)
        return await super().send_rendered_pig(
            event,
            display,
            user_id,
            intro=intro,
            fallback_title=fallback_title,
        )

    def render_roast_image(
        self, pig: dict, user_id: str, ai_copy: str | None = None
    ) -> Path:
        display = self._decorate_ex_variant(pig, str(user_id)) or dict(pig)
        return super().render_roast_image(display, user_id, ai_copy)
