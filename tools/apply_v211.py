from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


base = read("storage/base.py")
base = replace_once(
    base,
    "    supports_domain_reads = False\n",
    "    supports_domain_reads = False\n    supports_domain_writes = False\n",
    "base write capability",
)
base = replace_once(
    base,
    "    # Transitional domain read API. JSONStorage keeps using the in-memory\n",
    '''    # SQL-primary domain write API. JSONStorage deliberately does not implement\n    # these methods; callers retain the legacy JSON path when capability is false.\n    def create_daily_draw(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n    def replace_daily_pig_with_eaten(self, **kwargs: Any) -> dict[str, Any]:\n        raise NotImplementedError\n\n    # Transitional domain read API. JSONStorage keeps using the in-memory\n''',
    "base domain methods",
)
write("storage/base.py", base)

sqlite = read("storage/sqlite_storage.py")
sqlite = sqlite.replace(
    '''    v2.9 keeps the existing document model as the compatibility source of truth.\n    Projection tables are rebuilt transactionally from the real v2.8 document\n    shapes so later releases can move hot reads to SQL without a flag day.\n''',
    '''    v2.11 makes normalized tables authoritative for daily draws and eat events.\n    Compatibility documents remain transactionally synchronized only for export,\n    rollback and older code paths; these hot writes no longer rebuild whole tables.\n''',
)
sqlite = replace_once(
    sqlite,
    "    supports_domain_reads = True\n",
    "    supports_domain_reads = True\n    supports_domain_writes = True\n",
    "sqlite write capability",
)
anchor = '''    @staticmethod\n    def _expected_projection_counts(documents: dict[str, Any]) -> dict[str, int]:\n'''
methods = r'''    def _read_document_tx(
        self, connection: sqlite3.Connection, key: str, default: Any
    ) -> Any:
        row = connection.execute(
            "SELECT payload FROM documents WHERE key = ?", (str(key),)
        ).fetchone()
        return self._decode(str(row["payload"])) if row else self._clone(default)

    def _write_document_tx(
        self,
        connection: sqlite3.Connection,
        key: str,
        value: Any,
        *,
        updated_at: int | None = None,
    ) -> None:
        payload, digest = self._encode(value)
        connection.execute(
            """
            INSERT INTO documents(key, payload, payload_sha256, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                payload = excluded.payload,
                payload_sha256 = excluded.payload_sha256,
                updated_at = excluded.updated_at
            """,
            (str(key), payload, digest, int(updated_at or time.time())),
        )

    @staticmethod
    def _ordered_candidates(
        user_id: str, user_candidates: tuple[str, ...]
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item
                for item in (str(user_id), *(str(x) for x in user_candidates))
                if item
            )
        )

    @staticmethod
    def _event_key(event_date: str, group_id: str, user_id: str) -> str:
        return json.dumps(
            [str(event_date), str(group_id), str(user_id)], ensure_ascii=False
        )

    @staticmethod
    def _valid_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def create_daily_draw(
        self,
        *,
        draw_date: str,
        user_id: str,
        user_candidates: tuple[str, ...] = (),
        pig: dict[str, Any] | None = None,
        group_id: str = "",
        penalty_should_fail: bool = False,
    ) -> dict[str, Any]:
        """Create one daily draw with SQL uniqueness and synchronized export docs.

        A probe call with ``pig=None`` returns an existing draw, consumes/blocks a
        due penalty, or returns ``needs-pig``. The caller can then choose a pig and
        retry; a competing process that wins between the two calls is returned as
        ``existing`` instead of creating a second result.
        """
        draw_date = str(draw_date)
        canonical_id = str(user_id)
        candidates = self._ordered_candidates(canonical_id, user_candidates)
        now = int(time.time())
        history_default = {
            "version": 1,
            "users": {},
            "daily": {},
            "pig_snapshots": {},
        }
        roast_default = {
            "version": 1,
            "cooldowns": {},
            "daily_backdoors": {},
            "daily_roast_counts": {},
            "eaten_penalties": {},
            "eaten_events": {},
        }
        today_default = {"date": draw_date, "records": {}}

        with self.transaction() as connection:
            history = self._valid_dict(
                self._read_document_tx(connection, "pig_history.json", history_default)
            )
            roast = self._valid_dict(
                self._read_document_tx(connection, "roast_state.json", roast_default)
            )
            today_doc = self._valid_dict(
                self._read_document_tx(connection, "rollpig_today.json", today_default)
            )

            existing = None
            for candidate in candidates:
                existing = connection.execute(
                    "SELECT user_id, pig_id, original_pig_id FROM daily_draws "
                    "WHERE draw_date = ? AND user_id = ?",
                    (draw_date, candidate),
                ).fetchone()
                if existing:
                    break
            if existing:
                actual_id = str(existing["user_id"])
                pig_id = str(existing["pig_id"])
                if group_id:
                    connection.execute(
                        "INSERT OR IGNORE INTO daily_draw_groups VALUES (?, ?, ?)",
                        (draw_date, actual_id, str(group_id)),
                    )
                    groups = [
                        str(row[0])
                        for row in connection.execute(
                            "SELECT group_id FROM daily_draw_groups "
                            "WHERE draw_date = ? AND user_id = ? ORDER BY group_id",
                            (draw_date, actual_id),
                        ).fetchall()
                    ]
                    connection.execute(
                        "UPDATE daily_draws SET group_ids_json = ? "
                        "WHERE draw_date = ? AND user_id = ?",
                        (json.dumps(groups, ensure_ascii=False), draw_date, actual_id),
                    )
                    daily = history.setdefault("daily", {})
                    if not isinstance(daily, dict):
                        daily = {}
                        history["daily"] = daily
                    day = daily.setdefault(
                        draw_date,
                        {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
                    )
                    day_groups = day.setdefault("groups", {})
                    members = day_groups.setdefault(str(group_id), [])
                    if actual_id not in members:
                        members.append(actual_id)
                snapshot = connection.execute(
                    "SELECT payload_json FROM pig_snapshots WHERE pig_id = ?",
                    (pig_id,),
                ).fetchone()
                pig_payload = (
                    self._decode(str(snapshot["payload_json"]))
                    if snapshot
                    else {"id": pig_id}
                )
                if today_doc.get("date") != draw_date:
                    today_doc = {"date": draw_date, "records": {}}
                today_doc.setdefault("records", {})[actual_id] = pig_payload
                self._write_document_tx(
                    connection, "pig_history.json", history, updated_at=now
                )
                self._write_document_tx(
                    connection, "rollpig_today.json", today_doc, updated_at=now
                )
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES "
                    "('write_authority', 'sql-primary-v2.11') "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                )
                return {
                    "status": "existing",
                    "created": False,
                    "user_id": actual_id,
                    "pig_id": pig_id,
                    "pig": pig_payload,
                    "history": history,
                    "roast_state": roast,
                }

            penalty_row = None
            for candidate in candidates:
                penalty_row = connection.execute(
                    "SELECT user_id, due_date, failed FROM eaten_penalties "
                    "WHERE user_id = ?",
                    (candidate,),
                ).fetchone()
                if penalty_row:
                    break
            penalties_doc = roast.get("eaten_penalties")
            if not isinstance(penalties_doc, dict):
                penalties_doc = {}
                roast["eaten_penalties"] = penalties_doc
            roast_changed = False
            if penalty_row:
                penalty_user = str(penalty_row["user_id"])
                due_date = str(penalty_row["due_date"])
                failed = bool(penalty_row["failed"])
                if due_date < draw_date:
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )
                    penalties_doc.pop(penalty_user, None)
                    roast_changed = True
                elif due_date == draw_date and failed:
                    return {
                        "status": "penalty-blocked",
                        "created": False,
                        "history": history,
                        "roast_state": roast,
                    }
                elif due_date == draw_date and penalty_should_fail:
                    payload = {"due_date": draw_date, "failed": True}
                    connection.execute(
                        "UPDATE eaten_penalties SET failed = 1, payload_json = ? "
                        "WHERE user_id = ?",
                        (json.dumps(payload, ensure_ascii=False, sort_keys=True), penalty_user),
                    )
                    penalties_doc[penalty_user] = payload
                    self._write_document_tx(
                        connection, "roast_state.json", roast, updated_at=now
                    )
                    connection.execute(
                        "INSERT INTO projection_meta(key, value) VALUES "
                        "('write_authority', 'sql-primary-v2.11') "
                        "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                    )
                    return {
                        "status": "penalty-blocked",
                        "created": False,
                        "history": history,
                        "roast_state": roast,
                    }
                elif due_date == draw_date:
                    connection.execute(
                        "DELETE FROM eaten_penalties WHERE user_id = ?",
                        (penalty_user,),
                    )
                    penalties_doc.pop(penalty_user, None)
                    roast_changed = True

            if not isinstance(pig, dict) or not str(pig.get("id") or "").strip():
                if roast_changed:
                    self._write_document_tx(
                        connection, "roast_state.json", roast, updated_at=now
                    )
                connection.execute(
                    "INSERT INTO projection_meta(key, value) VALUES "
                    "('write_authority', 'sql-primary-v2.11') "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
                )
                return {
                    "status": "needs-pig",
                    "created": False,
                    "history": history,
                    "roast_state": roast,
                }

            pig_payload = self._clone(pig)
            pig_id = str(pig_payload["id"])
            self._remember_identity(connection, canonical_id)
            unlocked = (
                connection.execute(
                    "SELECT 1 FROM user_pigs WHERE user_id = ? AND pig_id = ?",
                    (canonical_id, pig_id),
                ).fetchone()
                is None
            )
            stats = connection.execute(
                "SELECT total_draws, active_days, duplicate_streak "
                "FROM user_stats WHERE user_id = ?",
                (canonical_id,),
            ).fetchone()
            total_draws = int(stats["total_draws"]) if stats else 0
            active_days = int(stats["active_days"]) if stats else 0
            duplicate_streak = int(stats["duplicate_streak"]) if stats else 0

            connection.execute(
                """
                INSERT INTO daily_draws(
                    draw_date, user_id, pig_id, original_pig_id, group_ids_json,
                    created_at, was_new_unlock
                ) VALUES (?, ?, ?, '', ?, ?, ?)
                """,
                (
                    draw_date,
                    canonical_id,
                    pig_id,
                    json.dumps([str(group_id)] if group_id else [], ensure_ascii=False),
                    now,
                    int(unlocked),
                ),
            )
            if group_id:
                connection.execute(
                    "INSERT INTO daily_draw_groups VALUES (?, ?, ?)",
                    (draw_date, canonical_id, str(group_id)),
                )
            connection.execute(
                """
                INSERT INTO user_pigs(
                    user_id, pig_id, first_unlocked, last_drawn, draw_count
                ) VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(user_id, pig_id) DO UPDATE SET
                    last_drawn = excluded.last_drawn,
                    draw_count = user_pigs.draw_count + 1
                """,
                (canonical_id, pig_id, draw_date, draw_date),
            )
            connection.execute(
                "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES (?, ?) "
                "ON CONFLICT(pig_id) DO UPDATE SET payload_json = excluded.payload_json",
                (
                    pig_id,
                    json.dumps(pig_payload, ensure_ascii=False, sort_keys=True),
                ),
            )

            users = history.get("users")
            if not isinstance(users, dict):
                users = {}
                history["users"] = users
            user_doc = users.setdefault(
                canonical_id, {"total_draws": 0, "active_days": 0, "pigs": {}}
            )
            pigs_doc = user_doc.get("pigs")
            if not isinstance(pigs_doc, dict):
                pigs_doc = {}
                user_doc["pigs"] = pigs_doc
            record_doc = pigs_doc.setdefault(
                pig_id,
                {
                    "first_unlocked": draw_date,
                    "last_drawn": draw_date,
                    "count": 0,
                },
            )
            record_doc["last_drawn"] = draw_date
            record_doc["count"] = int(record_doc.get("count", 0)) + 1
            user_doc["total_draws"] = total_draws + 1
            user_doc["active_days"] = active_days + 1
            user_doc["duplicate_streak"] = 0 if unlocked else duplicate_streak + 1

            daily = history.get("daily")
            if not isinstance(daily, dict):
                daily = {}
                history["daily"] = daily
            day = daily.setdefault(
                draw_date,
                {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
            )
            day.setdefault("users", []).append(canonical_id)
            day.setdefault("records", {})[canonical_id] = pig_id
            day["draws"] = int(day.get("draws", 0)) + 1
            if unlocked:
                day["new_unlocks"] = int(day.get("new_unlocks", 0)) + 1
            if group_id:
                members = day.setdefault("groups", {}).setdefault(str(group_id), [])
                if canonical_id not in members:
                    members.append(canonical_id)
            history.setdefault("pig_snapshots", {})[pig_id] = pig_payload

            connection.execute(
                """
                INSERT INTO user_stats(
                    user_id, total_draws, active_days, duplicate_streak, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_draws = excluded.total_draws,
                    active_days = excluded.active_days,
                    duplicate_streak = excluded.duplicate_streak,
                    payload_json = excluded.payload_json
                """,
                (
                    canonical_id,
                    total_draws + 1,
                    active_days + 1,
                    0 if unlocked else duplicate_streak + 1,
                    json.dumps(user_doc, ensure_ascii=False, sort_keys=True),
                ),
            )
            if today_doc.get("date") != draw_date:
                today_doc = {"date": draw_date, "records": {}}
            today_doc.setdefault("records", {})[canonical_id] = pig_payload

            self._write_document_tx(
                connection, "pig_history.json", history, updated_at=now
            )
            self._write_document_tx(
                connection, "rollpig_today.json", today_doc, updated_at=now
            )
            if roast_changed:
                self._write_document_tx(
                    connection, "roast_state.json", roast, updated_at=now
                )
            connection.execute(
                "INSERT INTO projection_meta(key, value) VALUES "
                "('write_authority', 'sql-primary-v2.11') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )
            return {
                "status": "created",
                "created": True,
                "user_id": canonical_id,
                "pig_id": pig_id,
                "pig": pig_payload,
                "was_new_unlock": unlocked,
                "history": history,
                "roast_state": roast,
            }

    def replace_daily_pig_with_eaten(
        self,
        *,
        draw_date: str,
        due_date: str,
        cutoff_date: str,
        user_id: str,
        user_candidates: tuple[str, ...] = (),
        group_id: str,
        actor_id: str,
        outcome: str,
        eaten_pig: dict[str, Any],
    ) -> dict[str, Any]:
        """Atomically replace a draw, create its penalty and record the event."""
        draw_date = str(draw_date)
        candidates = self._ordered_candidates(str(user_id), user_candidates)
        now = int(time.time())
        with self.transaction() as connection:
            row = None
            for candidate in candidates:
                row = connection.execute(
                    "SELECT user_id, pig_id, original_pig_id FROM daily_draws "
                    "WHERE draw_date = ? AND user_id = ?",
                    (draw_date, candidate),
                ).fetchone()
                if row:
                    break
            if not row:
                return {"status": "missing"}
            actual_id = str(row["user_id"])
            current_pig_id = str(row["pig_id"])
            if current_pig_id == "eaten":
                return {"status": "already-eaten", "user_id": actual_id}
            original_id = str(row["original_pig_id"] or current_pig_id)
            eaten_payload = self._clone(eaten_pig)
            eaten_payload["id"] = "eaten"

            connection.execute(
                "UPDATE daily_draws SET pig_id = 'eaten', original_pig_id = ? "
                "WHERE draw_date = ? AND user_id = ?",
                (original_id, draw_date, actual_id),
            )
            connection.execute(
                "INSERT INTO pig_snapshots(pig_id, payload_json) VALUES ('eaten', ?) "
                "ON CONFLICT(pig_id) DO UPDATE SET payload_json = excluded.payload_json",
                (json.dumps(eaten_payload, ensure_ascii=False, sort_keys=True),),
            )
            self._remember_identity(connection, actual_id)
            self._remember_identity(connection, str(actor_id))
            penalty_payload = {"due_date": str(due_date), "failed": False}
            connection.execute(
                """
                INSERT INTO eaten_penalties(user_id, due_date, failed, payload_json)
                VALUES (?, ?, 0, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    due_date = excluded.due_date,
                    failed = 0,
                    payload_json = excluded.payload_json
                """,
                (
                    actual_id,
                    str(due_date),
                    json.dumps(penalty_payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            event_key = self._event_key(draw_date, group_id, actual_id)
            event_payload = {
                "actor_id": str(actor_id),
                "outcome": str(outcome),
                "at": now,
            }
            connection.execute(
                """
                INSERT INTO eaten_events(
                    event_key, event_date, group_id, user_id, actor_id,
                    outcome, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_key) DO UPDATE SET
                    actor_id = excluded.actor_id,
                    outcome = excluded.outcome,
                    created_at = excluded.created_at,
                    payload_json = excluded.payload_json
                """,
                (
                    event_key,
                    draw_date,
                    str(group_id),
                    actual_id,
                    str(actor_id),
                    str(outcome),
                    now,
                    json.dumps(event_payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            connection.execute(
                "DELETE FROM eaten_events WHERE event_date < ?", (str(cutoff_date),)
            )
            connection.execute(
                "DELETE FROM eaten_penalties WHERE due_date < ?", (draw_date,)
            )

            history = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "pig_history.json",
                    {"version": 1, "users": {}, "daily": {}, "pig_snapshots": {}},
                )
            )
            roast = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "roast_state.json",
                    {
                        "version": 1,
                        "cooldowns": {},
                        "daily_backdoors": {},
                        "daily_roast_counts": {},
                        "eaten_penalties": {},
                        "eaten_events": {},
                    },
                )
            )
            today_doc = self._valid_dict(
                self._read_document_tx(
                    connection,
                    "rollpig_today.json",
                    {"date": draw_date, "records": {}},
                )
            )
            if today_doc.get("date") != draw_date:
                today_doc = {"date": draw_date, "records": {}}
            today_doc.setdefault("records", {})[actual_id] = eaten_payload

            daily = history.setdefault("daily", {})
            day = daily.setdefault(
                draw_date,
                {"draws": 0, "new_unlocks": 0, "users": [], "records": {}},
            )
            day.setdefault("records", {})[actual_id] = "eaten"
            day.setdefault("eaten_originals", {}).setdefault(actual_id, original_id)
            history.setdefault("pig_snapshots", {})["eaten"] = eaten_payload

            penalties_doc = roast.get("eaten_penalties")
            if not isinstance(penalties_doc, dict):
                penalties_doc = {}
                roast["eaten_penalties"] = penalties_doc
            penalties_doc[actual_id] = penalty_payload
            roast["eaten_penalties"] = {
                key: value
                for key, value in penalties_doc.items()
                if isinstance(value, dict)
                and str(value.get("due_date") or "") >= draw_date
            }
            events_doc = roast.get("eaten_events")
            if not isinstance(events_doc, dict):
                events_doc = {}
                roast["eaten_events"] = events_doc
            events_doc[event_key] = event_payload
            roast["eaten_events"] = {
                key: value
                for key, value in events_doc.items()
                if isinstance(value, dict)
                and (
                    (lambda parsed: isinstance(parsed, list) and len(parsed) == 3 and str(parsed[0]) >= str(cutoff_date))(
                        json.loads(key)
                    )
                    if isinstance(key, str)
                    else False
                )
            }

            self._write_document_tx(
                connection, "pig_history.json", history, updated_at=now
            )
            self._write_document_tx(
                connection, "roast_state.json", roast, updated_at=now
            )
            self._write_document_tx(
                connection, "rollpig_today.json", today_doc, updated_at=now
            )
            connection.execute(
                "INSERT INTO projection_meta(key, value) VALUES "
                "('write_authority', 'sql-primary-v2.11') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
            )
            return {
                "status": "updated",
                "user_id": actual_id,
                "previous_pig_id": current_pig_id,
                "original_pig_id": original_id,
                "history": history,
                "roast_state": roast,
            }

'''
sqlite = replace_once(sqlite, anchor, methods + anchor, "sqlite domain writes")
write("storage/sqlite_storage.py", sqlite)

main = read("main.py").replace("2.10.1", "2.11.0")
helper_anchor = '''    def _replace_today_with_eaten(\n        self, user_id: str, group_id: str, actor_id: str, outcome: str\n    ) -> dict | None:\n'''
helper = r'''    def _apply_domain_write_result(self, result: dict) -> None:
        history = result.get("history") if isinstance(result, dict) else None
        roast_state = result.get("roast_state") if isinstance(result, dict) else None
        if isinstance(history, dict):
            self.history = history
        if isinstance(roast_state, dict):
            self.roast_state = roast_state

    async def _replace_today_with_eaten_persisted(
        self, user_id: str, group_id: str, actor_id: str, outcome: str
    ) -> dict | None:
        if not getattr(self.storage, "supports_domain_writes", False):
            return self._replace_today_with_eaten(
                user_id, group_id, actor_id, outcome
            )
        eaten = (
            self._find_catalog_pig("eaten")
            or self.history.get("pig_snapshots", {}).get("eaten")
            or self.EATEN_PIG_FALLBACK
        )
        today = self._today()
        result = await asyncio.to_thread(
            self.storage.replace_daily_pig_with_eaten,
            draw_date=today.isoformat(),
            due_date=(today + datetime.timedelta(days=1)).isoformat(),
            cutoff_date=(today - datetime.timedelta(days=2)).isoformat(),
            user_id=self._storage_user_key(str(user_id)),
            user_candidates=tuple(self._user_read_candidates(str(user_id))),
            group_id=str(group_id),
            actor_id=self._storage_user_key(str(actor_id)),
            outcome=str(outcome),
            eaten_pig=dict(eaten),
        )
        self._apply_domain_write_result(result)
        return dict(eaten) if result.get("status") == "updated" else None

'''
main = replace_once(main, helper_anchor, helper + helper_anchor, "main eat helper")
start = main.index("    async def roll_pig(self, event: AstrMessageEvent):")
end = main.index('    @filter.command(\n        "我的猪圈"', start)
new_roll = r'''    async def roll_pig(self, event: AstrMessageEvent):
        """Draw for self; mentioning another user is strictly read-only."""
        today_str = self._today().isoformat()
        actor_id = self._event_sender_id(event)
        target_id = actor_id
        viewing_other = False
        if self.at_view_pig:
            at_ids = self.get_at_ids(event)
            if len(at_ids) > 1:
                await event.send(event.plain_result("一次只能查看一个小猪哦！"))
                return
            if at_ids:
                target_id = at_ids[0]
                viewing_other = target_id != actor_id
                if self._is_admin_id(event, target_id):
                    await event.send(event.plain_result("你这只小猪，不许对主人不敬！"))
                    return

        response_text = ""
        pig_to_send: dict | None = None
        send_user_id = actor_id
        group_id = self._event_group_id(event)
        async with self._daily_draw_lock:
            if getattr(self.storage, "supports_domain_writes", False):
                if viewing_other:
                    pig_to_send = self._get_daily_pig(target_id, self._today())
                    if pig_to_send:
                        send_user_id = target_id
                    else:
                        response_text = "对方今天还没有抽取小猪；查看不会替对方抽取。"
                else:
                    storage_id = self._storage_user_key(actor_id)
                    candidates = tuple(self._user_read_candidates(actor_id))
                    probe = await asyncio.to_thread(
                        self.storage.create_daily_draw,
                        draw_date=today_str,
                        user_id=storage_id,
                        user_candidates=candidates,
                        pig=None,
                        group_id=group_id,
                        penalty_should_fail=(
                            random.randrange(100)
                            < self.eaten_next_day_failure_percent
                        ),
                    )
                    self._apply_domain_write_result(probe)
                    status = str(probe.get("status") or "")
                    if status == "penalty-blocked":
                        response_text = (
                            "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                        )
                    elif status == "needs-pig":
                        if not self.pig_list:
                            response_text = "小猪信息加载失败，请检查后台报错！"
                        else:
                            proposed = self._choose_daily_pig(storage_id)
                            result = await asyncio.to_thread(
                                self.storage.create_daily_draw,
                                draw_date=today_str,
                                user_id=storage_id,
                                user_candidates=candidates,
                                pig=proposed,
                                group_id=group_id,
                                penalty_should_fail=False,
                            )
                            self._apply_domain_write_result(result)
                            if result.get("status") in {"created", "existing"}:
                                pig_to_send = result.get("pig") or proposed
                            elif result.get("status") == "penalty-blocked":
                                response_text = (
                                    "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                                )
                            else:
                                response_text = "今日小猪写入失败，请稍后再试。"
                    elif status == "existing":
                        pig_to_send = probe.get("pig")
                    else:
                        response_text = "今日小猪写入失败，请稍后再试。"
            else:
                today_cache = self.load_json(
                    self.today_path, {"date": "", "records": {}}
                )
                if today_cache.get("date") != today_str:
                    today_cache = {"date": today_str, "records": {}}
                user_records = today_cache.setdefault("records", {})
                existing_key = next(
                    (
                        candidate
                        for candidate in self._user_read_candidates(target_id)
                        if candidate in user_records
                    ),
                    "",
                )
                existing = user_records.get(existing_key) if existing_key else None

                if viewing_other:
                    if existing:
                        pig_to_send = existing
                        send_user_id = target_id
                    else:
                        response_text = "对方今天还没有抽取小猪；查看不会替对方抽取。"
                elif self._consume_eaten_penalty(str(actor_id), today_str):
                    response_text = (
                        "🍽️ 昨天被吃得太彻底，今天的抽猪资格还在消化中；请明天再来。"
                    )
                elif existing:
                    changed = self._record_unlock(
                        existing_key,
                        existing,
                        today_str,
                        group_id=group_id,
                        save=False,
                    )
                    if changed:
                        self.save_json(self.history_path, self.history)
                    pig_to_send = existing
                elif not self.pig_list:
                    response_text = "小猪信息加载失败，请检查后台报错！"
                else:
                    storage_id = self._storage_user_key(actor_id)
                    pig_to_send = self._choose_daily_pig(storage_id)
                    user_records[storage_id] = pig_to_send
                    self._record_unlock(
                        storage_id,
                        pig_to_send,
                        today_str,
                        group_id=group_id,
                        save=False,
                    )
                    self.save_json_batch(
                        {self.today_path: today_cache, self.history_path: self.history}
                    )

        if response_text:
            await event.send(event.plain_result(response_text))
            return
        if pig_to_send:
            await self.send_rendered_pig(event, pig_to_send, send_user_id)

'''
main = main[:start] + new_roll + main[end:]
main = main.replace(
    "eaten = self._replace_today_with_eaten(\n",
    "eaten = await self._replace_today_with_eaten_persisted(\n",
)
write("main.py", main)

metadata = read("metadata.yaml").replace('version: "2.10.1"', 'version: "2.11.0"')
write("metadata.yaml", metadata)
updater = read("updater.py").replace("2.10.1", "2.11.0")
write("updater.py", updater)

changelog = read("CHANGELOG.md")
entry = '''# 更新\n## v2.11.0 (2026-08-04)\n### SQLite 核心写入事务\n- 每日抽猪改为规范化 SQL 表的直接事务写入；`PRIMARY KEY(draw_date, user_id)` 现在真正承担跨连接并发唯一性。\n- 次日被吃惩罚的检查、消费与失败锁定和每日抽取放在同一个 `BEGIN IMMEDIATE` 事务边界内。\n- 吃群友的当天替换、原猪保存、次日惩罚和事件记录改为一次提交或全部回滚。\n- 兼容文档仍在同一事务中同步，供 JSON 导出、旧版回滚和灾难恢复使用，但热写入不再触发历史／烤猪投影全表删除重建。\n- JSON 后端继续保留旧逻辑；已迁移的 v2.10 数据库无需再次手动迁移即可使用 SQL 主写路径。\n\n'''
if not changelog.startswith("# 更新\n"):
    raise RuntimeError("unexpected changelog header")
changelog = entry + changelog[len("# 更新\n"):]
write("CHANGELOG.md", changelog)

tests = read("tests/test_sqlite_storage.py")
if "test_sql_primary_daily_draw_is_cross_connection_idempotent" not in tests:
    tests += r'''


def _empty_sql_documents(tmp_path: Path) -> tuple[SQLiteStorage, dict[str, object]]:
    values: dict[str, object] = {
        "rollpig_today.json": {"date": "", "records": {}},
        "pig_history.json": {
            "version": 1,
            "users": {},
            "daily": {},
            "pig_snapshots": {},
        },
        "roast_state.json": {
            "version": 1,
            "cooldowns": {},
            "daily_backdoors": {},
            "daily_roast_counts": {},
            "eaten_penalties": {},
            "eaten_events": {},
        },
        "ai_roast_copies.json": {"version": 1, "copies": {}},
        "pig_catalog.json": [],
        "local_overrides.json": [],
        "deleted_pigs.json": [],
    }
    storage = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    storage.save_json_batch(
        {tmp_path / name: value for name, value in values.items()}
    )
    return storage, values


def test_sql_primary_daily_draw_does_not_rebuild_history_projection(
    tmp_path, monkeypatch
):
    storage, _ = _empty_sql_documents(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("direct write must not rebuild history projection")

    monkeypatch.setattr(storage, "_project_history", forbidden)
    probe = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        user_candidates=("1",),
        pig=None,
        group_id="v2|qq|group|9",
        penalty_should_fail=False,
    )
    assert probe["status"] == "needs-pig"
    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        user_candidates=("1",),
        pig={"id": "pink-pig", "name": "粉红猪"},
        group_id="v2|qq|group|9",
        penalty_should_fail=False,
    )
    assert result["status"] == "created"
    assert storage.verify(deep=True)["projection_ok"] is True


def test_sql_primary_daily_draw_is_cross_connection_idempotent(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )

    def draw(storage, pig_id):
        return storage.create_daily_draw(
            draw_date="2026-08-04",
            user_id="v2|qq|user|1",
            user_candidates=("1",),
            pig={"id": pig_id, "name": pig_id},
            group_id="v2|qq|group|9",
            penalty_should_fail=False,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda args: draw(*args),
                ((first, "pig-a"), (second, "pig-b")),
            )
        )
    assert sorted(result["status"] for result in results) == ["created", "existing"]
    with first._connection() as connection:
        rows = connection.execute(
            "SELECT pig_id FROM daily_draws WHERE draw_date = '2026-08-04'"
        ).fetchall()
        stats = connection.execute(
            "SELECT total_draws FROM user_stats WHERE user_id = 'v2|qq|user|1'"
        ).fetchone()
    assert len(rows) == 1
    assert stats[0] == 1


def test_sql_primary_penalty_and_draw_share_transaction(tmp_path):
    storage, values = _empty_sql_documents(tmp_path)
    roast = values["roast_state.json"]
    roast["eaten_penalties"] = {
        "v2|qq|user|1": {"due_date": "2026-08-04", "failed": False}
    }
    storage.save_json(tmp_path / "roast_state.json", roast)
    result = storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        penalty_should_fail=True,
    )
    assert result["status"] == "penalty-blocked"
    with storage._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM daily_draws").fetchone()[0] == 0
        assert connection.execute(
            "SELECT failed FROM eaten_penalties WHERE user_id = 'v2|qq|user|1'"
        ).fetchone()[0] == 1


def test_sql_primary_eat_rolls_back_all_tables_and_documents(tmp_path, monkeypatch):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    original_writer = storage._write_document_tx

    def fail_on_roast(connection, key, value, **kwargs):
        if key == "roast_state.json":
            raise RuntimeError("fault injection")
        return original_writer(connection, key, value, **kwargs)

    monkeypatch.setattr(storage, "_write_document_tx", fail_on_roast)
    with pytest.raises(RuntimeError, match="fault injection"):
        storage.replace_daily_pig_with_eaten(
            draw_date="2026-08-04",
            due_date="2026-08-05",
            cutoff_date="2026-08-02",
            user_id="v2|qq|user|1",
            group_id="v2|qq|group|9",
            actor_id="v2|qq|user|2",
            outcome="eat_success",
            eaten_pig={"id": "eaten", "name": "吃掉了"},
        )
    with storage._connection() as connection:
        draw = connection.execute("SELECT pig_id FROM daily_draws").fetchone()[0]
        penalties = connection.execute("SELECT COUNT(*) FROM eaten_penalties").fetchone()[0]
        events = connection.execute("SELECT COUNT(*) FROM eaten_events").fetchone()[0]
    assert draw == "pig-a"
    assert penalties == 0
    assert events == 0
    docs = storage.export_documents()
    assert docs["pig_history.json"]["daily"]["2026-08-04"]["records"]["v2|qq|user|1"] == "pig-a"


def test_sql_primary_eat_updates_draw_penalty_event_and_export_docs(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.create_daily_draw(
        draw_date="2026-08-04",
        user_id="v2|qq|user|1",
        pig={"id": "pig-a", "name": "A"},
        group_id="v2|qq|group|9",
    )
    result = storage.replace_daily_pig_with_eaten(
        draw_date="2026-08-04",
        due_date="2026-08-05",
        cutoff_date="2026-08-02",
        user_id="v2|qq|user|1",
        group_id="v2|qq|group|9",
        actor_id="v2|qq|user|2",
        outcome="eat_success",
        eaten_pig={"id": "eaten", "name": "吃掉了"},
    )
    assert result["status"] == "updated"
    with storage._connection() as connection:
        draw = connection.execute(
            "SELECT pig_id, original_pig_id FROM daily_draws"
        ).fetchone()
        penalty = connection.execute(
            "SELECT due_date, failed FROM eaten_penalties"
        ).fetchone()
        event = connection.execute(
            "SELECT outcome, user_id FROM eaten_events"
        ).fetchone()
    assert tuple(draw) == ("eaten", "pig-a")
    assert tuple(penalty) == ("2026-08-05", 0)
    assert tuple(event) == ("eat_success", "v2|qq|user|1")
    assert storage.verify(deep=True)["projection_ok"] is True
'''
write("tests/test_sqlite_storage.py", tests)

regression = read("tests/test_source_regressions.py")
if "test_main_delegates_sql_primary_hot_writes" not in regression:
    regression += r'''


def test_main_delegates_sql_primary_hot_writes():
    assert 'supports_domain_writes' in MAIN
    assert 'self.storage.create_daily_draw' in MAIN
    assert 'self.storage.replace_daily_pig_with_eaten' in MAIN
    assert 'await self._replace_today_with_eaten_persisted' in MAIN
'''
write("tests/test_source_regressions.py", regression)
