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
