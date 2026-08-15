from __future__ import annotations

import string
from typing import Mapping


DEFAULT_PLAYER_LOCALE = "zh-TW"
SUPPORTED_PLAYER_LOCALES = ("zh-TW", "zh-CN")


PLAYER_COPY: dict[str, dict[str, str]] = {
    "zh-TW": {
        "help.section.daily": "每天一豬",
        "help.section.discovery": "圖鑑與探索",
        "help.section.group": "群聊玩法",
        "help.section.report": "豬圈日報",
        "help.section.mechanics": "已啟用機制",
        "help.section.admin": "管理與資源",
        "help.daily.today": "抽取或查看今天的小豬",
        "help.daily.today_other": "唯讀查看對方今天的小豬；不會替對方抽取",
        "help.daily.yesterday": "查看昨天的結果",
        "help.daily.tomorrow": "明天運勢預測，不會提前解鎖",
        "help.daily.weekly": "生成本週七日小豬週報",
        "help.discovery.pigsty": "永久圖鑑，例如 /我的豬圈 2",
        "help.discovery.random": "隨機展示，不影響今日結果",
        "help.discovery.search": "按名稱、ID、描述或文案搜尋",
        "help.group.roast_today": "把今天的小豬做成趣味料理卡",
        "help.group.roast_target": "群內指定目標；每人每群 {capacity} 格能量，每 {recovery}h 恢復 1 格{reservation_suffix}",
        "help.group.roast_reservation_suffix": "；目標未抽豬時自動建立預約",
        "help.group.random_roast": "從今天在本群抽過豬的可料理群友中隨機挑選",
        "help.group.force_roast": "後門別名每日一次；超管可用 /強行點火",
        "help.group.oven_refill": "發起本群今日協作補貨；發起者自動貢獻第一份煤",
        "help.group.oven_support": "今日在本群參與過 RollPig 的群友每輪可支持一次",
        "help.group.eat_target": "成功率 {percent}%；失敗會把自己吃掉",
        "help.group.random_eat": "隨機點名當前群可吃目標",
        "help.report.manual": "手動生成本群今日完整統計海報與稱號",
        "help.report.status": "也可使用 /豬圈日報 狀態；查看本群自動推送狀態、計劃時間與全局總開關",
        "help.report.toggle": "也可使用 /豬圈日報 開啟／關閉；僅 AstrBot 管理員可設定",
        "help.report.auto_off_title": "自動日報總開關",
        "help.report.auto_off": "當前全局關閉；本群仍可保存開啟狀態，手動日報不受影響",
        "help.mechanic.new_pig_pity_title": "新豬保底",
        "help.mechanic.new_pig_pity": "連續抽到已解鎖小豬時，逐步提高新豬重抽機會",
        "help.mechanic.duplicate_pity_title": "跨日疲勞保底",
        "help.mechanic.duplicate_pity": "連續多天重複時再疊加額外的新豬機會",
        "help.mechanic.oven_energy_title": "烤箱能量",
        "help.mechanic.oven_energy": "默認最多 {capacity} 格，按群獨立自然恢復",
        "help.mechanic.group_refill_title": "群體補貨",
        "help.mechanic.group_refill": "達成群體支持門檻後，今日活躍玩家統一恢復 +1 格能量",
        "help.mechanic.reservation_title": "預約烤豬",
        "help.mechanic.reservation": "未抽目標可提前埋伏，最多 {participants} 人加入蹲守；後續再次 /烤群友 @同一目標即可加入",
        "help.mechanic.protection_title": "次日保護",
        "help.mechanic.protection": "前一天被頻繁成功燒烤後，普通群烤／吃會受到保護",
        "help.mechanic.ai_copy_title": "AI 烤豬文案",
        "help.mechanic.ai_copy": "當前會話模型可生成料理文案；異常時自動回退本地模板",
        "help.mechanic.report_random_eat_title": "日報隨機祭品",
        "help.mechanic.report_random_eat": "僅自動日報發送時可能觸發；手動查看不會吃人",
        "help.admin.panel_title": "管理面板",
        "help.admin.panel": "同步資源，新增／編輯／刪除小豬，PigHub 選圖、EX 成長與公共源審核",
    },
    "zh-CN": {
        "help.section.daily": "每天一猪",
        "help.section.discovery": "图鉴与探索",
        "help.section.group": "群聊玩法",
        "help.section.report": "猪圈日报",
        "help.section.mechanics": "已启用机制",
        "help.section.admin": "管理与资源",
        "help.daily.today": "抽取或查看今天的小猪",
        "help.daily.today_other": "只读查看对方今天的小猪；不会替对方抽取",
        "help.daily.yesterday": "查看昨天的结果",
        "help.daily.tomorrow": "明天运势预测，不会提前解锁",
        "help.daily.weekly": "生成本周七日小猪周报",
        "help.discovery.pigsty": "永久图鉴，例如 /我的猪圈 2",
        "help.discovery.random": "随机展示，不影响今日结果",
        "help.discovery.search": "按名称、ID、描述或文案搜索",
        "help.group.roast_today": "把今天的小猪做成趣味料理卡",
        "help.group.roast_target": "群内指定目标；每人每群 {capacity} 格能量，每 {recovery}h 恢复 1 格{reservation_suffix}",
        "help.group.roast_reservation_suffix": "；目标未抽猪时自动建立预约",
        "help.group.random_roast": "从今天在本群抽过猪的可料理群友中随机挑选",
        "help.group.force_roast": "后门别名每日一次；超管可用 /强行点火",
        "help.group.oven_refill": "发起本群今日协作补货；发起者自动贡献第一份煤",
        "help.group.oven_support": "今日在本群参与过 RollPig 的群友每轮可支持一次",
        "help.group.eat_target": "成功率 {percent}%；失败会把自己吃掉",
        "help.group.random_eat": "随机点名当前群可吃目标",
        "help.report.manual": "手动生成本群今日完整统计海报与称号",
        "help.report.status": "也可使用 /猪圈日报 状态；查看本群自动推送状态、计划时间与全局总开关",
        "help.report.toggle": "也可使用 /猪圈日报 开启／关闭；仅 AstrBot 管理员可设置",
        "help.report.auto_off_title": "自动日报总开关",
        "help.report.auto_off": "当前全局关闭；本群仍可保存开启状态，手动日报不受影响",
        "help.mechanic.new_pig_pity_title": "新猪保底",
        "help.mechanic.new_pig_pity": "连续抽到已解锁小猪时，逐步提高新猪重抽机会",
        "help.mechanic.duplicate_pity_title": "跨日疲劳保底",
        "help.mechanic.duplicate_pity": "连续多天重复时再叠加额外的新猪机会",
        "help.mechanic.oven_energy_title": "烤箱能量",
        "help.mechanic.oven_energy": "默认最多 {capacity} 格，按群独立自然恢复",
        "help.mechanic.group_refill_title": "群体补货",
        "help.mechanic.group_refill": "达成群体支持门槛后，今日活跃玩家统一恢复 +1 格能量",
        "help.mechanic.reservation_title": "预约烤猪",
        "help.mechanic.reservation": "未抽目标可提前埋伏，最多 {participants} 人加入蹲守；后续再次 /烤群友 @同一目标即可加入",
        "help.mechanic.protection_title": "次日保护",
        "help.mechanic.protection": "前一天被频繁成功烧烤后，普通群烤／吃会受到保护",
        "help.mechanic.ai_copy_title": "AI 烤猪文案",
        "help.mechanic.ai_copy": "当前会话模型可生成料理文案；异常时自动回退本地模板",
        "help.mechanic.report_random_eat_title": "日报随机祭品",
        "help.mechanic.report_random_eat": "仅自动日报发送时可能触发；手动查看不会吃人",
        "help.admin.panel_title": "管理面板",
        "help.admin.panel": "同步资源，新增／编辑／删除小猪，PigHub 选图、EX 成长与公共源审核",
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


def copy_text(key: str, *, locale: object = DEFAULT_PLAYER_LOCALE, **values: object) -> str:
    normalized = normalize_player_locale(locale)
    catalog: Mapping[str, str] = PLAYER_COPY[normalized]
    fallback: Mapping[str, str] = PLAYER_COPY[DEFAULT_PLAYER_LOCALE]
    if key not in catalog and key not in fallback:
        raise KeyError(f"unknown player copy key: {key}")
    template = catalog.get(key, fallback[key])
    required = copy_placeholders(template)
    missing = required.difference(values)
    if missing:
        raise KeyError(f"missing player copy values for {key}: {', '.join(sorted(missing))}")
    return template.format(**values)
