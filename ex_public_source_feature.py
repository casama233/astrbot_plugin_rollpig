from __future__ import annotations

import asyncio
import base64
import copy
import re
from pathlib import Path

from astrbot.api import logger
from astrbot.api.web import request

try:
    from .ex_variants import serialize_ex_variants
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_variants import serialize_ex_variants


class ExPublicSourceMixin:
    """Bridge local EX authoring to the public-source review envelope v2."""

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
            "将本地小猪与 EX 差分一起提交到公共源审核",
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
            raise ValueError("这只小猪还没有本地 EX 差分；请先在 EX 成长管理中建立差分")

        canonical = serialize_ex_variants({str(pig_id): levels})
        image_root = getattr(self, "local_ex_variant_image_dir", None)
        variant_images: list[dict] = []
        referenced = []
        total_raw_size = len(raw)
        for level, item in sorted(levels.items()):
            image = str(item.get("image") or "")
            if not image:
                continue
            expected = f"{pig_id}-ex{int(level)}.png"
            if image != expected:
                raise ValueError(
                    f"EX Lv.{level} 图片文件名不是标准投稿格式：应为 {expected}"
                )
            if not isinstance(image_root, Path):
                raise ValueError("本地 EX 图片目录尚未初始化")
            path = image_root / image
            if not path.is_file():
                raise ValueError(f"EX Lv.{level} 引用的本地图片不存在")
            data = path.read_bytes()
            if not data or len(data) > self.PUBLIC_SOURCE_SUBMISSION_MAX_SIZE:
                raise ValueError(f"EX Lv.{level} 图片为空或超过 10MB")
            total_raw_size += len(data)
            if total_raw_size > self.PUBLIC_SOURCE_EX_RAW_TOTAL_MAX_SIZE:
                raise ValueError(
                    "基础图片与 EX 图片合计过大；请压缩图片后再投稿（总上限约 11 MiB）"
                )
            referenced.append(image)
            variant_images.append(
                {
                    "filename": image,
                    "content": base64.b64encode(data).decode("ascii"),
                }
            )
        if len(referenced) > 5:
            raise ValueError("每次投稿最多包含 5 张 EX 差分图片")
        return record, raw, canonical, variant_images

    async def _submit_local_ex_to_public_source(self, pig_id: str) -> dict:
        record, raw, ex_variants, variant_images = await asyncio.to_thread(
            self._ex_public_source_payload, pig_id
        )
        payload = {
            "submission_version": 2,
            "record": {
                key: str(record.get(key) or "")
                for key in ("id", "name", "description", "analysis")
            },
            "image": base64.b64encode(raw).decode("ascii"),
            "ex_variants": ex_variants,
            "variant_images": variant_images,
        }
        result = await self._request_public_source_json(
            "POST", "/submissions", payload=payload
        )
        if not isinstance(result, dict):
            raise ValueError("公共豬源返回了无效投稿结果")
        return result

    async def page_ex_submit_public_source(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not isinstance(payload, dict) or payload.get("confirm") is not True:
                raise ValueError(
                    "提交前必须明确确认会公开发送完整小猪资料、基础图片、EX 差分与 EX 图片"
                )
            pig_id = str(payload.get("id") or "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError("小猪 ID 无效")
            result = await self._submit_local_ex_to_public_source(pig_id)
            logger.info(f"管理页已提交小猪及 EX 差分到 AstrBot 公共豬源审核：{pig_id}")
            return self._jsonify(
                {"status": "ok", "message": result.get("message", "已提交"), "data": result}
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"提交 EX 差分到公共豬源失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "提交公共豬源失败，请稍后重试"})

    async def _public_source_review_variant_image_payload(
        self, submission_id: str, filename: str
    ) -> dict:
        if not re.fullmatch(r"[0-9a-f]{32}", submission_id):
            raise ValueError("投稿 ID 无效")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}-ex[1-5]\.png", filename):
            raise ValueError("EX 图片文件名无效")
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
                    raise ValueError("公共豬源 EX 投稿图片读取失败")
        return {
            "mime_type": "image/png",
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
            logger.error(f"读取公共豬源 EX 投稿图片失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "读取 EX 投稿图片失败"})
