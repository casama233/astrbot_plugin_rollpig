import json
import threading
from pathlib import Path

from daily_report_feature import DailyReportMixin


def _claim_harness(root: Path, owner: str):
    harness = object.__new__(DailyReportMixin)
    harness.daily_report_delivery_claim_dir = root
    root.mkdir(parents=True, exist_ok=True)
    harness._daily_report_delivery_owner = owner
    return harness


def test_delivery_claim_is_exclusive_across_instances(tmp_path):
    first = _claim_harness(tmp_path, "first")
    second = _claim_harness(tmp_path, "second")

    first_path, first_claim = first._try_acquire_daily_report_delivery(
        "group-1", "2026-08-18"
    )
    assert first_path is not None
    assert first_claim["status"] == "claimed"

    second_path, existing = second._try_acquire_daily_report_delivery(
        "group-1", "2026-08-18"
    )
    assert second_path is None
    assert existing["delivery_id"] == first_claim["delivery_id"]

    first._finalize_daily_report_delivery_claim(first_path, status="sent")
    persisted = json.loads(first_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "sent"

    third_path, third_existing = second._try_acquire_daily_report_delivery(
        "group-1", "2026-08-18"
    )
    assert third_path is None
    assert third_existing["status"] == "sent"


def test_definite_non_delivery_can_release_claim_for_retry(tmp_path):
    harness = _claim_harness(tmp_path, "owner")
    claim_path, _ = harness._try_acquire_daily_report_delivery(
        "group-2", "2026-08-18"
    )
    assert claim_path is not None
    harness._release_daily_report_delivery_claim(claim_path)
    retry_path, _ = harness._try_acquire_daily_report_delivery(
        "group-2", "2026-08-18"
    )
    assert retry_path is not None


def test_durable_flush_uses_debounced_writer_force_flush():
    class Writer:
        def __init__(self):
            self.calls = []

        def flush(self, *, force=False):
            self.calls.append(force)
            return True

    harness = object.__new__(DailyReportMixin)
    writer = Writer()
    harness._daily_report_state_writer = writer
    harness._flush_daily_report_state_durable()
    assert writer.calls == [True]


def test_delivery_contract_claims_before_platform_send_and_never_retries_uncertain():
    root = Path(__file__).resolve().parents[1]
    feature = (root / "daily_report_feature.py").read_text(encoding="utf-8")
    start = feature.index("    async def _send_scheduled_daily_report")
    end = feature.index("    async def _daily_report_tick", start)
    scheduled = feature[start:end]

    assert scheduled.index("_try_acquire_daily_report_delivery") < scheduled.index(
        "self.context.send_message(umo, chain)"
    )
    assert scheduled.index("_flush_daily_report_state_durable") < scheduled.index(
        "self.context.send_message(umo, chain)"
    )
    assert 'status="uncertain"' in scheduled

    tick = feature[end : feature.index("    async def _background_daily_report", end)]
    assert 'status in {"sent", "uncertain"}' in tick
    stale_start = tick.index('if status == "sending":')
    stale_end = tick.index('if now_ts < int(job.get("due_at", 0) or 0):', stale_start)
    stale = tick[stale_start:stale_end]
    assert 'status="uncertain"' in stale
    assert 'status="pending"' not in stale
