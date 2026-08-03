from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


base = read("storage/base.py")
base = replace_once(
    base,
    '''    def remember_identity_alias(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    # Transitional domain read API. JSONStorage keeps using the in-memory
''',
    '''    def remember_identity_alias(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def consume_roast_cooldown(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def increment_roast_count(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def consume_daily_backdoor(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def get_ai_roast_copies(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def store_ai_roast_copy(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def upsert_catalog_override(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def delete_catalog_entry(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    # Transitional domain read API. JSONStorage keeps using the in-memory
''',
    "storage domain write declarations",
)
base = replace_once(
    base,
    '''    def get_eaten_victims(self, event_date: str, group_id: str) -> list[str] | None:
        return None
''',
    '''    def get_eaten_victims(self, event_date: str, group_id: str) -> list[str] | None:
        return None

    def get_roast_count(
        self, draw_date: str, group_id: str, user_candidates: tuple[str, ...]
    ) -> int | None:
        return None
''',
    "roast count read declaration",
)
write("storage/base.py", base)

sqlite = read("storage/sqlite_storage.py")
sqlite = sqlite.replace("v2.11 makes normalized", "v2.12 makes normalized")
sqlite = sqlite.replace("sql-primary-v2.11", "sql-primary-v2.12")
insert_anchor = "    def create_daily_draw(\n"
if sqlite.count(insert_anchor) != 1:
    raise RuntimeError("sqlite domain insertion anchor missing")
sqlite_domain = r'''    @staticmethod
    def _roast_document_default() -> dict[str, Any]:
        return {
            "version": 1,
            "cooldowns": {},
            "daily_backdoors": {},
            "daily_roast_counts": {},
            "eaten_penalties": {},
            "eaten_events": {},
        }

    @staticmethod
    def _ai_document_default() -> dict[str, Any]:
        return {"version": 1, "copies": {}}

    @staticmethod
    def _set_write_authority(connection: sqlite3.Connection) -> None:
        connection.execute(
            "INSERT INTO projection_meta(key, value) VALUES "
            "('write_authority', 'sql-primary-v2.12') "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"
        )

    def consume_roast_cooldown(
        self,
        *,
        group_id: str,
        actor_id: str,
        now: float,
        cooldown_seconds: int,
    ) -> dict[str, Any]:
        """Claim one group-roast cooldown using the SQL primary key."""
        group_id = str(group_id)
        actor_id = str(actor_id)
        cooldown_key = f"{group_id}:{actor_id}"
        now = float(now)
        cooldown_seconds = max(1, int(cooldown_seconds))
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT last_used_at FROM roast_cooldowns WHERE cooldown_key = ?",
                (cooldown_key,),
            ).fetchone()
            if row:
                remaining = int(float(row["last_used_at"]) + cooldown_seconds - now)
                if remaining > 0:
                    return {"remaining": remaining, "claimed": False}
            self._remember_identity(connection, actor_id)
            connection.execute(
                """
                INSERT INTO roast_cooldowns(
                    cooldown_key, group_id, actor_id, last_used_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(cooldown_key) DO UPDATE SET
                    group_id = excluded.group_id,
                    actor_id = excluded.actor_id,
                    last_used_at = excluded.last_used_at
                """,
                (cooldown_key, group_id, actor_id, now),
            )
            roast = self._valid_dict(
                self._read_document_tx(
                    connection, "roast_state.json", self._roast_document_default()
                )
            )
            cooldowns = roast.get("cooldowns")
            if not isinstance(cooldowns, dict):
                cooldowns = {}
                roast["cooldowns"] = cooldowns
            cooldowns[cooldown_key] = now
            self._write_document_tx(connection, "roast_state.json", roast)
            self._set_write_authority(connection)
            return {"remaining": 0, "claimed": True, "roast_state": roast}

    def increment_roast_count(
        self,
        *,
        draw_date: str,
        group_id: str,
        user_id: str,
        cutoff_date: str,
    ) -> dict[str, Any]:
        """Increment one daily roast counter and prune old rows atomically."""
        draw_date = str(draw_date)
        group_id = str(group_id)
        user_id = str(user_id)
        with self.transaction() as connection:
            self._remember_identity(connection, user_id)
            connection.execute(
                """
                INSERT INTO daily_roast_counts(
                    draw_date, group_id, user_id, roast_count
                ) VALUES (?, ?, ?, 1)
                ON CONFLICT(draw_date, group_id, user_id) DO UPDATE SET
                    roast_count = daily_roast_counts.roast_count + 1
                """,
                (draw_date, group_id, user_id),
            )
            connection.execute(
                "DELETE FROM daily_roast_counts WHERE draw_date < ?",
                (str(cutoff_date),),
            )
            total = int(
                connection.execute(
                    "SELECT roast_count FROM daily_roast_counts "
                    "WHERE draw_date = ? AND group_id = ? AND user_id = ?",
                    (draw_date, group_id, user_id),
                ).fetchone()[0]
            )
            rows = connection.execute(
                "SELECT draw_date, group_id, user_id, roast_count "
                "FROM daily_roast_counts ORDER BY draw_date, group_id, user_id"
            ).fetchall()
            roast = self._valid_dict(
                self._read_document_tx(
                    connection, "roast_state.json", self._roast_document_default()
                )
            )
            roast["daily_roast_counts"] = {
                self._event_key(
                    str(row["draw_date"]),
                    str(row["group_id"]),
                    str(row["user_id"]),
                ): int(row["roast_count"])
                for row in rows
                if int(row["roast_count"]) > 0
            }
            self._write_document_tx(connection, "roast_state.json", roast)
            self._set_write_authority(connection)
            return {"count": total, "roast_state": roast}

    def get_roast_count(
        self, draw_date: str, group_id: str, user_candidates: tuple[str, ...]
    ) -> int | None:
        candidates = self._candidate_tuple(user_candidates)
        with self._lock, self._connection() as connection:
            for user_id in candidates:
                row = connection.execute(
                    "SELECT roast_count FROM daily_roast_counts "
                    "WHERE draw_date = ? AND group_id = ? AND user_id = ?",
                    (str(draw_date), str(group_id), user_id),
                ).fetchone()
                if row:
                    return int(row["roast_count"])
        return 0

    def consume_daily_backdoor(
        self,
        *,
        draw_date: str,
        actor_id: str,
        cutoff_date: str,
    ) -> dict[str, Any]:
        """Consume one per-user daily backdoor with cross-process uniqueness."""
        draw_date = str(draw_date)
        actor_id = str(actor_id)
        backdoor_key = f"{draw_date}:{actor_id}"
        with self.transaction() as connection:
            self._remember_identity(connection, actor_id)
            cursor = connection.execute(
                "INSERT OR IGNORE INTO daily_backdoors(" 
                "backdoor_key, draw_date, actor_id, used) VALUES (?, ?, ?, 1)",
                (backdoor_key, draw_date, actor_id),
            )
            if cursor.rowcount == 0:
                return {"consumed": False}
            connection.execute(
                "DELETE FROM daily_backdoors WHERE draw_date < ?",
                (str(cutoff_date),),
            )
            rows = connection.execute(
                "SELECT backdoor_key FROM daily_backdoors "
                "WHERE used = 1 ORDER BY draw_date, actor_id"
            ).fetchall()
            roast = self._valid_dict(
                self._read_document_tx(
                    connection, "roast_state.json", self._roast_document_default()
                )
            )
            roast["daily_backdoors"] = {
                str(row["backdoor_key"]): True for row in rows
            }
            self._write_document_tx(connection, "roast_state.json", roast)
            self._set_write_authority(connection)
            return {"consumed": True, "roast_state": roast}

    def _ai_document_from_sql(
        self, connection: sqlite3.Connection
    ) -> dict[str, Any]:
        document = self._valid_dict(
            self._read_document_tx(
                connection, "ai_roast_copies.json", self._ai_document_default()
            )
        )
        copies: dict[str, dict[str, str]] = {}
        for row in connection.execute(
            "SELECT pig_id, generated_date, content FROM ai_roast_copies "
            "ORDER BY pig_id, generated_date"
        ).fetchall():
            copies.setdefault(str(row["pig_id"]), {})[
                str(row["generated_date"])
            ] = str(row["content"])
        document["copies"] = copies
        return document

    def get_ai_roast_copies(
        self,
        *,
        pig_id: str,
        cutoff_date: str,
        through_date: str,
    ) -> dict[str, Any]:
        """Read the seven-day cache from SQL and prune invalid dates."""
        pig_id = str(pig_id)
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM ai_roast_copies "
                "WHERE generated_date < ? OR generated_date > ?",
                (str(cutoff_date), str(through_date)),
            )
            document = self._ai_document_from_sql(connection)
            self._write_document_tx(connection, "ai_roast_copies.json", document)
            self._set_write_authority(connection)
            selected = document.get("copies", {}).get(pig_id, {})
            return {
                "copies": dict(selected) if isinstance(selected, dict) else {},
                "ai_roast_copies": document,
            }

    def store_ai_roast_copy(
        self,
        *,
        pig_id: str,
        generated_date: str,
        content: str,
        cutoff_date: str,
        through_date: str,
    ) -> dict[str, Any]:
        """Store one copy; the first cross-process writer wins for the day."""
        pig_id = str(pig_id)
        generated_date = str(generated_date)
        content = str(content).strip()
        if not pig_id or not generated_date or not content:
            raise ValueError("AI 文案缓存参数无效")
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM ai_roast_copies "
                "WHERE generated_date < ? OR generated_date > ?",
                (str(cutoff_date), str(through_date)),
            )
            cursor = connection.execute(
                "INSERT OR IGNORE INTO ai_roast_copies(" 
                "pig_id, generated_date, content) VALUES (?, ?, ?)",
                (pig_id, generated_date, content),
            )
            stored = connection.execute(
                "SELECT content FROM ai_roast_copies "
                "WHERE pig_id = ? AND generated_date = ?",
                (pig_id, generated_date),
            ).fetchone()
            document = self._ai_document_from_sql(connection)
            self._write_document_tx(connection, "ai_roast_copies.json", document)
            self._set_write_authority(connection)
            selected = document.get("copies", {}).get(pig_id, {})
            return {
                "created": cursor.rowcount == 1,
                "content": str(stored["content"]),
                "copies": dict(selected) if isinstance(selected, dict) else {},
                "ai_roast_copies": document,
            }

    def upsert_catalog_override(
        self, *, record: dict[str, Any]
    ) -> dict[str, Any]:
        """Upsert one local catalog record and clear its tombstone atomically."""
        payload = self._clone(record)
        pig_id = str(payload.get("id") or "").strip()
        if not pig_id:
            raise ValueError("小猪 ID 无效")
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO catalog_overrides(pig_id, payload_json) VALUES (?, ?) "
                "ON CONFLICT(pig_id) DO UPDATE SET payload_json = excluded.payload_json",
                (pig_id, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )
            connection.execute(
                "DELETE FROM catalog_tombstones WHERE pig_id = ?", (pig_id,)
            )
            raw_overrides = self._read_document_tx(
                connection, "local_overrides.json", []
            )
            overrides = [
                dict(item)
                for item in raw_overrides if isinstance(raw_overrides, list)
                if isinstance(item, dict) and str(item.get("id") or "")
            ]
            index = next(
                (i for i, item in enumerate(overrides) if str(item["id"]) == pig_id),
                None,
            )
            if index is None:
                overrides.append(payload)
            else:
                overrides[index] = payload
            raw_tombstones = self._read_document_tx(
                connection, "deleted_pigs.json", []
            )
            tombstones = sorted(
                {
                    str(item)
                    for item in raw_tombstones if isinstance(raw_tombstones, list)
                    if str(item) and str(item) != pig_id
                }
            )
            self._write_document_tx(connection, "local_overrides.json", overrides)
            self._write_document_tx(connection, "deleted_pigs.json", tombstones)
            self._set_write_authority(connection)
            return {"overrides": overrides, "tombstones": tombstones}

    def delete_catalog_entry(self, *, pig_id: str) -> dict[str, Any]:
        """Remove a local override and add one tombstone atomically."""
        pig_id = str(pig_id).strip()
        if not pig_id:
            raise ValueError("小猪 ID 无效")
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM catalog_overrides WHERE pig_id = ?", (pig_id,)
            )
            connection.execute(
                "INSERT OR IGNORE INTO catalog_tombstones(pig_id) VALUES (?)",
                (pig_id,),
            )
            raw_overrides = self._read_document_tx(
                connection, "local_overrides.json", []
            )
            overrides = [
                dict(item)
                for item in raw_overrides if isinstance(raw_overrides, list)
                if isinstance(item, dict) and str(item.get("id") or "") != pig_id
            ]
            raw_tombstones = self._read_document_tx(
                connection, "deleted_pigs.json", []
            )
            tombstones = sorted(
                {
                    *(str(item) for item in raw_tombstones if isinstance(raw_tombstones, list) and str(item)),
                    pig_id,
                }
            )
            self._write_document_tx(connection, "local_overrides.json", overrides)
            self._write_document_tx(connection, "deleted_pigs.json", tombstones)
            self._set_write_authority(connection)
            return {"overrides": overrides, "tombstones": tombstones}

'''
sqlite = sqlite.replace(insert_anchor, sqlite_domain + insert_anchor, 1)
write("storage/sqlite_storage.py", sqlite)

main = read("main.py")
main = main.replace("2.11.1", "2.12.0")
old_roast = r'''    def _consume_group_roast_cooldown(
        self, group_id: str, actor_id: str
    ) -> int:
        """记录一次普通烤群友，返回剩余冷却秒数；0 表示已成功占用。"""
        storage_actor = self._storage_user_key(str(actor_id))
        key = f"{group_id}:{storage_actor}"
        now = time.time()
        with self._data_lock:
            cooldowns = self.roast_state.setdefault("cooldowns", {})
            previous = float(cooldowns.get(key, 0) or 0)
            remaining = int(previous + self.group_roast_cooldown_seconds - now)
            if remaining > 0:
                return remaining
            cooldowns[key] = now
            self._save_roast_state()
        return 0

    @staticmethod
    def _roast_count_key(draw_date: str, group_id: str, user_id: str) -> str:
        return json.dumps([draw_date, group_id, user_id], ensure_ascii=False)

    @staticmethod
    def _roast_count_date(key: str) -> str:
        try:
            value = json.loads(key)
            return str(value[0]) if isinstance(value, list) and len(value) == 3 else ""
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""

    def _record_group_roast(
        self, group_id: str, user_id: str, draw_date: str | None = None
    ) -> int:
        """记录群聊中实际被烤的一次结果，返回该用户当日累计次数。"""
        draw_date = draw_date or self._today().isoformat()
        storage_id = self._storage_user_key(str(user_id))
        key = self._roast_count_key(draw_date, group_id, storage_id)
        cutoff = (self._today() - datetime.timedelta(days=8)).isoformat()
        with self._data_lock:
            counts = self.roast_state.setdefault("daily_roast_counts", {})
            if not isinstance(counts, dict):
                counts = {}
                self.roast_state["daily_roast_counts"] = counts
            counts[key] = int(counts.get(key, 0) or 0) + 1
            self.roast_state["daily_roast_counts"] = {
                item: int(value or 0)
                for item, value in counts.items()
                if self._roast_count_date(item) >= cutoff and int(value or 0) > 0
            }
            total = int(self.roast_state["daily_roast_counts"].get(key, 0))
            self._save_roast_state()
        return total

    def _roast_protection_status(self, group_id: str, user_id: str) -> tuple[bool, int]:
        """昨天被烤达到阈值的成员，今天自动获得普通烧烤保护。"""
        if not self.enable_roast_protection:
            return False, 0
        yesterday = (self._today() - datetime.timedelta(days=1)).isoformat()
        storage_id = self._storage_user_key(str(user_id))
        key = self._roast_count_key(yesterday, group_id, storage_id)
        counts = self.roast_state.get("daily_roast_counts", {})
        count = int(counts.get(key, 0) or 0) if isinstance(counts, dict) else 0
        return count >= self.roast_protection_threshold, count
'''
new_roast = r'''    async def _consume_group_roast_cooldown(
        self, group_id: str, actor_id: str
    ) -> int:
        """记录一次普通烤群友，返回剩余冷却秒数；0 表示已成功占用。"""
        storage_actor = self._storage_user_key(str(actor_id))
        if getattr(self.storage, "supports_domain_writes", False):
            result = await asyncio.to_thread(
                self.storage.consume_roast_cooldown,
                group_id=str(group_id),
                actor_id=storage_actor,
                now=time.time(),
                cooldown_seconds=self.group_roast_cooldown_seconds,
            )
            roast_state = result.get("roast_state")
            if isinstance(roast_state, dict):
                self.roast_state = roast_state
            return int(result.get("remaining", 0) or 0)
        key = f"{group_id}:{storage_actor}"
        now = time.time()
        with self._data_lock:
            cooldowns = self.roast_state.setdefault("cooldowns", {})
            previous = float(cooldowns.get(key, 0) or 0)
            remaining = int(previous + self.group_roast_cooldown_seconds - now)
            if remaining > 0:
                return remaining
            cooldowns[key] = now
            self._save_roast_state()
        return 0

    @staticmethod
    def _roast_count_key(draw_date: str, group_id: str, user_id: str) -> str:
        return json.dumps([draw_date, group_id, user_id], ensure_ascii=False)

    @staticmethod
    def _roast_count_date(key: str) -> str:
        try:
            value = json.loads(key)
            return str(value[0]) if isinstance(value, list) and len(value) == 3 else ""
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""

    async def _record_group_roast(
        self, group_id: str, user_id: str, draw_date: str | None = None
    ) -> int:
        """记录群聊中实际被烤的一次结果，返回该用户当日累计次数。"""
        draw_date = draw_date or self._today().isoformat()
        storage_id = self._storage_user_key(str(user_id))
        cutoff = (self._today() - datetime.timedelta(days=8)).isoformat()
        if getattr(self.storage, "supports_domain_writes", False):
            result = await asyncio.to_thread(
                self.storage.increment_roast_count,
                draw_date=draw_date,
                group_id=str(group_id),
                user_id=storage_id,
                cutoff_date=cutoff,
            )
            roast_state = result.get("roast_state")
            if isinstance(roast_state, dict):
                self.roast_state = roast_state
            return int(result.get("count", 0) or 0)
        key = self._roast_count_key(draw_date, group_id, storage_id)
        with self._data_lock:
            counts = self.roast_state.setdefault("daily_roast_counts", {})
            if not isinstance(counts, dict):
                counts = {}
                self.roast_state["daily_roast_counts"] = counts
            counts[key] = int(counts.get(key, 0) or 0) + 1
            self.roast_state["daily_roast_counts"] = {
                item: int(value or 0)
                for item, value in counts.items()
                if self._roast_count_date(item) >= cutoff and int(value or 0) > 0
            }
            total = int(self.roast_state["daily_roast_counts"].get(key, 0))
            self._save_roast_state()
        return total

    async def _roast_protection_status(
        self, group_id: str, user_id: str
    ) -> tuple[bool, int]:
        """昨天被烤达到阈值的成员，今天自动获得普通烧烤保护。"""
        if not self.enable_roast_protection:
            return False, 0
        yesterday = (self._today() - datetime.timedelta(days=1)).isoformat()
        storage_id = self._storage_user_key(str(user_id))
        if getattr(self.storage, "supports_domain_reads", False):
            candidates = tuple(
                dict.fromkeys((storage_id, *self._user_read_candidates(str(user_id))))
            )
            count = await asyncio.to_thread(
                self.storage.get_roast_count,
                yesterday,
                str(group_id),
                candidates,
            )
            count = int(count or 0)
        else:
            key = self._roast_count_key(yesterday, group_id, storage_id)
            counts = self.roast_state.get("daily_roast_counts", {})
            count = int(counts.get(key, 0) or 0) if isinstance(counts, dict) else 0
        return count >= self.roast_protection_threshold, count
'''
main = replace_once(main, old_roast, new_roast, "roast state wrappers")
old_backdoor = r'''    def _consume_daily_backdoor(self, actor_id: str) -> bool:
        """普通后门每个用户每天仅消耗一次。"""
        storage_actor = self._storage_user_key(str(actor_id))
        key = f"{self._today().isoformat()}:{storage_actor}"
        with self._data_lock:
            used = self.roast_state.setdefault("daily_backdoors", {})
            if used.get(key):
                return False
            used[key] = True
            # 只保留近期数据，避免状态文件无限增长。
            cutoff = (self._today() - datetime.timedelta(days=7)).isoformat()
            self.roast_state["daily_backdoors"] = {
                item: value
                for item, value in used.items()
                if item.split(":", 1)[0] >= cutoff
            }
            self._save_roast_state()
        return True
'''
new_backdoor = r'''    async def _consume_daily_backdoor(self, actor_id: str) -> bool:
        """普通后门每个用户每天仅消耗一次。"""
        storage_actor = self._storage_user_key(str(actor_id))
        draw_date = self._today().isoformat()
        cutoff = (self._today() - datetime.timedelta(days=7)).isoformat()
        if getattr(self.storage, "supports_domain_writes", False):
            result = await asyncio.to_thread(
                self.storage.consume_daily_backdoor,
                draw_date=draw_date,
                actor_id=storage_actor,
                cutoff_date=cutoff,
            )
            roast_state = result.get("roast_state")
            if isinstance(roast_state, dict):
                self.roast_state = roast_state
            return bool(result.get("consumed"))
        key = f"{draw_date}:{storage_actor}"
        with self._data_lock:
            used = self.roast_state.setdefault("daily_backdoors", {})
            if used.get(key):
                return False
            used[key] = True
            self.roast_state["daily_backdoors"] = {
                item: value
                for item, value in used.items()
                if item.split(":", 1)[0] >= cutoff
            }
            self._save_roast_state()
        return True
'''
main = replace_once(main, old_backdoor, new_backdoor, "daily backdoor wrapper")
old_ai = r'''    def _save_ai_roast_copies(self) -> None:
        self.save_json(self.ai_roast_copies_path, self.ai_roast_copies)

    async def _get_ai_roast_copy(
        self, event: AstrMessageEvent, pig: dict
    ) -> str | None:
        """同一小猪每天只调用一次模型；后续随机复用近七天的缓存。"""
        if not self.enable_ai_roast_copy:
            return None
        pig_id = str(pig.get("id") or "").strip()
        if not pig_id:
            return await self._generate_ai_roast_copy(event, pig)
        today = self._today().isoformat()
        async with self._ai_roast_lock(pig_id):
            with self._data_lock:
                recent, changed = self._recent_ai_roast_copies(pig_id)
                if changed:
                    self._save_ai_roast_copies()
                if today in recent:
                    return random.choice(list(recent.values()))

            generated = await self._generate_ai_roast_copy(event, pig)
            if not generated:
                return None
            with self._data_lock:
                recent, _ = self._recent_ai_roast_copies(pig_id)
                # 锁保护下当天不可能已有另一份；写入后先展示新文案。
                recent[today] = generated
                self.ai_roast_copies.setdefault("copies", {})[pig_id] = recent
                self._save_ai_roast_copies()
            return generated
'''
new_ai = r'''    def _save_ai_roast_copies(self) -> None:
        self.save_json(self.ai_roast_copies_path, self.ai_roast_copies)

    async def _get_ai_roast_copy(
        self, event: AstrMessageEvent, pig: dict
    ) -> str | None:
        """同一小猪每天只保留一份 SQL 缓存；后续随机复用近七天内容。"""
        if not self.enable_ai_roast_copy:
            return None
        pig_id = str(pig.get("id") or "").strip()
        if not pig_id:
            return await self._generate_ai_roast_copy(event, pig)
        today_value = self._today()
        today = today_value.isoformat()
        cutoff = (today_value - datetime.timedelta(days=6)).isoformat()
        async with self._ai_roast_lock(pig_id):
            if getattr(self.storage, "supports_domain_writes", False):
                cached = await asyncio.to_thread(
                    self.storage.get_ai_roast_copies,
                    pig_id=pig_id,
                    cutoff_date=cutoff,
                    through_date=today,
                )
                document = cached.get("ai_roast_copies")
                if isinstance(document, dict):
                    self.ai_roast_copies = document
                recent = cached.get("copies")
                recent = recent if isinstance(recent, dict) else {}
                if today in recent:
                    return random.choice(list(recent.values()))
                generated = await self._generate_ai_roast_copy(event, pig)
                if not generated:
                    return None
                stored = await asyncio.to_thread(
                    self.storage.store_ai_roast_copy,
                    pig_id=pig_id,
                    generated_date=today,
                    content=generated,
                    cutoff_date=cutoff,
                    through_date=today,
                )
                document = stored.get("ai_roast_copies")
                if isinstance(document, dict):
                    self.ai_roast_copies = document
                return str(stored.get("content") or generated)

            with self._data_lock:
                recent, changed = self._recent_ai_roast_copies(pig_id)
                if changed:
                    self._save_ai_roast_copies()
                if today in recent:
                    return random.choice(list(recent.values()))
            generated = await self._generate_ai_roast_copy(event, pig)
            if not generated:
                return None
            with self._data_lock:
                recent, _ = self._recent_ai_roast_copies(pig_id)
                recent[today] = generated
                self.ai_roast_copies.setdefault("copies", {})[pig_id] = recent
                self._save_ai_roast_copies()
            return generated
'''
main = replace_once(main, old_ai, new_ai, "AI cache wrapper")
main = main.replace(
    "protected, roast_count = self._roast_protection_status(group_id, target_id)",
    "protected, roast_count = await self._roast_protection_status(group_id, target_id)",
)
main = main.replace(
    "protected, _ = self._roast_protection_status(group_id, user_id)",
    "protected, _ = await self._roast_protection_status(group_id, user_id)",
)
main = main.replace(
    "remaining = self._consume_group_roast_cooldown(group_id, actor_id)",
    "remaining = await self._consume_group_roast_cooldown(group_id, actor_id)",
)
main = main.replace(
    "            self._record_group_roast(group_id, actor_id)",
    "            await self._record_group_roast(group_id, actor_id)",
)
main = main.replace(
    "        self._record_group_roast(group_id, target_id)",
    "        await self._record_group_roast(group_id, target_id)",
)
main = main.replace(
    "if not is_super_phrase and not self._consume_daily_backdoor(actor_id):",
    "if not is_super_phrase and not await self._consume_daily_backdoor(actor_id):",
)
helper_anchor = '''    def _build_overview_data(self) -> dict:
'''
helpers = r'''    def _persist_catalog_override(
        self, record: dict, normalized_image: bytes | None
    ) -> None:
        pig_id = str(record.get("id") or "")
        with self._data_lock:
            if getattr(self.storage, "supports_domain_writes", False):
                self.storage.upsert_catalog_override(record=dict(record))
            else:
                overrides = self._validate_pig_records(
                    self.load_json(self.local_overrides_path, [])
                )
                override_index = next(
                    (
                        i
                        for i, item in enumerate(overrides)
                        if str(item.get("id")) == pig_id
                    ),
                    None,
                )
                if override_index is None:
                    overrides.append(dict(record))
                else:
                    overrides[override_index] = dict(record)
                tombstones = {
                    str(item) for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.discard(pig_id)
                self.save_json_batch(
                    {
                        self.local_overrides_path: overrides,
                        self.tombstones_path: sorted(tombstones),
                    }
                )
            if normalized_image:
                self._write_custom_image(pig_id, normalized_image)
            self._reload_catalog_layers()

    def _persist_catalog_delete(self, pig_id: str) -> None:
        with self._data_lock:
            if getattr(self.storage, "supports_domain_writes", False):
                self.storage.delete_catalog_entry(pig_id=str(pig_id))
            else:
                overrides = [
                    dict(item)
                    for item in self.load_json(self.local_overrides_path, [])
                    if str(item.get("id")) != pig_id
                ]
                tombstones = {
                    str(item) for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.add(pig_id)
                self.save_json_batch(
                    {
                        self.local_overrides_path: overrides,
                        self.tombstones_path: sorted(tombstones),
                    }
                )
            for ext in self.IMAGE_EXTENSIONS:
                (self.custom_image_dir / f"{pig_id}.{ext}").unlink(missing_ok=True)
            self._reload_catalog_layers()

'''
if main.count(helper_anchor) != 1:
    raise RuntimeError("catalog helper insertion anchor missing")
main = main.replace(helper_anchor, helpers + helper_anchor, 1)
old_save_block = r'''            with self._data_lock:
                overrides = self._validate_pig_records(
                    self.load_json(self.local_overrides_path, [])
                )
                override_index = next(
                    (
                        i
                        for i, item in enumerate(overrides)
                        if str(item.get("id")) == pig_id
                    ),
                    None,
                )
                if override_index is None:
                    overrides.append(record)
                else:
                    overrides[override_index] = record
                tombstones = {
                    str(item)
                    for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.discard(pig_id)
                if normalized_image:
                    self._write_custom_image(pig_id, normalized_image)
                self.save_json_batch(
                    {
                        self.local_overrides_path: overrides,
                        self.tombstones_path: sorted(tombstones),
                    }
                )
                self._reload_catalog_layers()
'''
new_save_block = r'''            await asyncio.to_thread(
                self._persist_catalog_override, record, normalized_image
            )
'''
main = replace_once(main, old_save_block, new_save_block, "catalog save delegation")
old_delete_block = r'''            with self._data_lock:
                overrides = [
                    dict(item)
                    for item in self.load_json(self.local_overrides_path, [])
                    if str(item.get("id")) != pig_id
                ]
                tombstones = {
                    str(item)
                    for item in self.load_json(self.tombstones_path, [])
                }
                tombstones.add(pig_id)
                self.save_json_batch(
                    {
                        self.local_overrides_path: overrides,
                        self.tombstones_path: sorted(tombstones),
                    }
                )
                for ext in self.IMAGE_EXTENSIONS:
                    (self.custom_image_dir / f"{pig_id}.{ext}").unlink(
                        missing_ok=True
                    )
                self._reload_catalog_layers()
'''
new_delete_block = r'''            await asyncio.to_thread(self._persist_catalog_delete, pig_id)
'''
main = replace_once(main, old_delete_block, new_delete_block, "catalog delete delegation")
write("main.py", main)

metadata = read("metadata.yaml").replace('version: "2.11.1"', 'version: "2.12.0"')
write("metadata.yaml", metadata)
updater = read("updater.py").replace("2.11.1", "2.12.0")
write("updater.py", updater)

changelog = read("CHANGELOG.md")
entry = '''# 更新\n## v2.12.0 (2026-08-04)\n### 烤猪、AI 文案与图鉴后台 SQL 主写\n- 烤群友冷却、每日被烤次数与每日后门改为规范化 SQL 表直接事务写入，跨连接唯一性由数据库约束承担。\n- 猪圈保护次数改为直接查询 `daily_roast_counts`，聊天命令通过工作线程执行 SQLite I/O，不阻塞事件循环。\n- AI 烤猪文案缓存改为 SQL 读取、清理与首写获胜；多进程并发生成时只保留当天第一份已提交文案。\n- 管理后台新增、编辑和删除小猪改为 `catalog_overrides`／`catalog_tombstones` 原子事务写入。\n- 兼容 JSON 仍在同一事务内同步，用于导出、旧版回滚和灾难恢复；上述热路径不再触发对应投影全表重建。\n\n'''
if not changelog.startswith("# 更新\n"):
    raise RuntimeError("unexpected changelog header")
changelog = entry + changelog[len("# 更新\n"):]
write("CHANGELOG.md", changelog)

tests = read("tests/test_sqlite_storage.py")
if "test_sql_primary_roast_cooldown_is_cross_connection_unique" not in tests:
    tests += r'''


def test_sql_primary_roast_cooldown_is_cross_connection_unique(tmp_path):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    claimed = first.consume_roast_cooldown(
        group_id="v2|qq|group|g",
        actor_id="v2|qq|user|1",
        now=1000.0,
        cooldown_seconds=3600,
    )
    blocked = second.consume_roast_cooldown(
        group_id="v2|qq|group|g",
        actor_id="v2|qq|user|1",
        now=1001.0,
        cooldown_seconds=3600,
    )
    assert claimed["claimed"] is True
    assert blocked["claimed"] is False
    assert blocked["remaining"] == 3599
    with first._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM roast_cooldowns").fetchone()[0] == 1
    document = first.export_documents()["roast_state.json"]
    assert document["cooldowns"]["v2|qq|group|g:v2|qq|user|1"] == 1000.0


def test_sql_primary_roast_counts_increment_and_prune(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    storage.increment_roast_count(
        draw_date="2026-07-01",
        group_id="g",
        user_id="v2|qq|user|old",
        cutoff_date="2026-08-01",
    )
    first = storage.increment_roast_count(
        draw_date="2026-08-04",
        group_id="g",
        user_id="v2|qq|user|1",
        cutoff_date="2026-08-01",
    )
    second = storage.increment_roast_count(
        draw_date="2026-08-04",
        group_id="g",
        user_id="v2|qq|user|1",
        cutoff_date="2026-08-01",
    )
    assert first["count"] == 1
    assert second["count"] == 2
    assert storage.get_roast_count(
        "2026-08-04", "g", ("v2|qq|user|1",)
    ) == 2
    with storage._connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM daily_roast_counts WHERE draw_date < '2026-08-01'"
        ).fetchone()[0] == 0


def test_sql_primary_daily_backdoor_is_cross_connection_unique(tmp_path):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    one = first.consume_daily_backdoor(
        draw_date="2026-08-04",
        actor_id="v2|qq|user|1",
        cutoff_date="2026-07-28",
    )
    two = second.consume_daily_backdoor(
        draw_date="2026-08-04",
        actor_id="v2|qq|user|1",
        cutoff_date="2026-07-28",
    )
    assert one["consumed"] is True
    assert two["consumed"] is False
    assert first.export_documents()["roast_state.json"]["daily_backdoors"] == {
        "2026-08-04:v2|qq|user|1": True
    }


def test_sql_primary_ai_copy_first_writer_wins_and_prunes(tmp_path):
    first, _ = _empty_sql_documents(tmp_path)
    second = SQLiteStorage(
        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS
    )
    first.store_ai_roast_copy(
        pig_id="pig-a",
        generated_date="2026-07-01",
        content="过期",
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    one = first.store_ai_roast_copy(
        pig_id="pig-a",
        generated_date="2026-08-04",
        content="第一份",
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    two = second.store_ai_roast_copy(
        pig_id="pig-a",
        generated_date="2026-08-04",
        content="第二份",
        cutoff_date="2026-07-29",
        through_date="2026-08-04",
    )
    assert one["created"] is True
    assert two["created"] is False
    assert two["content"] == "第一份"
    cached = first.get_ai_roast_copies(
        pig_id="pig-a", cutoff_date="2026-07-29", through_date="2026-08-04"
    )
    assert cached["copies"] == {"2026-08-04": "第一份"}
    assert first.export_documents()["ai_roast_copies.json"]["copies"] == {
        "pig-a": {"2026-08-04": "第一份"}
    }


def test_sql_primary_catalog_override_and_delete_are_atomic(tmp_path):
    storage, _ = _empty_sql_documents(tmp_path)
    record = {
        "id": "local-pig",
        "name": "本地猪",
        "description": "本地限定",
        "analysis": "事务保存",
    }
    saved = storage.upsert_catalog_override(record=record)
    assert saved["overrides"] == [record]
    assert saved["tombstones"] == []
    with storage._connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM catalog_overrides WHERE pig_id = 'local-pig'"
        ).fetchone()[0] == 1
    deleted = storage.delete_catalog_entry(pig_id="local-pig")
    assert deleted["overrides"] == []
    assert deleted["tombstones"] == ["local-pig"]
    documents = storage.export_documents()
    assert documents["local_overrides.json"] == []
    assert documents["deleted_pigs.json"] == ["local-pig"]


def test_sql_primary_catalog_write_rolls_back_with_document_failure(
    tmp_path, monkeypatch
):
    storage, _ = _empty_sql_documents(tmp_path)
    original = storage._write_document_tx

    def fail_on_tombstones(connection, key, value, **kwargs):
        if key == "deleted_pigs.json":
            raise RuntimeError("catalog fault injection")
        return original(connection, key, value, **kwargs)

    monkeypatch.setattr(storage, "_write_document_tx", fail_on_tombstones)
    with pytest.raises(RuntimeError, match="catalog fault injection"):
        storage.upsert_catalog_override(
            record={
                "id": "broken-pig",
                "name": "坏猪",
                "description": "测试",
                "analysis": "测试",
            }
        )
    with storage._connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM catalog_overrides WHERE pig_id = 'broken-pig'"
        ).fetchone()[0] == 0
'''
write("tests/test_sqlite_storage.py", tests)

regressions = read("tests/test_source_regressions.py")
if "test_main_delegates_v212_sql_hot_writes" not in regressions:
    regressions += r'''


def test_main_delegates_v212_sql_hot_writes():
    cooldown = ast.get_source_segment(SOURCE, _method("_consume_group_roast_cooldown")) or ""
    counts = ast.get_source_segment(SOURCE, _method("_record_group_roast")) or ""
    protection = ast.get_source_segment(SOURCE, _method("_roast_protection_status")) or ""
    backdoor = ast.get_source_segment(SOURCE, _method("_consume_daily_backdoor")) or ""
    ai = ast.get_source_segment(SOURCE, _method("_get_ai_roast_copy")) or ""
    save = ast.get_source_segment(SOURCE, _method("_persist_catalog_override")) or ""
    delete = ast.get_source_segment(SOURCE, _method("_persist_catalog_delete")) or ""
    assert "asyncio.to_thread" in cooldown and "consume_roast_cooldown" in cooldown
    assert "asyncio.to_thread" in counts and "increment_roast_count" in counts
    assert "get_roast_count" in protection
    assert "consume_daily_backdoor" in backdoor
    assert "get_ai_roast_copies" in ai and "store_ai_roast_copy" in ai
    assert "upsert_catalog_override" in save
    assert "delete_catalog_entry" in delete
'''
write("tests/test_source_regressions.py", regressions)
