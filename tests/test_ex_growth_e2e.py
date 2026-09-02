from __future__ import annotations

import asyncio
import datetime
import json
import sys
import types
from pathlib import Path

try:  # CI/unit tests do not require a full AstrBot runtime.
    import astrbot.api  # type: ignore  # noqa: F401
except ModuleNotFoundError:
    astrbot_module = types.ModuleType("astrbot")
    api_module = types.ModuleType("astrbot.api")
    api_module.logger = types.SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
    )
    astrbot_module.api = api_module
    sys.modules.setdefault("astrbot", astrbot_module)
    sys.modules.setdefault("astrbot.api", api_module)

from ex_variant_feature import ExVariantMixin
from gameplay_events import (
    EVENT_EX_LEVEL_UP,
    append_gameplay_event,
    build_gameplay_event,
    read_gameplay_events,
)


BASE_PIG = {
    "id": "sleep-pig",
    "name": "睡觉猪",
    "description": "基础描述",
    "analysis": "基础旁白",
}


class _BaseHarness:
    IMAGE_EXTENSIONS = ("png", "gif")

    def __init__(self, context, config):
        del context
        self.res_dir = Path(config["res_dir"])
        self.resource_active_dir = Path(config["resource_active_dir"])
        self.local_overrides_path = Path(config["local_overrides_path"])
        self.pig_list = [dict(BASE_PIG)]
        self.collections = config["collections"]
        self.gameplay_events: dict[str, object] = {}
        self.sent_cards: list[dict] = []
        self.sent_intros: list[str] = []
        self.last_roast_pig: dict | None = None
        self.fixed_today = datetime.date(2026, 8, 15)

    def _runtime_document(self, key, path, default):
        del key
        path = Path(path)
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _get_user_collection(self, user_id: str):
        return self.collections.get(str(user_id), {})

    def _find_catalog_pig(self, pig_id: str):
        return next(
            (dict(item) for item in self.pig_list if item.get("id") == str(pig_id)),
            None,
        )

    def _get_daily_pig(self, user_id, date_value):
        del user_id, date_value
        return dict(BASE_PIG)

    def _get_weekly_pig(self, user_id, date_value):
        del user_id, date_value
        return dict(BASE_PIG), False

    async def send_rendered_pig(
        self,
        event,
        pig_data: dict,
        user_id: str,
        intro: str = ". 这是你的今日小猪：",
        fallback_title: str = "今日小猪",
    ):
        del event, user_id, fallback_title
        payload = dict(pig_data)
        self.sent_cards.append(payload)
        self.sent_intros.append(intro)
        return payload

    def render_roast_image(
        self,
        pig: dict,
        user_id: str,
        ai_copy: str | None = None,
        local_copy: dict[str, str] | None = None,
    ) -> Path:
        del user_id, ai_copy, local_copy
        self.last_roast_pig = dict(pig)
        return Path("roast.png")

    def _event_sender_id(self, event):
        return event.sender_id

    def _event_group_id(self, event):
        return event.group_id

    def _today(self):
        return self.fixed_today

    def _record_gameplay_event(
        self,
        group_id: str,
        kind: str,
        *,
        actor_id: str = "",
        target_id: str = "",
        victim_id: str = "",
        pig_id: str = "",
        metadata=None,
        draw_date: str = "",
        event_id: str = "",
        dedupe_across_scopes: bool = False,
        **kwargs,
    ):
        del kwargs
        payload = build_gameplay_event(
            kind,
            actor_id=actor_id,
            target_id=target_id,
            victim_id=victim_id,
            pig_id=pig_id,
            metadata=metadata,
            event_id=event_id,
            at=1,
        )
        return append_gameplay_event(
            self.gameplay_events,
            draw_date or self._today().isoformat(),
            group_id,
            payload,
            dedupe_across_scopes=dedupe_across_scopes,
        )


class _Harness(ExVariantMixin, _BaseHarness):
    pass


def _write_variant_source(
    root: Path,
    *,
    description: str = "EX1 描述",
    include_images: bool = True,
) -> None:
    image_root = root / "ex_variants"
    image_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "pigs": {
            "sleep-pig": {
                "1": {"description": description},
                "2": {"image": "sleep-pig-ex2.png"},
                "4": {"analysis": "EX4 旁白"},
                "5": {"image": "sleep-pig-ex5.gif"},
            }
        },
    }
    (root / "pig_ex_variants.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    if include_images:
        (image_root / "sleep-pig-ex2.png").write_bytes(b"png")
        (image_root / "sleep-pig-ex5.gif").write_bytes(b"gif")


def _make_harness(tmp_path: Path, *, count: int = 1) -> _Harness:
    bundled = tmp_path / "bundled"
    active = tmp_path / "active"
    bundled.mkdir()
    active.mkdir()
    _write_variant_source(bundled)
    collections = {
        "u1": {
            "pigs": {
                "sleep-pig": {
                    "count": count,
                    "last_drawn": "2026-08-15",
                }
            }
        }
    }
    return _Harness(
        None,
        {
            "res_dir": bundled,
            "resource_active_dir": active,
            "local_overrides_path": tmp_path / "local_overrides.json",
            "collections": collections,
        },
    )


def _set_count(harness: _Harness, count: int) -> None:
    harness.collections["u1"]["pigs"]["sleep-pig"]["count"] = count


def test_owned_growth_flows_through_daily_history_weekly_roast_and_images(tmp_path):
    harness = _make_harness(tmp_path, count=1)
    assert harness._ex_variant_source == "bundled"

    first = harness._get_daily_pig("u1", harness._today())
    assert first["_ex_level"] == 0
    assert first["description"] == "基础描述"
    assert "_ex_image" not in first

    _set_count(harness, 2)
    second = harness._get_daily_pig("u1", harness._today())
    assert second["_ex_level"] == 1
    assert second["description"] == "EX1 描述"

    historical = harness._get_daily_pig(
        "u1", harness._today() - datetime.timedelta(days=1)
    )
    assert historical["_ex_level"] == 1
    assert historical["description"] == "EX1 描述"

    weekly, eaten = harness._get_weekly_pig("u1", harness._today())
    assert not eaten
    assert weekly["_ex_level"] == 1
    assert weekly["description"] == "EX1 描述"

    _set_count(harness, 6)
    ex5 = harness._get_daily_pig("u1", harness._today())
    assert ex5["_ex_level"] == 5
    assert ex5["_ex_variant_level"] == 5
    assert ex5["description"] == "EX1 描述"
    assert ex5["analysis"] == "EX4 旁白"
    assert ex5["_ex_image"] == "sleep-pig-ex5.gif"
    assert harness._ex_variant_image_path("sleep-pig", 5).name == "sleep-pig-ex5.gif"

    _set_count(harness, 10)
    ex9 = harness._get_daily_pig("u1", harness._today())
    assert ex9["_ex_level"] == 9
    assert ex9["_ex_variant_level"] == 5
    assert ex9["_ex_image"] == "sleep-pig-ex5.gif"
    assert ex9["analysis"] == "EX4 旁白"
    assert harness._ex_variant_image_path("sleep-pig", 9).name == "sleep-pig-ex5.gif"

    harness.render_roast_image(BASE_PIG, "u1")
    assert harness.last_roast_pig is not None
    assert harness.last_roast_pig["_ex_level"] == 9
    assert harness.last_roast_pig["_ex_image"] == "sleep-pig-ex5.gif"


def test_today_records_one_ex_event_but_tomorrow_preview_never_leaks_owned_growth(tmp_path):
    harness = _make_harness(tmp_path, count=2)
    event = types.SimpleNamespace(sender_id="u1", group_id="g1")

    today_card = asyncio.run(
        harness.send_rendered_pig(
            event,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert today_card["_ex_level"] == 1
    assert today_card["description"] == "EX1 描述"
    assert harness.sent_intros[-1] == (
        ". 这是你的今日小猪：\n"
        "✨ 重逢第 2 次 · EX Lv.0 → Lv.1"
    )

    asyncio.run(
        harness.send_rendered_pig(
            event,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1] == ". 这是你的今日小猪："

    another_group = types.SimpleNamespace(sender_id="u1", group_id="g2")
    asyncio.run(
        harness.send_rendered_pig(
            another_group,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1] == ". 这是你的今日小猪："
    assert not read_gameplay_events(
        harness.gameplay_events, harness._today().isoformat(), "g2"
    )

    rows = read_gameplay_events(
        harness.gameplay_events, harness._today().isoformat(), "g1"
    )
    assert len(rows) == 1
    assert rows[0]["kind"] == EVENT_EX_LEVEL_UP
    assert rows[0]["pig_id"] == "sleep-pig"
    assert rows[0]["metadata"] == {"from": 0, "to": 1}
    assert rows[0]["id"] == "ex:2026-08-15:u1:sleep-pig:1"

    _set_count(harness, 10)
    tomorrow_card = asyncio.run(
        harness.send_rendered_pig(
            event,
            BASE_PIG,
            "u1",
            fallback_title="明日小猪预测",
        )
    )
    assert tomorrow_card["description"] == "基础描述"
    assert tomorrow_card["analysis"] == "基础旁白"
    assert "_ex_level" not in tomorrow_card
    assert "_ex_image" not in tomorrow_card


def test_local_override_blocks_remote_ex_but_keeps_numeric_growth(tmp_path):
    harness = _make_harness(tmp_path, count=6)
    harness.local_overrides_path.write_text(
        json.dumps(
            [{"id": "sleep-pig", "description": "管理员本地版本"}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    decorated = harness._decorate_ex_variant(BASE_PIG, "u1")
    assert decorated["_ex_level"] == 5
    assert decorated["description"] == "基础描述"
    assert decorated["analysis"] == "基础旁白"
    assert "_ex_image" not in decorated
    assert harness._ex_variant_image_path("sleep-pig", 5) is None


def test_cloud_source_wins_and_invalid_cloud_falls_back_to_bundled(tmp_path):
    harness = _make_harness(tmp_path, count=2)
    _write_variant_source(harness.resource_active_dir, description="云端 EX1")
    harness._reload_ex_variants()
    assert harness._ex_variant_source == "cloud"
    assert harness._get_daily_pig("u1", harness._today())["description"] == "云端 EX1"

    # A broken active snapshot must not poison gameplay; bundled remains usable.
    (harness.resource_active_dir / "ex_variants" / "sleep-pig-ex5.gif").unlink()
    harness._reload_ex_variants()
    assert harness._ex_variant_source == "bundled"
    assert harness._get_daily_pig("u1", harness._today())["description"] == "EX1 描述"


def test_private_level_up_notice_uses_isolated_scope_and_stays_one_time(tmp_path):
    harness = _make_harness(tmp_path, count=4)
    private_event = types.SimpleNamespace(sender_id="u1", group_id="")

    asyncio.run(
        harness.send_rendered_pig(
            private_event,
            BASE_PIG,
            "u1",
            intro="今天抽到：",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1] == (
        "今天抽到：\n✨ 重逢第 4 次 · EX Lv.2 → Lv.3"
    )
    private_rows = read_gameplay_events(
        harness.gameplay_events,
        harness._today().isoformat(),
        "private:u1",
    )
    assert len(private_rows) == 1
    assert private_rows[0]["metadata"] == {"from": 2, "to": 3}

    group_event = types.SimpleNamespace(sender_id="u1", group_id="g1")
    asyncio.run(
        harness.send_rendered_pig(
            group_event,
            BASE_PIG,
            "u1",
            intro="今天抽到：",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1] == "今天抽到："
    assert not read_gameplay_events(
        harness.gameplay_events, harness._today().isoformat(), "g1"
    )


def test_level_up_notice_uses_uncapped_level_and_writer_failure_is_safe(tmp_path):
    success_root = tmp_path / "success"
    success_root.mkdir()
    harness = _make_harness(success_root, count=10)
    event = types.SimpleNamespace(sender_id="u1", group_id="g1")

    asyncio.run(
        harness.send_rendered_pig(
            event,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1].endswith(
        "✨ 重逢第 10 次 · EX Lv.8 → Lv.9"
    )

    failure_root = tmp_path / "failure"
    failure_root.mkdir()
    failure = _make_harness(failure_root, count=2)

    def broken_writer(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("disk unavailable")

    failure._record_gameplay_event = broken_writer
    card = asyncio.run(
        failure.send_rendered_pig(
            event,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert card["_ex_level"] == 1
    assert failure.sent_intros[-1] == ". 这是你的今日小猪："
    assert failure.gameplay_events == {}


def test_level_up_notice_skips_unlock_other_user_and_stale_draw(tmp_path):
    harness = _make_harness(tmp_path, count=1)
    own_event = types.SimpleNamespace(sender_id="u1", group_id="g1")

    asyncio.run(
        harness.send_rendered_pig(
            own_event,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1] == ". 这是你的今日小猪："
    assert harness.gameplay_events == {}

    _set_count(harness, 4)
    other_event = types.SimpleNamespace(sender_id="viewer", group_id="g1")
    asyncio.run(
        harness.send_rendered_pig(
            other_event,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1] == ". 这是你的今日小猪："
    assert harness.gameplay_events == {}

    harness.collections["u1"]["pigs"]["sleep-pig"]["last_drawn"] = "2026-08-14"
    asyncio.run(
        harness.send_rendered_pig(
            own_event,
            BASE_PIG,
            "u1",
            fallback_title="今日小猪",
        )
    )
    assert harness.sent_intros[-1] == ". 这是你的今日小猪："
    assert harness.gameplay_events == {}
