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

    pass
