from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

try:
    from .player_copy import DEFAULT_PLAYER_LOCALE, copy_text
except ImportError:  # pragma: no cover - direct module loading compatibility
    from player_copy import DEFAULT_PLAYER_LOCALE, copy_text


@dataclass(frozen=True)
class HelpEntry:
    command: str
    detail: str
    kind: str = "command"


@dataclass(frozen=True)
class HelpSection:
    title: str
    entries: tuple[HelpEntry, ...]


@dataclass(frozen=True)
class HelpFeatureState:
    at_view_pig: bool = False
    enable_new_pig_pity: bool = True
    enable_daily_duplicate_pity: bool = True
    enable_roast: bool = True
    enable_group_roast: bool = True
    enable_roast_reservation: bool = True
    enable_oven_refill: bool = True
    enable_group_eat: bool = True
    enable_roast_protection: bool = True
    enable_ai_roast_copy: bool = False
    enable_daily_report: bool = True
    daily_report_auto_send: bool = True
    daily_report_random_eat_enabled: bool = False
    eat_success_percent: int = 15
    group_roast_max_charges: int = 2
    group_roast_recovery_hours: float = 8.0
    roast_reservation_max_participants: int = 12


def _section(title: str, entries: list[HelpEntry]) -> HelpSection | None:
    return HelpSection(title, tuple(entries)) if entries else None


def build_help_sections(
    state: HelpFeatureState, *, locale: object = DEFAULT_PLAYER_LOCALE
) -> tuple[HelpSection, ...]:
    """Build visible help from enabled features and the shared copy catalog.

    Command rows are omitted when the feature that makes them usable is disabled.
    Passive mechanics use the same rule so the card never advertises an inactive
    behavior. Command spellings remain stable protocol/UI tokens; descriptions
    and section copy are resolved through ``player_copy``.
    """

    def t(key: str, **values: object) -> str:
        return copy_text(key, locale=locale, **values)

    daily_entries = [
        HelpEntry("/今日小豬", t("help.daily.today")),
        HelpEntry("/昨日小豬", t("help.daily.yesterday")),
        HelpEntry("/明日小豬", t("help.daily.tomorrow")),
        HelpEntry("/本週小豬", t("help.daily.weekly")),
    ]
    if state.at_view_pig:
        daily_entries.insert(
            1,
            HelpEntry("/今日小豬 @某人", t("help.daily.today_other")),
        )

    discovery_entries = [
        HelpEntry("/我的豬圈 [頁碼]", t("help.discovery.pigsty")),
        HelpEntry("/隨機小豬 [1-9]", t("help.discovery.random")),
        HelpEntry("/找豬／搜豬 關鍵詞", t("help.discovery.search")),
    ]

    group_entries: list[HelpEntry] = []
    if state.enable_roast:
        group_entries.append(HelpEntry("/今日烤豬", t("help.group.roast_today")))

    group_roast_enabled = state.enable_roast and state.enable_group_roast
    if group_roast_enabled:
        capacity = max(1, int(state.group_roast_max_charges))
        recovery = max(1, round(float(state.group_roast_recovery_hours)))
        reservation_suffix = (
            t("help.group.roast_reservation_suffix")
            if state.enable_roast_reservation
            else ""
        )
        detail = t(
            "help.group.roast_target",
            capacity=capacity,
            recovery=recovery,
            reservation_suffix=reservation_suffix,
        )
        group_entries.extend(
            [
                HelpEntry("/烤群友 @某人", detail),
                HelpEntry("/隨機烤群友", t("help.group.random_roast")),
                HelpEntry("/打點後廚 @某人", t("help.group.force_roast")),
            ]
        )
        if state.enable_roast_reservation:
            group_entries.append(
                HelpEntry("/添柴 [@某人]", t("help.group.reservation_firewood"))
            )
        if state.enable_oven_refill:
            group_entries.extend(
                [
                    HelpEntry("/烤箱補貨", t("help.group.oven_refill")),
                    HelpEntry("/添煤", t("help.group.oven_support")),
                ]
            )

    if state.enable_group_eat:
        group_entries.extend(
            [
                HelpEntry(
                    "/吃群友 @某人",
                    t(
                        "help.group.eat_target",
                        percent=max(1, int(state.eat_success_percent)),
                    ),
                ),
                HelpEntry("/隨機吃群友", t("help.group.random_eat")),
            ]
        )

    report_entries: list[HelpEntry] = []
    if state.enable_daily_report:
        report_entries.extend(
            [
                HelpEntry("/豬圈日報", t("help.report.manual")),
                HelpEntry("/豬圈日報狀態", t("help.report.status")),
                HelpEntry("/豬圈日報開啟／關閉", t("help.report.toggle")),
            ]
        )
        if not state.daily_report_auto_send:
            report_entries.append(
                HelpEntry(
                    t("help.report.auto_off_title"),
                    t("help.report.auto_off"),
                    kind="status",
                )
            )

    mechanics: list[HelpEntry] = []
    if state.enable_new_pig_pity:
        mechanics.append(
            HelpEntry(
                t("help.mechanic.new_pig_pity_title"),
                t("help.mechanic.new_pig_pity"),
                kind="feature",
            )
        )
    if state.enable_daily_duplicate_pity:
        mechanics.append(
            HelpEntry(
                t("help.mechanic.duplicate_pity_title"),
                t("help.mechanic.duplicate_pity"),
                kind="feature",
            )
        )
    if group_roast_enabled:
        mechanics.append(
            HelpEntry(
                t("help.mechanic.oven_energy_title"),
                t(
                    "help.mechanic.oven_energy",
                    capacity=max(1, int(state.group_roast_max_charges)),
                ),
                kind="feature",
            )
        )
    if group_roast_enabled and state.enable_oven_refill:
        mechanics.append(
            HelpEntry(
                t("help.mechanic.group_refill_title"),
                t("help.mechanic.group_refill"),
                kind="feature",
            )
        )
    if group_roast_enabled and state.enable_roast_reservation:
        mechanics.append(
            HelpEntry(
                t("help.mechanic.reservation_title"),
                t(
                    "help.mechanic.reservation",
                    participants=max(
                        2, int(state.roast_reservation_max_participants)
                    ),
                ),
                kind="feature",
            )
        )
    if state.enable_roast_protection and (group_roast_enabled or state.enable_group_eat):
        mechanics.append(
            HelpEntry(
                t("help.mechanic.protection_title"),
                t("help.mechanic.protection"),
                kind="feature",
            )
        )
    if state.enable_ai_roast_copy and state.enable_roast:
        mechanics.append(
            HelpEntry(
                t("help.mechanic.ai_copy_title"),
                t("help.mechanic.ai_copy"),
                kind="feature",
            )
        )
    if state.enable_daily_report and state.daily_report_random_eat_enabled:
        mechanics.append(
            HelpEntry(
                t("help.mechanic.report_random_eat_title"),
                t("help.mechanic.report_random_eat"),
                kind="feature",
            )
        )

    sections = [
        _section(t("help.section.daily"), daily_entries),
        _section(t("help.section.discovery"), discovery_entries),
        _section(t("help.section.group"), group_entries),
        _section(t("help.section.report"), report_entries),
        _section(t("help.section.mechanics"), mechanics),
        _section(
            t("help.section.admin"),
            [
                HelpEntry(
                    t("help.admin.panel_title"),
                    t("help.admin.panel"),
                    kind="feature",
                )
            ],
        ),
    ]
    return tuple(section for section in sections if section is not None)


def help_sections_fingerprint(
    sections: tuple[HelpSection, ...], *, theme: str = ""
) -> str:
    """Stable cache identity derived from the actual rendered help content."""

    payload = {
        "theme": str(theme),
        "sections": [
            {
                "title": section.title,
                "entries": [asdict(entry) for entry in section.entries],
            }
            for section in sections
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:20]
