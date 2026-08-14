from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


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
    enable_group_eat: bool = True
    enable_roast_protection: bool = True
    enable_ai_roast_copy: bool = False
    enable_daily_report: bool = True
    daily_report_auto_send: bool = True
    daily_report_random_eat_enabled: bool = False
    eat_success_percent: int = 15
    group_roast_cooldown_hours: float = 8.0
    roast_reservation_max_participants: int = 12


def _section(title: str, entries: list[HelpEntry]) -> HelpSection | None:
    return HelpSection(title, tuple(entries)) if entries else None


def build_help_sections(state: HelpFeatureState) -> tuple[HelpSection, ...]:
    """Build the visible help model from the currently enabled feature set.

    Command rows are omitted when the feature that makes them usable is disabled.
    Passive mechanics use the same rule so the card never advertises an inactive
    behavior.
    """

    daily_entries = [
        HelpEntry("/今日小猪", "抽取或查看今天的小猪"),
        HelpEntry("/昨日小猪", "查看昨天的结果"),
        HelpEntry("/明日小猪", "明天运势预测，不会提前解锁"),
        HelpEntry("/本周小猪", "生成本周七日小猪周报"),
    ]
    if state.at_view_pig:
        daily_entries.insert(
            1,
            HelpEntry("/今日小猪 @某人", "只读查看对方今天的小猪；不会替对方抽取"),
        )

    discovery_entries = [
        HelpEntry("/我的猪圈 [页码]", "永久图鉴，例如 /我的猪圈 2"),
        HelpEntry("/随机小猪 [1-9]", "随机展示，不影响今日结果"),
        HelpEntry("/找猪／搜猪 关键词", "按名称、ID、描述或文案搜索"),
    ]

    group_entries: list[HelpEntry] = []
    if state.enable_roast:
        group_entries.append(HelpEntry("/今日烤猪", "把今天的小猪做成趣味料理卡"))

    group_roast_enabled = state.enable_roast and state.enable_group_roast
    if group_roast_enabled:
        cooldown = max(1, round(float(state.group_roast_cooldown_hours)))
        detail = f"群内指定目标；普通烧烤约 {cooldown}h 冷却"
        if state.enable_roast_reservation:
            detail += "；目标未抽猪时自动建立预约"
        group_entries.extend(
            [
                HelpEntry("/烤群友 @某人", detail),
                HelpEntry("/随机烤群友", "从今天在本群抽过猪的可料理群友中随机挑选"),
                HelpEntry("后门口令 @某人", "打点后厨等每日一次；超管可用 /强行点火"),
            ]
        )

    if state.enable_group_eat:
        group_entries.extend(
            [
                HelpEntry(
                    "/吃群友 @某人",
                    f"成功率 {max(1, int(state.eat_success_percent))}%；失败会把自己吃掉",
                ),
                HelpEntry("/随机吃群友", "随机点名当前群可吃目标"),
            ]
        )

    report_entries: list[HelpEntry] = []
    if state.enable_daily_report:
        report_entries.extend(
            [
                HelpEntry("/猪圈日报", "手动生成本群今日完整统计海报与称号"),
                HelpEntry("/猪圈日报 状态", "查看本群自动推送状态、计划时间与全局总开关"),
                HelpEntry(
                    "/猪圈日报 开启／关闭",
                    "群主、群管理员或 AstrBot 管理员设置本群自动推送",
                ),
            ]
        )
        if not state.daily_report_auto_send:
            report_entries.append(
                HelpEntry(
                    "自动日报总开关",
                    "当前全局关闭；本群仍可保存开启状态，手动日报不受影响",
                    kind="status",
                )
            )

    mechanics: list[HelpEntry] = []
    if state.enable_new_pig_pity:
        mechanics.append(
            HelpEntry("新猪保底", "连续抽到已解锁小猪时，逐步提高新猪重抽机会", kind="feature")
        )
    if state.enable_daily_duplicate_pity:
        mechanics.append(
            HelpEntry("跨日疲劳保底", "连续多天重复时再叠加额外的新猪机会", kind="feature")
        )
    if group_roast_enabled and state.enable_roast_reservation:
        mechanics.append(
            HelpEntry(
                "预约烤猪",
                f"未抽目标可提前埋伏，最多 {max(2, int(state.roast_reservation_max_participants))} 人添柴",
                kind="feature",
            )
        )
    if state.enable_roast_protection and (group_roast_enabled or state.enable_group_eat):
        mechanics.append(
            HelpEntry("次日保护", "前一天被频繁成功烧烤后，普通群烤／吃会受到保护", kind="feature")
        )
    if state.enable_ai_roast_copy and state.enable_roast:
        mechanics.append(
            HelpEntry("AI 烤猪文案", "当前会话模型可生成料理文案；异常时自动回退本地模板", kind="feature")
        )
    if state.enable_daily_report and state.daily_report_random_eat_enabled:
        mechanics.append(
            HelpEntry("日报随机祭品", "仅自动日报发送时可能触发；手动查看不会吃人", kind="feature")
        )

    sections = [
        _section("每天一猪", daily_entries),
        _section("图鉴与探索", discovery_entries),
        _section("群聊玩法", group_entries),
        _section("猪圈日报", report_entries),
        _section("已启用机制", mechanics),
        _section(
            "管理与资源",
            [
                HelpEntry(
                    "管理面板",
                    "同步资源，新增／编辑／删除小猪，PigHub 选图与公共源审核",
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
