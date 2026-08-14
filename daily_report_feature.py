from __future__ import annotations

import asyncio
import datetime
import hashlib
import io
import json
import random
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from PIL import Image as PILImage
from PIL import ImageDraw, ImageOps

try:
    from .daily_report_core import (
        aggregate_daily_report,
        due_datetime,
        parse_report_time,
        prune_state,
    )
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_core import (
        aggregate_daily_report,
        due_datetime,
        parse_report_time,
        prune_state,
    )


class DailyReportMixin:
    """Daily Pigsty report feature layered over the historical RollPig plugin.

    This mixin deliberately keeps report routing/profile/event metadata in a
    small auxiliary JSON file. Core draw/eaten state continues to use the
    plugin's existing SQLite/JSON storage authority and domain write APIs.
    """

    DAILY_REPORT_STATE_VERSION = 1
    DAILY_REPORT_STATE_KEEP_DAYS = 14
    DAILY_REPORT_MAX_AVATAR_BYTES = 2 * 1024 * 1024
    DAILY_REPORT_RETRY_SECONDS = 10 * 60
    DAILY_REPORT_CATCHUP_HOURS = 12
    DAILY_REPORT_SYSTEM_ACTOR = "v2|system|user|daily-report"

    _REPORT_QUIPS = {
        "roast_maniac": "后厨正在考虑给他发长期工牌。",
        "miserable_ingredient": "今天基本没怎么离开过烤架。",
        "escape_master": "烤架至今没想明白他是怎么跑掉的。",
        "backlash_king": "你以为你在烤他，其实他在等你上桌。",
    }

    def __init__(self, context, config):
        super().__init__(context, config)
        self._init_daily_report_feature()

    @staticmethod
    def _report_bool(value: Any, default: bool) -> bool:
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

    def _init_daily_report_feature(self) -> None:
        config = self.config if isinstance(self.config, dict) or hasattr(self.config, "get") else {}
        self.enable_daily_report = self._report_bool(
            config.get("enable_daily_report", True), True
        )
        self.daily_report_auto_send = self._report_bool(
            config.get("daily_report_auto_send", True), True
        )
        hour, minute = parse_report_time(config.get("daily_report_send_time", "23:50"))
        self.daily_report_send_hour = hour
        self.daily_report_send_minute = minute
        self.daily_report_send_time = f"{hour:02d}:{minute:02d}"
        try:
            delay_minutes = int(config.get("daily_report_random_delay_minutes", 10))
        except (TypeError, ValueError):
            delay_minutes = 10
        self.daily_report_random_delay_minutes = min(60, max(0, delay_minutes))
        self.daily_report_skip_empty_groups = self._report_bool(
            config.get("daily_report_skip_empty_groups", True), True
        )
        self.daily_report_random_eat_enabled = self._report_bool(
            config.get("daily_report_random_eat_enabled", False), False
        )
        self.daily_report_avatar_enabled = self._report_bool(
            config.get("daily_report_avatar_enabled", True), True
        )
        try:
            cache_hours = int(config.get("daily_report_avatar_cache_hours", 24))
        except (TypeError, ValueError):
            cache_hours = 24
        self.daily_report_avatar_cache_hours = min(168, max(1, cache_hours))

        self.daily_report_state_path = self.plugin_data_dir / "daily_report_state.json"
        self.daily_report_avatar_dir = self.plugin_data_dir / "daily_report_avatars"
        self.daily_report_avatar_dir.mkdir(parents=True, exist_ok=True)
        default_state = {
            "version": self.DAILY_REPORT_STATE_VERSION,
            "groups": {},
            "events": {},
            "jobs": {},
        }
        try:
            loaded = self.load_json(self.daily_report_state_path, default_state)
        except Exception as exc:
            logger.warning(f"猪圈日报状态读取失败，已使用空状态：{exc}")
            loaded = default_state
        self.daily_report_state = loaded if isinstance(loaded, dict) else default_state
        self.daily_report_state.setdefault("groups", {})
        self.daily_report_state.setdefault("events", {})
        self.daily_report_state.setdefault("jobs", {})
        self.daily_report_state["version"] = self.DAILY_REPORT_STATE_VERSION
        with self._data_lock:
            if prune_state(
                self.daily_report_state,
                self._today(),
                self.DAILY_REPORT_STATE_KEEP_DAYS,
            ):
                self._save_daily_report_state_locked()

        self._daily_report_send_lock = asyncio.Lock()
        self._daily_report_task: asyncio.Task | None = None
        if self.enable_daily_report and self.daily_report_auto_send:
            try:
                self._daily_report_task = asyncio.get_running_loop().create_task(
                    self._background_daily_report()
                )
            except RuntimeError:
                logger.info("当前尚无事件循环，猪圈日报自动推送将在插件下次加载时启动")

    def _save_daily_report_state_locked(self) -> None:
        self.save_json(self.daily_report_state_path, self.daily_report_state)

    def _event_sender_id(self, event: AstrMessageEvent) -> str:
        user_id = super()._event_sender_id(event)
        if self.enable_daily_report and getattr(self, "daily_report_state", None) is not None:
            try:
                self._remember_daily_report_context(event, user_id)
            except Exception as exc:
                logger.debug(f"记录猪圈日报会话资料失败：{exc}")
        return user_id

    def _sender_display_name(self, event: AstrMessageEvent, fallback: str) -> str:
        try:
            name = str(event.get_sender_name() or "").strip()
        except (AttributeError, TypeError):
            name = ""
        sender = getattr(getattr(event, "message_obj", None), "sender", None)
        if not name:
            for attr in ("nickname", "display_name", "global_name", "name", "username"):
                value = getattr(sender, attr, None)
                if value:
                    name = str(value).strip()
                    if name:
                        break
        if not name:
            name = self._legacy_identity(fallback) or "群友"
        return re.sub(r"\s+", " ", name)[:36]

    @staticmethod
    def _url_candidate(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            text = value.strip()
            return text if text.startswith("https://") else ""
        nested = getattr(value, "url", None)
        if nested and str(nested).startswith("https://"):
            return str(nested)
        return ""

    def _avatar_url_from_event(self, event: AstrMessageEvent, user_id: str) -> str:
        message_obj = getattr(event, "message_obj", None)
        sender = getattr(message_obj, "sender", None)
        raw = getattr(message_obj, "raw_message", None)
        keys = (
            "avatar_url",
            "avatarUrl",
            "avatar",
            "face",
            "head_img",
            "headimgurl",
            "head_image",
            "photo_url",
            "icon_url",
        )
        candidates: list[Any] = [sender]
        if isinstance(raw, dict):
            candidates.extend(
                value
                for value in (
                    raw.get("sender"),
                    raw.get("author"),
                    raw.get("user"),
                    raw.get("member"),
                )
                if value is not None
            )
            candidates.append(raw)
        for obj in candidates:
            if isinstance(obj, dict):
                for key in keys:
                    url = self._url_candidate(obj.get(key))
                    if url:
                        return url[:2048]
            elif obj is not None:
                for key in keys:
                    url = self._url_candidate(getattr(obj, key, None))
                    if url:
                        return url[:2048]

        native_id = self._legacy_identity(str(user_id))
        if self._platform_type(event) == "aiocqhttp" and native_id.isdigit():
            return f"https://q1.qlogo.cn/g?b=qq&nk={native_id}&s=640"
        return ""

    def _remember_daily_report_context(
        self, event: AstrMessageEvent, user_id: str = ""
    ) -> None:
        group_id = self._event_group_id(event)
        if not group_id:
            return
        umo = str(getattr(event, "unified_msg_origin", "") or "").strip()
        platform = self._platform_namespace(event)
        user_id = str(user_id or "").strip()
        now = int(time.time())
        with self._data_lock:
            groups = self.daily_report_state.setdefault("groups", {})
            group = groups.setdefault(str(group_id), {})
            if umo:
                group["umo"] = umo
            group["platform"] = platform
            group["last_seen_at"] = now
            members = group.setdefault("members", {})
            if user_id:
                profile = members.setdefault(user_id, {})
                profile.update(
                    {
                        "display_name": self._sender_display_name(event, user_id),
                        "platform": platform,
                        "native_id": self._legacy_identity(user_id),
                        "last_seen_at": now,
                    }
                )
                avatar_url = self._avatar_url_from_event(event, user_id)
                if avatar_url:
                    profile["avatar_url"] = avatar_url
            prune_state(
                self.daily_report_state,
                self._today(),
                self.DAILY_REPORT_STATE_KEEP_DAYS,
            )
            self._save_daily_report_state_locked()

    def _record_daily_report_event(
        self,
        group_id: str,
        kind: str,
        *,
        actor_id: str = "",
        target_id: str = "",
        victim_id: str = "",
        draw_date: str | None = None,
        event_id: str = "",
    ) -> None:
        if not self.enable_daily_report or not group_id:
            return
        date_key = draw_date or self._today().isoformat()
        payload = {
            "id": event_id or uuid.uuid4().hex,
            "kind": str(kind),
            "actor_id": str(actor_id or ""),
            "target_id": str(target_id or ""),
            "victim_id": str(victim_id or ""),
            "at": int(time.time()),
        }
        with self._data_lock:
            by_date = self.daily_report_state.setdefault("events", {}).setdefault(
                date_key, {}
            )
            rows = by_date.setdefault(str(group_id), [])
            if not isinstance(rows, list):
                rows = []
                by_date[str(group_id)] = rows
            if payload["id"] and any(
                isinstance(item, dict) and str(item.get("id") or "") == payload["id"]
                for item in rows
            ):
                return
            rows.append(payload)
            if len(rows) > 2000:
                del rows[:-2000]
            prune_state(
                self.daily_report_state,
                self._today(),
                self.DAILY_REPORT_STATE_KEEP_DAYS,
            )
            self._save_daily_report_state_locked()

    def _report_events(self, group_id: str, draw_date: str) -> list[dict[str, Any]]:
        with self._data_lock:
            rows = (
                self.daily_report_state.get("events", {})
                .get(str(draw_date), {})
                .get(str(group_id), [])
            )
            return [dict(item) for item in rows if isinstance(item, dict)]

    def _profile_for_report(self, group_id: str, user_id: str) -> dict[str, Any]:
        with self._data_lock:
            group = self.daily_report_state.get("groups", {}).get(str(group_id), {})
            profile = (
                group.get("members", {}).get(str(user_id), {})
                if isinstance(group, dict)
                else {}
            )
            result = dict(profile) if isinstance(profile, dict) else {}
        result.setdefault("display_name", self._legacy_identity(user_id) or "群友")
        result.setdefault("native_id", self._legacy_identity(user_id))
        return result

    def _daily_group_roast_total(self, group_id: str, draw_date: str) -> int:
        members = self._daily_group_members(group_id, draw_date)
        if getattr(self.storage, "supports_domain_reads", False):
            total = 0
            for user_id in members if isinstance(members, list) else []:
                candidates = tuple(self._user_read_candidates(str(user_id)))
                try:
                    count = self.storage.get_roast_count(
                        draw_date, str(group_id), candidates
                    )
                except Exception:
                    count = 0
                total += int(count or 0)
            return total
        counts = self.roast_state.get("daily_roast_counts", {})
        total = 0
        for raw_key, value in counts.items() if isinstance(counts, dict) else ():
            try:
                date_value, event_group, _user_id = json.loads(str(raw_key))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if str(date_value) == draw_date and str(event_group) == str(group_id):
                total += int(value or 0)
        return total

    async def _build_daily_report_payload(
        self, group_id: str, draw_date: str, sacrifice_id: str = ""
    ) -> dict[str, Any]:
        try:
            date_value = datetime.date.fromisoformat(str(draw_date))
        except ValueError:
            date_value = self._today()
            draw_date = date_value.isoformat()
        members = self._daily_group_members(group_id, draw_date)
        member_pigs: list[dict[str, Any]] = []
        for user_id in members if isinstance(members, list) else []:
            user_id = str(user_id)
            pig, was_eaten = self._get_weekly_pig(user_id, date_value)
            if not pig:
                continue
            member_pigs.append(
                {
                    "user_id": user_id,
                    "pig_id": str(pig.get("id") or ""),
                    "pig_name": str(pig.get("name") or pig.get("id") or "未知小猪"),
                    "was_eaten": bool(was_eaten),
                }
            )
        victims = self._daily_eaten_victims(group_id, draw_date)
        events = self._report_events(group_id, draw_date)
        roast_total = await asyncio.to_thread(
            self._daily_group_roast_total, group_id, draw_date
        )
        stats = aggregate_daily_report(
            member_pigs,
            events,
            victims,
            roast_total=roast_total,
        )
        stats["date"] = draw_date
        stats["group_id"] = str(group_id)
        stats["sacrifice_id"] = str(sacrifice_id or "")

        user_ids: set[str] = set()
        for award in stats.get("awards", {}).values():
            if isinstance(award, dict):
                user_ids.update(str(item) for item in award.get("winners", []) if str(item))
        if sacrifice_id:
            user_ids.add(str(sacrifice_id))
        profiles = {
            user_id: self._profile_for_report(group_id, user_id)
            for user_id in user_ids
        }
        stats["profiles"] = profiles

        avatar_bytes: dict[str, bytes] = {}
        if self.daily_report_avatar_enabled and profiles:
            semaphore = asyncio.Semaphore(4)

            async def load_one(user_id: str, profile: dict[str, Any]) -> None:
                async with semaphore:
                    raw = await self._report_avatar_bytes(user_id, profile)
                    if raw:
                        avatar_bytes[user_id] = raw

            await asyncio.gather(
                *(load_one(user_id, profile) for user_id, profile in profiles.items()),
                return_exceptions=True,
            )
        stats["avatars"] = avatar_bytes
        return stats

    def _avatar_cache_path(self, user_id: str, avatar_url: str) -> Path:
        digest = hashlib.sha256(
            f"{user_id}\0{avatar_url}".encode("utf-8", errors="ignore")
        ).hexdigest()
        return self.daily_report_avatar_dir / f"{digest}.png"

    @staticmethod
    def _normalise_report_avatar(raw: bytes) -> bytes:
        with PILImage.open(io.BytesIO(raw)) as source:
            source = ImageOps.exif_transpose(source).convert("RGBA")
            method = getattr(PILImage, "Resampling", PILImage).LANCZOS
            fitted = ImageOps.fit(source, (256, 256), method)
            output = io.BytesIO()
            fitted.save(output, "PNG", optimize=True)
            return output.getvalue()

    async def _report_avatar_bytes(
        self, user_id: str, profile: dict[str, Any]
    ) -> bytes | None:
        avatar_url = str(profile.get("avatar_url") or "").strip()
        if not avatar_url or not avatar_url.startswith("https://"):
            return None
        path = self._avatar_cache_path(user_id, avatar_url)
        max_age = self.daily_report_avatar_cache_hours * 3600
        try:
            if path.exists() and time.time() - path.stat().st_mtime <= max_age:
                return await asyncio.to_thread(path.read_bytes)
        except OSError:
            pass
        try:
            parsed = urlsplit(avatar_url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username:
                return None
            async with self._new_http_client(
                follow_redirects=False, request_timeout=6
            ) as client:
                raw = await self._download_limited(
                    client,
                    avatar_url,
                    self.DAILY_REPORT_MAX_AVATAR_BYTES,
                    attempts=1,
                )
            self._validate_image_dimensions(raw, "平台头像")
            normalized = await asyncio.to_thread(self._normalise_report_avatar, raw)

            def save() -> None:
                with tempfile.NamedTemporaryFile(
                    "wb",
                    dir=self.daily_report_avatar_dir,
                    suffix=".tmp",
                    delete=False,
                ) as tmp:
                    tmp.write(normalized)
                    temp = Path(tmp.name)
                temp.replace(path)

            await asyncio.to_thread(save)
            return normalized
        except Exception as exc:
            logger.debug(f"平台头像获取失败，日报将使用首字占位：{exc}")
            return None

    def _report_palette(self) -> dict[str, tuple[int, int, int]]:
        base = self._image_palette()
        if bool(base.get("night")):
            return {
                "canvas": base["canvas"],
                "surface": base["surface"],
                "surface_alt": base["surface_muted"],
                "title": base["title"],
                "body": base["body"],
                "secondary": base["secondary"],
                "muted": base["muted"],
                "accent": base["accent"],
                "accent_soft": (92, 49, 68),
                "good": (119, 207, 169),
                "warn": (244, 181, 93),
                "danger": (238, 115, 131),
                "line": (85, 64, 78),
            }
        return {
            "canvas": base["canvas"],
            "surface": base["surface"],
            "surface_alt": base["surface_muted"],
            "title": base["title"],
            "body": base["body"],
            "secondary": base["secondary"],
            "muted": base["muted"],
            "accent": base["accent"],
            "accent_soft": (255, 224, 232),
            "good": (60, 155, 112),
            "warn": (194, 126, 39),
            "danger": (190, 75, 99),
            "line": (226, 205, 211),
        }

    def _report_display_name(
        self, report: dict[str, Any], user_id: str, limit: int = 16
    ) -> str:
        profile = report.get("profiles", {}).get(str(user_id), {})
        name = str(profile.get("display_name") or self._legacy_identity(user_id) or "群友")
        return name if len(name) <= limit else name[: max(1, limit - 1)] + "…"

    def _paste_report_avatar(
        self,
        canvas: PILImage.Image,
        draw: ImageDraw.ImageDraw,
        report: dict[str, Any],
        user_id: str,
        box: tuple[int, int, int, int],
        palette: dict[str, tuple[int, int, int]],
    ) -> None:
        left, top, right, bottom = box
        size = min(right - left, bottom - top)
        raw = report.get("avatars", {}).get(str(user_id))
        avatar = None
        if isinstance(raw, (bytes, bytearray)):
            try:
                with PILImage.open(io.BytesIO(raw)) as source:
                    method = getattr(PILImage, "Resampling", PILImage).LANCZOS
                    avatar = ImageOps.fit(
                        ImageOps.exif_transpose(source).convert("RGBA"),
                        (size, size),
                        method,
                    )
            except Exception:
                avatar = None
        mask = PILImage.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        if avatar is not None:
            canvas.paste(avatar.convert("RGB"), (left, top), mask)
        else:
            draw.ellipse(
                (left, top, left + size, top + size),
                fill=palette["accent_soft"],
                outline=palette["accent"],
                width=3,
            )
            name = self._report_display_name(report, user_id, limit=2)
            initial = name[:1] or "P"
            font = self.font_bold.font_variant(size=max(28, int(size * 0.38)))
            text_w, text_h = self._get_text_size(initial, font)
            draw.text(
                (
                    left + (size - text_w) // 2,
                    top + (size - text_h) // 2 - 4,
                ),
                initial,
                font=font,
                fill=palette["accent"],
            )

    def _draw_metric_card(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        label: str,
        value: int,
        palette: dict[str, tuple[int, int, int]],
    ) -> None:
        left, top, right, bottom = box
        draw.rounded_rectangle(box, 24, fill=palette["surface"])
        value_font = self.font_bold.font_variant(size=45)
        label_font = self.font_bold.font_variant(size=21)
        draw.text(
            (left + 24, top + 20),
            str(int(value)),
            font=value_font,
            fill=palette["title"],
        )
        draw.text(
            (left + 25, bottom - 43),
            label,
            font=label_font,
            fill=palette["secondary"],
        )

    def _draw_award_card(
        self,
        canvas: PILImage.Image,
        draw: ImageDraw.ImageDraw,
        report: dict[str, Any],
        box: tuple[int, int, int, int],
        award_key: str,
        title: str,
        palette: dict[str, tuple[int, int, int]],
    ) -> None:
        left, top, right, bottom = box
        award = report.get("awards", {}).get(award_key, {})
        winners = [str(item) for item in award.get("winners", []) if str(item)]
        value = int(award.get("value", 0) or 0)
        draw.rounded_rectangle(box, 28, fill=palette["surface"])
        badge_font = self.font_bold.font_variant(size=21)
        title_font = self.font_bold.font_variant(size=31)
        name_font = self.font_bold.font_variant(size=27)
        small_font = self.font_regular.font_variant(size=19)
        draw.rounded_rectangle(
            (left + 24, top + 22, left + 166, top + 58),
            18,
            fill=palette["accent_soft"],
        )
        draw.text(
            (left + 40, top + 27),
            "今日称号",
            font=badge_font,
            fill=palette["accent"],
        )
        draw.text(
            (left + 24, top + 76),
            title,
            font=title_font,
            fill=palette["title"],
        )
        if not winners:
            draw.text(
                (left + 24, top + 136),
                "本日空缺",
                font=name_font,
                fill=palette["muted"],
            )
            draw.text(
                (left + 24, top + 181),
                "猪圈今天意外地很和平。",
                font=small_font,
                fill=palette["secondary"],
            )
            return

        winner = winners[0]
        self._paste_report_avatar(
            canvas,
            draw,
            report,
            winner,
            (right - 142, top + 70, right - 42, top + 170),
            palette,
        )
        draw.text(
            (left + 24, top + 132),
            self._report_display_name(report, winner),
            font=name_font,
            fill=palette["title"],
        )
        suffix = f"{value} 次"
        if len(winners) > 1:
            suffix += f" · 并列 {len(winners)} 人"
        draw.text(
            (left + 24, top + 171),
            suffix,
            font=small_font,
            fill=palette["accent"],
        )
        quip = self._REPORT_QUIPS.get(award_key, "")
        draw.text(
            (left + 24, bottom - 40),
            quip,
            font=small_font,
            fill=palette["secondary"],
        )

    def render_daily_report_image(self, report: dict[str, Any]) -> Path:
        palette = self._report_palette()
        sacrifice_id = str(report.get("sacrifice_id") or "")
        width = 1200
        height = 1680 + (285 if sacrifice_id else 0)
        canvas = PILImage.new("RGB", (width, height), palette["canvas"])
        draw = ImageDraw.Draw(canvas)

        title_font = self.font_bold.font_variant(size=62)
        label_font = self.font_bold.font_variant(size=26)
        body_font = self.font_regular.font_variant(size=22)
        big_font = self.font_bold.font_variant(size=40)
        small_font = self.font_regular.font_variant(size=19)

        draw.rounded_rectangle((36, 34, 1164, 235), 36, fill=palette["surface"])
        draw.text((76, 66), "猪圈日报", font=title_font, fill=palette["title"])
        draw.text(
            (79, 146),
            str(report.get("date") or ""),
            font=label_font,
            fill=palette["accent"],
        )
        draw.text(
            (79, 190),
            "今天猪圈里也很不太平。",
            font=body_font,
            fill=palette["secondary"],
        )
        draw.rounded_rectangle(
            (850, 72, 1112, 184), 28, fill=palette["accent_soft"]
        )
        draw.text(
            (886, 94),
            "PIGSTY",
            font=self.font_bold.font_variant(size=30),
            fill=palette["accent"],
        )
        draw.text(
            (886, 135),
            "DAILY AWARDS",
            font=self.font_bold.font_variant(size=19),
            fill=palette["secondary"],
        )

        metrics = [
            ("活跃猪友", report.get("active_users", 0)),
            ("今日抽猪", report.get("draws", 0)),
            ("成功上烤架", report.get("roasts", 0)),
            ("今日被吃", report.get("eats", 0)),
            ("成功逃脱", report.get("escapes", 0)),
            ("触发反噬", report.get("backlashes", 0)),
        ]
        card_w, card_h = 350, 118
        for index, (label, value) in enumerate(metrics):
            row, col = divmod(index, 3)
            x = 44 + col * 378
            y = 266 + row * 140
            self._draw_metric_card(
                draw,
                (x, y, x + card_w, y + card_h),
                label,
                int(value or 0),
                palette,
            )

        pop_y = 558
        draw.rounded_rectangle((44, pop_y, 1156, pop_y + 255), 30, fill=palette["surface"])
        draw.text(
            (76, pop_y + 30),
            "今日最热门猪形态",
            font=big_font,
            fill=palette["title"],
        )
        popular = report.get("popular_pigs", [])
        if popular:
            pig = popular[0]
            pig_id = str(pig.get("id") or "")
            path = self.find_image_file(pig_id)
            if path:
                try:
                    thumb = self._fit_card_image(path, (178, 178))
                    mask = PILImage.new("L", (178, 178), 0)
                    ImageDraw.Draw(mask).rounded_rectangle(
                        (0, 0, 177, 177), 32, fill=255
                    )
                    canvas.paste(
                        thumb.convert("RGB"),
                        (76, pop_y + 65),
                        mask,
                    )
                except Exception:
                    pass
            name = str(pig.get("name") or pig_id or "未知小猪")
            draw.text(
                (292, pop_y + 92),
                name[:22],
                font=self.font_bold.font_variant(size=37),
                fill=palette["title"],
            )
            count = int(pig.get("count", 0) or 0)
            tie = f" · 并列 {len(popular)} 种" if len(popular) > 1 else ""
            draw.text(
                (294, pop_y + 145),
                f"今天出现 {count} 次{tie}",
                font=label_font,
                fill=palette["accent"],
            )
            draw.text(
                (294, pop_y + 190),
                "今日猪圈指定制服，撞衫属于集体行为。",
                font=body_font,
                fill=palette["secondary"],
            )
        else:
            draw.text(
                (76, pop_y + 105),
                "今天还没有形成流行趋势。",
                font=label_font,
                fill=palette["muted"],
            )

        awards_y = 846
        draw.text((56, awards_y), "今日猪圈名人堂", font=big_font, fill=palette["title"])
        award_defs = [
            ("roast_maniac", "烧烤狂人"),
            ("miserable_ingredient", "最惨食材"),
            ("escape_master", "逃脱大师"),
            ("backlash_king", "反噬之王"),
        ]
        for index, (key, title) in enumerate(award_defs):
            row, col = divmod(index, 2)
            x = 44 + col * 566
            y = awards_y + 66 + row * 300
            self._draw_award_card(
                canvas,
                draw,
                report,
                (x, y, x + 546, y + 270),
                key,
                title,
                palette,
            )

        footer_y = 1512
        if sacrifice_id:
            sac_y = 1490
            draw.rounded_rectangle(
                (44, sac_y, 1156, sac_y + 255),
                32,
                fill=palette["surface"],
                outline=palette["danger"],
                width=3,
            )
            draw.rounded_rectangle(
                (74, sac_y + 27, 232, sac_y + 67),
                18,
                fill=palette["accent_soft"],
            )
            draw.text(
                (92, sac_y + 32),
                "今日祭品",
                font=label_font,
                fill=palette["danger"],
            )
            self._paste_report_avatar(
                canvas,
                draw,
                report,
                sacrifice_id,
                (88, sac_y + 86, 228, sac_y + 226),
                palette,
            )
            draw.text(
                (270, sac_y + 94),
                self._report_display_name(report, sacrifice_id, 22),
                font=self.font_bold.font_variant(size=38),
                fill=palette["title"],
            )
            draw.text(
                (272, sac_y + 151),
                "日报发布前的最后一刻，他还是完整的小猪。",
                font=body_font,
                fill=palette["secondary"],
            )
            draw.text(
                (272, sac_y + 196),
                "今日状态：吃掉了 · 明日抽猪可能受到影响",
                font=label_font,
                fill=palette["danger"],
            )
            footer_y = 1800

        draw.line((64, footer_y, 1136, footer_y), fill=palette["line"], width=2)
        draw.text(
            (68, footer_y + 24),
            "统计只记录 RollPig 玩法事件 · 称号并列时保留真实并列关系",
            font=small_font,
            fill=palette["muted"],
        )
        draw.text(
            (68, footer_y + 58),
            f"自动推送 {self.daily_report_send_time} + 0–{self.daily_report_random_delay_minutes} 分钟随机延迟",
            font=small_font,
            fill=palette["secondary"],
        )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output = Path(tmp.name)
        canvas.save(output, "PNG", optimize=True)
        return output

    async def _replace_report_date_with_eaten(
        self,
        user_id: str,
        group_id: str,
        draw_date: str,
        outcome: str = "daily_report_sacrifice",
    ) -> str:
        """Apply the existing eaten semantics to an explicitly locked report date."""
        try:
            date_value = datetime.date.fromisoformat(draw_date)
        except ValueError:
            return "invalid-date"
        eaten = (
            self._find_catalog_pig("eaten")
            or self.history.get("pig_snapshots", {}).get("eaten")
            or self.EATEN_PIG_FALLBACK
        )
        storage_id = self._storage_user_key(str(user_id))
        if getattr(self.storage, "supports_domain_writes", False):
            result = await asyncio.to_thread(
                self.storage.replace_daily_pig_with_eaten,
                draw_date=draw_date,
                due_date=(date_value + datetime.timedelta(days=1)).isoformat(),
                cutoff_date=(date_value - datetime.timedelta(days=2)).isoformat(),
                user_id=storage_id,
                user_candidates=tuple(self._user_read_candidates(str(user_id))),
                group_id=str(group_id),
                actor_id=self.DAILY_REPORT_SYSTEM_ACTOR,
                outcome=outcome,
                eaten_pig=dict(eaten),
            )
            self._apply_domain_write_result(result)
            return str(result.get("status") or "error")

        today_cache = self.load_json(
            self.today_path, {"date": "", "records": {}}
        )
        with self._data_lock:
            daily = self.history.setdefault("daily", {})
            day = daily.get(draw_date)
            if not isinstance(day, dict):
                return "missing"
            records = day.setdefault("records", {})
            actual_id = next(
                (
                    candidate
                    for candidate in self._user_read_candidates(str(user_id))
                    if candidate in records
                ),
                storage_id if storage_id in records else "",
            )
            if not actual_id:
                return "missing"
            current_id = str(records.get(actual_id) or "")
            if current_id == "eaten":
                return "already-eaten"
            if not current_id:
                return "missing"
            day.setdefault("eaten_originals", {}).setdefault(actual_id, current_id)
            records[actual_id] = "eaten"
            self.history.setdefault("pig_snapshots", {})["eaten"] = dict(eaten)

            if str(today_cache.get("date") or "") == draw_date:
                cache_records = today_cache.setdefault("records", {})
                cache_records[actual_id] = dict(eaten)

            due_date = (date_value + datetime.timedelta(days=1)).isoformat()
            penalties = self.roast_state.setdefault("eaten_penalties", {})
            penalties[actual_id] = {"due_date": due_date, "failed": False}
            events = self.roast_state.setdefault("eaten_events", {})
            events[self._roast_count_key(draw_date, group_id, actual_id)] = {
                "actor_id": self.DAILY_REPORT_SYSTEM_ACTOR,
                "outcome": outcome,
                "at": int(time.time()),
            }
            cutoff = (date_value - datetime.timedelta(days=2)).isoformat()
            self.roast_state["eaten_events"] = {
                key: value
                for key, value in events.items()
                if self._roast_count_date(str(key)) >= cutoff
            }
            now_date = self._today().isoformat()
            self.roast_state["eaten_penalties"] = {
                key: value
                for key, value in penalties.items()
                if isinstance(value, dict)
                and str(value.get("due_date") or "") >= now_date
            }
            updates = {
                self.history_path: self.history,
                self.roast_state_path: self.roast_state,
            }
            if str(today_cache.get("date") or "") == draw_date:
                updates[self.today_path] = today_cache
            self.save_json_batch(updates)
        return "updated"

    def _eligible_sacrifice_candidates(
        self, group_id: str, draw_date: str
    ) -> list[str]:
        try:
            date_value = datetime.date.fromisoformat(draw_date)
        except ValueError:
            return []
        result: list[str] = []
        for raw_user_id in self._daily_group_members(group_id, draw_date):
            user_id = str(raw_user_id)
            pig = self._get_daily_pig(user_id, date_value)
            if not pig:
                continue
            if str(pig.get("id") or "") == "eaten":
                continue
            if self._eat_target_block_reason(pig):
                continue
            result.append(user_id)
        return list(dict.fromkeys(result))

    def _job_bucket(self, draw_date: str) -> dict[str, Any]:
        return self.daily_report_state.setdefault("jobs", {}).setdefault(
            str(draw_date), {}
        )

    def _ensure_daily_report_job(
        self, group_id: str, report_date: datetime.date
    ) -> dict[str, Any]:
        date_key = report_date.isoformat()
        with self._data_lock:
            jobs = self._job_bucket(date_key)
            job = jobs.get(str(group_id))
            if not isinstance(job, dict):
                max_delay = self.daily_report_random_delay_minutes * 60
                delay = random.SystemRandom().randint(0, max_delay) if max_delay else 0
                due = due_datetime(
                    report_date,
                    self.daily_report_send_hour,
                    self.daily_report_send_minute,
                    self.timezone,
                    delay,
                )
                job = {
                    "status": "pending",
                    "delay_seconds": delay,
                    "due_at": int(due.timestamp()),
                    "attempts": 0,
                    "created_at": int(time.time()),
                }
                jobs[str(group_id)] = job
                self._save_daily_report_state_locked()
            return dict(job)

    def _update_daily_report_job(
        self, draw_date: str, group_id: str, **updates: Any
    ) -> dict[str, Any]:
        with self._data_lock:
            job = self._job_bucket(draw_date).setdefault(str(group_id), {})
            job.update(updates)
            self._save_daily_report_state_locked()
            return dict(job)

    async def _apply_job_sacrifice(
        self, group_id: str, draw_date: str
    ) -> str:
        with self._data_lock:
            job = self._job_bucket(draw_date).setdefault(str(group_id), {})
            claimed = "sacrifice_id" in job
            sacrifice_id = str(job.get("sacrifice_id") or "")
            applied = bool(job.get("sacrifice_applied"))
        if applied:
            return sacrifice_id
        if not claimed:
            candidates = self._eligible_sacrifice_candidates(group_id, draw_date)
            sacrifice_id = random.SystemRandom().choice(candidates) if candidates else ""
            self._update_daily_report_job(
                draw_date,
                group_id,
                sacrifice_id=sacrifice_id,
                sacrifice_applied=False,
            )
        if not sacrifice_id:
            self._update_daily_report_job(
                draw_date, group_id, sacrifice_applied=True
            )
            return ""

        status = await self._replace_report_date_with_eaten(
            sacrifice_id,
            group_id,
            draw_date,
            "daily_report_sacrifice",
        )
        if status not in {"updated", "already-eaten"}:
            raise RuntimeError(f"日报祭品状态写入失败：{status}")
        self._record_daily_report_event(
            group_id,
            "daily_sacrifice",
            target_id=sacrifice_id,
            victim_id=sacrifice_id,
            draw_date=draw_date,
            event_id=f"sacrifice:{draw_date}:{group_id}:{sacrifice_id}",
        )
        self._update_daily_report_job(
            draw_date, group_id, sacrifice_applied=True
        )
        return sacrifice_id

    async def _send_scheduled_daily_report(
        self, group_id: str, draw_date: str
    ) -> None:
        async with self._daily_report_send_lock:
            with self._data_lock:
                group = dict(
                    self.daily_report_state.get("groups", {}).get(str(group_id), {})
                )
                current_job = dict(
                    self._job_bucket(draw_date).get(str(group_id), {})
                )
            if str(current_job.get("status") or "") == "sent":
                return
            umo = str(group.get("umo") or "").strip()
            if not umo:
                raise RuntimeError("没有可用于主动推送的 unified_msg_origin")

            self._update_daily_report_job(
                draw_date,
                group_id,
                status="sending",
                started_at=int(time.time()),
                attempts=int(current_job.get("attempts", 0) or 0) + 1,
            )
            sacrifice_id = ""
            if self.daily_report_random_eat_enabled:
                sacrifice_id = await self._apply_job_sacrifice(group_id, draw_date)

            report = await self._build_daily_report_payload(
                group_id, draw_date, sacrifice_id
            )
            if self.daily_report_skip_empty_groups and not int(
                report.get("active_users", 0) or 0
            ):
                self._update_daily_report_job(
                    draw_date,
                    group_id,
                    status="sent",
                    sent_at=int(time.time()),
                    skipped="empty",
                )
                return

            output = await asyncio.to_thread(self.render_daily_report_image, report)
            uncertain = False
            try:
                chain = MessageChain().file_image(str(output.absolute()))
                sent = await self.context.send_message(umo, chain)
                if sent is False:
                    raise RuntimeError("AstrBot 未找到匹配的消息平台")
                self._update_daily_report_job(
                    draw_date,
                    group_id,
                    status="sent",
                    sent_at=int(time.time()),
                    last_error="",
                )
                logger.info(
                    f"猪圈日报自动推送成功：group={group_id} date={draw_date}"
                )
            except Exception:
                uncertain = True
                raise
            finally:
                if uncertain:
                    asyncio.create_task(self._cleanup_temp_file_later(output))
                else:
                    output.unlink(missing_ok=True)

    async def _daily_report_tick(self) -> None:
        now = self._now()
        today = now.date()
        candidates = [today]
        yesterday = today - datetime.timedelta(days=1)
        yesterday_base = due_datetime(
            yesterday,
            self.daily_report_send_hour,
            self.daily_report_send_minute,
            self.timezone,
            self.daily_report_random_delay_minutes * 60,
        )
        catchup_deadline = yesterday_base + datetime.timedelta(
            hours=self.DAILY_REPORT_CATCHUP_HOURS
        )
        if now <= catchup_deadline:
            candidates.append(yesterday)

        with self._data_lock:
            groups = {
                str(group_id): dict(value)
                for group_id, value in self.daily_report_state.get("groups", {}).items()
                if isinstance(value, dict) and str(value.get("umo") or "").strip()
            }

        now_ts = int(now.timestamp())
        for report_date in candidates:
            base_due = due_datetime(
                report_date,
                self.daily_report_send_hour,
                self.daily_report_send_minute,
                self.timezone,
                0,
            )
            if now < base_due:
                continue
            date_key = report_date.isoformat()
            for group_id in groups:
                members = self._daily_group_members(group_id, date_key)
                if self.daily_report_skip_empty_groups and not members:
                    continue
                job = self._ensure_daily_report_job(group_id, report_date)
                status = str(job.get("status") or "pending")
                if status == "sent":
                    continue
                if status == "sending":
                    started = int(job.get("started_at", 0) or 0)
                    if started and now_ts - started < self.DAILY_REPORT_RETRY_SECONDS:
                        continue
                    self._update_daily_report_job(
                        date_key, group_id, status="pending"
                    )
                    status = "pending"
                if now_ts < int(job.get("due_at", 0) or 0):
                    continue
                last_attempt = int(job.get("last_attempt_at", 0) or 0)
                if last_attempt and now_ts - last_attempt < self.DAILY_REPORT_RETRY_SECONDS:
                    continue
                self._update_daily_report_job(
                    date_key, group_id, last_attempt_at=now_ts
                )
                try:
                    await self._send_scheduled_daily_report(group_id, date_key)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        f"猪圈日报自动推送失败，稍后重试：group={group_id} "
                        f"date={date_key} ({exc})"
                    )
                    self._update_daily_report_job(
                        date_key,
                        group_id,
                        status="pending",
                        last_error=str(exc)[:300],
                    )

        with self._data_lock:
            if prune_state(
                self.daily_report_state,
                today,
                self.DAILY_REPORT_STATE_KEEP_DAYS,
            ):
                self._save_daily_report_state_locked()

    async def _background_daily_report(self) -> None:
        try:
            await asyncio.sleep(random.randint(5, 20))
            while True:
                try:
                    await self._daily_report_tick()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(f"猪圈日报后台调度异常：{exc}")
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass

    async def _roast_group_target(
        self,
        event: AstrMessageEvent,
        target_id: str,
        *,
        bypass: bool = False,
    ) -> None:
        """Base roast flow plus auditable outcome events for daily awards."""
        actor_id = self._event_sender_id(event)
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(event.plain_result("烤群友只能在群聊中使用。"))
            return
        if not target_id:
            await event.send(event.plain_result("请 @ 一位群友，或回复对方的消息后再使用。"))
            return
        if target_id == actor_id:
            await event.send(event.plain_result("不能对自己使用烤群友；请用 /今日烤猪。"))
            return
        target_pig = self._get_daily_pig(target_id, self._today())
        reason = self._roast_block_reason(target_pig)
        if reason:
            await event.send(event.plain_result(reason))
            return
        protected, roast_count = await self._roast_protection_status(group_id, target_id)
        if protected and not bypass:
            await event.send(event.plain_result(self._roast_protection_message(roast_count)))
            return
        if not bypass:
            remaining = await self._consume_group_roast_cooldown(group_id, actor_id)
            if remaining:
                await event.send(
                    event.plain_result(
                        f"烤架还在降温，请 {self._format_cooldown(remaining)} 后再试。"
                    )
                )
                return

        result = "success" if bypass else random.choices(
            ["success", "escape", "backlash"], weights=[60, 30, 10], k=1
        )[0]
        if result == "escape":
            self._record_daily_report_event(
                group_id,
                "roast_escape",
                actor_id=actor_id,
                target_id=target_id,
            )
            await event.send(event.plain_result("💨 对方一溜烟逃走了，烤架上只剩一阵风。"))
            return
        if result == "backlash":
            actor_pig = self._get_daily_pig(actor_id, self._today())
            actor_reason = self._roast_block_reason(actor_pig, subject="actor")
            victim_id = "" if actor_reason else actor_id
            self._record_daily_report_event(
                group_id,
                "roast_backlash",
                actor_id=actor_id,
                target_id=target_id,
                victim_id=victim_id,
            )
            if actor_reason:
                await event.send(
                    event.plain_result(
                        "🔥 烤架反噬了！但你今天没有可料理的小猪，侥幸躲过一劫。"
                    )
                )
                return
            await event.send(event.plain_result("🔥 烤架反噬！这次轮到你的今日小猪上桌。"))
            await self._record_group_roast(group_id, actor_id)
            await self._send_roast_card(event, actor_pig, actor_id)
            return

        self._record_daily_report_event(
            group_id,
            "roast_success",
            actor_id=actor_id,
            target_id=target_id,
            victim_id=target_id,
        )
        prefix = "🔥 后门生效，" if bypass else "🔥 烧烤成功，"
        await event.send(event.plain_result(f"{prefix}对方今天的小猪已被端上料理台。"))
        await self._record_group_roast(group_id, target_id)
        await self._send_roast_card(event, target_pig, target_id)

    @filter.command(
        "猪圈日报",
        alias={"豬圈日報", "今日猪圈日报", "今日豬圈日報"},
    )
    async def pigsty_daily_report(self, event: AstrMessageEvent):
        """Render the current group's rich report; manual views never sacrifice."""
        if not self.enable_daily_report:
            await event.send(event.plain_result("猪圈日报功能已在配置中关闭。"))
            return
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(event.plain_result("猪圈日报只能在群聊中查看。"))
            return
        actor_id = super()._event_sender_id(event)
        self._remember_daily_report_context(event, actor_id)
        draw_date = self._today().isoformat()
        members = self._daily_group_members(group_id, draw_date)
        if not members:
            await event.send(event.plain_result("今天本群还没有 RollPig 数据，晚点再来看看吧。"))
            return
        output = None
        try:
            report = await self._build_daily_report_payload(group_id, draw_date)
            output = await asyncio.to_thread(self.render_daily_report_image, report)
            await event.send(event.image_result(str(output.absolute())))
        except Exception as exc:
            logger.error(f"生成猪圈日报失败：{exc}", exc_info=True)
            await event.send(event.plain_result("猪圈日报生成失败，请稍后再试。"))
        finally:
            if output:
                output.unlink(missing_ok=True)

    async def terminate(self):
        if getattr(self, "_daily_report_task", None):
            task = self._daily_report_task
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        await super().terminate()
