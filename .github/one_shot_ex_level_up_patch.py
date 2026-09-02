from pathlib import Path


def read_lines(path: str) -> list[str]:
    return Path(path).read_text(encoding="utf-8").splitlines()


def write_lines(path: str, lines: list[str]) -> None:
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def locate(
    lines: list[str], value: str, *, start: int = 0, end: int | None = None
) -> int:
    stop = len(lines) if end is None else end
    matches = [index for index in range(start, stop) if lines[index] == value]
    if len(matches) != 1:
        raise SystemExit(
            f"expected one line {value!r} in [{start}, {stop}), found {matches}"
        )
    return matches[0]


def append_block(path: str, marker: str, block: str) -> None:
    text = Path(path).read_text(encoding="utf-8")
    if marker in text:
        return
    Path(path).write_text(
        text.rstrip() + "\n\n\n" + block.strip() + "\n",
        encoding="utf-8",
    )


path = "gameplay_events.py"
lines = read_lines(path)
idx = locate(lines, "    max_events: int = 2000,")
lines.insert(idx + 1, "    dedupe_across_scopes: bool = False,")
idx = locate(
    lines,
    '    """Append one event idempotently to the existing date/group bucket."""',
)
lines[idx] = '    """Append one event idempotently to one scope or the whole date."""'
start = locate(lines, "    payload = dict(event)")
finish = locate(lines, "        return False", start=start) + 1
lines[start:finish] = """    payload = dict(event)
    event_id = str(payload.get("id") or "")
    buckets = (
        (bucket for bucket in by_date.values() if isinstance(bucket, list))
        if dedupe_across_scopes
        else (rows,)
    )
    if event_id and any(
        isinstance(item, dict) and str(item.get("id") or "") == event_id
        for bucket in buckets
        for item in bucket
    ):
        return False""".splitlines()
write_lines(path, lines)

path = "daily_report_feature.py"
lines = read_lines(path)
fn = locate(lines, "    def _record_gameplay_event(")
event_id_line = locate(lines, '        event_id: str = "",', start=fn, end=fn + 30)
lines.insert(event_id_line + 1, "        dedupe_across_scopes: bool = False,")
call = locate(
    lines,
    "            if not append_gameplay_event(",
    start=fn,
    end=fn + 70,
)
lines[call : call + 3] = """            if not append_gameplay_event(
                events,
                date_key,
                str(group_id),
                payload,
                max_events=2000,
                dedupe_across_scopes=dedupe_across_scopes,
            ):""".splitlines()
write_lines(path, lines)

path = "ex_variant_feature.py"
lines = read_lines(path)
start = locate(lines, "    def _maybe_record_ex_level_event(")
finish = locate(lines, "    async def send_rendered_pig(", start=start)
replacement = """    @staticmethod
    def _ex_level_up_notice(ex_level: int) -> str:
        return (
            f"✨ 重逢第 {ex_level + 1} 次 · "
            f"EX Lv.{ex_level - 1} → Lv.{ex_level}"
        )

    def _maybe_record_ex_level_event(
        self, event, pig: dict | None, user_id: str, fallback_title: str
    ) -> str:
        """Claim today's duplicate growth and return its one-time notice."""
        target_user_id = str(user_id or "")
        if (
            fallback_title != "今日小猪"
            or not target_user_id
            or not isinstance(pig, dict)
        ):
            return ""
        try:
            sender_id = str(self._event_sender_id(event))
            group_id = str(self._event_group_id(event) or "")
        except Exception:
            return ""
        if sender_id != target_user_id:
            return ""
        pig_id = str(pig.get("id") or "")
        if not pig_id:
            return ""
        ex_level = self._ex_level_for_user(target_user_id, pig_id)
        if ex_level <= 0:
            return ""
        today = self._today().isoformat()
        user = self._get_user_collection(target_user_id)
        pigs = user.get("pigs", {}) if isinstance(user, dict) else {}
        record = pigs.get(pig_id, {}) if isinstance(pigs, dict) else {}
        if str(record.get("last_drawn") or "") != today:
            return ""
        writer = getattr(self, "_record_gameplay_event", None)
        if not callable(writer):
            return ""
        event_scope = group_id or f"private:{target_user_id}"
        try:
            created = bool(
                writer(
                    event_scope,
                    EVENT_EX_LEVEL_UP,
                    actor_id=target_user_id,
                    pig_id=pig_id,
                    metadata={"from": ex_level - 1, "to": ex_level},
                    draw_date=today,
                    event_id=f"ex:{today}:{target_user_id}:{pig_id}:{ex_level}",
                    dedupe_across_scopes=True,
                )
            )
        except Exception as exc:
            logger.warning(f"EX 升级事件记录失败，已跳过一次性提示：{exc}")
            return ""
        if not created:
            return ""
        return self._ex_level_up_notice(ex_level)

""".splitlines()
lines[start:finish] = replacement
call = locate(
    lines,
    "        self._maybe_record_ex_level_event(event, display, str(user_id), fallback_title)",
)
lines[call : call + 1] = """        level_up_notice = self._maybe_record_ex_level_event(
            event, display, str(user_id), fallback_title
        )
        if level_up_notice:
            intro = f"{intro}\\n{level_up_notice}" if intro else level_up_notice""".splitlines()
write_lines(path, lines)

path = "tests/test_ex_growth_e2e.py"
lines = read_lines(path)
idx = locate(lines, "        self.sent_cards: list[dict] = []")
lines.insert(idx + 1, "        self.sent_intros: list[str] = []")
idx = locate(lines, "        del event, user_id, intro, fallback_title")
lines[idx] = "        del event, user_id, fallback_title"
idx = locate(lines, "        self.sent_cards.append(payload)")
lines.insert(idx + 1, "        self.sent_intros.append(intro)")

fn = locate(lines, "    def _record_gameplay_event(")
event_id_line = locate(lines, '        event_id: str = "",', start=fn, end=fn + 30)
lines.insert(event_id_line + 1, "        dedupe_across_scopes: bool = False,")
payload_line = locate(lines, "            payload,", start=fn, end=fn + 60)
lines.insert(
    payload_line + 1,
    "            dedupe_across_scopes=dedupe_across_scopes,",
)

test_start = locate(
    lines,
    "def test_today_records_one_ex_event_but_tomorrow_preview_never_leaks_owned_growth(tmp_path):",
)
description_line = locate(
    lines,
    '    assert today_card["description"] == "EX1 描述"',
    start=test_start,
    end=test_start + 50,
)
lines[description_line + 1 : description_line + 1] = """    assert harness.sent_intros[-1] == (
        ". 这是你的今日小猪：\\n"
        "✨ 重逢第 2 次 · EX Lv.0 → Lv.1"
    )""".splitlines()

rows_line = locate(
    lines,
    "    rows = read_gameplay_events(",
    start=test_start,
    end=test_start + 90,
)
lines[rows_line:rows_line] = """    assert harness.sent_intros[-1] == ". 这是你的今日小猪："

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

""".splitlines()
write_lines(path, lines)

append_block(
    "tests/test_ex_growth_e2e.py",
    "def test_private_level_up_notice_uses_isolated_scope_and_stays_one_time",
    """
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
""",
)

append_block(
    "tests/test_gameplay_events.py",
    "def test_append_can_dedupe_event_id_across_scopes",
    """
def test_append_can_dedupe_event_id_across_scopes():
    event = build_gameplay_event(EVENT_EX_LEVEL_UP, event_id="global", at=1)

    default_state: dict[str, object] = {}
    assert append_gameplay_event(default_state, "2026-08-14", "g1", event)
    assert append_gameplay_event(default_state, "2026-08-14", "g2", event)

    global_state: dict[str, object] = {}
    assert append_gameplay_event(
        global_state,
        "2026-08-14",
        "g1",
        event,
        dedupe_across_scopes=True,
    )
    assert not append_gameplay_event(
        global_state,
        "2026-08-14",
        "private:u1",
        event,
        dedupe_across_scopes=True,
    )
    assert not read_gameplay_events(global_state, "2026-08-14", "private:u1")
""",
)

path = "docs/EX-VARIANTS.md"
lines = read_lines(path)
idx = locate(
    lines,
    "玩家當天真正完成重複抽取並形成 EX 成長時，可記錄 Gameplay Event v1 `ex_level_up`。事件 ID 必須可確定性去重，同一天重複查看今日結果不能再次記錄升級。",
)
lines[idx] = (
    "玩家當天真正完成重複抽取並形成 EX 成長時，首次成功寫入 Gameplay Event v1 "
    "`ex_level_up` 會在今日小豬圖片前顯示一次 `✨ 重逢第 N 次 · EX Lv.a → Lv.b`。"
    "事件 ID 會跨群聊與私聊作用域確定性去重，因此同一天換群或重複查看不能再次顯示；"
    "私聊事件只保存到 `private:<user-id>` 作用域，不會混入任何群組日報。事件寫入失敗、"
    "首次解鎖、查看他人、過期抽取與明日預測均不顯示升級提示。"
)
write_lines(path, lines)

path = "CHANGELOG.md"
lines = read_lines(path)
idx = locate(lines, "## 未發佈")
entry = (
    "- 今日小豬新增一次性 EX 成長提示：真正重複抽中時顯示 `✨ 重逢第 N 次 · EX Lv.a → Lv.b`，"
    "沿用 `ex_level_up` Gameplay Event 作為持久化去重憑證；同日跨群／私聊重看不重播，"
    "私聊作用域不污染群組日報，EX5 以上仍顯示真實未封頂等級，事件寫入失敗則安全降級為只發卡。"
)
lines[idx + 2 : idx + 2] = [entry, ""]
write_lines(path, lines)
