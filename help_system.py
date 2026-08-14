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


def build_help_sections(state: HelpFeatureState) -> tuple[HelpSection, ...]:
    """Build the visible help model from the currently enabled feature set.

    Command rows are omitted when the feature that makes them usable is disabled.
    Passive mechanics use the same rule so the card never advertises an inactive
    behavior. Traditional Chinese is the display canonical form; Simplified
    aliases remain accepted by the command registration layer.
    """

    daily_entries = [
        HelpEntry("/今日小豬", "抽取或查看今天的小豬"),
        HelpEntry("/昨日小豬", "查看昨天的結果"),
        HelpEntry("/明日小豬", "明天運勢預測，不會提前解鎖"),
        HelpEntry("/本週小豬", "生成本週七日小豬週報"),
    ]
    if state.at_view_pig:
        daily_entries.insert(
            1,
            HelpEntry("/今日小豬 @某人", "唯讀查看對方今天的小豬；不會替對方抽取"),
        )

    discovery_entries = [
        HelpEntry("/我的豬圈 [頁碼]", "永久圖鑑，例如 /我的豬圈 2"),
        HelpEntry("/隨機小豬 [1-9]", "隨機展示，不影響今日結果"),
        HelpEntry("/找豬／搜豬 關鍵詞", "按名稱、ID、描述或文案搜尋"),
    ]

    group_entries: list[HelpEntry] = []
    if state.enable_roast:
        group_entries.append(HelpEntry("/今日烤豬", "把今天的小豬做成趣味料理卡"))

    group_roast_enabled = state.enable_roast and state.enable_group_roast
    if group_roast_enabled:
        capacity = max(1, int(state.group_roast_max_charges))
        recovery = max(1, round(float(state.group_roast_recovery_hours)))
        detail = f"群內指定目標；每人每群 {capacity} 格能量，每 {recovery}h 恢復 1 格"
        if state.enable_roast_reservation:
            detail += "；目標未抽豬時自動建立預約"
        group_entries.extend(
            [
                HelpEntry("/烤群友 @某人", detail),
                HelpEntry("/隨機烤群友", "從今天在本群抽過豬的可料理群友中隨機挑選"),
                HelpEntry("/打點後廚 @某人", "後門別名每日一次；超管可用 /強行點火"),
            ]
        )
        if state.enable_oven_refill:
            group_entries.extend(
                [
                    HelpEntry("/烤箱補貨", "發起本群今日協作補貨；發起者自動貢獻第一份煤"),
                    HelpEntry("/添煤", "今日在本群參與過 RollPig 的群友每輪可支持一次"),
                ]
            )

    if state.enable_group_eat:
        group_entries.extend(
            [
                HelpEntry(
                    "/吃群友 @某人",
                    f"成功率 {max(1, int(state.eat_success_percent))}%；失敗會把自己吃掉",
                ),
                HelpEntry("/隨機吃群友", "隨機點名當前群可吃目標"),
            ]
        )

    report_entries: list[HelpEntry] = []
    if state.enable_daily_report:
        report_entries.extend(
            [
                HelpEntry("/豬圈日報", "手動生成本群今日完整統計海報與稱號"),
                HelpEntry(
                    "/豬圈日報 狀態",
                    "亦可直接 /豬圈日報狀態；查看本群自動推送狀態、計劃時間與全局總開關",
                ),
                HelpEntry(
                    "/豬圈日報 開啟／關閉",
                    "亦支援 /豬圈日報開啟、/豬圈日報關閉；僅 AstrBot 管理員可設定",
                ),
            ]
        )
        if not state.daily_report_auto_send:
            report_entries.append(
                HelpEntry(
                    "自動日報總開關",
                    "當前全局關閉；本群仍可保存開啟狀態，手動日報不受影響",
                    kind="status",
                )
            )

    mechanics: list[HelpEntry] = []
    if state.enable_new_pig_pity:
        mechanics.append(
            HelpEntry("新豬保底", "連續抽到已解鎖小豬時，逐步提高新豬重抽機會", kind="feature")
        )
    if state.enable_daily_duplicate_pity:
        mechanics.append(
            HelpEntry("跨日疲勞保底", "連續多天重複時再疊加額外的新豬機會", kind="feature")
        )
    if group_roast_enabled:
        mechanics.append(
            HelpEntry(
                "烤箱能量",
                f"默認最多 {max(1, int(state.group_roast_max_charges))} 格，按群獨立自然恢復",
                kind="feature",
            )
        )
    if group_roast_enabled and state.enable_oven_refill:
        mechanics.append(
            HelpEntry("群體補貨", "達成群體支持門檻後，今日活躍玩家統一恢復 +1 格能量", kind="feature")
        )
    if group_roast_enabled and state.enable_roast_reservation:
        mechanics.append(
            HelpEntry(
                "預約烤豬",
                f"未抽目標可提前埋伏，最多 {max(2, int(state.roast_reservation_max_participants))} 人添柴",
                kind="feature",
            )
        )
    if state.enable_roast_protection and (group_roast_enabled or state.enable_group_eat):
        mechanics.append(
            HelpEntry("次日保護", "前一天被頻繁成功燒烤後，普通群烤／吃會受到保護", kind="feature")
        )
    if state.enable_ai_roast_copy and state.enable_roast:
        mechanics.append(
            HelpEntry("AI 烤豬文案", "當前會話模型可生成料理文案；異常時自動回退本地模板", kind="feature")
        )
    if state.enable_daily_report and state.daily_report_random_eat_enabled:
        mechanics.append(
            HelpEntry("日報隨機祭品", "僅自動日報發送時可能觸發；手動查看不會吃人", kind="feature")
        )

    sections = [
        _section("每天一豬", daily_entries),
        _section("圖鑑與探索", discovery_entries),
        _section("群聊玩法", group_entries),
        _section("豬圈日報", report_entries),
        _section("已啟用機制", mechanics),
        _section(
            "管理與資源",
            [
                HelpEntry(
                    "管理面板",
                    "同步資源，新增／編輯／刪除小豬，PigHub 選圖與公共源審核",
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
