from __future__ import annotations

import base64
import re
import tempfile
from pathlib import Path

try:
    from .animated_images import (
        image_extension_from_bytes,
        image_mime_type_from_bytes,
        is_animated_gif_path,
        normalize_image_bytes,
    )
    from .renderers.animated_pig_card import render_animated_pig_card
except ImportError:  # pragma: no cover - direct module loading compatibility
    from animated_images import (
        image_extension_from_bytes,
        image_mime_type_from_bytes,
        is_animated_gif_path,
        normalize_image_bytes,
    )
    from renderers.animated_pig_card import render_animated_pig_card


class AnimatedImageMixin:
    """Preserve animated GIF pig assets across import, rendering and submission."""

    def _normalise_image_bytes(self, raw: bytes) -> bytes:
        return normalize_image_bytes(raw, (512, 512))

    def _write_custom_image(self, pig_id: str, data: bytes):
        ext = image_extension_from_bytes(data)
        if ext not in {"png", "gif"}:
            raise ValueError("规范化后的小猪图片格式无效")
        target = self.custom_image_dir / f"{pig_id}.{ext}"
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=self.custom_image_dir,
            prefix=f".{pig_id}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)
        for old_ext in self.IMAGE_EXTENSIONS:
            old = self.custom_image_dir / f"{pig_id}.{old_ext}"
            if old != target:
                old.unlink(missing_ok=True)

    def render_pig_image(self, pig_data):
        pig_id = str(pig_data.get("id", "") or "")
        ex_level = int(pig_data.get("_ex_level", 0) or 0)
        avatar_path = self.find_image_file(pig_id, ex_level=ex_level)
        if avatar_path and is_animated_gif_path(avatar_path):
            output = render_animated_pig_card(
                pig_data,
                avatar_path=avatar_path,
                palette=self._image_palette(),
                font_bold=self.font_bold,
                font_regular=self.font_regular,
            )
            if output is not None:
                return output
        return super().render_pig_image(pig_data)

    def _public_source_submission_payload(self, pig_id: str) -> tuple[dict, bytes]:
        """Keep animated GIFs animated while retaining the 512×512 submission norm."""
        with self._data_lock:
            overrides = self._validate_pig_records(
                self._runtime_document(
                    "catalog_overrides", self.local_overrides_path, []
                )
            )
            record = next(
                (dict(item) for item in overrides if item["id"] == pig_id), None
            )
            if not record:
                raise ValueError("只能提交本地新增或本地覆盖的小猪")
            path = self.find_image_file(pig_id)
            if not path or not path.is_file():
                raise ValueError("这只本地小猪没有可提交的图片")
            raw = path.read_bytes()
        if not raw:
            raise ValueError("小猪图片为空")
        if len(raw) > self.PUBLIC_SOURCE_SUBMISSION_MAX_SIZE:
            raise ValueError("公共豬源投稿图片不能超过 10MB")
        normalized = normalize_image_bytes(raw, (512, 512))
        if len(normalized) > self.PUBLIC_SOURCE_SUBMISSION_MAX_SIZE:
            raise ValueError("转换后的公共豬源投稿图片超过 10MB")
        return record, normalized

    async def _public_source_review_image_payload(self, submission_id: str) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", submission_id):
            raise ValueError("投稿 ID 无效")
        url = (
            self.PUBLIC_SOURCE_API_URL
            + f"/admin/submissions/{submission_id}/image"
        )
        async with self._new_http_client(
            follow_redirects=False,
            request_timeout=30,
            extra_headers=self._public_source_headers(admin=True),
        ) as client:
            async with client.stream("GET", url) as response:
                raw = await self._read_response_limited(
                    response, self.PUBLIC_SOURCE_SUBMISSION_MAX_SIZE
                )
                if response.status_code < 200 or response.status_code >= 300:
                    raise ValueError("公共豬源投稿图片读取失败")
        return {
            "mime_type": image_mime_type_from_bytes(raw),
            "base64": base64.b64encode(raw).decode("ascii"),
        }
