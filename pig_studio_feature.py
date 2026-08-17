from __future__ import annotations

import asyncio
import base64
import io
import json
import re
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from astrbot.api import logger
from astrbot.api.web import request
from PIL import Image as PILImage
from PIL import ImageOps


class PigStudioMixin:
    """AI-assisted pig authoring APIs for the authenticated Plugin Page.

    Design goals:
    - text planning reuses AstrBot's active provider;
    - image-provider secrets stay server-side and are never returned to the page;
    - generated full-resolution images are staged in plugin data and represented
      in the browser by opaque draft ids plus small previews;
    - final imports reuse the existing local catalog override persistence boundary.

    The product concept is inspired by AutoPig-Studio (MIT, xiaoting qu, 2026),
    but this implementation is native to RollPig's Plugin Page/storage model.
    """

    PIG_STUDIO_DRAFT_TTL_SECONDS = 6 * 60 * 60
    PIG_STUDIO_MAX_RESPONSE_BYTES = 24 * 1024 * 1024
    PIG_STUDIO_PREVIEW_SIZE = 256

    def __init__(self, context, config):
        super().__init__(context, config)
        cfg = config if hasattr(config, "get") else {}
        self.enable_pig_studio = self._studio_bool(cfg.get("enable_pig_studio", True), True)
        self.pig_studio_image_base_url = str(
            cfg.get("pig_studio_image_base_url", "") or ""
        ).strip()
        self.pig_studio_image_api_key = str(
            cfg.get("pig_studio_image_api_key", "") or ""
        ).strip()
        self.pig_studio_image_model = str(
            cfg.get("pig_studio_image_model", "gemini-3.1-flash-image-preview")
            or "gemini-3.1-flash-image-preview"
        ).strip()[:128]
        try:
            max_batch = int(cfg.get("pig_studio_max_batch", 4))
        except (TypeError, ValueError):
            max_batch = 4
        self.pig_studio_max_batch = min(8, max(1, max_batch))
        self.pig_studio_draft_dir = self.plugin_data_dir / "pig_studio_drafts"
        self.pig_studio_draft_dir.mkdir(parents=True, exist_ok=True)
        self._studio_cleanup_drafts()

        context.register_web_api(
            f"/{self.PLUGIN_NAME}/studio/status",
            self.page_studio_status,
            ["GET"],
            "查看 AI 小猪工坊能力状态",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/studio/plan",
            self.page_studio_plan,
            ["POST"],
            "AI 批量策划小猪主题",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/studio/render",
            self.page_studio_render,
            ["POST"],
            "按图鉴参考图生成小猪草稿",
        )
        context.register_web_api(
            f"/{self.PLUGIN_NAME}/studio/import",
            self.page_studio_import,
            ["POST"],
            "把 AI 小猪草稿安全导入本地图鉴层",
        )

    @staticmethod
    def _studio_bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return default

    def _studio_image_configured(self) -> bool:
        return bool(
            self.enable_pig_studio
            and self.pig_studio_image_base_url
            and self.pig_studio_image_api_key
            and self.pig_studio_image_model
        )

    def _studio_safe_base_url(self) -> str:
        value = str(self.pig_studio_image_base_url or "").strip().rstrip("/")
        if not value:
            raise ValueError("尚未配置 AI 小猪工坊生图 Base URL")
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        loopback = host in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError("生图 Base URL 必须使用 HTTPS；仅本机回环地址允许 HTTP")
        if not host or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("生图 Base URL 格式无效")
        return value

    def _studio_cleanup_drafts(self) -> None:
        root = getattr(self, "pig_studio_draft_dir", None)
        if not isinstance(root, Path) or not root.exists():
            return
        cutoff = time.time() - self.PIG_STUDIO_DRAFT_TTL_SECONDS
        for path in root.iterdir():
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    @staticmethod
    def _studio_slug(value: Any) -> str:
        text = str(value or "").strip().lower().replace(" ", "-")
        text = re.sub(r"[^a-z0-9_-]+", "-", text)
        text = re.sub(r"[-_]{2,}", "-", text).strip("-_")
        return text[:48]

    def _studio_unique_slug(self, candidate: str, reserved: set[str]) -> str:
        base = self._studio_slug(candidate) or "studio-pig"
        value = base
        index = 2
        while value in reserved or self._find_catalog_pig(value):
            suffix = f"-{index}"
            value = f"{base[: max(1, 48 - len(suffix))]}{suffix}"
            index += 1
        reserved.add(value)
        return value

    @staticmethod
    def _studio_json_array(text: str) -> list[dict[str, Any]]:
        cleaned = str(text or "").strip()
        cleaned = re.sub(
            r"^\s*```(?:json)?\s*|\s*```\s*$", "", cleaned, flags=re.IGNORECASE
        )
        match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("AI 返回内容不是有效 JSON 数组")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError("AI 返回内容不是有效 JSON 数组") from exc
        if not isinstance(payload, list):
            raise ValueError("AI 返回内容格式无效")
        return [item for item in payload if isinstance(item, dict)]

    def _studio_existing_reference(self) -> str:
        examples = []
        for item in getattr(self, "pig_list", []):
            if not isinstance(item, dict):
                continue
            pig_id = str(item.get("id") or "")
            if not pig_id or pig_id == "eaten":
                continue
            examples.append(
                f"{pig_id}｜{str(item.get('name') or pig_id)}｜{str(item.get('description') or '')}"
            )
            if len(examples) >= 80:
                break
        return "\n".join(examples)

    async def _studio_generate_plan(
        self, count: int, style_vibe: str, guidance: str
    ) -> list[dict[str, str]]:
        provider = self.context.get_using_provider()
        if provider is None:
            raise RuntimeError("当前没有可用的 AstrBot AI 提供商，请先配置模型")
        reference = self._studio_existing_reference()
        prompt = (
            "你是 RollPig 图鉴的角色策划。请只返回 JSON 数组，不要 Markdown。\n"
            f"设计 {count} 只新的小猪。风格偏好：{style_vibe or '趣味职业、生活与轻幻想'}。\n"
            f"补充要求：{guidance or '配饰简洁、主题一眼可识别、不要复刻已有角色'}。\n"
            "每项必须包含：name（中文名称，2-12字）、slug（英文小写短 ID）、"
            "features（1-2 个极简视觉特征）、description（10-28字外观描述）、"
            "analysis（35-90字带一点猪味的图鉴文案）。\n"
            "禁止输出现实人物姓名、品牌 Logo、色情、仇恨、血腥或违法主题。\n"
            "已有图鉴，务必避免同题或近似：\n"
            f"{reference}"
        )
        response = await asyncio.wait_for(
            provider.text_chat(
                prompt=prompt,
                session_id=None,
                contexts=[],
                image_urls=[],
                func_tool=None,
                system_prompt="",
            ),
            timeout=self.ai_generation_timeout,
        )
        raw = self._studio_json_array(
            str(getattr(response, "completion_text", "") or "")
        )
        if not raw:
            raise ValueError("AI 没有返回可用的小猪策划")
        reserved: set[str] = set()
        result = []
        for item in raw[:count]:
            name = re.sub(r"\s+", "", str(item.get("name") or "小猪"))[:12] or "小猪"
            slug = self._studio_unique_slug(str(item.get("slug") or name), reserved)
            features = re.sub(r"\s+", " ", str(item.get("features") or "简洁主题配饰")).strip()[:80]
            description = re.sub(r"\s+", " ", str(item.get("description") or "")).strip()[:80]
            analysis = re.sub(r"\s+", " ", str(item.get("analysis") or "")).strip()[:360]
            result.append(
                {
                    "id": slug,
                    "name": name,
                    "features": features,
                    "description": description,
                    "analysis": analysis,
                }
            )
        return result

    def _studio_reference_image(self, pig_id: str) -> tuple[dict, bytes]:
        pig_id = str(pig_id or "").strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
            raise ValueError("参考小猪 ID 无效")
        pig = self._find_catalog_pig(pig_id)
        if not pig or pig_id == "eaten":
            raise ValueError("参考小猪不存在")
        path = self.find_image_file(pig_id)
        if not path or not Path(path).is_file():
            raise ValueError("参考小猪缺少可用图片")
        raw = Path(path).read_bytes()
        normalized = self._normalise_image_bytes(raw)
        return dict(pig), normalized

    @staticmethod
    def _studio_extract_image_candidate(payload: Any) -> str:
        def visit(value: Any) -> str:
            if isinstance(value, str):
                match = re.search(
                    r"data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+", value
                )
                if match:
                    return match.group(0)
                match = re.search(r"https://[^\s\)\]>'\"]+", value)
                return match.group(0) if match else ""
            if isinstance(value, dict):
                for key in ("url", "image_url", "content", "data", "images"):
                    if key in value:
                        found = visit(value.get(key))
                        if found:
                            return found
                for nested in value.values():
                    found = visit(nested)
                    if found:
                        return found
            if isinstance(value, list):
                for nested in value:
                    found = visit(nested)
                    if found:
                        return found
            return ""

        return visit(payload)

    async def _studio_download_generated_url(self, url: str) -> bytes:
        parsed = urlsplit(str(url or ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("生图服务返回了不安全的图片地址")
        timeout = min(120.0, max(10.0, float(self.ai_generation_timeout)))
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=bool(getattr(self, "resource_use_system_proxy", False)),
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            if len(response.content) > self.PIG_STUDIO_MAX_RESPONSE_BYTES:
                raise ValueError("生图服务返回的图片超过大小上限")
            return bytes(response.content)

    async def _studio_render_image(
        self,
        reference_pig: dict,
        reference_bytes: bytes,
        *,
        theme: str,
        features: str,
        feedback: str,
    ) -> tuple[bytes, str]:
        base_url = self._studio_safe_base_url()
        if not self.pig_studio_image_api_key:
            raise ValueError("尚未配置 AI 小猪工坊生图 API Key")
        model = self.pig_studio_image_model
        reference_b64 = base64.b64encode(reference_bytes).decode("ascii")
        reference_name = str(reference_pig.get("name") or reference_pig.get("id") or "参考小猪")
        prompt = (
            f"以输入图片中的「{reference_name}」为唯一基础体态和画风参考，设计【{theme}】主题小猪。\n"
            f"只添加少量主题元素：{features or '1-2 个极简、易识别的配饰'}。\n"
            "必须保持参考小猪原本的四足动物体态、身体比例、脸型、猪鼻和整体二维插画质感；"
            "禁止改成人形站立，禁止增加复杂背景、文字、水印或品牌 Logo。\n"
            "构图保持完整居中，背景纯白或透明，适合作为 512×512 游戏图鉴资产。"
        )
        if feedback:
            prompt += f"\n本轮微调：{feedback[:300]}"
        body = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{reference_b64}"
                            },
                        },
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.pig_studio_image_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        timeout = min(120.0, max(10.0, float(self.ai_generation_timeout)))
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=bool(getattr(self, "resource_use_system_proxy", False)),
            headers=headers,
        ) as client:
            response = await client.post(f"{base_url}/chat/completions", json=body)
            if len(response.content) > self.PIG_STUDIO_MAX_RESPONSE_BYTES:
                raise ValueError("生图服务响应超过大小上限")
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise ValueError("生图服务没有返回有效 JSON") from exc
        candidate = self._studio_extract_image_candidate(payload)
        if not candidate:
            raise ValueError("生图服务响应中没有找到图片")
        if candidate.startswith("data:image/"):
            try:
                encoded = candidate.split(",", 1)[1]
                raw = base64.b64decode(re.sub(r"\s+", "", encoded), validate=False)
            except Exception as exc:
                raise ValueError("生图服务返回的图片数据损坏") from exc
        else:
            raw = await self._studio_download_generated_url(candidate)
        if len(raw) > self.PIG_STUDIO_MAX_RESPONSE_BYTES:
            raise ValueError("生成图片超过大小上限")
        normalized = await asyncio.to_thread(self._normalise_image_bytes, raw)
        return normalized, model

    def _studio_preview(self, raw: bytes) -> str:
        with PILImage.open(io.BytesIO(raw)) as source:
            image = ImageOps.exif_transpose(source).convert("RGBA")
            method = getattr(PILImage, "Resampling", PILImage).LANCZOS
            image.thumbnail((self.PIG_STUDIO_PREVIEW_SIZE, self.PIG_STUDIO_PREVIEW_SIZE), method)
            canvas = PILImage.new(
                "RGBA",
                (self.PIG_STUDIO_PREVIEW_SIZE, self.PIG_STUDIO_PREVIEW_SIZE),
                (255, 255, 255, 0),
            )
            x = (canvas.width - image.width) // 2
            y = (canvas.height - image.height) // 2
            canvas.alpha_composite(image, (x, y))
            output = io.BytesIO()
            canvas.save(output, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")

    def _studio_store_draft(
        self,
        raw: bytes,
        *,
        theme: str,
        features: str,
        reference_pig_id: str,
        model: str,
    ) -> tuple[str, str]:
        self._studio_cleanup_drafts()
        token = secrets.token_urlsafe(18).rstrip("=")
        root = self.pig_studio_draft_dir
        image_path = root / f"{token}.png"
        meta_path = root / f"{token}.json"
        with tempfile.NamedTemporaryFile("wb", dir=root, suffix=".tmp", delete=False) as tmp:
            tmp.write(raw)
            temp_path = Path(tmp.name)
        temp_path.replace(image_path)
        self.save_json(
            meta_path,
            {
                "created_at": int(time.time()),
                "theme": str(theme)[:80],
                "features": str(features)[:160],
                "reference_pig_id": str(reference_pig_id),
                "model": str(model)[:128],
            },
        )
        return token, self._studio_preview(raw)

    def _studio_draft_paths(self, token: str) -> tuple[Path, Path]:
        value = str(token or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{12,64}", value):
            raise ValueError("草稿 ID 无效")
        image_path = self.pig_studio_draft_dir / f"{value}.png"
        meta_path = self.pig_studio_draft_dir / f"{value}.json"
        if not image_path.is_file() or not meta_path.is_file():
            raise ValueError("草稿不存在或已经过期")
        if time.time() - image_path.stat().st_mtime > self.PIG_STUDIO_DRAFT_TTL_SECONDS:
            image_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            raise ValueError("草稿已经过期，请重新生成")
        return image_path, meta_path

    async def page_studio_status(self):
        try:
            provider = self.context.get_using_provider()
            host = ""
            if self.pig_studio_image_base_url:
                try:
                    host = urlsplit(self.pig_studio_image_base_url).hostname or ""
                except ValueError:
                    host = ""
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "enabled": bool(self.enable_pig_studio),
                        "planning_available": provider is not None,
                        "image_configured": self._studio_image_configured(),
                        "image_model": self.pig_studio_image_model if self._studio_image_configured() else "",
                        "image_host": host if self._studio_image_configured() else "",
                        "max_batch": self.pig_studio_max_batch,
                        "draft_ttl_minutes": self.PIG_STUDIO_DRAFT_TTL_SECONDS // 60,
                        "reference_mode": "catalog-pig",
                    },
                }
            )
        except Exception as exc:
            logger.error(f"读取 AI 小猪工坊状态失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "读取 AI 小猪工坊状态失败"})

    async def page_studio_plan(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not self.enable_pig_studio:
                raise ValueError("AI 小猪工坊已关闭")
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")
            try:
                count = int(payload.get("count", 3))
            except (TypeError, ValueError):
                count = 3
            count = min(self.pig_studio_max_batch, max(1, count))
            style_vibe = re.sub(r"\s+", " ", str(payload.get("style_vibe") or "")).strip()[:120]
            guidance = re.sub(r"\s+", " ", str(payload.get("guidance") or "")).strip()[:300]
            tasks = await self._studio_generate_plan(count, style_vibe, guidance)
            return self._jsonify({"status": "ok", "data": {"tasks": tasks}})
        except (ValueError, RuntimeError) as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except asyncio.TimeoutError:
            return self._jsonify({"status": "error", "message": "AI 策划超时，请稍后再试"})
        except Exception as exc:
            logger.error(f"AI 小猪批量策划失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "AI 小猪批量策划失败"})

    async def page_studio_render(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not self.enable_pig_studio:
                raise ValueError("AI 小猪工坊已关闭")
            if not self._studio_image_configured():
                raise ValueError("尚未配置 AI 小猪工坊生图通道")
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")
            theme = re.sub(r"\s+", " ", str(payload.get("theme") or "")).strip()[:80]
            features = re.sub(r"\s+", " ", str(payload.get("features") or "")).strip()[:160]
            feedback = re.sub(r"\s+", " ", str(payload.get("feedback") or "")).strip()[:300]
            reference_id = str(payload.get("reference_pig_id") or "").strip()
            if not theme:
                raise ValueError("请先填写小猪主题")
            reference_pig, reference_bytes = await asyncio.to_thread(
                self._studio_reference_image, reference_id
            )
            image, model = await self._studio_render_image(
                reference_pig,
                reference_bytes,
                theme=theme,
                features=features,
                feedback=feedback,
            )
            draft_id, preview = await asyncio.to_thread(
                self._studio_store_draft,
                image,
                theme=theme,
                features=features,
                reference_pig_id=reference_id,
                model=model,
            )
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "draft_id": draft_id,
                        "preview": preview,
                        "model": model,
                        "expires_in_minutes": self.PIG_STUDIO_DRAFT_TTL_SECONDS // 60,
                    },
                }
            )
        except (ValueError, httpx.HTTPError) as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except asyncio.TimeoutError:
            return self._jsonify({"status": "error", "message": "AI 生图超时，请稍后再试"})
        except Exception as exc:
            logger.error(f"AI 小猪生图失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "AI 小猪生图失败"})

    async def page_studio_import(self):
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify({"status": "error", "message": "请求来源或令牌无效"})
            if not isinstance(payload, dict):
                raise ValueError("请求格式无效")
            pig_id = str(payload.get("id") or "").strip().lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError("小猪 ID 无效")
            if self._find_catalog_pig(pig_id):
                raise ValueError("该小猪 ID 已存在；AI 工坊只允许新增，编辑请回图鉴管理")
            name = re.sub(r"\s+", " ", str(payload.get("name") or "")).strip()[:30]
            description = re.sub(r"\s+", " ", str(payload.get("description") or "")).strip()[:120]
            analysis = re.sub(r"\s+", " ", str(payload.get("analysis") or "")).strip()[:600]
            if not name or not description or not analysis:
                raise ValueError("名称、描述和完整文案都不能为空")
            image_path, meta_path = self._studio_draft_paths(str(payload.get("draft_id") or ""))
            normalized = await asyncio.to_thread(
                self._normalise_image_bytes, image_path.read_bytes()
            )
            record = {
                "id": pig_id,
                "name": name,
                "description": description,
                "analysis": analysis,
            }
            await asyncio.to_thread(self._persist_catalog_override, record, normalized)
            image_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            logger.info(f"AI 小猪工坊新增小猪：{pig_id}")
            return self._jsonify(
                {
                    "status": "ok",
                    "data": {
                        "id": pig_id,
                        "message": "AI 草稿已写入本地图鉴层，可继续编辑 EX 或投稿公共源",
                    },
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"AI 小猪草稿入库失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "AI 小猪草稿入库失败"})
