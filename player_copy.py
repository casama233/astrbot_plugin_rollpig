from __future__ import annotations

import string
from typing import Mapping


DEFAULT_PLAYER_LOCALE = "zh-TW"
SUPPORTED_PLAYER_LOCALES = ("zh-TW", "zh-CN")


PLAYER_COPY: dict[str, dict[str, str]] = {
    "zh-TW": {
        "help.section.daily": "今日豬事",
        "help.section.discovery": "豬圈收藏",
        "help.section.group": "後廚搞事",
        "help.section.report": "豬圈日報",
        "help.section.mechanics": "豬圈機關",
        "help.section.admin": "管理員後廚",
        "help.daily.today": "抽今天專屬的小豬；抽過就原樣端回來",
        "help.daily.today_other": "偷看對方今天是哪隻豬；只看，不替他抽",
        "help.daily.yesterday": "翻昨天的豬圈舊帳",
        "help.daily.tomorrow": "偷瞄明日豬運；只預測，不提前開獎",
        "help.daily.weekly": "把本週七隻豬排成一張週報",
        "help.discovery.pigsty": "翻永久豬圈圖鑑，例如 /我的豬圈 2",
        "help.discovery.random": "隨手薅幾隻豬出來看看；不動今日結果",
        "help.discovery.search": "按名稱、ID、描述或梗文案翻豬牌",
        "help.group.roast_today": "把今天的小豬送進後廚，做成料理卡",
        "help.group.roast_target": "指定群友開火；每人每群 {capacity} 格 Charge，每 {recovery}h 回 1 格{reservation_suffix}",
        "help.group.roast_reservation_suffix": "；目標沒抽豬就先埋伏烤箱",
        "help.group.reservation_firewood": "給待結算的埋伏添柴；一口鍋直接 /添柴，多口鍋請 @目標",
        "help.group.random_roast": "從今天在本群露過面的可料理群友裡隨機抓一隻",
        "help.group.force_roast": "後門每天一次；超管還能 /強行點火——門鎖基本是裝飾",
        "help.group.oven_refill": "烤太猛沒電了？發起全群搬煤；發起人先鏟第 1 份",
        "help.group.oven_support": "今天在本群養過豬的群友，每輪都能 /添煤 一次",
        "help.group.eat_target": "成功率 {percent}%；沒吃到別人，就可能把自己吃沒",
        "help.group.random_eat": "從本群目前可吃名單裡隨機挑一位食材",
        "help.report.manual": "把今天誰最慘、誰最能烤，統統貼上豬圈日報",
        "help.report.status": "也可 /豬圈日報 狀態；看看晚報醒沒醒、幾點來、總閘有沒有拉下",
        "help.report.toggle": "也可 /豬圈日報 開啟／關閉；管理員管開關，群友負責看熱鬧",
        "help.report.auto_off_title": "自動日報在睡覺",
        "help.report.auto_off": "全局總閘已關；本群開關先記著，手動翻報紙照常",
        "help.mechanic.new_pig_pity_title": "新豬保底｜豬圈不許一直敷衍你",
        "help.mechanic.new_pig_pity": "老面孔連續返場時，未解鎖小豬的重抽機會會越攢越高",
        "help.mechanic.duplicate_pity_title": "跨日疲勞｜同一批豬也會看膩",
        "help.mechanic.duplicate_pity": "連續多天都抽到已收藏小豬，再額外疊一層新豬機會",
        "help.mechanic.oven_energy_title": "烤箱 Charge｜火不是無限的",
        "help.mechanic.oven_energy": "默認最多 {capacity} 格；每個群各算各的，時間到了自己回火",
        "help.mechanic.group_refill_title": "群體補貨｜烤太猛就一起搬煤",
        "help.mechanic.group_refill": "支持人數達標後，今天活躍群友各恢復 1 格 Charge",
        "help.mechanic.reservation_title": "預約烤豬｜人沒到，鍋先熱",
        "help.mechanic.reservation": "目標還沒抽豬也能先埋伏，最多 {participants} 人圍鍋添柴",
        "help.mechanic.protection_title": "次日保護｜昨天烤太狠，今天上保險",
        "help.mechanic.protection": "前一天被成功烤太多次，普通群烤／吃會先被豬圈保安攔下",
        "help.mechanic.ai_copy_title": "AI 料理文案｜主廚偶爾請外援",
        "help.mechanic.ai_copy": "可請當前會話模型寫菜譜；模型罷工時自動翻回本地菜單",
        "help.mechanic.report_random_eat_title": "日報祭品｜晚報偶爾真會吃人",
        "help.mechanic.report_random_eat": "只可能在自動日報發送時觸發；手動翻報紙不會少人",
        "help.admin.panel_title": "管理面板｜后厨总控室｜後廚總控室",
        "help.admin.panel": "同步豬源、改豬、選圖、配 EX、審投稿；按鈕很多，豬還是那些豬",
    },
    "zh-CN": {
        "help.section.daily": "今日猪事",
        "help.section.discovery": "猪圈收藏",
        "help.section.group": "后厨搞事",
        "help.section.report": "猪圈日报",
        "help.section.mechanics": "猪圈机关",
        "help.section.admin": "管理员后厨",
        "help.daily.today": "抽今天专属的小猪；抽过就原样端回来",
        "help.daily.today_other": "偷看对方今天是哪只猪；只看，不替他抽",
        "help.daily.yesterday": "翻昨天的猪圈旧账",
        "help.daily.tomorrow": "偷瞄明日猪运；只预测，不提前开奖",
        "help.daily.weekly": "把本周七只猪排成一张周报",
        "help.discovery.pigsty": "翻永久猪圈图鉴，例如 /我的猪圈 2",
        "help.discovery.random": "随手薅几只猪出来看看；不动今日结果",
        "help.discovery.search": "按名称、ID、描述或梗文案翻猪牌",
        "help.group.roast_today": "把今天的小猪送进后厨，做成料理卡",
        "help.group.roast_target": "指定群友开火；每人每群 {capacity} 格 Charge，每 {recovery}h 回 1 格{reservation_suffix}",
        "help.group.roast_reservation_suffix": "；目标没抽猪就先埋伏烤箱",
        "help.group.reservation_firewood": "给待结算的埋伏添柴；一口锅直接 /添柴，多口锅请 @目标",
        "help.group.random_roast": "从今天在本群露过面的可料理群友里随机抓一只",
        "help.group.force_roast": "后门每天一次；超管还能 /强行点火——门锁基本是装饰",
        "help.group.oven_refill": "烤太猛没电了？发起全群搬煤；发起人先铲第 1 份",
        "help.group.oven_support": "今天在本群养过猪的群友，每轮都能 /添煤 一次",
        "help.group.eat_target": "成功率 {percent}%；没吃到别人，就可能把自己吃没",
        "help.group.random_eat": "从本群目前可吃名单里随机挑一位食材",
        "help.report.manual": "把今天谁最惨、谁最能烤，统统贴上猪圈日报",
        "help.report.status": "也可 /猪圈日报 状态；看看晚报醒没醒、几点来、总闸有没有拉下",
        "help.report.toggle": "也可 /猪圈日报 开启／关闭；管理员管开关，群友负责看热闹",
        "help.report.auto_off_title": "自动日报在睡觉",
        "help.report.auto_off": "全局总闸已关；本群开关先记着，手动翻报纸照常",
        "help.mechanic.new_pig_pity_title": "新猪保底｜猪圈不许一直敷衍你",
        "help.mechanic.new_pig_pity": "老面孔连续返场时，未解锁小猪的重抽机会会越攒越高",
        "help.mechanic.duplicate_pity_title": "跨日疲劳｜同一批猪也会看腻",
        "help.mechanic.duplicate_pity": "连续多天都抽到已收藏小猪，再额外叠一层新猪机会",
        "help.mechanic.oven_energy_title": "烤箱 Charge｜火不是无限的",
        "help.mechanic.oven_energy": "默认最多 {capacity} 格；每个群各算各的，时间到了自己回火",
        "help.mechanic.group_refill_title": "群体补货｜烤太猛就一起搬煤",
        "help.mechanic.group_refill": "支持人数达标后，今天活跃群友各恢复 1 格 Charge",
        "help.mechanic.reservation_title": "预约烤猪｜人没到，锅先热",
        "help.mechanic.reservation": "目标还没抽猪也能先埋伏，最多 {participants} 人围锅添柴",
        "help.mechanic.protection_title": "次日保护｜昨天烤太狠，今天上保险",
        "help.mechanic.protection": "前一天被成功烤太多次，普通群烤／吃会先被猪圈保安拦下",
        "help.mechanic.ai_copy_title": "AI 料理文案｜主厨偶尔请外援",
        "help.mechanic.ai_copy": "可请当前会话模型写菜谱；模型罢工时自动翻回本地菜单",
        "help.mechanic.report_random_eat_title": "日报祭品｜晚报偶尔真会吃人",
        "help.mechanic.report_random_eat": "只可能在自动日报发送时触发；手动翻报纸不会少人",
        "help.admin.panel_title": "管理面板",
        "help.admin.panel": "同步猪源、改猪、选图、配 EX、审投稿；按钮很多，猪还是那些猪",
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
