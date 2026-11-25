from __future__ import annotations

import asyncio
import base64
import re
from urllib.parse import urlsplit

from astrbot.api import logger
from astrbot.api.web import request

try:
    from .ex_public_source_legacy import ExPublicSourceMixin as _LegacyExPublicSourceMixin
except ImportError:  # pragma: no cover - direct module loading compatibility
    from ex_public_source_legacy import ExPublicSourceMixin as _LegacyExPublicSourceMixin


class ExPublicSourceMixin(_LegacyExPublicSourceMixin):
    """Rights-aware public-source bridge using submission envelope v3.

    Shared EX payload normalization and review-image proxying live in
    ``ex_public_source_legacy.py``. Submissions and review decisions live here
    so missing rights evidence fails closed.
    """

    PUBLIC_SOURCE_RIGHTS_VERSION = 3
    PUBLIC_SOURCE_RIGHTS_BASES = {"original", "license", "explicit_permission"}
    PUBLIC_SOURCE_RIGHTS_PERSON_MAX = 120
    PUBLIC_SOURCE_RIGHTS_URL_MAX = 1200
    PUBLIC_SOURCE_RIGHTS_ATTRIBUTION_MAX = 600
    PUBLIC_SOURCE_RIGHTS_NOTES_MAX = 1200
    PUBLIC_SOURCE_REVIEW_NOTE_MAX = 600
    USER_AGENT = (
        "AstrBot-RollPig/3.11.7 "
        "(+https://github.com/casama233/astrbot_plugin_rollpig)"
    )

    @staticmethod
    def _rights_text(value: object, label: str, limit: int, *, required: bool) -> str:
        text = str(value or "").strip()
        if required and not text:
            raise ValueError(f'{label} 为必填项，不能为空')
        if len(text) > limit:
            raise ValueError(f'{label} 内容过长，超出限制')
        return text

    @classmethod
    def _rights_https_url(cls, value: object, label: str, *, required: bool) -> str:
        text = cls._rights_text(
            value,
            label,
            cls.PUBLIC_SOURCE_RIGHTS_URL_MAX,
            required=required,
        )
        if not text:
            return ""
        parsed = urlsplit(text)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError(f'{label} 必须是未携带账号密码的 HTTPS 链接')
        return text

    @classmethod
    def _normalize_public_source_rights(cls, payload: object) -> dict:
        if not isinstance(payload, dict):
            raise ValueError('发起投稿前必须先填妥 rights 版权声明资料')

        basis = str(payload.get("basis") or "").strip()
        if basis not in cls.PUBLIC_SOURCE_RIGHTS_BASES:
            raise ValueError(
                'rights.basis 的取值必须是 original、license 或 explicit_permission 之一'
            )

        author = cls._rights_text(
            payload.get("author"),
            "rights.author",
            cls.PUBLIC_SOURCE_RIGHTS_PERSON_MAX,
            required=True,
        )
        rights_holder = cls._rights_text(
            payload.get("rights_holder"),
            "rights.rights_holder",
            cls.PUBLIC_SOURCE_RIGHTS_PERSON_MAX,
            required=True,
        )
        source_url = cls._rights_https_url(
            payload.get("source_url"), "rights.source_url", required=True
        )
        attribution = cls._rights_text(
            payload.get("attribution"),
            "rights.attribution",
            cls.PUBLIC_SOURCE_RIGHTS_ATTRIBUTION_MAX,
            required=True,
        )
        notes = cls._rights_text(
            payload.get("notes"),
            "rights.notes",
            cls.PUBLIC_SOURCE_RIGHTS_NOTES_MAX,
            required=False,
        )

        license_id = str(payload.get("license_id") or "").strip()
        if license_id and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}", license_id):
            raise ValueError('许可证编号（rights.license_id）填得不对劲，格式没通过')
        if basis == "license" and not license_id:
            raise ValueError('选了按许可证投稿，必须填上许可证编号（rights.license_id）')

        evidence_url = cls._rights_https_url(
            payload.get("permission_evidence_url"),
            "rights.permission_evidence_url",
            required=basis == "explicit_permission",
        )

        if payload.get("redistribution_authorized") is not True:
            raise ValueError(
                '得先勾选确认允许分发（rights.redistribution_authorized=true），才能把小猪投出去'
            )
        if payload.get("attestation") is not True:
            raise ValueError('投稿前必须先勾上版权声明确认（rights.attestation=true）')

        return {
            "basis": basis,
            "author": author,
            "rights_holder": rights_holder,
            "source_url": source_url,
            "license_id": license_id,
            "permission_evidence_url": evidence_url,
            "attribution": attribution,
            "notes": notes,
            "redistribution_authorized": True,
            "attestation": True,
        }

    async def _submit_local_pig_to_public_source(
        self, pig_id: str, rights: dict
    ) -> dict:
        record, raw = await asyncio.to_thread(
            self._public_source_submission_payload, pig_id
        )
        payload = {
            "submission_version": self.PUBLIC_SOURCE_RIGHTS_VERSION,
            "record": {
                key: str(record.get(key) or "")
                for key in ("id", "name", "description", "analysis")
            },
            "image": base64.b64encode(raw).decode("ascii"),
            "rights": rights,
        }
        result = await self._public_source_request_json(
            "POST", "/submissions", payload=payload
        )
        if not isinstance(result, dict):
            raise ValueError('公共猪圈那边吐回了一串看不懂的投稿回执')
        return result

    async def page_pig_submit_public_source(self):
        """Submit one local base pig only after rights-v3 validation."""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify(
                    {"status": "error", "message": '来路不明或通行令牌失效了，操作被拦下'}
                )
            if not isinstance(payload, dict) or payload.get("confirm") is not True:
                raise ValueError('发车投稿前，请先确认资料齐全且权利证明无误')
            pig_id = str(payload.get("id") or "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError('翻遍了猪圈也没对上这只小猪的编号')
            rights = self._normalize_public_source_rights(payload.get("rights"))
            result = await self._submit_local_pig_to_public_source(pig_id, rights)
            logger.info(
                f"管理页已按 rights-v3 提交小猪到 AstrBot 公共猪源审核：{pig_id}"
            )
            return self._jsonify(
                {
                    "status": "ok",
                    "message": result.get(
                        "message", "已进入内容与权利资料审核队列；审核不会自动发布"
                    ),
                    "data": result,
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"提交公共猪源失败：{exc}", exc_info=True)
            return self._jsonify(
                {"status": "error", "message": '往公共猪圈投递小猪时卡壳了，歇会儿再试一次吧'}
            )

    async def _submit_local_ex_to_public_source(
        self, pig_id: str, rights: dict
    ) -> dict:
        record, raw, ex_variants, variant_images = await asyncio.to_thread(
            self._ex_public_source_payload, pig_id
        )
        payload = {
            "submission_version": self.PUBLIC_SOURCE_RIGHTS_VERSION,
            "record": {
                key: str(record.get(key) or "")
                for key in ("id", "name", "description", "analysis")
            },
            "image": base64.b64encode(raw).decode("ascii"),
            "ex_variants": ex_variants,
            "variant_images": variant_images,
            "rights": rights,
        }
        result = await self._public_source_request_json(
            "POST", "/submissions", payload=payload
        )
        if not isinstance(result, dict):
            raise ValueError('公共猪圈回传的投稿结果乱七八糟，系统没看懂')
        return result

    async def page_ex_submit_public_source(self):
        """Submit base + local EX through the same rights-v3 envelope."""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify(
                    {"status": "error", "message": '请求来源不对或者令牌过期了，先刷新看看'}
                )
            if not isinstance(payload, dict) or payload.get("confirm") is not True:
                raise ValueError(
                    '投稿前得先点确认，把基础档案、EX 变身图和版权证明打包一起交上去'
                )
            pig_id = str(payload.get("id") or "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", pig_id):
                raise ValueError('这只小猪的档案编号没对上，查无此猪')
            rights = self._normalize_public_source_rights(payload.get("rights"))
            result = await self._submit_local_ex_to_public_source(pig_id, rights)
            logger.info(
                f"管理页已按 rights-v3 提交小猪及 EX 差分到公共猪源审核：{pig_id}"
            )
            return self._jsonify(
                {
                    "status": "ok",
                    "message": result.get(
                        "message", "已进入内容与权利资料审核队列；审核不会自动发布"
                    ),
                    "data": result,
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"提交 EX 差分到公共猪源失败：{exc}", exc_info=True)
            return self._jsonify(
                {"status": "error", "message": '往公共猪圈发送投稿失败了，稍后再重新投递吧'}
            )

    async def page_public_source_review_decision(self):
        """Review rights evidence without treating approval as publication."""
        try:
            payload = await request.json(default={})
            if not self._is_authorized_write_request(request, payload):
                return self._jsonify(
                    {"status": "error", "message": '请求来源异常或验证令牌已失效'}
                )
            if not isinstance(payload, dict) or payload.get("confirm") is not True:
                raise ValueError('拍板审核之前，得先勾选确认一下哦')

            submission_id = str(
                payload.get("id") or payload.get("submission_id") or ""
            ).strip()
            decision = str(payload.get("decision") or "").strip()
            note = str(payload.get("note") or "").strip()
            rights_verified = payload.get("rights_verified") is True

            if not re.fullmatch(r"[0-9a-f]{32}", submission_id):
                raise ValueError('这份投稿单的编号没对上，找不到对应记录')
            if decision not in {"approve", "reject"}:
                raise ValueError('这个审核操作指令不合法，系统没法执行')
            if len(note) > self.PUBLIC_SOURCE_REVIEW_NOTE_MAX:
                raise ValueError('审核小作文写太长啦，最多只能写 600 字')
            if decision == "approve":
                if not rights_verified:
                    raise ValueError('点通过之前，必须先明确确认权利核验已通过（rights_verified=true）')
                if len(note) < 8:
                    raise ValueError('想点批准的话，权利审核备注至少得写够 8 个字才行')

            result = await self._public_source_request_json(
                "POST",
                f"/admin/submissions/{submission_id}/review",
                payload={
                    "decision": decision,
                    "note": note,
                    "rights_verified": rights_verified,
                },
                admin=True,
            )
            if not isinstance(result, dict):
                raise ValueError('公共猪圈传回来的审核反馈格式不对，解析失败')
            return self._jsonify(
                {
                    "status": "ok",
                    "message": result.get("message", "审核完成；尚未发布"),
                    "data": result,
                }
            )
        except ValueError as exc:
            return self._jsonify({"status": "error", "message": str(exc)})
        except Exception as exc:
            logger.error(f"公共猪源权利审核失败：{exc}", exc_info=True)
            return self._jsonify(
                {"status": "error", "message": '公共猪圈审核请求没发出去，过一会儿再试吧'}
            )
