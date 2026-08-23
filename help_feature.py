from __future__ import annotations

import asyncio
import os
import shutil
import threading
import uuid
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

try:
    from .help_system import (
        HelpFeatureState,
        build_help_sections,
        help_sections_fingerprint,
    )
    from .renderers.help import render_help_card
    from .wiki_links import WIKI_HOME_URL, WIKI_TROUBLESHOOTING_URL
except ImportError:  # pragma: no cover - direct module loading compatibility
    from help_system import HelpFeatureState, build_help_sections, help_sections_fingerprint
    from renderers.help import render_help_card
    from wiki_links import WIKI_HOME_URL, WIKI_TROUBLESHOOTING_URL


_HELP_CACHE_LOCK = threading.Lock()


class HelpFeatureMixin:
    """Configuration-aware RollPig help model, rendering and caching."""

    HELP_RENDER_CACHE_VERSION = 7
    HELP_RENDER_CACHE_KEEP = 8

    def _help_feature_state(self) -> HelpFeatureState:
        recovery_seconds = int(
            getattr(self, "group_roast_cooldown_seconds", 8 * 3600) or 0
        )
        return HelpFeatureState(
            at_view_pig=bool(getattr(self, "at_view_pig", False)),
            enable_new_pig_pity=bool(getattr(self, "enable_new_pig_pity", True)),
            enable_daily_duplicate_pity=bool(
                getattr(self, "enable_daily_duplicate_pity", True)
            ),
            enable_roast=bool(getattr(self, "enable_roast", True)),
            enable_group_roast=bool(getattr(self, "enable_group_roast", True)),
            enable_roast_reservation=bool(
                getattr(self, "enable_roast_reservation", True)
            ),
            enable_oven_refill=bool(getattr(self, "enable_oven_refill", True)),
            enable_group_eat=bool(getattr(self, "enable_group_eat", True)),
            enable_roast_protection=bool(
                getattr(self, "enable_roast_protection", True)
            ),
            enable_ai_roast_copy=bool(getattr(self, "enable_ai_roast_copy", False)),
            enable_daily_report=bool(getattr(self, "enable_daily_report", True)),
            daily_report_auto_send=bool(
                getattr(self, "daily_report_auto_send", True)
            ),
            daily_report_random_eat_enabled=bool(
                getattr(self, "daily_report_random_eat_enabled", False)
            ),
            eat_success_percent=int(getattr(self, "eat_success_percent", 15) or 15),
            group_roast_max_charges=int(
                getattr(self, "group_roast_max_charges", 2) or 2
            ),
            group_roast_recovery_hours=max(1.0, recovery_seconds / 3600.0),
            roast_reservation_max_participants=int(
                getattr(self, "roast_reservation_max_participants", 12) or 12
            ),
        )

    def _help_sections(self):
        return build_help_sections(self._help_feature_state(), locale="zh-CN")

    @staticmethod
    def _font_identity(font) -> str:
        if font is None:
            return "none"
        path = str(getattr(font, "path", "") or "")
        try:
            family = "/".join(str(item) for item in font.getname())
        except Exception:
            family = font.__class__.__name__
        return f"{path}|{family}"

    def _help_font_identity(self) -> str:
        """Fingerprint the one font used by the Simplified Chinese help bitmap."""

        return f"bold={self._font_identity(self.font_bold)}"

    def _help_cache_identity(self) -> str:
        """Hash actual visible content and visual inputs to prevent stale masters."""

        palette = self._image_palette()
        theme = "night" if bool(palette.get("night")) else "light"
        visual_identity = (
            f"{theme}|renderer={self.HELP_RENDER_CACHE_VERSION}|"
            f"font={self._help_font_identity()}"
        )
        return help_sections_fingerprint(
            self._help_sections(),
            theme=visual_identity,
        )

    def _help_cache_dir(self) -> Path:
        path = self.plugin_data_dir / "render_cache" / "help"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _help_master_path(self) -> Path:
        return self._help_cache_dir() / f"help-{self._help_cache_identity()}.png"

    @staticmethod
    def _valid_help_master(path: Path) -> bool:
        try:
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False

    def _prune_help_masters(self, keep: Path) -> None:
        candidates = []
        for path in self._help_cache_dir().glob("help-*.png"):
            if path == keep:
                continue
            try:
                candidates.append((path.stat().st_mtime_ns, path))
            except OSError:
                continue
        candidates.sort(reverse=True)
        for _mtime, path in candidates[self.HELP_RENDER_CACHE_KEEP - 1 :]:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def _ensure_help_master(self) -> Path:
        """Render once per effective help model and keep a persistent master."""

        master = self._help_master_path()
        if self._valid_help_master(master):
            return master

        with _HELP_CACHE_LOCK:
            if self._valid_help_master(master):
                return master
            kwargs = {
                "palette": self._image_palette(),
                "font_bold": self.font_bold,
            }
            gate = getattr(self, "_run_with_render_slot", None)
            if callable(gate):
                rendered = gate(render_help_card, self._help_sections(), **kwargs)
            else:
                rendered = render_help_card(self._help_sections(), **kwargs)
            staging = master.with_name(f".{master.name}.{uuid.uuid4().hex}.tmp")
            try:
                shutil.copyfile(rendered, staging)
                staging.replace(master)
            finally:
                rendered.unlink(missing_ok=True)
                staging.unlink(missing_ok=True)
            self._prune_help_masters(master)
            return master

    def render_help_image(self) -> Path:
        """Return a disposable hardlink/copy while retaining the cached master."""

        master = self._ensure_help_master()
        output = master.with_name(f"help-send-{uuid.uuid4().hex}.png")
        try:
            os.link(master, output)
        except OSError:
            shutil.copyfile(master, output)
        return output

    async def rollpig_help(self, event: AstrMessageEvent):
        """Prepare and copy dynamic help outside the asyncio event loop."""

        self._claim_command_event(event)
        output = None
        try:
            output = await asyncio.to_thread(self.render_help_image)
            await event.send(event.image_result(str(output.absolute())))
            try:
                await event.send(
                    event.plain_result(
                        "📖 想看完整玩法、管理、投稿与排障？今日小猪 Wiki：\n"
                        f"{WIKI_HOME_URL}"
                    )
                )
            except Exception as link_exc:
                logger.warning(f"发送今日小猪 Wiki 入口失败：{link_exc}")
        except Exception as exc:
            logger.error(f"生成猪猪帮助图片失败：{exc}", exc_info=True)
            await event.send(
                event.plain_result(
                    "猪猪帮助图片生成失败，请查看后台日志。\n"
                    f"🧯 排障指南：{WIKI_TROUBLESHOOTING_URL}"
                )
            )
        finally:
            if output:
                output.unlink(missing_ok=True)
