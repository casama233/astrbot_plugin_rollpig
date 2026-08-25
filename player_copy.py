from __future__ import annotations

import string
from typing import Mapping


DEFAULT_PLAYER_LOCALE = "zh-TW"
SUPPORTED_PLAYER_LOCALES = ("zh-TW", "zh-CN")


PLAYER_COPY: dict[str, dict[str, str]] = {
    "zh-TW": {
        "help.section.daily": "每天抽猪",
        "help.section.discovery": "找猪收藏",
        "help.section.group": "后厨搞事",
        "help.section.report": "猪圈日报",
        "help.section.mechanics": "玩法速记",
        "help.section.admin": "管理",
        "help.mention.native_at_note": "⚠ QQ请从@弹窗点选群友，勿复制或手打昵称",
        "help.daily.today": "抽今天的小猪；抽过就回同一只",
        "help.daily.today_other": "查看对方今日猪；不替对方抽",
        "help.daily.yesterday": "看昨天抽到哪只猪",
        "help.daily.tomorrow": "预览明日猪运；不提前开奖",
        "help.daily.weekly": "把本周七天小猪排成周报",
        "help.discovery.pigsty": "看永久猪籍；可加页码翻页",
        "help.discovery.random": "随机看 1–9 只；不影响今日抽取",
        "help.discovery.search": "按名称、ID 或描述找猪",
        "help.group.roast_today": "把自己今天的小猪做成料理卡",
        "help.group.roast_target": "烤指定群友{reservation_suffix}",
        "help.group.roast_reservation_suffix": "；没抽猪可先埋伏",
        "help.group.random_roast": "随机抓一位今天可料理的群友",
        "help.group.force_roast": "每天一次绕过普通限制开火",
        "help.group.oven_refill": "开一轮全群添柴，帮大家回 Charge",
        "help.group.oven_support": "补货轮次中，每人可添柴一次",
        "help.group.firewood_router": "补货就添柴；有预约可 @目标 蹲锅",
        "help.group.eat_target": "吃指定群友；失败可能反吃自己",
        "help.group.random_eat": "随机挑一位目前可吃的群友",
        "help.report.manual": "生成今天的猪圈晚报",
        "help.report.status": "查看日报开关、时间与状态",
        "help.report.toggle": "管理员开启或关闭本群日报",
        "help.report.auto_off_title": "自动日报休息中",
        "help.report.auto_off": "自动发送已关；手动日报仍可用",
        "help.mechanic.new_pig_pity_title": "新猪保底",
        "help.mechanic.new_pig_pity": "老猪连续返场时，新猪机率会提高",
        "help.mechanic.duplicate_pity_title": "跨日疲劳",
        "help.mechanic.duplicate_pity": "跨日仍重复收藏，再叠新猪机会",
        "help.mechanic.ex_growth_title": "EX 成长",
        "help.mechanic.ex_growth": "重复抽同一只猪，会升到 EX Lv.1–5",
        "help.mechanic.oven_energy_title": "烤箱 Charge",
        "help.mechanic.oven_energy": "每群最多 {capacity} 格；用掉后按时间恢复",
        "help.mechanic.group_refill_title": "群体补货",
        "help.mechanic.group_refill": "全群添柴达标，活跃群友各回 1 格",
        "help.mechanic.reservation_title": "预约烤猪",
        "help.mechanic.reservation": "没抽猪先埋伏；/添柴/烤群友都能加入",
        "help.mechanic.protection_title": "次日保护",
        "help.mechanic.protection": "昨天被烤太狠，今天群烤/吃会被拦",
        "help.mechanic.ai_copy_title": "AI 料理文案",
        "help.mechanic.ai_copy": "模型写料理文案；失败就回本地模板",
        "help.mechanic.report_random_eat_title": "日报祭品",
        "help.mechanic.report_random_eat": "只在自动日报可能触发；手动不吃人",
        "help.admin.panel_title": "管理面板",
        "help.admin.panel": "猪源、猪图、EX、投稿都在后台管理",
    },
    "zh-CN": {
        "help.section.daily": "每天抽猪",
        "help.section.discovery": "找猪收藏",
        "help.section.group": "后厨搞事",
        "help.section.report": "猪圈日报",
        "help.section.mechanics": "玩法速记",
        "help.section.admin": "管理",
        "help.mention.native_at_note": "⚠ QQ请从@弹窗点选群友，勿复制或手打昵称",
        "help.daily.today": "抽今天的小猪；抽过就回同一只",
        "help.daily.today_other": "查看对方今日猪；不替对方抽",
        "help.daily.yesterday": "看昨天抽到哪只猪",
        "help.daily.tomorrow": "预览明日猪运；不提前开奖",
        "help.daily.weekly": "把本周七天小猪排成周报",
        "help.discovery.pigsty": "看永久猪籍；可加页码翻页",
        "help.discovery.random": "随机看 1–9 只；不影响今日抽取",
        "help.discovery.search": "按名称、ID 或描述找猪",
        "help.group.roast_today": "把自己今天的小猪做成料理卡",
        "help.group.roast_target": "烤指定群友{reservation_suffix}",
        "help.group.roast_reservation_suffix": "；没抽猪可先埋伏",
        "help.group.random_roast": "随机抓一位今天可料理的群友",
        "help.group.force_roast": "每天一次绕过普通限制开火",
        "help.group.oven_refill": "开一轮全群添柴，帮大家回 Charge",
        "help.group.oven_support": "补货轮次中，每人可添柴一次",
        "help.group.firewood_router": "补货就添柴；有预约可 @目标 蹲锅",
        "help.group.eat_target": "吃指定群友；失败可能反吃自己",
        "help.group.random_eat": "随机挑一位目前可吃的群友",
        "help.report.manual": "生成今天的猪圈晚报",
        "help.report.status": "查看日报开关、时间与状态",
        "help.report.toggle": "管理员开启或关闭本群日报",
        "help.report.auto_off_title": "自动日报休息中",
        "help.report.auto_off": "自动发送已关；手动日报仍可用",
        "help.mechanic.new_pig_pity_title": "新猪保底",
        "help.mechanic.new_pig_pity": "老猪连续返场时，新猪概率会提高",
        "help.mechanic.duplicate_pity_title": "跨日疲劳",
        "help.mechanic.duplicate_pity": "跨日仍重复收藏，再叠新猪机会",
        "help.mechanic.ex_growth_title": "EX 成长",
        "help.mechanic.ex_growth": "重复抽同一只猪，会升到 EX Lv.1–5",
        "help.mechanic.oven_energy_title": "烤箱 Charge",
        "help.mechanic.oven_energy": "每群最多 {capacity} 格；用掉后按时间恢复",
        "help.mechanic.group_refill_title": "群体补货",
        "help.mechanic.group_refill": "全群添柴达标，活跃群友各回 1 格",
        "help.mechanic.reservation_title": "预约烤猪",
        "help.mechanic.reservation": "没抽猪先埋伏；/添柴/烤群友都能加入",
        "help.mechanic.protection_title": "次日保护",
        "help.mechanic.protection": "昨天被烤太狠，今天群烤/吃会被拦",
        "help.mechanic.ai_copy_title": "AI 料理文案",
        "help.mechanic.ai_copy": "模型写料理文案；失败就回本地模板",
        "help.mechanic.report_random_eat_title": "日报祭品",
        "help.mechanic.report_random_eat": "只在自动日报可能触发；手动不吃人",
        "help.admin.panel_title": "管理面板",
        "help.admin.panel": "猪源、猪图、EX、投稿都在后台管理",
    },
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
