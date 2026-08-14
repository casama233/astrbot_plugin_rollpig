from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQLITE = ROOT / "storage" / "sqlite_storage.py"
LEGACY = ROOT / "legacy_main.py"
MAIN = ROOT / "main.py"
CHANGELOG = ROOT / "CHANGELOG.md"
TEST = ROOT / "tests" / "test_dashboard_accuracy_contract.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, got {count}")
    return updated


# ---------------------------------------------------------------------------
# SQLite analytics: explicit claim-aware logical-user facts.
# ---------------------------------------------------------------------------
sqlite = SQLITE.read_text(encoding="utf-8")

overview_method = r'''    def get_dashboard_overview(
        self,
        *,
        start_date: str,
        end_date: str,
        catalog_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        """Aggregate dashboard facts with claim-aware logical-user identity."""
        started = time.monotonic()
        catalog = {str(item) for item in catalog_ids if str(item)}
        with self._lock, self._connection() as connection:
            summary = connection.execute(
                "WITH logical_stats AS ("
                "  SELECT COALESCE(ic.namespaced_id, us.user_id) AS logical_user, "
                "         MAX(CASE WHEN us.user_id = COALESCE(ic.namespaced_id, us.user_id) "
                "                  THEN us.total_draws END) AS authoritative_draws, "
                "         MAX(us.total_draws) AS fallback_draws "
                "  FROM user_stats us LEFT JOIN identity_claims ic "
                "    ON ic.claim_kind = 'users' AND ic.legacy_id = us.user_id "
                "  GROUP BY COALESCE(ic.namespaced_id, us.user_id)"
                ") SELECT COUNT(*) AS users, "
                "COALESCE(SUM(COALESCE(authoritative_draws, fallback_draws)), 0) AS draws "
                "FROM logical_stats"
            ).fetchone()
            total_users = int(summary["users"] if summary else 0)
            total_draws = int(summary["draws"] if summary else 0)

            pig_rows = connection.execute(
                "WITH logical_pigs AS ("
                "  SELECT COALESCE(ic.namespaced_id, up.user_id) AS logical_user, "
                "         up.pig_id, MAX(up.draw_count) AS draw_count "
                "  FROM user_pigs up LEFT JOIN identity_claims ic "
                "    ON ic.claim_kind = 'users' AND ic.legacy_id = up.user_id "
                "  GROUP BY COALESCE(ic.namespaced_id, up.user_id), up.pig_id"
                ") SELECT pig_id, COALESCE(SUM(draw_count), 0) AS draws, "
                "COUNT(*) AS collectors FROM logical_pigs GROUP BY pig_id"
            ).fetchall()
            pig_stats = [
                {
                    "id": str(row["pig_id"]),
                    "draws": int(row["draws"]),
                    "collectors": int(row["collectors"]),
                }
                for row in pig_rows
                if str(row["pig_id"]) in catalog
            ]
            unlocked_total = sum(item["collectors"] for item in pig_stats)
            average_unlocked = unlocked_total / total_users if total_users else 0.0
            average_rate = average_unlocked / len(catalog) * 100 if catalog else 0.0
            top_pigs = sorted(
                pig_stats,
                key=lambda item: (-item["draws"], -item["collectors"], item["id"]),
            )[:10]

            trend = [
                {
                    "date": str(row["draw_date"]),
                    "users": int(row["users"]),
                    "draws": int(row["draws"]),
                    "new_unlocks": int(row["new_unlocks"]),
                }
                for row in connection.execute(
                    "WITH logical_days AS ("
                    "  SELECT d.draw_date, COALESCE(ic.namespaced_id, d.user_id) AS logical_user, "
                    "         MAX(d.was_new_unlock) AS was_new_unlock "
                    "  FROM daily_draws d LEFT JOIN identity_claims ic "
                    "    ON ic.claim_kind = 'users' AND ic.legacy_id = d.user_id "
                    "  WHERE d.draw_date BETWEEN ? AND ? "
                    "  GROUP BY d.draw_date, COALESCE(ic.namespaced_id, d.user_id)"
                    ") SELECT draw_date, COUNT(*) AS users, COUNT(*) AS draws, "
                    "COALESCE(SUM(was_new_unlock), 0) AS new_unlocks "
                    "FROM logical_days GROUP BY draw_date ORDER BY draw_date",
                    (str(start_date), str(end_date)),
                ).fetchall()
            ]
            observability = self._analytics_observability(connection)

        observability["identity_scope"] = "claim-aware-logical-users"
        observability["query_elapsed_ms"] = round(
            (time.monotonic() - started) * 1000, 3
        )
        return {
            "total_users": total_users,
            "total_draws": total_draws,
            "average_unlocked": average_unlocked,
            "average_unlock_rate": average_rate,
            "trend": trend,
            "top_pigs": top_pigs,
            "observability": observability,
        }
'''

sqlite = replace_regex_once(
    sqlite,
    r"    def get_dashboard_overview\(.*?(?=\n    def get_dashboard_insights\()",
    overview_method.rstrip(),
    "replace dashboard overview",
)

insights_method = r'''    def get_dashboard_insights(
        self,
        *,
        current_start: str,
        current_end: str,
        previous_start: str,
        previous_end: str,
        activity_start: str,
        catalog_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        """Return aggregate-only analytics over claim-aware logical-user facts."""
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

            # Build short-lived logical facts.  A legacy fragment is folded only
            # when identity_claims explicitly proves that it belongs to the
            # namespaced user.  Overlapping ownership counters use MAX, matching
            # CollectionService and avoiding EX/stat inflation from migration copies.
            connection.execute(
                "CREATE TEMP TABLE IF NOT EXISTS dashboard_logical_users("
                "user_id TEXT PRIMARY KEY)"
            )
            connection.execute("DELETE FROM dashboard_logical_users")
            connection.execute(
                "INSERT OR IGNORE INTO dashboard_logical_users(user_id) "
                "SELECT COALESCE(ic.namespaced_id, us.user_id) "
                "FROM user_stats us LEFT JOIN identity_claims ic "
                "ON ic.claim_kind = 'users' AND ic.legacy_id = us.user_id "
                "GROUP BY COALESCE(ic.namespaced_id, us.user_id)"
            )

            connection.execute(
                "CREATE TEMP TABLE IF NOT EXISTS dashboard_logical_pigs("
                "user_id TEXT NOT NULL, pig_id TEXT NOT NULL, draw_count INTEGER NOT NULL, "
                "PRIMARY KEY(user_id, pig_id))"
            )
            connection.execute("DELETE FROM dashboard_logical_pigs")
            connection.execute(
                "INSERT INTO dashboard_logical_pigs(user_id, pig_id, draw_count) "
                "SELECT COALESCE(ic.namespaced_id, up.user_id), up.pig_id, MAX(up.draw_count) "
                "FROM user_pigs up "
                "INNER JOIN dashboard_catalog_ids c ON c.pig_id = up.pig_id "
                "LEFT JOIN identity_claims ic "
                "ON ic.claim_kind = 'users' AND ic.legacy_id = up.user_id "
                "GROUP BY COALESCE(ic.namespaced_id, up.user_id), up.pig_id"
            )

            connection.execute(
                "CREATE TEMP TABLE IF NOT EXISTS dashboard_logical_draws("
                "draw_date TEXT NOT NULL, user_id TEXT NOT NULL, pig_id TEXT NOT NULL, "
                "was_new_unlock INTEGER NOT NULL, PRIMARY KEY(draw_date, user_id))"
            )
            connection.execute("DELETE FROM dashboard_logical_draws")
            connection.execute(
                "INSERT INTO dashboard_logical_draws(draw_date, user_id, pig_id, was_new_unlock) "
                "SELECT draw_date, logical_user, effective_pig, logical_new_unlock FROM ("
                "  SELECT d.draw_date, COALESCE(ic.namespaced_id, d.user_id) AS logical_user, "
                "         COALESCE(NULLIF(d.original_pig_id, ''), d.pig_id) AS effective_pig, "
                "         MAX(d.was_new_unlock) OVER ("
                "           PARTITION BY d.draw_date, COALESCE(ic.namespaced_id, d.user_id)"
                "         ) AS logical_new_unlock, "
                "         ROW_NUMBER() OVER ("
                "           PARTITION BY d.draw_date, COALESCE(ic.namespaced_id, d.user_id) "
                "           ORDER BY CASE WHEN d.user_id = COALESCE(ic.namespaced_id, d.user_id) "
                "                         THEN 0 ELSE 1 END, d.user_id"
                "         ) AS rank_value "
                "  FROM daily_draws d LEFT JOIN identity_claims ic "
                "  ON ic.claim_kind = 'users' AND ic.legacy_id = d.user_id "
                "  WHERE d.draw_date BETWEEN ? AND ?"
                ") WHERE rank_value = 1",
                (str(activity_start), str(current_end)),
            )

            def summary(start_date: str, end_date: str) -> dict[str, Any]:
                row = connection.execute(
                    "SELECT COUNT(DISTINCT user_id) AS active_users, "
                    "COUNT(*) AS draws, COALESCE(SUM(was_new_unlock), 0) AS new_unlocks "
                    "FROM dashboard_logical_draws WHERE draw_date BETWEEN ? AND ?",
                    (start_date, end_date),
                ).fetchone()
                day_rows = connection.execute(
                    "SELECT draw_date, COUNT(*) AS users FROM dashboard_logical_draws "
                    "WHERE draw_date BETWEEN ? AND ? GROUP BY draw_date",
                    (start_date, end_date),
                ).fetchall()
                date_module = __import__("datetime").date
                days = max(
                    1,
                    (date_module.fromisoformat(end_date) - date_module.fromisoformat(start_date)).days
                    + 1,
                )
                draws = int(row["draws"] if row else 0)
                unlocks = int(row["new_unlocks"] if row else 0)
                return {
                    "start": start_date,
                    "end": end_date,
                    "active_users": int(row["active_users"] if row else 0),
                    "draws": draws,
                    "new_unlocks": unlocks,
                    "avg_daily_users": round(
                        sum(int(item["users"]) for item in day_rows) / days, 2
                    ),
                    "unlock_efficiency": round(unlocks / draws * 100, 2) if draws else 0,
                }

            current = summary(str(current_start), str(current_end))
            previous = summary(str(previous_start), str(previous_end))
            current_users = {
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT user_id FROM dashboard_logical_draws "
                    "WHERE draw_date BETWEEN ? AND ?",
                    (str(current_start), str(current_end)),
                ).fetchall()
            }
            previous_users = {
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT user_id FROM dashboard_logical_draws "
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
                    "SELECT draw_date, COUNT(*) AS users, COUNT(*) AS draws, "
                    "COALESCE(SUM(was_new_unlock), 0) AS new_unlocks "
                    "FROM dashboard_logical_draws WHERE draw_date BETWEEN ? AND ? "
                    "GROUP BY draw_date ORDER BY draw_date",
                    (str(activity_start), str(current_end)),
                ).fetchall()
            }

            logical_roast_rows = connection.execute(
                "WITH logical_roasts AS ("
                " SELECT r.draw_date, r.group_id, COALESCE(ic.namespaced_id, r.user_id) AS logical_user, "
                "        MAX(r.roast_count) AS roast_count "
                " FROM daily_roast_counts r LEFT JOIN identity_claims ic "
                " ON ic.claim_kind = 'users' AND ic.legacy_id = r.user_id "
                " WHERE r.draw_date BETWEEN ? AND ? "
                " GROUP BY r.draw_date, r.group_id, COALESCE(ic.namespaced_id, r.user_id)"
                ") SELECT draw_date, COALESCE(SUM(roast_count), 0) AS total "
                "FROM logical_roasts GROUP BY draw_date",
                (str(activity_start), str(current_end)),
            ).fetchall()
            for row in logical_roast_rows:
                daily_rows.setdefault(
                    str(row["draw_date"]),
                    {
                        "date": str(row["draw_date"]),
                        "users": 0,
                        "draws": 0,
                        "new_unlocks": 0,
                        "roasts": 0,
                        "eats": 0,
                    },
                )["roasts"] = int(row["total"])
            for row in connection.execute(
                "SELECT event_date, COUNT(*) AS total FROM eaten_events "
                "WHERE event_date BETWEEN ? AND ? GROUP BY event_date",
                (str(activity_start), str(current_end)),
            ).fetchall():
                daily_rows.setdefault(
                    str(row["event_date"]),
                    {
                        "date": str(row["event_date"]),
                        "users": 0,
                        "draws": 0,
                        "new_unlocks": 0,
                        "roasts": 0,
                        "eats": 0,
                    },
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
                        {
                            "date": key,
                            "users": 0,
                            "draws": 0,
                            "new_unlocks": 0,
                            "roasts": 0,
                            "eats": 0,
                        },
                    )
                )
                cursor += one_day

            unlocked_counts = [
                int(row["unlocked"])
                for row in connection.execute(
                    "SELECT u.user_id, COUNT(p.pig_id) AS unlocked "
                    "FROM dashboard_logical_users u LEFT JOIN dashboard_logical_pigs p "
                    "ON p.user_id = u.user_id GROUP BY u.user_id"
                ).fetchall()
            ]
            pig_rows = [
                {
                    "id": str(row["pig_id"]),
                    "draws": int(row["draws"]),
                    "collectors": int(row["collectors"]),
                }
                for row in connection.execute(
                    "SELECT pig_id, COALESCE(SUM(draw_count), 0) AS draws, "
                    "COUNT(*) AS collectors FROM dashboard_logical_pigs GROUP BY pig_id"
                ).fetchall()
            ]
            catalog_size = len(catalog)
            labels = ("0–10%", "10–25%", "25–50%", "50–75%", "75–100%")
            buckets = {label: 0 for label in labels}
            for unlocked in unlocked_counts:
                ratio = unlocked / catalog_size * 100 if catalog_size else 0
                label = (
                    "0–10%"
                    if ratio <= 10
                    else "10–25%"
                    if ratio <= 25
                    else "25–50%"
                    if ratio <= 50
                    else "50–75%"
                    if ratio <= 75
                    else "75–100%"
                )
                buckets[label] += 1
            total_users = len(unlocked_counts)
            long_tail_limit = max(1, int(total_users * 0.01 + 0.999999))
            all_draws = sum(item["draws"] for item in pig_rows)
            top5_draws = sum(
                sorted((item["draws"] for item in pig_rows), reverse=True)[:5]
            )

            rising = [
                {
                    "id": str(row["pig_id"]),
                    "current": int(row["current_draws"]),
                    "previous": int(row["previous_draws"]),
                    "delta": int(row["current_draws"]) - int(row["previous_draws"]),
                }
                for row in connection.execute(
                    "SELECT d.pig_id, "
                    "SUM(CASE WHEN d.draw_date BETWEEN ? AND ? THEN 1 ELSE 0 END) AS current_draws, "
                    "SUM(CASE WHEN d.draw_date BETWEEN ? AND ? THEN 1 ELSE 0 END) AS previous_draws "
                    "FROM dashboard_logical_draws d INNER JOIN dashboard_catalog_ids c "
                    "ON c.pig_id = d.pig_id WHERE d.draw_date BETWEEN ? AND ? GROUP BY d.pig_id",
                    (
                        str(current_start),
                        str(current_end),
                        str(previous_start),
                        str(previous_end),
                        str(previous_start),
                        str(current_end),
                    ),
                ).fetchall()
            ]
            rising.sort(
                key=lambda item: (-item["delta"], -item["current"], item["id"])
            )

            platforms = [
                {"platform": str(row["namespace"]), "users": int(row["users"])}
                for row in connection.execute(
                    "SELECT i.namespace, COUNT(*) AS users FROM dashboard_logical_users u "
                    "INNER JOIN identities i ON i.identity_key = u.user_id "
                    "WHERE i.identity_type = 'user' GROUP BY i.namespace "
                    "ORDER BY users DESC, i.namespace LIMIT 8"
                ).fetchall()
            ]
            roast_row = connection.execute(
                "WITH logical_roasts AS ("
                " SELECT r.draw_date, r.group_id, COALESCE(ic.namespaced_id, r.user_id) AS logical_user, "
                "        MAX(r.roast_count) AS roast_count "
                " FROM daily_roast_counts r LEFT JOIN identity_claims ic "
                " ON ic.claim_kind = 'users' AND ic.legacy_id = r.user_id "
                " WHERE r.draw_date BETWEEN ? AND ? "
                " GROUP BY r.draw_date, r.group_id, COALESCE(ic.namespaced_id, r.user_id)"
                ") SELECT COALESCE(SUM(roast_count), 0) FROM logical_roasts",
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

        observability["identity_scope"] = "claim-aware-logical-users"
        observability["query_elapsed_ms"] = round(
            (time.monotonic() - started) * 1000, 3
        )
        return {
            "source": "normalized-sql",
            "periods": {"current": current, "previous": previous},
            "deltas": {
                "active_users": delta(current["active_users"], previous["active_users"]),
                "draws": delta(current["draws"], previous["draws"]),
                "new_unlocks": delta(
                    current["new_unlocks"], previous["new_unlocks"]
                ),
            },
            "retention": {
                "returning_users": len(returning),
                "previous_active_users": len(previous_users),
                "new_current_users": len(current_users - previous_users),
                "rate": round(len(returning) / len(previous_users) * 100, 2)
                if previous_users
                else 0,
            },
            "activity": activity,
            "catalog": {
                "catalog_count": catalog_size,
                "median_unlocked": percentile(unlocked_counts, 0.5),
                "p90_unlocked": percentile(unlocked_counts, 0.9),
                "zero_collector_count": max(0, catalog_size - len(pig_rows)),
                "long_tail_count": sum(
                    1
                    for item in pig_rows
                    if 0 < item["collectors"] <= long_tail_limit
                ),
                "top5_draw_share": round(top5_draws / all_draws * 100, 2)
                if all_draws
                else 0,
                "distribution": [
                    {"label": label, "users": buckets[label]} for label in labels
                ],
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

sqlite = replace_regex_once(
    sqlite,
    r"    def get_dashboard_insights\(.*?(?=\n    def get_user_collection\()",
    insights_method.rstrip(),
    "replace dashboard insights",
)
SQLITE.write_text(sqlite, encoding="utf-8")


# ---------------------------------------------------------------------------
# JSON compatibility path: use the same claim-aware ownership model.
# ---------------------------------------------------------------------------
legacy = LEGACY.read_text(encoding="utf-8")
old_aggregate = '''    def _catalog_aggregates(self) -> tuple[Counter, Counter]:\n        draws: Counter = Counter()\n        collectors: Counter = Counter()\n        for user in self.history.get("users", {}).values():\n            for pig_id, record in user.get("pigs", {}).items():\n                draws[pig_id] += int(record.get("count", 0))\n                collectors[pig_id] += 1\n        return draws, collectors\n'''
new_aggregate = '''    def _dashboard_canonical_user_id(self, user_id: str) -> str:\n        raw = str(user_id or "")\n        claims_root = self.history.get("identity_claims", {}) if isinstance(self.history, dict) else {}\n        claims = claims_root.get("users", {}) if isinstance(claims_root, dict) else {}\n        return str(claims.get(raw) or raw) if isinstance(claims, dict) else raw\n\n    def _dashboard_logical_users(self) -> dict[str, dict]:\n        users = self.history.get("users", {}) if isinstance(self.history, dict) else {}\n        users = users if isinstance(users, dict) else {}\n        buckets: dict[str, list[tuple[str, dict]]] = {}\n        for raw_id, raw_user in users.items():\n            if not isinstance(raw_user, dict):\n                continue\n            user_id = str(raw_id or "")\n            canonical = self._dashboard_canonical_user_id(user_id)\n            buckets.setdefault(canonical, []).append((user_id, raw_user))\n\n        logical: dict[str, dict] = {}\n        for canonical, fragments in buckets.items():\n            fragments.sort(key=lambda item: (0 if item[0] == canonical else 1, item[0]))\n            logical[canonical] = self.collection_service.merge_ownership(\n                [item[1] for item in fragments]\n            )\n        return logical\n\n    def _dashboard_json_day_facts(\n        self, day_key: str, item: dict, logical_users: dict[str, dict] | None = None\n    ) -> dict:\n        item = item if isinstance(item, dict) else {}\n        logical_users = logical_users if logical_users is not None else self._dashboard_logical_users()\n        records = item.get("records", {})\n        records = records if isinstance(records, dict) else {}\n        originals = item.get("eaten_originals", {})\n        originals = originals if isinstance(originals, dict) else {}\n        canonical_records: dict[str, str] = {}\n        canonical_priority: dict[str, int] = {}\n        for raw_user, raw_pig in records.items():\n            raw_user = str(raw_user or "")\n            canonical = self._dashboard_canonical_user_id(raw_user)\n            priority = 0 if raw_user == canonical else 1\n            if canonical in canonical_records and canonical_priority[canonical] <= priority:\n                continue\n            pig_id = str(originals.get(raw_user) or raw_pig or "")\n            canonical_records[canonical] = pig_id\n            canonical_priority[canonical] = priority\n\n        active = {\n            self._dashboard_canonical_user_id(str(value))\n            for value in item.get("users", [])\n            if str(value)\n        }\n        active.update(canonical_records)\n        new_unlocks = 0\n        for canonical, pig_id in canonical_records.items():\n            user = logical_users.get(canonical, {})\n            pigs = user.get("pigs", {}) if isinstance(user, dict) else {}\n            record = pigs.get(pig_id, {}) if isinstance(pigs, dict) else {}\n            if isinstance(record, dict) and str(record.get("first_unlocked") or "") == day_key:\n                new_unlocks += 1\n        if not canonical_records:\n            new_unlocks = int(item.get("new_unlocks", 0) or 0)\n        return {\n            "users": active,\n            "draws": len(canonical_records) if canonical_records else len(active),\n            "new_unlocks": new_unlocks,\n            "records": canonical_records,\n        }\n\n    def _catalog_aggregates(self) -> tuple[Counter, Counter]:\n        draws: Counter = Counter()\n        collectors: Counter = Counter()\n        for user in self._dashboard_logical_users().values():\n            for pig_id, record in user.get("pigs", {}).items():\n                if not isinstance(record, dict):\n                    continue\n                draws[pig_id] += int(record.get("count", 0) or 0)\n                collectors[pig_id] += 1\n        return draws, collectors\n'''
legacy = replace_once(legacy, old_aggregate, new_aggregate, "claim-aware json aggregates")

legacy = replace_once(
    legacy,
    '            catalog_ids = {str(pig.get("id")) for pig in self.pig_list}\n',
    '            catalog_ids = {\n                str(pig.get("id") or "")\n                for pig in self.pig_list\n                if str(pig.get("id") or "")\n            }\n',
    "filter empty overview catalog ids",
)

sql_return_old = '''                    "trend": trend,\n                    "top_pigs": top_pigs,\n                    "analytics": stored.get("observability", {}),\n                }\n            total_users = len(users)\n            total_draws = sum(int(u.get("total_draws", 0)) for u in users.values())\n            unlocked_counts = [\n                len(set(u.get("pigs", {})).intersection(catalog_ids))\n                for u in users.values()\n            ]\n'''
sql_return_new = '''                    "trend": trend,\n                    "top_pigs": top_pigs,\n                    "analytics": stored.get("observability", {}),\n                    "meta": {\n                        "source": "normalized-sql",\n                        "identity_scope": "claim-aware-logical-users",\n                        "trend_days": 14,\n                        "catalog_scope": "active",\n                        "as_of": today.isoformat(),\n                    },\n                }\n            logical_users = self._dashboard_logical_users()\n            total_users = len(logical_users)\n            total_draws = sum(\n                int(user.get("total_draws", 0) or 0)\n                for user in logical_users.values()\n            )\n            unlocked_counts = [\n                len(set(user.get("pigs", {})).intersection(catalog_ids))\n                for user in logical_users.values()\n            ]\n'''
legacy = replace_once(legacy, sql_return_old, sql_return_new, "overview logical users + meta")

trend_old = '''            daily = self.history.get("daily", {})\n            trend = []\n            for offset in range(13, -1, -1):\n                day = today - datetime.timedelta(days=offset)\n                item = daily.get(day.isoformat(), {})\n                trend.append(\n                    {\n                        "date": f"{day.month}/{day.day}",\n                        "users": len(item.get("users", [])),\n                        "draws": int(item.get("draws", 0)),\n                        "new_unlocks": int(item.get("new_unlocks", 0)),\n                    }\n                )\n'''
trend_new = '''            daily = self.history.get("daily", {})\n            trend = []\n            for offset in range(13, -1, -1):\n                day = today - datetime.timedelta(days=offset)\n                day_key = day.isoformat()\n                facts = self._dashboard_json_day_facts(\n                    day_key, daily.get(day_key, {}), logical_users\n                )\n                trend.append(\n                    {\n                        "date": f"{day.month}/{day.day}",\n                        "users": len(facts["users"]),\n                        "draws": int(facts["draws"]),\n                        "new_unlocks": int(facts["new_unlocks"]),\n                    }\n                )\n'''
legacy = replace_once(legacy, trend_old, trend_new, "overview json daily facts")

json_return_old = '''            today_item = daily.get(today.isoformat(), {})\n            return {\n                "metrics": {\n                    "total_users": total_users,\n                    "total_draws": total_draws,\n                    "catalog_count": len(catalog_ids),\n                    "today_users": len(today_item.get("users", [])),\n                    "average_unlocked": round(average_unlocked, 2),\n                    "average_unlock_rate": round(average_rate, 2),\n                },\n                "trend": trend,\n                "top_pigs": top_pigs,\n            }\n'''
json_return_new = '''            today_key = today.isoformat()\n            today_facts = self._dashboard_json_day_facts(\n                today_key, daily.get(today_key, {}), logical_users\n            )\n            return {\n                "metrics": {\n                    "total_users": total_users,\n                    "total_draws": total_draws,\n                    "catalog_count": len(catalog_ids),\n                    "today_users": len(today_facts["users"]),\n                    "average_unlocked": round(average_unlocked, 2),\n                    "average_unlock_rate": round(average_rate, 2),\n                },\n                "trend": trend,\n                "top_pigs": top_pigs,\n                "analytics": {\n                    "analytics_source": "json-compatibility",\n                    "identity_scope": "claim-aware-logical-users",\n                },\n                "meta": {\n                    "source": "json-compatibility",\n                    "identity_scope": "claim-aware-logical-users",\n                    "trend_days": 14,\n                    "catalog_scope": "active",\n                    "as_of": today.isoformat(),\n                },\n            }\n'''
legacy = replace_once(legacy, json_return_old, json_return_new, "overview json meta")

# JSON deep analytics uses canonical identity for period, coverage and rising rows.
legacy = replace_once(
    legacy,
    '''            users = history.get("users", {})\n            users = users if isinstance(users, dict) else {}\n            daily = history.get("daily", {})\n''',
    '''            users = self._dashboard_logical_users()\n            daily = history.get("daily", {})\n''',
    "deep json logical users",
)

old_day_users = '''            def day_users(day: datetime.date) -> set[str]:\n                item = daily.get(day.isoformat(), {})\n                values = item.get("users", []) if isinstance(item, dict) else []\n                return {str(value) for value in values if str(value)}\n'''
new_day_users = '''            def day_users(day: datetime.date) -> set[str]:\n                key = day.isoformat()\n                return set(\n                    self._dashboard_json_day_facts(key, daily.get(key, {}), users)[\n                        "users"\n                    ]\n                )\n'''
legacy = replace_once(legacy, old_day_users, new_day_users, "deep day users")

old_period_loop = '''                    item = daily.get(cursor.isoformat(), {})\n                    if isinstance(item, dict):\n                        active.update(str(value) for value in item.get("users", []) if str(value))\n                        draws += int(item.get("draws", 0) or 0)\n                        unlocks += int(item.get("new_unlocks", 0) or 0)\n                    cursor += datetime.timedelta(days=1)\n'''
new_period_loop = '''                    key = cursor.isoformat()\n                    facts = self._dashboard_json_day_facts(\n                        key, daily.get(key, {}), users\n                    )\n                    active.update(facts["users"])\n                    draws += int(facts["draws"])\n                    unlocks += int(facts["new_unlocks"])\n                    cursor += datetime.timedelta(days=1)\n'''
legacy = replace_once(legacy, old_period_loop, new_period_loop, "deep period facts")

old_activity = '''                item = daily.get(key, {})\n                item = item if isinstance(item, dict) else {}\n                activity.append(\n                    {\n                        "date": key,\n                        "users": len({str(value) for value in item.get("users", []) if str(value)}),\n                        "draws": int(item.get("draws", 0) or 0),\n                        "new_unlocks": int(item.get("new_unlocks", 0) or 0),\n                        "roasts": int(roast_by_date.get(key, 0)),\n                        "eats": int(eat_by_date.get(key, 0)),\n                    }\n                )\n'''
new_activity = '''                facts = self._dashboard_json_day_facts(key, daily.get(key, {}), users)\n                activity.append(\n                    {\n                        "date": key,\n                        "users": len(facts["users"]),\n                        "draws": int(facts["draws"]),\n                        "new_unlocks": int(facts["new_unlocks"]),\n                        "roasts": int(roast_by_date.get(key, 0)),\n                        "eats": int(eat_by_date.get(key, 0)),\n                    }\n                )\n'''
legacy = replace_once(legacy, old_activity, new_activity, "deep activity facts")

legacy = replace_once(
    legacy,
    '            long_tail_limit = max(1, int(len(users) * 0.01 + 0.999999))\n',
    '            long_tail_limit = max(1, int(len(unlocked_counts) * 0.01 + 0.999999))\n',
    "deep long-tail logical denominator",
)

old_rising_records = '''                item = daily.get(cursor.isoformat(), {})\n                records = item.get("records", {}) if isinstance(item, dict) else {}\n                originals = item.get("eaten_originals", {}) if isinstance(item, dict) else {}\n                bucket = "current" if cursor >= current_start else "previous"\n                for user_id, pig_id in records.items() if isinstance(records, dict) else ():\n                    pig_id = str(pig_id or "")\n                    effective = str(originals.get(user_id) or pig_id) if isinstance(originals, dict) else pig_id\n                    if effective in catalog:\n                        period_pigs[bucket][effective] += 1\n'''
new_rising_records = '''                key = cursor.isoformat()\n                facts = self._dashboard_json_day_facts(key, daily.get(key, {}), users)\n                bucket = "current" if cursor >= current_start else "previous"\n                for effective in facts["records"].values():\n                    if effective in catalog:\n                        period_pigs[bucket][effective] += 1\n'''
legacy = replace_once(legacy, old_rising_records, new_rising_records, "deep rising logical records")

# Version is bumped because the analytics JS/CSS bundle changes in the companion patch.
legacy = legacy.replace('UI_ASSET_VERSION = "3.1.2"', 'UI_ASSET_VERSION = "3.2.0"')
LEGACY.write_text(legacy, encoding="utf-8")

main = MAIN.read_text(encoding="utf-8")
main = replace_once(
    main,
    '    UI_ASSET_VERSION = "3.1.2"\n',
    '    UI_ASSET_VERSION = "3.2.0"\n',
    "main ui asset version",
)
MAIN.write_text(main, encoding="utf-8")


# ---------------------------------------------------------------------------
# Regression contracts: overlapping claimed fragments must never double count.
# ---------------------------------------------------------------------------
TEST.write_text(
    '''from __future__ import annotations\n\nfrom pathlib import Path\n\nfrom storage import SQLiteStorage, StorageManager\n\n\ndef _pig(pig_id: str) -> dict:\n    return {\n        "id": pig_id,\n        "name": pig_id,\n        "description": "test",\n        "analysis": "test",\n    }\n\n\ndef test_claimed_identity_fragments_do_not_double_count_dashboard(tmp_path):\n    storage = SQLiteStorage(\n        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS\n    )\n    canonical = "v2|qq@one|user|1"\n    legacy = "1"\n    storage.create_daily_draw(\n        draw_date="2026-08-01", user_id=canonical, pig=_pig("pig-a")\n    )\n    storage.create_daily_draw(\n        draw_date="2026-08-01", user_id=legacy, pig=_pig("pig-a")\n    )\n    with storage.transaction() as connection:\n        connection.execute(\n            "INSERT OR REPLACE INTO identity_claims(claim_kind, legacy_id, namespaced_id) "\n            "VALUES ('users', ?, ?)",\n            (legacy, canonical),\n        )\n\n    overview = storage.get_dashboard_overview(\n        start_date="2026-08-01",\n        end_date="2026-08-14",\n        catalog_ids=("pig-a", "pig-b"),\n    )\n    assert overview["total_users"] == 1\n    assert overview["total_draws"] == 1\n    assert overview["average_unlocked"] == 1\n    assert overview["average_unlock_rate"] == 50\n    assert overview["top_pigs"] == [\n        {"id": "pig-a", "draws": 1, "collectors": 1}\n    ]\n    assert overview["trend"] == [\n        {\n            "date": "2026-08-01",\n            "users": 1,\n            "draws": 1,\n            "new_unlocks": 1,\n        }\n    ]\n    assert overview["observability"]["identity_scope"] == (\n        "claim-aware-logical-users"\n    )\n\n\ndef test_claimed_identity_fragments_do_not_distort_deep_analytics(tmp_path):\n    storage = SQLiteStorage(\n        tmp_path / "rollpig.db", tmp_path, StorageManager.MANAGED_PATHS\n    )\n    canonical = "v2|qq@one|user|1"\n    legacy = "1"\n    for user_id in (canonical, legacy):\n        storage.create_daily_draw(\n            draw_date="2026-08-01", user_id=user_id, pig=_pig("pig-a")\n        )\n    with storage.transaction() as connection:\n        connection.execute(\n            "INSERT OR REPLACE INTO identity_claims(claim_kind, legacy_id, namespaced_id) "\n            "VALUES ('users', ?, ?)",\n            (legacy, canonical),\n        )\n\n    insights = storage.get_dashboard_insights(\n        current_start="2026-08-01",\n        current_end="2026-08-07",\n        previous_start="2026-07-25",\n        previous_end="2026-07-31",\n        activity_start="2026-07-11",\n        catalog_ids=("pig-a", "pig-b"),\n    )\n    assert insights["periods"]["current"]["active_users"] == 1\n    assert insights["periods"]["current"]["draws"] == 1\n    assert insights["catalog"]["median_unlocked"] == 1\n    assert insights["catalog"]["zero_collector_count"] == 1\n    assert insights["observability"]["identity_scope"] == (\n        "claim-aware-logical-users"\n    )\n\n\ndef test_core_dashboard_no_longer_fabricates_metric_sparklines():\n    page = Path("pages/pig-manager/index.html").read_text(encoding="utf-8")\n    forbidden = (\n        "catalog-unlocks.slice",\n        "v+(users[i]||0)",\n        "unlocks.map(v=>v/catalog*100)",\n        "数据正在实时生长",\n    )\n    for token in forbidden:\n        assert token not in page\n    assert "chart-draw-bar" in page\n    assert "本地事实快照" in page\n\n\ndef test_deep_analytics_success_rate_excludes_in_progress_attempts():\n    source = Path("pages/pig-manager/ui-analytics.js").read_text(encoding="utf-8")\n    assert "completedAi" in source\n    assert "ready + failed" in source or "ready||0) + Number(ai.failed" in source\n    assert "上期→本期回访率" in source\n    assert "本期独有活跃" in source\n''',
    encoding="utf-8",
)

changelog = CHANGELOG.read_text(encoding="utf-8")
marker = "## 未發佈\n"
addition = '''## 未發佈\n\n### Dashboard Accuracy & Motion\n- 管理面板統計改為 claim-aware logical-user 口徑：SQLite 與 JSON fallback 都不再把已確認屬於同一人的 legacy fragment 重複計入使用者、收藏、熱門豬與週期活躍；重疊收藏次數沿用 `max` 而非相加，避免遷移副本虛增。\n- 修正核心 KPI 的誤導性迷你趨勢：移除以「新解鎖倒推圖鑑數」、「新解鎖 + 活躍人數」等非指標資料拼出的 sparkline；只保留可證明的累計抽取／日活序列與明確標示的當前快照視覺。\n- 深度分析修正 AI 文案成功率分母（只計已完成 ready + failed，不把 generating 當失敗），並把回訪、平台身份與本期獨有活躍的標籤改為精確口徑。\n- Overview / Analytics 新增本地事實快照與資料口徑提示；14/28 日圖表、熱門榜、收藏覆蓋等繼續只輸出聚合資料，不暴露使用者或群組原始 ID。\n'''
if addition not in changelog:
    changelog = replace_once(changelog, marker, addition, "changelog dashboard section")
CHANGELOG.write_text(changelog, encoding="utf-8")
