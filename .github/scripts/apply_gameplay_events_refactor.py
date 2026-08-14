from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GAMEPLAY_EVENTS = '''from __future__ import annotations

import datetime
import time
import uuid
from collections.abc import Mapping
from typing import Any

EVENT_SCHEMA_VERSION = 1

# Current event kinds consumed by the daily report.
EVENT_ROAST_SUCCESS = "roast_success"
EVENT_ROAST_ESCAPE = "roast_escape"
EVENT_ROAST_BACKLASH = "roast_backlash"
EVENT_DAILY_SACRIFICE = "daily_sacrifice"

# Reserved gameplay kinds for the next feature layers. Defining the namespace
# here prevents each feature from inventing incompatible strings later.
EVENT_DRAW_COMPLETED = "draw_completed"
EVENT_PIG_UNLOCKED = "pig_unlocked"
EVENT_EX_LEVEL_UP = "ex_level_up"
EVENT_PITY_TRIGGERED = "pity_triggered"
EVENT_ROAST_RESERVATION_CREATED = "roast_reservation_created"
EVENT_ROAST_RESERVATION_JOINED = "roast_reservation_joined"
EVENT_ROAST_RESERVATION_TRIGGERED = "roast_reservation_triggered"
EVENT_ROAST_RESERVATION_CANCELLED = "roast_reservation_cancelled"
EVENT_OVEN_REFILL_STARTED = "oven_refill_started"
EVENT_OVEN_REFILL_SUPPORTED = "oven_refill_supported"
EVENT_OVEN_REFILL_SUCCEEDED = "oven_refill_succeeded"
EVENT_OVEN_REFILL_FAILED = "oven_refill_failed"


def build_gameplay_event(
    kind: str,
    *,
    actor_id: str = "",
    target_id: str = "",
    victim_id: str = "",
    pig_id: str = "",
    metadata: Mapping[str, Any] | None = None,
    event_id: str = "",
    at: int | None = None,
) -> dict[str, Any]:
    """Build the stable JSON shape shared by RollPig gameplay features.

    The first version deliberately stays compatible with the event dictionaries
    already written by the daily-report feature. New optional fields are
    additive, so old report state can be consumed without migration.
    """
    payload: dict[str, Any] = {
        "version": EVENT_SCHEMA_VERSION,
        "id": str(event_id or uuid.uuid4().hex),
        "kind": str(kind or "").strip(),
        "actor_id": str(actor_id or ""),
        "target_id": str(target_id or ""),
        "victim_id": str(victim_id or ""),
        "at": int(time.time() if at is None else at),
    }
    if pig_id:
        payload["pig_id"] = str(pig_id)
    if isinstance(metadata, Mapping) and metadata:
        payload["metadata"] = {str(key): value for key, value in metadata.items()}
    return payload


def append_gameplay_event(
    events: dict[str, Any],
    date_key: str,
    group_id: str,
    event: Mapping[str, Any],
    *,
    max_events: int = 2000,
) -> bool:
    """Append one event idempotently to the existing date/group bucket."""
    date_key = str(date_key or "").strip()
    group_id = str(group_id or "").strip()
    if not date_key or not group_id or not isinstance(event, Mapping):
        return False

    by_date = events.setdefault(date_key, {})
    if not isinstance(by_date, dict):
        by_date = {}
        events[date_key] = by_date
    rows = by_date.setdefault(group_id, [])
    if not isinstance(rows, list):
        rows = []
        by_date[group_id] = rows

    payload = dict(event)
    event_id = str(payload.get("id") or "")
    if event_id and any(
        isinstance(item, dict) and str(item.get("id") or "") == event_id
        for item in rows
    ):
        return False

    rows.append(payload)
    limit = max(1, int(max_events))
    if len(rows) > limit:
        del rows[:-limit]
    return True


def read_gameplay_events(
    events: Mapping[str, Any], date_key: str, group_id: str
) -> list[dict[str, Any]]:
    """Return defensive copies of one group's events for a natural day."""
    by_date = events.get(str(date_key), {}) if isinstance(events, Mapping) else {}
    rows = by_date.get(str(group_id), []) if isinstance(by_date, Mapping) else []
    return [dict(item) for item in rows if isinstance(item, Mapping)]


def prune_gameplay_events(
    events: dict[str, Any], today: datetime.date, keep_days: int = 14
) -> bool:
    """Prune old date buckets while preserving the existing on-disk shape."""
    changed = False
    cutoff = (today - datetime.timedelta(days=max(2, int(keep_days)))).isoformat()
    for date_key in list(events):
        if str(date_key) < cutoff:
            events.pop(date_key, None)
            changed = True
    return changed
'''

TESTS = '''from __future__ import annotations

import datetime

from gameplay_events import (
    EVENT_EX_LEVEL_UP,
    EVENT_ROAST_SUCCESS,
    append_gameplay_event,
    build_gameplay_event,
    prune_gameplay_events,
    read_gameplay_events,
)


def test_build_event_keeps_legacy_shape_and_adds_optional_fields():
    event = build_gameplay_event(
        EVENT_EX_LEVEL_UP,
        actor_id="u1",
        pig_id="sleep-pig",
        metadata={"from": 2, "to": 3},
        event_id="evt-1",
        at=123,
    )
    assert event["version"] == 1
    assert event["id"] == "evt-1"
    assert event["kind"] == EVENT_EX_LEVEL_UP
    assert event["actor_id"] == "u1"
    assert event["target_id"] == ""
    assert event["victim_id"] == ""
    assert event["pig_id"] == "sleep-pig"
    assert event["metadata"] == {"from": 2, "to": 3}
    assert event["at"] == 123


def test_append_is_idempotent_and_bounded():
    state: dict[str, object] = {}
    first = build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="same", at=1)
    assert append_gameplay_event(state, "2026-08-14", "g1", first, max_events=2)
    assert not append_gameplay_event(state, "2026-08-14", "g1", first, max_events=2)
    assert append_gameplay_event(
        state,
        "2026-08-14",
        "g1",
        build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="two", at=2),
        max_events=2,
    )
    assert append_gameplay_event(
        state,
        "2026-08-14",
        "g1",
        build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="three", at=3),
        max_events=2,
    )
    assert [row["id"] for row in read_gameplay_events(state, "2026-08-14", "g1")] == [
        "two",
        "three",
    ]


def test_read_returns_defensive_copies():
    state: dict[str, object] = {}
    append_gameplay_event(
        state,
        "2026-08-14",
        "g1",
        build_gameplay_event(EVENT_ROAST_SUCCESS, event_id="evt", at=1),
    )
    rows = read_gameplay_events(state, "2026-08-14", "g1")
    rows[0]["kind"] = "mutated"
    assert read_gameplay_events(state, "2026-08-14", "g1")[0]["kind"] == EVENT_ROAST_SUCCESS


def test_prune_uses_same_keep_window_as_daily_report():
    state = {
        "2026-07-01": {"g1": []},
        "2026-08-13": {"g1": []},
        "2026-08-14": {"g1": []},
    }
    assert prune_gameplay_events(state, datetime.date(2026, 8, 14), keep_days=14)
    assert "2026-07-01" not in state
    assert "2026-08-13" in state
'''

ARCHITECTURE = '''# RollPig 架構與事件層

本文記錄 v3.5.x 之後的漸進式拆分方向。目標不是一次重寫 `legacy_main.py`，而是在不改變既有 SQLite／JSON 權威資料與玩法語義的前提下，讓新功能有穩定的接入點。

## Gameplay Event v1

`gameplay_events.py` 定義跨功能共用的事件 JSON 形狀、事件名稱、去重寫入、讀取與自然日裁剪。PR #51 已建立的 `daily_report_state.json -> events` 暫時繼續作為持久化容器，因此既有資料**不需要遷移**。

事件最小形狀：

```json
{
  "version": 1,
  "id": "唯一事件 ID",
  "kind": "roast_success",
  "actor_id": "發起者",
  "target_id": "目標",
  "victim_id": "實際受害者",
  "at": 0
}
```

新功能可選增加 `pig_id` 與 `metadata`。舊日報事件沒有 `version`、`pig_id` 或 `metadata` 仍然有效；讀取端必須保持向下兼容。

## 事件名稱

目前日報正式消費：`roast_success`、`roast_escape`、`roast_backlash`、`daily_sacrifice`。

事件層同時預留下一階段的穩定名稱，包括：

- 收藏：`draw_completed`、`pig_unlocked`、`ex_level_up`、`pity_triggered`；
- 預約烤豬：`roast_reservation_created/joined/triggered/cancelled`；
- 烤箱補貨：`oven_refill_started/supported/succeeded/failed`。

預留名稱只建立契約，不代表對應玩法已經啟用。

## 寫入邊界

`DailyReportMixin._record_daily_report_event()` 保留原有「日報關閉時不寫輔助事件」語義，確保 PR #51 行為不變；新的 `_record_gameplay_event()` 是後續玩法可使用的共用入口。

目前事件仍存放在日報輔助狀態中，是刻意的低風險過渡。等 EX、預約與補貨都接入後，再評估把事件持久化抽成獨立 repository 或 SQLite 表，而不是現在提前做資料遷移。

## 後續拆分順序

1. 先讓新功能只透過 Gameplay Event API 寫事件。
2. 把日報、統計、管理面板等讀模型改為消費共用事件。
3. 逐步把 `legacy_main.py` 的收藏、烤豬、資源與管理面板邏輯移入獨立 service／renderer／command 模組。
4. 最後再決定是否把事件持久化從日報狀態提升為獨立存儲權威。
'''


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


write("gameplay_events.py", GAMEPLAY_EVENTS)
write("tests/test_gameplay_events.py", TESTS)
write("docs/ARCHITECTURE.md", ARCHITECTURE)

# daily_report_core: consume stable event constants and shared pruning.
core_path = ROOT / "daily_report_core.py"
core = core_path.read_text(encoding="utf-8")
import_anchor = "from typing import Any\n\n"
imports = '''from typing import Any\n\ntry:\n    from .gameplay_events import (\n        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n    )\nexcept ImportError:  # pragma: no cover - direct module loading compatibility\n    from gameplay_events import (\n        EVENT_ROAST_BACKLASH,\n        EVENT_ROAST_ESCAPE,\n        EVENT_ROAST_SUCCESS,\n        prune_gameplay_events,\n    )\n\n'''
if "from .gameplay_events import" not in core:
    if import_anchor not in core:
        raise RuntimeError("daily_report_core import anchor not found")
    core = core.replace(import_anchor, imports, 1)
core = core.replace('if kind == "roast_success":', "if kind == EVENT_ROAST_SUCCESS:")
core = core.replace('elif kind == "roast_escape":', "elif kind == EVENT_ROAST_ESCAPE:")
core = core.replace('elif kind == "roast_backlash":', "elif kind == EVENT_ROAST_BACKLASH:")
old_prune = '''def prune_state(state: dict[str, Any], today: datetime.date, keep_days: int = 14) -> bool:\n    """Prune dated report events/jobs while keeping group routing metadata."""\n    changed = False\n    cutoff = (today - datetime.timedelta(days=max(2, int(keep_days)))).isoformat()\n    for key in ("events", "jobs"):\n        bucket = state.get(key)\n        if not isinstance(bucket, dict):\n            state[key] = {}\n            changed = True\n            continue\n        for date_key in list(bucket):\n            if str(date_key) < cutoff:\n                bucket.pop(date_key, None)\n                changed = True\n    return changed\n'''
new_prune = '''def prune_state(state: dict[str, Any], today: datetime.date, keep_days: int = 14) -> bool:\n    """Prune dated report events/jobs while keeping group routing metadata."""\n    changed = False\n    events = state.get("events")\n    if not isinstance(events, dict):\n        events = {}\n        state["events"] = events\n        changed = True\n    changed = prune_gameplay_events(events, today, keep_days) or changed\n\n    jobs = state.get("jobs")\n    if not isinstance(jobs, dict):\n        jobs = {}\n        state["jobs"] = jobs\n        changed = True\n    cutoff = (today - datetime.timedelta(days=max(2, int(keep_days)))).isoformat()\n    for date_key in list(jobs):\n        if str(date_key) < cutoff:\n            jobs.pop(date_key, None)\n            changed = True\n    return changed\n'''
if old_prune not in core and "prune_gameplay_events(events" not in core:
    raise RuntimeError("daily_report_core prune block not found")
core = core.replace(old_prune, new_prune, 1)
core_path.write_text(core, encoding="utf-8")

# daily_report_feature: add a generic writer while retaining the old wrapper.
feature_path = ROOT / "daily_report_feature.py"
feature = feature_path.read_text(encoding="utf-8")
feature_anchor = '''    from daily_report_core import (\n        aggregate_daily_report,\n        due_datetime,\n        parse_report_time,\n        prune_state,\n    )\n\n\nclass DailyReportMixin:\n'''
feature_imports = '''    from daily_report_core import (\n        aggregate_daily_report,\n        due_datetime,\n        parse_report_time,\n        prune_state,\n    )\n\ntry:\n    from .gameplay_events import (\n        append_gameplay_event,\n        build_gameplay_event,\n        read_gameplay_events,\n    )\nexcept ImportError:  # pragma: no cover - direct module loading compatibility\n    from gameplay_events import (\n        append_gameplay_event,\n        build_gameplay_event,\n        read_gameplay_events,\n    )\n\n\nclass DailyReportMixin:\n'''
if "append_gameplay_event" not in feature:
    if feature_anchor not in feature:
        raise RuntimeError("daily_report_feature import anchor not found")
    feature = feature.replace(feature_anchor, feature_imports, 1)

start = feature.find("    def _record_daily_report_event(\n")
end = feature.find("    def _profile_for_report(\n", start)
if start < 0 or end < 0:
    raise RuntimeError("daily_report event method block not found")
replacement = '''    def _record_gameplay_event(\n        self,\n        group_id: str,\n        kind: str,\n        *,\n        actor_id: str = "",\n        target_id: str = "",\n        victim_id: str = "",\n        pig_id: str = "",\n        metadata: dict[str, Any] | None = None,\n        draw_date: str | None = None,\n        event_id: str = "",\n    ) -> bool:\n        """Write one shared gameplay event without changing core domain state."""\n        if not group_id:\n            return False\n        date_key = draw_date or self._today().isoformat()\n        payload = build_gameplay_event(\n            kind,\n            actor_id=actor_id,\n            target_id=target_id,\n            victim_id=victim_id,\n            pig_id=pig_id,\n            metadata=metadata,\n            event_id=event_id,\n            at=int(time.time()),\n        )\n        with self._data_lock:\n            events = self.daily_report_state.setdefault("events", {})\n            if not isinstance(events, dict):\n                events = {}\n                self.daily_report_state["events"] = events\n            if not append_gameplay_event(\n                events, date_key, str(group_id), payload, max_events=2000\n            ):\n                return False\n            prune_state(\n                self.daily_report_state,\n                self._today(),\n                self.DAILY_REPORT_STATE_KEEP_DAYS,\n            )\n            self._save_daily_report_state_locked()\n        return True\n\n    def _record_daily_report_event(\n        self,\n        group_id: str,\n        kind: str,\n        *,\n        actor_id: str = "",\n        target_id: str = "",\n        victim_id: str = "",\n        draw_date: str | None = None,\n        event_id: str = "",\n    ) -> None:\n        """Compatibility wrapper preserving PR #51 report-enable semantics."""\n        if not self.enable_daily_report or not group_id:\n            return\n        self._record_gameplay_event(\n            group_id,\n            kind,\n            actor_id=actor_id,\n            target_id=target_id,\n            victim_id=victim_id,\n            draw_date=draw_date,\n            event_id=event_id,\n        )\n\n    def _report_events(self, group_id: str, draw_date: str) -> list[dict[str, Any]]:\n        with self._data_lock:\n            events = self.daily_report_state.get("events", {})\n            return read_gameplay_events(events, draw_date, group_id)\n\n'''
feature = feature[:start] + replacement + feature[end:]
feature_path.write_text(feature, encoding="utf-8")

# CI should compile the new module explicitly.
ci_path = ROOT / ".github/workflows/ci.yml"
ci = ci_path.read_text(encoding="utf-8")
old_compile = "main.py legacy_main.py daily_report_core.py daily_report_feature.py rollpig_core.py"
new_compile = "main.py legacy_main.py daily_report_core.py daily_report_feature.py gameplay_events.py rollpig_core.py"
if old_compile not in ci and new_compile not in ci:
    raise RuntimeError("CI compile anchor not found")
ci = ci.replace(old_compile, new_compile, 1)
ci_path.write_text(ci, encoding="utf-8")

# Keep an explicit unreleased architecture note without rewriting release history.
changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
note = '''# 更新\n\n## 未發佈\n\n### 架構\n\n- 新增共用 `gameplay_events.py` Gameplay Event v1 契約；PR #51 的日報事件保持原 JSON 相容，並改由共用寫入／去重／讀取／裁剪函式管理。\n- `DailyReportMixin` 增加 `_record_gameplay_event()` 作為後續 EX 成長、預約烤豬與烤箱補貨的統一事件入口；原 `_record_daily_report_event()` 開關語義保持不變。\n- 新增 `docs/ARCHITECTURE.md`，記錄漸進式拆分與事件持久化邊界。\n\n'''
if "Gameplay Event v1" not in changelog:
    if not changelog.startswith("# 更新\n"):
        raise RuntimeError("CHANGELOG header not found")
    changelog = note + changelog[len("# 更新\n\n"):]
changelog_path.write_text(changelog, encoding="utf-8")
