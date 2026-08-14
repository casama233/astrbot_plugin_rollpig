"""RollPig plugin entry point.

The long-lived v3.5.0 implementation remains in ``legacy_main`` while focused
feature mixins provide independently testable growth/report/gameplay layers.
Keeping the entry point thin avoids changing existing storage, resource and
admin semantics while the historical implementation is split gradually.
"""

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

