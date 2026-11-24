from __future__ import annotations

import string
from typing import Mapping


DEFAULT_PLAYER_LOCALE = "zh-TW"
SUPPORTED_PLAYER_LOCALES = ("zh-TW", "zh-CN")


# Help cards share Simplified display copy; retain the supported locale aliases.
_HELP_COPY: dict[str, str] = {
    "help.section.daily": "每天抽猪",
    "help.section.discovery": "找猪收藏",
    "help.section.group": "后厨搞事",
    "help.section.report": "猪圈日报",
    "help.section.mechanics": "玩法速记",
    "help.section.admin": "管理",
    "help.mention.native_at_note": '⚠ QQ得从@弹窗点选群友，手打或复制认不出来',
    "help.daily.today": '领今日小猪，重复发只看同一只。',
    "help.daily.today_other": '查看对方今日小猪，不代抽',
    "help.daily.yesterday": '翻出昨天领到的那只猪。',
    "help.daily.tomorrow": '偷瞄明天猪运，不算提前检票。',
    "help.daily.weekly": '查看本周七天的抽猪记录。',
    "help.discovery.pigsty": '翻永久图鉴，带上页码往后翻。',
    "help.discovery.random": '随机预览 1–9 只，不占今天名额。',
    "help.discovery.search": '按名字、ID 或描述把猪搜出来。',
    "help.group.roast_today": '把你今天的猪印成料理卡。',
    "help.group.roast_target": "消耗1格，逃脱不退{reservation_suffix}",
    "help.group.roast_reservation_suffix": '；没抽猪可先蹲点',
    "help.group.random_roast": '在今天可烤的群友里随机点名。',
    "help.group.force_roast": '每天一次绕过常规限制开火',
    "help.group.oven_refill": '招呼全群一起添柴，给大家回 Charge',
    "help.group.oven_support": '补货期间，每人都能搭把手添一次柴',
    "help.group.firewood_router": '补货可添柴，预约能指定 @目标',
    "help.group.eat_target": '{percent}%成功；失败直接吃掉自己',
    "help.group.random_eat": '在当前可吃的群友里随机抓一个。',
    "help.report.manual": '手动打印今天本群的猪圈收据。',
    "help.report.status": "查看日报开关、时间与状态",
    "help.report.toggle": "管理员开启或关闭本群日报",
    "help.report.auto_off_title": '自动日报打盹中',
    "help.report.auto_off": '自动播报关了，想看就手动打日报。',
    "help.mechanic.new_pig_pity_title": "新猪保底",
    "help.mechanic.new_pig_pity": '老面孔总来串门，遇见新猪的概率会涨',
    "help.mechanic.duplicate_pity_title": "跨日疲劳",
    "help.mechanic.duplicate_pity": '跨日还在收老熟人，新猪机会继续攒',
    "help.mechanic.ex_growth_title": "EX 成长",
    "help.mechanic.ex_growth": "收藏 EX 可超5；文案沿用最高可用差分",
    "help.mechanic.oven_energy_title": "烤箱 Charge",
    "help.mechanic.oven_energy": "每人每群{capacity}格；每{hours}小时回1格",
    "help.mechanic.group_refill_title": "群体补货",
    "help.mechanic.group_refill": "全群添柴达标，活跃群友各回 1 格",
    "help.mechanic.reservation_title": "预约烤猪",
    "help.mechanic.reservation": "最多{participants}人；/烤群友加入不扣格",
    "help.mechanic.protection_title": "次日保护",
    "help.mechanic.protection": '昨天被烤得太惨，今天群烤/吃会被拦',
    "help.mechanic.ai_copy_title": "AI 料理文案",
    "help.mechanic.ai_copy": '让模型编料理文案，失败就用本地模板顶上',
    "help.mechanic.report_random_eat_title": "日报祭品",
    "help.mechanic.report_random_eat": '只有自动日报可能抓人；手动不伤无辜',
    "help.admin.panel_title": "管理面板",
    "help.admin.panel": "猪源、猪图、EX、投稿都在后台管理",
}


PLAYER_COPY: dict[str, dict[str, str]] = {
    "zh-TW": {
        **_HELP_COPY,
        "help.mechanic.new_pig_pity": '老猪老是赖着不走，新猪登场的机率就会悄悄变高',
    },
    "zh-CN": dict(_HELP_COPY),
}


def normalize_player_locale(locale: object) -> str:
    text = str(locale or "").strip().replace("_", "-").lower()
    if text in {"zh-cn", "zh-hans", "zh-sg"}:
        return "zh-CN"
    if text in {"zh-tw", "zh-hant", "zh-hk", "zh-mo"}:
        return "zh-TW"
    return DEFAULT_PLAYER_LOCALE


def copy_placeholders(template: str) -> frozenset[str]:
    formatter = string.Formatter()
    return frozenset(
        field_name
        for _, field_name, _, _ in formatter.parse(str(template))
        if field_name
    )


def copy_text(
    key: str,
    *,
    locale: object = DEFAULT_PLAYER_LOCALE,
    **values: object,
) -> str:
    normalized = normalize_player_locale(locale)
    catalog: Mapping[str, str] = PLAYER_COPY[normalized]
    fallback: Mapping[str, str] = PLAYER_COPY[DEFAULT_PLAYER_LOCALE]
    if key not in catalog and key not in fallback:
        raise KeyError(f"unknown player copy key: {key}")
    template = catalog.get(key, fallback[key])
    required = copy_placeholders(template)
    missing = required.difference(values)
    if missing:
        raise KeyError(
            f"missing player copy values for {key}: {', '.join(sorted(missing))}"
        )
    return template.format(**values)
