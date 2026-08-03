from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


route_anchor = '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/overview",
            self.page_overview,
            ["GET"],
            "今日小猪统计总览",
        )
'''
route_insert = route_anchor + '''        context.register_web_api(
            f"/{self.PLUGIN_NAME}/analytics/insights",
            self.page_analytics_insights,
            ["GET"],
            "今日小猪深度分析",
        )
'''
replace_once("main.py", route_anchor, route_insert)

page_anchor = '''

    async def page_pigs(self):
'''
page_methods = r'''

    @staticmethod
    def _analytics_delta(current: int | float, previous: int | float) -> float:
        current_value = float(current or 0)
        previous_value = float(previous or 0)
        if not previous_value:
            return 100.0 if current_value else 0.0
        return round((current_value - previous_value) / previous_value * 100, 2)

    @staticmethod
    def _analytics_percentile(values: list[int], fraction: float) -> int:
        if not values:
            return 0
        ordered = sorted(int(value or 0) for value in values)
        index = min(
            len(ordered) - 1,
            max(0, int(round((len(ordered) - 1) * float(fraction)))),
        )
        return ordered[index]

    def _build_analytics_insights(self) -> dict:
        """Build aggregate-only commercial analytics without exposing identities."""
        started = time.monotonic()
        with self._data_lock:
            today = self._today()
            current_start = today - datetime.timedelta(days=6)
            previous_start = today - datetime.timedelta(days=13)
            previous_end = today - datetime.timedelta(days=7)
            activity_start = today - datetime.timedelta(days=27)
            catalog = {
                str(item.get("id") or ""): str(
                    item.get("name") or item.get("id") or ""
                )
                for item in self.pig_list
                if str(item.get("id") or "")
            }
            if getattr(self.storage, "supports_dashboard_analytics", False):
                stored = self.storage.get_dashboard_insights(
                    current_start=current_start.isoformat(),
                    current_end=today.isoformat(),
                    previous_start=previous_start.isoformat(),
                    previous_end=previous_end.isoformat(),
                    activity_start=activity_start.isoformat(),
                    catalog_ids=tuple(sorted(catalog)),
                ) or {}
                stored["rising_pigs"] = [
                    {
                        **dict(item),
                        "name": catalog.get(
                            str(item.get("id") or ""),
                            str(item.get("id") or ""),
                        ),
                    }
                    for item in stored.get("rising_pigs", [])
                    if str(item.get("id") or "") in catalog
                ]
                stored.setdefault("source", "normalized-sql")
                stored.setdefault("observability", {})["handler_elapsed_ms"] = round(
                    (time.monotonic() - started) * 1000, 3
                )
                return stored

            history = self.history if isinstance(self.history, dict) else {}
            users = history.get("users", {})
            users = users if isinstance(users, dict) else {}
            daily = history.get("daily", {})
            daily = daily if isinstance(daily, dict) else {}

            def day_users(day: datetime.date) -> set[str]:
                item = daily.get(day.isoformat(), {})
                values = item.get("users", []) if isinstance(item, dict) else []
                return {str(value) for value in values if str(value)}

            def period_summary(start: datetime.date, end: datetime.date) -> tuple[dict, set[str]]:
                active: set[str] = set()
                draws = 0
                unlocks = 0
                cursor = start
                while cursor <= end:
                    item = daily.get(cursor.isoformat(), {})
                    if isinstance(item, dict):
                        active.update(str(value) for value in item.get("users", []) if str(value))
                        draws += int(item.get("draws", 0) or 0)
                        unlocks += int(item.get("new_unlocks", 0) or 0)
                    cursor += datetime.timedelta(days=1)
                days = max(1, (end - start).days + 1)
                return (
                    {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "active_users": len(active),
                        "draws": draws,
                        "new_unlocks": unlocks,
                        "avg_daily_users": round(
                            sum(len(day_users(start + datetime.timedelta(days=offset))) for offset in range(days)) / days,
                            2,
                        ),
                        "unlock_efficiency": round(unlocks / draws * 100, 2) if draws else 0,
                    },
                    active,
                )

            current, current_users = period_summary(current_start, today)
            previous, previous_users = period_summary(previous_start, previous_end)
            returning = current_users.intersection(previous_users)

            roast_by_date: Counter[str] = Counter()
            roast_state = self.roast_state if isinstance(self.roast_state, dict) else {}
            roast_counts = roast_state.get("daily_roast_counts", {})
            for raw_key, count in roast_counts.items() if isinstance(roast_counts, dict) else ():
                draw_date = self._roast_count_date(str(raw_key))
                if draw_date:
                    roast_by_date[draw_date] += int(count or 0)

            eat_by_date: Counter[str] = Counter()
            eaten_events = roast_state.get("eaten_events", {})
            for raw_key, entry in eaten_events.items() if isinstance(eaten_events, dict) else ():
                event_date = ""
                if isinstance(entry, dict):
                    event_date = str(entry.get("event_date") or entry.get("date") or "")
                if not event_date:
                    try:
                        parsed = json.loads(str(raw_key))
                        event_date = str(parsed[0]) if isinstance(parsed, list) and parsed else ""
                    except (TypeError, ValueError, json.JSONDecodeError):
                        event_date = str(raw_key).split(":", 1)[0]
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", event_date):
                    eat_by_date[event_date] += 1

            activity = []
            cursor = activity_start
            while cursor <= today:
                key = cursor.isoformat()
                item = daily.get(key, {})
                item = item if isinstance(item, dict) else {}
                activity.append(
                    {
                        "date": key,
                        "users": len({str(value) for value in item.get("users", []) if str(value)}),
                        "draws": int(item.get("draws", 0) or 0),
                        "new_unlocks": int(item.get("new_unlocks", 0) or 0),
                        "roasts": int(roast_by_date.get(key, 0)),
                        "eats": int(eat_by_date.get(key, 0)),
                    }
                )
                cursor += datetime.timedelta(days=1)

            unlocked_counts: list[int] = []
            collectors: Counter[str] = Counter()
            draw_counts: Counter[str] = Counter()
            platform_counts: Counter[str] = Counter()
            for user_id, raw_user in users.items():
                raw_user = raw_user if isinstance(raw_user, dict) else {}
                pigs = raw_user.get("pigs", {})
                pigs = pigs if isinstance(pigs, dict) else {}
                unlocked = 0
                for pig_id, item in pigs.items():
                    pig_id = str(pig_id)
                    if pig_id not in catalog or not isinstance(item, dict):
                        continue
                    unlocked += 1
                    collectors[pig_id] += 1
                    draw_counts[pig_id] += int(item.get("count", 0) or 0)
                unlocked_counts.append(unlocked)
                match = re.match(r"^v2\|([^|]+)\|user\|", str(user_id))
                platform_counts[match.group(1) if match else "legacy"] += 1

            catalog_size = len(catalog)
            distribution_labels = ("0–10%", "10–25%", "25–50%", "50–75%", "75–100%")
            distribution = Counter({label: 0 for label in distribution_labels})
            for unlocked in unlocked_counts:
                ratio = unlocked / catalog_size * 100 if catalog_size else 0
                label = (
                    "0–10%" if ratio <= 10 else
                    "10–25%" if ratio <= 25 else
                    "25–50%" if ratio <= 50 else
                    "50–75%" if ratio <= 75 else "75–100%"
                )
                distribution[label] += 1
            total_catalog_draws = sum(draw_counts.values())
            top5_draws = sum(value for _, value in draw_counts.most_common(5))
            long_tail_limit = max(1, int(len(users) * 0.01 + 0.999999))

            period_pigs: dict[str, Counter[str]] = {
                "current": Counter(),
                "previous": Counter(),
            }
            cursor = previous_start
            while cursor <= today:
                item = daily.get(cursor.isoformat(), {})
                records = item.get("records", {}) if isinstance(item, dict) else {}
                originals = item.get("eaten_originals", {}) if isinstance(item, dict) else {}
                bucket = "current" if cursor >= current_start else "previous"
                for user_id, pig_id in records.items() if isinstance(records, dict) else ():
                    pig_id = str(pig_id or "")
                    effective = str(originals.get(user_id) or pig_id) if isinstance(originals, dict) else pig_id
                    if effective in catalog:
                        period_pigs[bucket][effective] += 1
                cursor += datetime.timedelta(days=1)
            rising = []
            for pig_id in catalog:
                current_count = period_pigs["current"][pig_id]
                previous_count = period_pigs["previous"][pig_id]
                if current_count or previous_count:
                    rising.append(
                        {
                            "id": pig_id,
                            "name": catalog[pig_id],
                            "current": current_count,
                            "previous": previous_count,
                            "delta": current_count - previous_count,
                        }
                    )
            rising.sort(key=lambda item: (-item["delta"], -item["current"], item["id"]))

            attempts = self.ai_roast_copies.get("attempts", {}) if isinstance(self.ai_roast_copies, dict) else {}
            ai_counts = Counter()
            for by_date in attempts.values() if isinstance(attempts, dict) else ():
                for generated_date, status in by_date.items() if isinstance(by_date, dict) else ():
                    if current_start.isoformat() <= str(generated_date) <= today.isoformat():
                        ai_counts[str(status)] += 1

            return {
                "source": "json-compatibility",
                "periods": {"current": current, "previous": previous},
                "deltas": {
                    "active_users": self._analytics_delta(current["active_users"], previous["active_users"]),
                    "draws": self._analytics_delta(current["draws"], previous["draws"]),
                    "new_unlocks": self._analytics_delta(current["new_unlocks"], previous["new_unlocks"]),
                },
                "retention": {
                    "returning_users": len(returning),
                    "previous_active_users": len(previous_users),
                    "new_current_users": len(current_users - previous_users),
                    "rate": round(len(returning) / len(previous_users) * 100, 2) if previous_users else 0,
                },
                "activity": activity,
                "catalog": {
                    "catalog_count": catalog_size,
                    "median_unlocked": self._analytics_percentile(unlocked_counts, 0.5),
                    "p90_unlocked": self._analytics_percentile(unlocked_counts, 0.9),
                    "zero_collector_count": max(0, catalog_size - len(collectors)),
                    "long_tail_count": sum(1 for pig_id in catalog if 0 < collectors[pig_id] <= long_tail_limit),
                    "top5_draw_share": round(top5_draws / total_catalog_draws * 100, 2) if total_catalog_draws else 0,
                    "distribution": [
                        {"label": label, "users": distribution[label]}
                        for label in distribution_labels
                    ],
                },
                "platforms": [
                    {"platform": platform, "users": count}
                    for platform, count in platform_counts.most_common(8)
                ],
                "rising_pigs": rising[:8],
                "operations": {
                    "roasts": sum(roast_by_date.get((current_start + datetime.timedelta(days=offset)).isoformat(), 0) for offset in range(7)),
                    "eats": sum(eat_by_date.get((current_start + datetime.timedelta(days=offset)).isoformat(), 0) for offset in range(7)),
                    "ai": {
                        "ready": ai_counts["ready"],
                        "failed": ai_counts["failed"],
                        "generating": ai_counts["generating"],
                    },
                },
                "observability": {
                    "query_elapsed_ms": round((time.monotonic() - started) * 1000, 3)
                },
            }

    async def page_analytics_insights(self):
        """管理面板：只读聚合分析；不返回用户、群组或聊天原始标识。"""
        try:
            data = await asyncio.to_thread(self._build_analytics_insights)
            return self._jsonify({"status": "ok", "data": data})
        except Exception as exc:
            logger.error(f"今日小猪管理页深度分析失败：{exc}", exc_info=True)
            return self._jsonify({"status": "error", "message": "获取深度分析失败"})
'''
replace_once("main.py", page_anchor, page_methods + page_anchor)
replace_once(
    "main.py",
    '"AstrBot-RollPig/2.14.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
    '"AstrBot-RollPig/2.15.0 (+https://github.com/casama233/astrbot_plugin_rollpig)"',
)

base_anchor = '''    def get_dashboard_overview(self, **kwargs: Any) -> dict[str, Any] | None:
        return None
'''
replace_once(
    "storage/base.py",
    base_anchor,
    base_anchor
    + '''
    def get_dashboard_insights(self, **kwargs: Any) -> dict[str, Any] | None:
        return None
''',
)

sqlite_anchor = '''    def get_user_collection(self, user_candidates: tuple[str, ...]) -> dict[str, Any] | None:
'''
sqlite_method = r'''    def get_dashboard_insights(
        self,
        *,
        current_start: str,
        current_end: str,
        previous_start: str,
        previous_end: str,
        activity_start: str,
        catalog_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        """Return aggregate-only growth, coverage and runtime analytics."""
        started = time.monotonic()
        catalog = tuple(dict.fromkeys(str(item) for item in catalog_ids if str(item)))

        def delta(current: int, previous: int) -> float:
            if not previous:
                return 100.0 if current else 0.0
            return round((current - previous) / previous * 100, 2)

        def percentile(values: list[int], fraction: float) -> int:
            if not values:
                return 0
            ordered = sorted(values)
            index = min(
                len(ordered) - 1,
                max(0, int(round((len(ordered) - 1) * fraction))),
            )
            return int(ordered[index])

        with self._lock, self._connection() as connection:
            connection.execute(
                "CREATE TEMP TABLE IF NOT EXISTS dashboard_catalog_ids("
                "pig_id TEXT PRIMARY KEY)"
            )
            connection.execute("DELETE FROM dashboard_catalog_ids")
            connection.executemany(
                "INSERT OR IGNORE INTO dashboard_catalog_ids(pig_id) VALUES (?)",
                ((pig_id,) for pig_id in catalog),
            )

            def summary(start_date: str, end_date: str) -> dict[str, Any]:
                row = connection.execute(
                    "SELECT COUNT(DISTINCT user_id) AS active_users, "
                    "COUNT(*) AS draws, COALESCE(SUM(was_new_unlock), 0) AS new_unlocks "
                    "FROM daily_draws WHERE draw_date BETWEEN ? AND ?",
                    (start_date, end_date),
                ).fetchone()
                day_rows = connection.execute(
                    "SELECT draw_date, COUNT(DISTINCT user_id) AS users "
                    "FROM daily_draws WHERE draw_date BETWEEN ? AND ? GROUP BY draw_date",
                    (start_date, end_date),
                ).fetchall()
                days = max(1, (__import__("datetime").date.fromisoformat(end_date) - __import__("datetime").date.fromisoformat(start_date)).days + 1)
                draws = int(row["draws"] if row else 0)
                unlocks = int(row["new_unlocks"] if row else 0)
                return {
                    "start": start_date,
                    "end": end_date,
                    "active_users": int(row["active_users"] if row else 0),
                    "draws": draws,
                    "new_unlocks": unlocks,
                    "avg_daily_users": round(sum(int(item["users"]) for item in day_rows) / days, 2),
                    "unlock_efficiency": round(unlocks / draws * 100, 2) if draws else 0,
                }

            current = summary(str(current_start), str(current_end))
            previous = summary(str(previous_start), str(previous_end))
            current_users = {
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT user_id FROM daily_draws "
                    "WHERE draw_date BETWEEN ? AND ?",
                    (str(current_start), str(current_end)),
                ).fetchall()
            }
            previous_users = {
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT user_id FROM daily_draws "
                    "WHERE draw_date BETWEEN ? AND ?",
                    (str(previous_start), str(previous_end)),
                ).fetchall()
            }
            returning = current_users.intersection(previous_users)

            daily_rows = {
                str(row["draw_date"]): {
                    "date": str(row["draw_date"]),
                    "users": int(row["users"]),
                    "draws": int(row["draws"]),
                    "new_unlocks": int(row["new_unlocks"]),
                    "roasts": 0,
                    "eats": 0,
                }
                for row in connection.execute(
                    "SELECT draw_date, COUNT(DISTINCT user_id) AS users, "
                    "COUNT(*) AS draws, COALESCE(SUM(was_new_unlock), 0) AS new_unlocks "
                    "FROM daily_draws WHERE draw_date BETWEEN ? AND ? "
                    "GROUP BY draw_date ORDER BY draw_date",
                    (str(activity_start), str(current_end)),
                ).fetchall()
            }
            for row in connection.execute(
                "SELECT draw_date, COALESCE(SUM(roast_count), 0) AS total "
                "FROM daily_roast_counts WHERE draw_date BETWEEN ? AND ? "
                "GROUP BY draw_date",
                (str(activity_start), str(current_end)),
            ).fetchall():
                daily_rows.setdefault(
                    str(row["draw_date"]),
                    {"date": str(row["draw_date"]), "users": 0, "draws": 0, "new_unlocks": 0, "roasts": 0, "eats": 0},
                )["roasts"] = int(row["total"])
            for row in connection.execute(
                "SELECT event_date, COUNT(*) AS total FROM eaten_events "
                "WHERE event_date BETWEEN ? AND ? GROUP BY event_date",
                (str(activity_start), str(current_end)),
            ).fetchall():
                daily_rows.setdefault(
                    str(row["event_date"]),
                    {"date": str(row["event_date"]), "users": 0, "draws": 0, "new_unlocks": 0, "roasts": 0, "eats": 0},
                )["eats"] = int(row["total"])

            date_module = __import__("datetime").date
            cursor = date_module.fromisoformat(str(activity_start))
            end_value = date_module.fromisoformat(str(current_end))
            one_day = __import__("datetime").timedelta(days=1)
            activity: list[dict[str, Any]] = []
            while cursor <= end_value:
                key = cursor.isoformat()
                activity.append(
                    daily_rows.get(
                        key,
                        {"date": key, "users": 0, "draws": 0, "new_unlocks": 0, "roasts": 0, "eats": 0},
                    )
                )
                cursor += one_day

            unlocked_counts = [
                int(row["unlocked"])
                for row in connection.execute(
                    "SELECT us.user_id, COUNT(dc.pig_id) AS unlocked "
                    "FROM user_stats us LEFT JOIN ("
                    "  SELECT up.user_id, up.pig_id FROM user_pigs up "
                    "  INNER JOIN dashboard_catalog_ids c ON c.pig_id = up.pig_id"
                    ") dc ON dc.user_id = us.user_id GROUP BY us.user_id"
                ).fetchall()
            ]
            pig_rows = [
                {
                    "id": str(row["pig_id"]),
                    "draws": int(row["draws"]),
                    "collectors": int(row["collectors"]),
                }
                for row in connection.execute(
                    "SELECT up.pig_id, COALESCE(SUM(up.draw_count), 0) AS draws, "
                    "COUNT(*) AS collectors FROM user_pigs up "
                    "INNER JOIN dashboard_catalog_ids c ON c.pig_id = up.pig_id "
                    "GROUP BY up.pig_id"
                ).fetchall()
            ]
            catalog_size = len(catalog)
            labels = ("0–10%", "10–25%", "25–50%", "50–75%", "75–100%")
            buckets = {label: 0 for label in labels}
            for unlocked in unlocked_counts:
                ratio = unlocked / catalog_size * 100 if catalog_size else 0
                label = (
                    "0–10%" if ratio <= 10 else
                    "10–25%" if ratio <= 25 else
                    "25–50%" if ratio <= 50 else
                    "50–75%" if ratio <= 75 else "75–100%"
                )
                buckets[label] += 1
            total_users = len(unlocked_counts)
            long_tail_limit = max(1, int(total_users * 0.01 + 0.999999))
            all_draws = sum(item["draws"] for item in pig_rows)
            top5_draws = sum(sorted((item["draws"] for item in pig_rows), reverse=True)[:5])

            rising = [
                {
                    "id": str(row["pig_id"]),
                    "current": int(row["current_draws"]),
                    "previous": int(row["previous_draws"]),
                    "delta": int(row["current_draws"]) - int(row["previous_draws"]),
                }
                for row in connection.execute(
                    "SELECT COALESCE(NULLIF(d.original_pig_id, ''), d.pig_id) AS pig_id, "
                    "SUM(CASE WHEN d.draw_date BETWEEN ? AND ? THEN 1 ELSE 0 END) AS current_draws, "
                    "SUM(CASE WHEN d.draw_date BETWEEN ? AND ? THEN 1 ELSE 0 END) AS previous_draws "
                    "FROM daily_draws d INNER JOIN dashboard_catalog_ids c "
                    "ON c.pig_id = COALESCE(NULLIF(d.original_pig_id, ''), d.pig_id) "
                    "WHERE d.draw_date BETWEEN ? AND ? GROUP BY pig_id",
                    (
                        str(current_start), str(current_end),
                        str(previous_start), str(previous_end),
                        str(previous_start), str(current_end),
                    ),
                ).fetchall()
            ]
            rising.sort(key=lambda item: (-item["delta"], -item["current"], item["id"]))

            platforms = [
                {"platform": str(row["namespace"]), "users": int(row["users"])}
                for row in connection.execute(
                    "SELECT i.namespace, COUNT(*) AS users FROM user_stats us "
                    "INNER JOIN identities i ON i.identity_key = us.user_id "
                    "WHERE i.identity_type = 'user' GROUP BY i.namespace "
                    "ORDER BY users DESC, i.namespace LIMIT 8"
                ).fetchall()
            ]
            roast_row = connection.execute(
                "SELECT COALESCE(SUM(roast_count), 0) FROM daily_roast_counts "
                "WHERE draw_date BETWEEN ? AND ?",
                (str(current_start), str(current_end)),
            ).fetchone()
            eat_row = connection.execute(
                "SELECT COUNT(*) FROM eaten_events WHERE event_date BETWEEN ? AND ?",
                (str(current_start), str(current_end)),
            ).fetchone()
            ai = {"ready": 0, "failed": 0, "generating": 0}
            for row in connection.execute(
                "SELECT status, COUNT(*) AS total FROM ai_roast_generation_attempts "
                "WHERE generated_date BETWEEN ? AND ? GROUP BY status",
                (str(current_start), str(current_end)),
            ).fetchall():
                if str(row["status"]) in ai:
                    ai[str(row["status"])] = int(row["total"])
            observability = self._analytics_observability(connection)

        observability["query_elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        return {
            "source": "normalized-sql",
            "periods": {"current": current, "previous": previous},
            "deltas": {
                "active_users": delta(current["active_users"], previous["active_users"]),
                "draws": delta(current["draws"], previous["draws"]),
                "new_unlocks": delta(current["new_unlocks"], previous["new_unlocks"]),
            },
            "retention": {
                "returning_users": len(returning),
                "previous_active_users": len(previous_users),
                "new_current_users": len(current_users - previous_users),
                "rate": round(len(returning) / len(previous_users) * 100, 2) if previous_users else 0,
            },
            "activity": activity,
            "catalog": {
                "catalog_count": catalog_size,
                "median_unlocked": percentile(unlocked_counts, 0.5),
                "p90_unlocked": percentile(unlocked_counts, 0.9),
                "zero_collector_count": max(0, catalog_size - len(pig_rows)),
                "long_tail_count": sum(1 for item in pig_rows if 0 < item["collectors"] <= long_tail_limit),
                "top5_draw_share": round(top5_draws / all_draws * 100, 2) if all_draws else 0,
                "distribution": [{"label": label, "users": buckets[label]} for label in labels],
            },
            "platforms": platforms,
            "rising_pigs": rising[:8],
            "operations": {
                "roasts": int(roast_row[0] if roast_row else 0),
                "eats": int(eat_row[0] if eat_row else 0),
                "ai": ai,
            },
            "observability": observability,
        }

'''
replace_once("storage/sqlite_storage.py", sqlite_anchor, sqlite_method + sqlite_anchor)

replace_once("metadata.yaml", 'version: "2.14.0"', 'version: "2.15.0"')
replace_once(
    "updater.py",
    '"User-Agent": "AstrBot-RollPig-Safe-Updater/2.12.0",',
    '"User-Agent": "AstrBot-RollPig-Safe-Updater/2.15.0",',
)
replace_once(
    "CHANGELOG.md",
    "# 更新\n",
    """# 更新
## v2.15.0 (2026-08-04)
### 商业级 Analytics 管理后台
- 管理页改为紧凑的企业级 Analytics 工作台，统一明暗主题、状态语义、组件密度、响应式与无障碍体验。
- 新增只读 `analytics/insights` 聚合接口，展示双周期增长、七日回访、二十八日活动热力、图鉴覆盖分布、平台构成、上升猪猪及玩法运行健康。
- 深度分析只返回聚合数字和猪猪 ID／名称，不返回用户 ID、群号或原始聊天记录；读取失败也不会影响原总览、图鉴和维护功能。
- SQLite 直接聚合规范化表；JSON 后端保留兼容统计路径，不改变现有数据结构、写入逻辑或业务流程。

""",
)

old_release = ROOT / "tests/test_v214_release_contract.py"
old_release.unlink(missing_ok=True)
write(
    "tests/test_v215_release_contract.py",
    '''from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v215_release_contract_and_analytics_assets():
    metadata = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    storage = (ROOT / "storage" / "sqlite_storage.py").read_text(encoding="utf-8")
    loader = (ROOT / "pages" / "pig-manager" / "ui-feedback.js").read_text(encoding="utf-8")
    assert 'version: "2.15.0"' in metadata
    assert 'AstrBot-RollPig/2.15.0' in main
    assert '/analytics/insights' in main
    assert 'get_dashboard_insights' in storage
    assert 'schema_version = 5' in storage
    assert 'sql-primary-v2.14' in storage
    assert './analytics-theme.css' in loader
    assert './ui-analytics.js' in loader
''',
)

write(
    "tests/test_dashboard_insights.py",
    '''from __future__ import annotations

import json

from storage import SQLiteStorage, StorageManager


def _pig(pig_id: str) -> dict:
    return {"id": pig_id, "name": pig_id, "description": "test", "analysis": "test"}


def test_sql_dashboard_insights_are_aggregate_only(tmp_path):
    storage = SQLiteStorage(tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS)
    storage.create_daily_draw(draw_date="2026-07-22", user_id="v2|qq@one|user|1", pig=_pig("pig-a"))
    storage.create_daily_draw(draw_date="2026-07-23", user_id="v2|discord@one|user|2", pig=_pig("pig-b"))
    storage.create_daily_draw(draw_date="2026-07-29", user_id="v2|qq@one|user|1", pig=_pig("pig-a"))
    storage.create_daily_draw(draw_date="2026-08-01", user_id="v2|telegram@one|user|3", pig=_pig("pig-c"))
    storage.increment_roast_count(
        draw_date="2026-08-02", group_id="g", user_id="v2|qq@one|user|1", cutoff_date="2026-07-01"
    )
    storage.increment_roast_count(
        draw_date="2026-08-02", group_id="g", user_id="v2|qq@one|user|1", cutoff_date="2026-07-01"
    )
    claim = storage.claim_ai_roast_generation(
        pig_id="pig-a", generated_date="2026-08-03", owner_token="owner", attempted_at=1.0,
        cutoff_date="2026-07-29", through_date="2026-08-04",
    )
    assert claim["claimed"] is True
    storage.complete_ai_roast_generation(
        pig_id="pig-a", generated_date="2026-08-03", owner_token="owner", content="ready",
        completed_at=2.0, cutoff_date="2026-07-29", through_date="2026-08-04",
    )

    insights = storage.get_dashboard_insights(
        current_start="2026-07-29", current_end="2026-08-04",
        previous_start="2026-07-22", previous_end="2026-07-28",
        activity_start="2026-07-08", catalog_ids=("pig-a", "pig-b", "pig-c", "pig-d"),
    )
    assert insights["source"] == "normalized-sql"
    assert insights["periods"]["current"]["active_users"] == 2
    assert insights["periods"]["previous"]["active_users"] == 2
    assert insights["retention"]["returning_users"] == 1
    assert insights["retention"]["rate"] == 50
    assert insights["catalog"]["zero_collector_count"] == 1
    assert insights["operations"]["roasts"] == 2
    assert insights["operations"]["ai"]["ready"] == 1
    assert insights["rising_pigs"][0]["id"] == "pig-c"
    assert {item["platform"] for item in insights["platforms"]} == {
        "qq@one", "discord@one", "telegram@one"
    }
    encoded = json.dumps(insights, ensure_ascii=False)
    assert "v2|qq@one|user|1" not in encoded
    assert "v2|discord@one|user|2" not in encoded


def test_dashboard_insights_fill_all_twenty_eight_activity_days(tmp_path):
    storage = SQLiteStorage(tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS)
    result = storage.get_dashboard_insights(
        current_start="2026-07-29", current_end="2026-08-04",
        previous_start="2026-07-22", previous_end="2026-07-28",
        activity_start="2026-07-08", catalog_ids=("pig-a",),
    )
    assert len(result["activity"]) == 28
    assert result["activity"][0]["date"] == "2026-07-08"
    assert result["activity"][-1]["date"] == "2026-08-04"
''',
)

feedback_path = ROOT / "tests/test_dashboard_feedback.py"
feedback = feedback_path.read_text(encoding="utf-8")
feedback = feedback.replace(
    'THEME = (ROOT / "pages/pig-manager/enterprise-theme.css").read_text(encoding="utf-8")\n',
    'THEME = (ROOT / "pages/pig-manager/enterprise-theme.css").read_text(encoding="utf-8")\n'
    'ANALYTICS = (ROOT / "pages/pig-manager/ui-analytics.js").read_text(encoding="utf-8")\n'
    'ANALYTICS_THEME = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")\n',
)
feedback = feedback.replace(
    '    assert LOADER.index("./ui-feedback-core.js") < LOADER.index("./ui-enterprise.js")\n',
    '    assert LOADER.index("./ui-feedback-core.js") < LOADER.index("./ui-enterprise.js")\n'
    '    assert "./ui-analytics.js" in LOADER\n'
    '    assert "./analytics-theme.css" in LOADER\n'
    '    assert LOADER.index("./ui-enterprise.js") < LOADER.index("./ui-analytics.js")\n',
)
feedback += '''

def test_commercial_analytics_layer_is_read_only_responsive_and_resilient():
    for marker in (
        "analytics/insights",
        "analyticsSuite",
        "activity-heatmap",
        "retention-ring",
        "rising-table",
        "renderError",
        "analyticsRetry",
    ):
        assert marker in ANALYTICS
    assert "apiPost" not in ANALYTICS
    assert "@media (max-width: 620px)" in ANALYTICS_THEME
    assert "@media (prefers-reduced-motion: reduce)" in ANALYTICS_THEME
    assert ".analytics-kpis" in ANALYTICS_THEME
    assert ".analytics-grid" in ANALYTICS_THEME


def test_read_only_analytics_route_is_registered():
    assert "/analytics/insights" in MAIN
    assert "page_analytics_insights" in MAIN
    assert "不返回用户、群组或聊天原始标识" in MAIN
'''
feedback_path.write_text(feedback, encoding="utf-8")

print("v2.15 analytics integration applied")
