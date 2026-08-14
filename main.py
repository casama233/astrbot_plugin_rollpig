"""RollPig plugin entry point.

The long-lived v3.5.0 implementation remains in ``legacy_main`` while focused
feature mixins provide independently testable growth/report/gameplay layers.
Keeping the entry point thin avoids changing existing storage, resource and
admin semantics while the historical implementation is split gradually.

AstrBot stores handler ownership from ``handler.__module__`` when decorators
run. Since v3.6.0 keeps decorated handlers in ``legacy_main`` and feature
mixins but registers the Star itself from this module, those handlers must be
rebound to the real entry module or AstrBot can discover a command yet skip it
at dispatch time because ``star_map`` has no Star registered for the helper
module. The rebind below restores the v3.5.x ownership semantics without moving
thousands of lines back into this file.
"""

from astrbot.api import logger
from astrbot.core.star.star_handler import star_handlers_registry

try:
    from .daily_report_feature import DailyReportMixin
    from .ex_variant_feature import ExVariantMixin
    from .legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from .roast_reservation_feature import RoastReservationMixin
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_feature import DailyReportMixin
    from ex_variant_feature import ExVariantMixin
    from legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from roast_reservation_feature import RoastReservationMixin


_COMMAND_HANDLER_PRIORITY = 1000


def _rebind_rollpig_handlers_to_entrypoint() -> tuple[int, int]:
    """Make inherited/mixin handlers belong to the actual AstrBot Star module.

    AstrBot's decorator registry captures the defining module of each handler.
    After the v3.6.0 split that means commands defined in ``legacy_main`` or a
    feature mixin are registered under those helper modules, while the only
    Star metadata entry belongs to ``main``. ``StarRequestSubStage`` resolves a
    handler through ``star_map[handler.handler_module_path]``; a helper-module
    path therefore makes the handler discoverable during wake/command matching
    but non-dispatchable at execution time.

    Rebinding only metadata keeps function bodies, storage and data formats
    unchanged. Command handlers also receive an explicit high priority so a
    generic message/AI handler cannot consume a matched RollPig command before
    RollPig has a chance to stop event propagation.
    """

    package = __package__ or __name__.rpartition(".")[0]
    package_prefix = f"{package}." if package else ""
    rebound = 0
    prioritized = 0

    for handler in list(star_handlers_registry):
        module_path = str(getattr(handler, "handler_module_path", "") or "")
        belongs_to_rollpig = module_path == __name__ or (
            bool(package_prefix) and module_path.startswith(package_prefix)
        )
        if not belongs_to_rollpig:
            continue

        if module_path != __name__:
            handler.handler_module_path = __name__
            rebound += 1

        filters = getattr(handler, "event_filters", ()) or ()
        is_command = any(
            item.__class__.__name__ in {"CommandFilter", "CommandGroupFilter"}
            for item in filters
        )
        if not is_command:
            continue

        extras = getattr(handler, "extras_configs", None)
        if not isinstance(extras, dict):
            extras = {}
            handler.extras_configs = extras
        try:
            current_priority = int(extras.get("priority", 0) or 0)
        except (TypeError, ValueError):
            current_priority = 0
        if current_priority < _COMMAND_HANDLER_PRIORITY:
            extras["priority"] = _COMMAND_HANDLER_PRIORITY
        prioritized += 1

    # StarHandlerRegistry sorts only when handlers are appended. We changed
    # priorities after decorator registration, so re-sort the existing list.
    handlers = getattr(star_handlers_registry, "_handlers", None)
    if isinstance(handlers, list):
        handlers.sort(
            key=lambda item: -int(
                (getattr(item, "extras_configs", {}) or {}).get("priority", 0) or 0
            )
        )

    return rebound, prioritized


_REBOUND_HANDLER_COUNT, _PRIORITIZED_COMMAND_COUNT = (
    _rebind_rollpig_handlers_to_entrypoint()
)
if _REBOUND_HANDLER_COUNT or _PRIORITIZED_COMMAND_COUNT:
    logger.info(
        "RollPig 指令注册已绑定到主入口：rebound=%s, prioritized=%s, module=%s",
        _REBOUND_HANDLER_COUNT,
        _PRIORITIZED_COMMAND_COUNT,
        __name__,
    )


class RollPigPlugin(
    RoastReservationMixin, DailyReportMixin, ExVariantMixin, _BaseRollPigPlugin
):
    """RollPig Plus with growth, roast reservations and rich daily reports."""

    # Keep the management UI cache contract visible at the plugin entry point.
    UI_ASSET_VERSION = "3.1.2"

    def _init_regular_font(self):
        """Load the packaged full CJK font before platform fallbacks.

        Marketplace archives have a strict 16 MB ceiling. Release builds keep
        荆南麦圆体.otf as the single bundled full CJK face so both body text and
        titles remain readable without silently falling through to DejaVu.
        """
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "常规")

    def _init_bold_font(self):
        """Load the packaged full CJK title font before platform fallbacks."""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Bold.otf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        return self._load_font(font_paths, self.NAME_FONT_SIZE, "加粗")

    def _init_traditional_font(self):
        """Use the packaged full CJK face for traditional/AI copy before system fallbacks."""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "HanyiYongZiXiaoXiongMaoFan.ttf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "繁体兜底")
