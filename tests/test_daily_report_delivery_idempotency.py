import asyncio
import os
import time
from pathlib import Path

from daily_report_delivery import DailyReportDeliveryClaims


class _LeakedDailyReportScheduler:
    def __init__(self, plugin_data_dir):
        self.plugin_data_dir = plugin_data_dir

    async def _background_daily_report(self):
        while True:
            await asyncio.sleep(3600)


def test_delivery_claim_is_exclusive_across_instances(tmp_path):
    first = DailyReportDeliveryClaims(tmp_path, keep_days=14, owner="first")
    second = DailyReportDeliveryClaims(tmp_path, keep_days=14, owner="second")
    first_path, first_claim = first.try_acquire("group-1", "2026-08-18")
    assert first_path is not None
    second_path, existing = second.try_acquire("group-1", "2026-08-18")
    assert second_path is None
    assert existing["delivery_id"] == first_claim["delivery_id"]
    first.finalize(first_path, status="sent")
    third_path, third_existing = second.try_acquire("group-1", "2026-08-18")
    assert third_path is None
    assert third_existing["status"] == "sent"


def test_delivery_claim_scope_is_group_and_date(tmp_path):
    claims = DailyReportDeliveryClaims(tmp_path, keep_days=14, owner="owner")
    first_path, _ = claims.try_acquire("group-1", "2026-08-18")
    other_group_path, _ = claims.try_acquire("group-2", "2026-08-18")
    other_date_path, _ = claims.try_acquire("group-1", "2026-08-19")
    assert first_path is not None
    assert other_group_path is not None
    assert other_date_path is not None
    assert len({first_path, other_group_path, other_date_path}) == 3


def test_definite_non_delivery_can_release_claim_for_retry(tmp_path):
    claims = DailyReportDeliveryClaims(tmp_path, keep_days=14, owner="owner")
    claim_path, _ = claims.try_acquire("group-2", "2026-08-18")
    assert claim_path is not None
    claims.release(claim_path)
    retry_path, _ = claims.try_acquire("group-2", "2026-08-18")
    assert retry_path is not None


def test_malformed_existing_claim_fails_closed(tmp_path):
    claims = DailyReportDeliveryClaims(tmp_path, keep_days=14)
    path = claims.path_for("group-3", "2026-08-18")
    path.write_text("not-json", encoding="utf-8")
    acquired, existing = claims.try_acquire("group-3", "2026-08-18")
    assert acquired is None
    assert existing == {"status": "unknown"}


def test_old_claims_are_pruned_without_touching_recent_claims(tmp_path):
    claims = DailyReportDeliveryClaims(tmp_path, keep_days=14)
    old = claims.path_for("old", "2026-07-01")
    recent = claims.path_for("recent", "2026-08-18")
    old.write_text("{}", encoding="utf-8")
    recent.write_text("{}", encoding="utf-8")
    now = time.time()
    os.utime(old, (now - 20 * 86400, now - 20 * 86400))
    claims.prune()
    assert not old.exists()
    assert recent.exists()


def test_three_hot_reloads_leave_only_latest_daily_report_scheduler(tmp_path):
    async def scenario():
        plugin_data_dir = tmp_path / "rollpig-data"
        claims_root = plugin_data_dir / "daily_report_delivery_claims"
        tasks = []

        for index in range(3):
            claims = DailyReportDeliveryClaims(
                claims_root, keep_days=14, owner=f"reload-{index}"
            )
            if index:
                assert claims.cancelled_stale_schedulers == 1
            owner = _LeakedDailyReportScheduler(plugin_data_dir)
            task = asyncio.create_task(owner._background_daily_report())
            tasks.append(task)
            await asyncio.sleep(0)

        assert tasks[0].cancelled()
        assert tasks[1].cancelled()
        assert not tasks[2].done()

        tasks[2].cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(scenario())


def test_reload_sweep_does_not_cancel_other_plugin_data_namespace(tmp_path):
    async def scenario():
        first_data_dir = tmp_path / "first"
        second_data_dir = tmp_path / "second"
        owner = _LeakedDailyReportScheduler(second_data_dir)
        other_task = asyncio.create_task(owner._background_daily_report())
        await asyncio.sleep(0)

        claims = DailyReportDeliveryClaims(
            first_data_dir / "daily_report_delivery_claims",
            keep_days=14,
            owner="new",
        )
        await asyncio.sleep(0)
        assert claims.cancelled_stale_schedulers == 0
        assert not other_task.done()

        other_task.cancel()
        await asyncio.gather(other_task, return_exceptions=True)

    asyncio.run(scenario())


def test_delivery_contract_claims_before_platform_send_and_never_retries_uncertain():
    root = Path(__file__).resolve().parents[1]
    feature = (root / "daily_report_feature.py").read_text(encoding="utf-8")

    durable_start = feature.index("    def _flush_daily_report_state_durable")
    durable_end = feature.index("    def _event_sender_id", durable_start)
    durable = feature[durable_start:durable_end]
    assert "writer.flush(force=True)" in durable

    start = feature.index("    async def _send_scheduled_daily_report")
    end = feature.index("    async def _daily_report_tick", start)
    scheduled = feature[start:end]
    send_call = "self.context.send_message(umo, chain)"
    assert scheduled.index("daily_report_delivery_claims.try_acquire") < scheduled.index(
        send_call
    )
    assert scheduled.index("_flush_daily_report_state_durable") < scheduled.index(
        send_call
    )
    assert 'status="uncertain"' in scheduled

    tick = feature[end : feature.index("    async def _background_daily_report", end)]
    assert 'status in {"sent", "uncertain"}' in tick
    stale_start = tick.index('if status == "sending":')
    stale_end = tick.index(
        'if now_ts < int(job.get("due_at", 0) or 0):', stale_start
    )
    stale = tick[stale_start:stale_end]
    assert 'status="uncertain"' in stale
    assert 'status="pending"' not in stale
