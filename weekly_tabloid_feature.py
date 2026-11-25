from __future__ import annotations

import asyncio
import datetime
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from astrbot.api import logger, message_components
from astrbot.api.event import MessageChain, filter

try:
    from .daily_report_core import aggregate_daily_report
    from .gameplay_copy import GAMEPLAY_COPY
    from .renderers.weekly_tabloid import render_weekly_tabloid
    from .rollpig_core import parse_config_bool
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_core import aggregate_daily_report
    from gameplay_copy import GAMEPLAY_COPY
    from renderers.weekly_tabloid import render_weekly_tabloid
    from rollpig_core import parse_config_bool


WEEKLY_VOTE_ACTION = "rollpig:weekly_vote"
WEEKLY_STATS = ("active_users", "draws", "roasts", "eats", "escapes", "backlashes")
_STORY_KEYS = ("backlashes", "escapes", "eats", "roasts", "draws")
_AWARD_EVENT_FIELDS = {
    "roast_success": (("roast_maniac", "actor_id"), ("miserable_ingredient", "victim_id")),
    "roast_escape": (("escape_master", "target_id"),),
    "roast_backlash": (
        ("backlash_king", "victim_id"),
        ("miserable_ingredient", "victim_id"),
    ),
}


def _weekly_copy(key: str, **values: object) -> str:
    return GAMEPLAY_COPY[f"weekly_{key}"].format(**values)


class WeeklyTabloidMixin:
    """Weekly group report and persisted Sunday poll."""

    def __init__(self, context, config):
        super().__init__(context, config)
        config = config if hasattr(config, "get") else {}
        self.enable_weekly_tabloid = parse_config_bool(
            config.get("enable_weekly_tabloid", False), False
        )
        self.weekly_tabloid_ai = parse_config_bool(
            config.get("weekly_tabloid_ai", False), False
        )
        self.weekly_tabloid_state_path = self.plugin_data_dir / "weekly_tabloid_state.json"
        loaded = (
            self.load_json(self.weekly_tabloid_state_path, {})
            if self.enable_weekly_tabloid and self.weekly_tabloid_state_path.exists()
            else {}
        )
        self.weekly_tabloid_state = loaded if isinstance(loaded, dict) else {}

    def _weekly_name(self, group_id: str, user_id: str) -> str:
        display = self._profile_for_report(group_id, user_id)["display_name"]
        return " ".join(str(display).split())[:24].replace("@", "＠")

    def _weekly_identity(self, user_id: str) -> str:
        claims = self.history.get("identity_claims", {}).get("users", {})
        return claims.get(user_id) or user_id

    def _weekly_activity(self, group_id: str, day: datetime.date) -> tuple[dict, Counter]:
        start = day - datetime.timedelta(days=day.weekday())
        totals: Counter[str] = Counter()
        draws: Counter[str] = Counter()
        award_counts: dict[str, Counter[str]] = {}
        sacrifices = []
        for offset in range(day.weekday() + 1):
            date_key = (start + datetime.timedelta(days=offset)).isoformat()
            people = {
                self._weekly_identity(user_id)
                for user_id in self._daily_group_members(group_id, date_key)
            }
            draws.update(people)
            events = self._report_events(group_id, date_key)
            daily = aggregate_daily_report(
                [{"user_id": user_id} for user_id in people],
                events,
                self._daily_eaten_victims(group_id, date_key),
                roast_total=self._daily_group_roast_total(group_id, date_key),
            )
            totals.update({key: daily[key] for key in WEEKLY_STATS[1:]})
            for event in events:
                kind = event.get("kind")
                for award, field in _AWARD_EVENT_FIELDS.get(kind, ()):
                    if user_id := event.get(field):
                        award_counts.setdefault(award, Counter())[self._weekly_identity(user_id)] += 1
                if kind == "daily_sacrifice" and (victim := event.get("victim_id")):
                    sacrifices.append((offset + 1, self._weekly_identity(victim)))

        # Prefer frequent draws and use a group/week hash to break ties.
        def rank(user_id: str) -> tuple:
            seed = f"{group_id}\0{day.isoformat()}\0{user_id}"
            return -draws[user_id], hashlib.sha256(seed.encode()).digest(), user_id

        candidates = sorted(draws, key=rank)[:5]
        awards = {}
        for award, counts in award_counts.items():
            peak = max(counts.values())
            awards[award] = {
                "count": peak,
                "players": sorted(user for user, count in counts.items() if count == peak),
            }

        totals["active_users"] = len(draws)
        story_key = next((key for key in _STORY_KEYS if totals[key]), "empty")
        return {
            "start": start.isoformat(),
            "end": day.isoformat(),
            "totals": dict(totals),
            "awards": awards,
            "sacrifices": sacrifices,
            "candidates": candidates if len(candidates) >= 2 else [],
            "story": _weekly_copy(f"story_{story_key}", count=totals[story_key]),
        }, draws

    def _weekly_poll(
        self, group_id: str, sunday: str, *, published: bool = False
    ) -> dict | None:
        groups = self.weekly_tabloid_state.get(sunday)
        poll = groups.get(group_id) if isinstance(groups, dict) else None
        if not isinstance(poll, dict):
            return None
        if not published:
            return poll
        job = self.daily_report_state.get("jobs", {}).get(sunday, {}).get(group_id, {})
        if job.get("report_type") != "weekly" or job.get("skipped"):
            return None
        claims = self.daily_report_delivery_claims
        return poll if claims.read(claims.path_for(group_id, sunday)).get("status") == "sent" else None

    def _save_weekly_poll(self, group_id: str, sunday: str, poll: dict) -> None:
        cutoff = (self._today() - datetime.timedelta(days=14)).isoformat()
        state = {
            day: dict(groups)
            for day, groups in self.weekly_tabloid_state.items()
            if day >= cutoff and isinstance(groups, dict)
        }
        state.setdefault(sunday, {})[group_id] = poll
        self.save_json(self.weekly_tabloid_state_path, state)
        self.weekly_tabloid_state = state

    async def _weekly_llm_story(self, group_id: str, umo: str, report: dict) -> str:
        fallback = report["story"]
        if not self.weekly_tabloid_ai:
            return fallback
        get_provider_id = getattr(self.context, "get_current_chat_provider_id", None)
        get_provider = getattr(self.context, "get_provider_by_id", None)
        generate = getattr(self.context, "llm_generate", None)
        if not all(callable(method) for method in (get_provider_id, get_provider, generate)):
            return fallback
        anonymous: dict[str, str] = {}

        def alias(user_id: str) -> str:
            return anonymous.setdefault(user_id, f"P{len(anonymous) + 1}")

        facts = {
            "totals": report["totals"],
            "awards": {
                kind: {
                    "count": award["count"],
                    "players": [alias(user_id) for user_id in award["players"][:3]],
                }
                for kind, award in report["awards"].items()
            },
            "sacrifices": [
                {"weekday": weekday, "player": alias(user_id)}
                for weekday, user_id in report["sacrifices"]
            ],
        }
        prompt = _weekly_copy("story_prompt", facts=json.dumps(facts, ensure_ascii=False))

        async def request():
            provider_id = await get_provider_id(umo=umo)
            if provider_id:
                provider = get_provider(provider_id)
                if provider and "gemini" in str(provider.get_model()).lower():
                    return await generate(chat_provider_id=provider_id, prompt=prompt)
            return None

        try:
            response = await asyncio.wait_for(request(), timeout=12)
        except Exception as exc:
            logger.debug(f"Weekly RollPig story used local copy ({type(exc).__name__})")
            return fallback
        story = str(getattr(response, "completion_text", "") or "").strip()
        if (
            not 0 < len(story) <= 110
            or story.count("\n") > 1
            or re.search(r"```|https?://|[@<>]|\[CQ:", story, re.IGNORECASE)
        ):
            return fallback

        names = {token: self._weekly_name(group_id, user_id) for user_id, token in anonymous.items()}
        story = re.sub(r"(?<![A-Z0-9])P\d+(?![A-Z0-9])", lambda m: names.get(m[0], m[0]), story)
        return story if len(story) <= 150 else fallback

    def _weekly_poll_text(self, report: dict) -> list[str]:
        if not report["candidates"]:
            return [_weekly_copy("poll_empty")]
        return [
            _weekly_copy("poll_title"),
            _weekly_copy("poll_effect"),
            _weekly_copy("poll_hint"),
            *(
                _weekly_copy("poll_item", number=number, name=report["names"][user_id])
                for number, user_id in enumerate(report["candidates"], start=1)
            ),
        ]

    def _weekly_poll_buttons(self, group_id: str, report: dict):
        platform = self.daily_report_state.get("groups", {}).get(group_id, {}).get("platform", "")
        if not (group_id.startswith("v2|discord@") or platform.startswith("discord@")):
            return None
        if not report["candidates"]:
            return None
        action_row = getattr(message_components, "ActionRow", None)
        button = getattr(message_components, "Button", None)
        if not action_row or not button or not callable(getattr(filter, "button_action", None)):
            return None
        now = self._now()
        if now.date().isoformat() != report["end"]:
            return None
        deadline = datetime.datetime.combine(
            now.date() + datetime.timedelta(days=1), datetime.time.min, tzinfo=now.tzinfo
        )
        return action_row(
            buttons=[
                button(
                    id=WEEKLY_VOTE_ACTION,
                    label=_weekly_copy("poll_item", number=number, name=report["names"][user_id])[:80],
                    action=button.CallbackAction(data={"date": report["end"], "number": number}),
                )
                for number, user_id in enumerate(report["candidates"], start=1)
            ],
            action_timeout=(deadline - now).total_seconds(),
        )

    def _weekly_render_text(self, report: dict, *, preview: bool) -> dict:
        awards = []
        for kind, data in report["awards"].items():
            winners = data["players"]
            names = " / ".join(report["names"][user_id] for user_id in winners[:3])
            if len(winners) > 3:
                names += " …"
            awards.append((_weekly_copy(f"award_{kind}"), names, str(data["count"])))
        return {
            "title": _weekly_copy("title"),
            "story": report["story"],
            "period": f'{report["start"]}  →  {report["end"]}',
            "stats": [
                (_weekly_copy(f"label_{key}"), str(report["totals"][key])) for key in WEEKLY_STATS
            ],
            "awards_title": _weekly_copy("awards_title"),
            "awards": awards,
            "poll": [_weekly_copy("preview_hint")] if preview else self._weekly_poll_text(report),
        }

    async def _weekly_message(
        self, group_id: str, report: dict, *, preview: bool = False
    ) -> tuple[MessageChain, Path | None]:
        text = self._weekly_render_text(report, preview=preview)
        awards = [f"{label} · {players} ({count})" for label, players, count in text["awards"]]
        chain = MessageChain().message(
            "\n".join(
                [
                    text["title"],
                    text["period"],
                    text["story"],
                    _weekly_copy("stats", **report["totals"]),
                    *awards,
                    *text["poll"],
                ]
            )
        )
        output = None
        try:
            output = await asyncio.to_thread(
                self._run_with_render_slot, render_weekly_tabloid, self, text
            )
            chain.file_image(str(output.absolute()))
        except Exception as exc:
            logger.warning(f"Weekly RollPig image used text fallback ({type(exc).__name__})")
            if output is not None:
                output.unlink(missing_ok=True)
                output = None
        if not preview:
            try:
                if row := self._weekly_poll_buttons(group_id, report):
                    chain.chain.append(row)
            except (AttributeError, TypeError, ValueError) as exc:
                logger.debug(f"Weekly RollPig buttons used text choices ({type(exc).__name__})")
        return chain, output

    def _weekly_report_names(self, group_id: str, report: dict) -> dict[str, str]:
        players = set(report["candidates"])
        for award in report["awards"].values():
            players.update(award["players"])
        return {user_id: self._weekly_name(group_id, user_id) for user_id in players}

    async def _prepare_scheduled_weekly_tabloid(
        self, group_id: str, draw_date: str, umo: str
    ) -> tuple[MessageChain, Path | None] | None:
        if not self.enable_weekly_tabloid:
            return None
        today = self._today()
        if today.weekday() != 6 or draw_date != today.isoformat():
            return None
        with self._data_lock:
            poll = self._weekly_poll(group_id, draw_date)
        if poll is None:
            report, players = await asyncio.to_thread(self._weekly_activity, group_id, today)
            if not any(report["totals"].values()) and self.daily_report_skip_empty_groups:
                return None
            report["names"] = self._weekly_report_names(group_id, report)
            report["story"] = await self._weekly_llm_story(group_id, umo, report)
            if self._today() != today:
                return None
            with self._data_lock:
                poll = {"report": report, "eligible": sorted(players), "votes": {}}
                self._save_weekly_poll(group_id, draw_date, poll)
        chain, output = await self._weekly_message(group_id, poll["report"])
        if self._today() != today:
            if output is not None:
                output.unlink(missing_ok=True)
            return None
        return chain, output

    def _weekly_vote(self, group_id: str, voter: str, sunday: str, number: int) -> str:
        with self._data_lock:
            today = self._today()
            if today.weekday() != 6 or today.isoformat() != sunday:
                return _weekly_copy("poll_closed")
            poll = self._weekly_poll(group_id, sunday, published=True)
            if poll is None or not poll["report"]["candidates"]:
                return _weekly_copy("poll_closed")
            report = poll["report"]
            voters = self._user_read_candidates(voter)
            eligible = next((user_id for user_id in voters if user_id in poll["eligible"]), None)
            if eligible is None:
                return _weekly_copy("not_eligible")
            voted = poll["votes"].get(eligible)
            choice = voted if voted is not None else number
            if not 1 <= choice <= len(report["candidates"]):
                return _weekly_copy("vote_usage")
            name = report["names"][report["candidates"][choice - 1]]
            if voted is not None:
                return _weekly_copy("vote_duplicate", number=choice, name=name)
            updated = {**poll, "votes": {**poll["votes"], eligible: choice}}
            try:
                self._save_weekly_poll(group_id, sunday, updated)
            except OSError as exc:
                logger.warning(f"Weekly RollPig vote save failed ({type(exc).__name__})")
                return _weekly_copy("vote_save_failed")
            return _weekly_copy("vote_ok", number=choice, name=name)

    def _weekly_aura(self, group_id: str, user_id: str, day: datetime.date) -> bool:
        if not self.enable_weekly_tabloid or not self.enable_daily_report or day.weekday() != 0:
            return False
        sunday = (day - datetime.timedelta(days=1)).isoformat()
        with self._data_lock:
            poll = self._weekly_poll(group_id, sunday, published=True)
            if poll is None or not poll["votes"]:
                return False
            votes = Counter(poll["votes"].values())
            winner = min(votes, key=lambda number: (-votes[number], number))
            return poll["report"]["candidates"][winner - 1] in self._user_read_candidates(user_id)

    async def _weekly_command(self, event, args: str) -> bool:
        parts = str(args or "").strip().split(maxsplit=1)
        if not parts or parts[0] not in {"八卦", "投票"}:
            return False
        group_id = self._event_group_id(event)
        if not group_id:
            await event.send(event.plain_result(_weekly_copy("vote_only_group")))
            return True
        if not self.enable_weekly_tabloid:
            await event.send(event.plain_result(_weekly_copy("disabled")))
            return True
        if parts[0] == "投票":
            number = parts[1] if len(parts) == 2 else ""
            result = (
                self._weekly_vote(
                    group_id, self._event_sender_id(event), self._today().isoformat(), int(number)
                )
                if re.fullmatch(r"[1-5１-５]", number)
                else _weekly_copy("vote_usage")
            )
            await event.send(event.plain_result(result))
            return True

        today = self._today()
        with self._data_lock:
            poll = self._weekly_poll(group_id, today.isoformat(), published=True)
        if poll is None:
            report, _ = await asyncio.to_thread(self._weekly_activity, group_id, today)
            report["names"] = self._weekly_report_names(group_id, report)
        else:
            report = poll["report"]
        chain, output = await self._weekly_message(group_id, report, preview=poll is None)
        try:
            await event.send(chain)
        finally:
            if output is not None:
                output.unlink(missing_ok=True)
        return True

    async def _weekly_vote_button(self, event) -> None:
        if not self.enable_weekly_tabloid or not self.enable_daily_report:
            return
        group_id = self._event_group_id(event)
        interaction = event.get_button_interaction()
        data = getattr(interaction, "data", None)
        if not group_id or not isinstance(data, dict):
            return
        number = data.get("number")
        sunday = data.get("date")
        if type(number) is not int or not isinstance(sunday, str):
            return
        self._claim_command_event(event)
        result = self._weekly_vote(group_id, self._event_sender_id(event), sunday, number)
        await event.send(event.plain_result(result))
