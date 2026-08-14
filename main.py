"""RollPig plugin entry point.

The long-lived v3.5.0 implementation remains in ``legacy_main`` while the daily
Pigsty report is layered on as a focused mixin. Keeping the entry point thin
makes the report scheduler/rendering independently testable without changing
existing draw, storage, resource, or admin-panel semantics.
"""

try:
    from .daily_report_feature import DailyReportMixin
    from .legacy_main import RollPigPlugin as _BaseRollPigPlugin
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_feature import DailyReportMixin
    from legacy_main import RollPigPlugin as _BaseRollPigPlugin


class RollPigPlugin(DailyReportMixin, _BaseRollPigPlugin):
    """RollPig Plus with configurable rich daily Pigsty reports."""

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
