from __future__ import annotations

import base64
import copy
import re
from pathlib import Path

from astrbot.api import logger
from astrbot.api.web import request

try:
    from .animated_images import image_mime_type_from_bytes
    from .ex_variants import serialize_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from animated_images import image_mime_type_from_bytes
    from ex_variants import serialize_ex_variants


class ExPublicSourceMixin:
    """Shared EX payload normalization, routes and review-image helpers."""

    # The review service accepts a 16 MiB JSON request. Base64 expands binary
    # content by roughly 4/3, so keep the combined normalized image bytes below
    # 11 MiB to leave room for JSON/copy metadata and encoding overhead.
    PUBLIC_SOURCE_EX_RAW_TOTAL_MAX_SIZE = 11 * 1024 * 1024

    def __init__(self, context, config):
        super().__init__(context, config)
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/ex/submit-public-source",
            self.page_ex_submit_public_source,
            ["POST"],
            '把本地小猪连同 EX 差分一起提交去公共源审核',
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/ex/source/reviews/variant-image",
            self.page_ex_public_source_review_variant_image,
            ["POST"],
            "读取公共源待审核 EX 差分图片",
        )

    def _ex_public_source_payload(self, pig_id: str) -> tuple[dict, bytes, dict, list[dict]]:
        record, raw = self._public_source_submission_payload(pig_id)
        with self._data_lock:
            levels = copy.deepcopy(
                getattr(self, "_local_ex_variants", {}).get(str(pig_id), {})
            )
        if not levels:
            raise ValueError('这只小猪还没本地 EX 差分，先去 EX 成长管理里建一个吧')

        canonical = serialize_ex_variants({str(pig_id): levels})
        image_root = getattr(self, "local_ex_variant_image_dir", None)
        variant_images: list[dict] = []
        referenced = []
        total_raw_size = len(raw)
        for level, item in sorted(levels.items()):
            image = str(item.get("image") or "")
            if not image:
                continue
            expected = {
                f"{pig_id}-ex{int(level)}.png",
                f"{pig_id}-ex{int(level)}.gif",
            }
            if image not in expected:
                raise ValueError(
                    f"EX Lv.{level} 图片文件名不是标准投稿格式：应为 PNG 或 GIF canonical 文件名"
                )
            if not isinstance(image_root, Path):
                raise ValueError('本地 EX 图片文件夹还没初始化好')
            path = image_root / image
            if not path.is_file():
                raise ValueError(f'本地找不到 EX Lv.{level} 对应的图片')
            data = path.read_bytes()
            if not data or len(data) > self.PUBLIC_SOURCE_SUBMISSION_MAX_SIZE:
                raise ValueError(f'EX Lv.{level} 图片是空的，或者超过 10MB 了')
            total_raw_size += len(data)
            if total_raw_size > self.PUBLIC_SOURCE_EX_RAW_TOTAL_MAX_SIZE:
                raise ValueError(
                    '基础图和 EX 图加起来太胖啦，压小点再投吧（总上限约 11 MiB）'
                )
            referenced.append(image)
            variant_images.append(
                {
                    "filename": image,
                    "content": base64.b64encode(data).decode("ascii"),
                }
            )
        if len(referenced) > 5:
            raise ValueError('每次投稿最多只能塞 5 张 EX 差分图')
        return record, raw, canonical, variant_images

    async def _public_source_review_variant_image_payload(
        self, submission_id: str, filename: str
    ) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", submission_id):
            raise ValueError('这份投稿的 ID 没对上号')
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}-ex[1-5]\.(?:png|gif)", filename):
            raise ValueError('EX 图片的名字格式不对')
        url = (
            self.PUBLIC_SOURCE_API_URL
            + f"/admin/submissions/{submission_id}/variant-image/{filename}"
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
                    raise ValueError('读取公共猪源的 EX 投稿图片失败了')
        return {
            "mime_type": image_mime_type_from_bytes(raw),
            "base64": base64.b64encode(raw).decode("ascii"),
        }

    async def page_ex_public_source_review_variant_image(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")
            result = await self._public_source_review_variant_image_payload(
                str(payload.get("submission_id") or "").strip(),
                str(payload.get("filename") or "").strip(),
            )
            return self._jsonify({"status": "ok", "data": result})
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"读取公共猪源 EX 投稿图片失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": '读取 EX 投稿图片失败了'})
