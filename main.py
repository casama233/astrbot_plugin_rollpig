"""RollPig plugin entry point.

The long-lived v3.5.0 implementation remains in ``legacy_main`` while focused
feature mixins provide independently testable growth/report layers. Keeping the
entry point thin avoids changing existing draw, storage, resource and admin
semantics while the historical implementation is split gradually.
"""

try:
    from .daily_report_feature import DailyReportMixin
    from .ex_variant_feature import ExVariantMixin
    from .legacy_main import RollPigPlugin as _BaseRollPigPlugin
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_feature import DailyReportMixin
    from ex_variant_feature import ExVariantMixin
    from legacy_main import RollPigPlugin as _BaseRollPigPlugin


class RollPigPlugin(DailyReportMixin, ExVariantMixin, _BaseRollPigPlugin):
    """RollPig Plus with EX growth variants and rich daily Pigsty reports."""

    # Keep the management UI cache contract visible at the plugin entry point.
    UI_ASSET_VERSION = "3.1.2"
