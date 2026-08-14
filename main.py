"""RollPig plugin entry point.

AstrBot command decorators intentionally live in this module. Business logic may
remain in ``legacy_main`` or focused feature mixins during the gradual refactor,
but helper modules must not register commands themselves. Thin wrappers below
delegate to the inherited implementation and keep AstrBot handler ownership,
priority and unload semantics bound to the real Star entry point.
"""

from astrbot.api.event import AstrMessageEvent, filter

try:
    from .daily_report_feature import DailyReportMixin
    from .ex_variant_feature import ExVariantMixin
    from .legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from .permanent_collection_feature import PermanentCollectionMixin
    from .roast_reservation_feature import RoastReservationMixin
except ImportError:  # pragma: no cover - direct module loading compatibility
    from daily_report_feature import DailyReportMixin
    from ex_variant_feature import ExVariantMixin
    from legacy_main import RollPigPlugin as _BaseRollPigPlugin
    from permanent_collection_feature import PermanentCollectionMixin
    from roast_reservation_feature import RoastReservationMixin


class RollPigPlugin(
    RoastReservationMixin,
    DailyReportMixin,
    ExVariantMixin,
    PermanentCollectionMixin,
    _BaseRollPigPlugin,
):
    """RollPig Plus with growth, roast reservations and rich daily reports."""

    # BEGIN MAIN COMMAND REGISTRATION
    # Decorators stay on the real Star entry module; implementations live below.
    @filter.command('猪猪帮助', alias={'豬豬幫助', '小猪帮助', '小豬幫助', 'rollpig帮助', 'rollpig幫助'}, priority=1000)
    async def rollpig_help(self, event: AstrMessageEvent):
        """展示今日小猪的完整指令说明。"""
        return await super().rollpig_help(event)

    @filter.command('今日小猪', alias={'今日小豬', '今天是什么小猪', '今天是什麼小豬', '抽小猪', '抽小豬', '我的小猪', '我的小豬', 'rollpig'}, priority=1000)
    async def roll_pig(self, event: AstrMessageEvent):
        """Draw for self; mentioning another user is strictly read-only."""
        return await super().roll_pig(event)

    @filter.command('我的猪圈', alias={'我的豬圈', '小猪图鉴', '小豬圖鑑', '猪圈', '豬圈'}, priority=1000)
    async def my_pigsty(self, event: AstrMessageEvent, args: str=''):
        """查看永久解锁的小猪图鉴，可附带页码。"""
        return await super().my_pigsty(event, args)

    @filter.command('昨日小猪', alias={'昨日小豬', '昨天小猪', '昨天小豬'}, priority=1000)
    async def yesterday_pig(self, event: AstrMessageEvent):
        """查看昨天抽到的小猪。"""
        return await super().yesterday_pig(event)

    @filter.command('明日小猪', alias={'明日小豬', '明天小猪', '明天小豬'}, priority=1000)
    async def tomorrow_pig(self, event: AstrMessageEvent):
        """给出每天固定、但不会提前解锁图鉴的明日预测。"""
        return await super().tomorrow_pig(event)

    @filter.command('本周小猪', alias={'本周小豬', '本週小猪', '本週小豬', '本周猪报', '本週豬報'}, priority=1000)
    async def weekly_pigs(self, event: AstrMessageEvent):
        """生成本周七日抽取总结。"""
        return await super().weekly_pigs(event)

    @filter.command('随机小猪', alias={'随机小豬', '隨機小猪', '隨機小豬', '随机猪', '隨機豬'}, priority=1000)
    async def random_pigs(self, event: AstrMessageEvent, args: str=''):
        """从本地图鉴随机展示 1-9 只小猪，不影响每日抽取。"""
        return await super().random_pigs(event, args)

    @filter.command('找猪', alias={'找豬', '搜猪', '搜豬'}, priority=1000)
    async def find_pigs(self, event: AstrMessageEvent, keyword: str=''):
        """在管理员维护的本地图鉴内搜索。"""
        return await super().find_pigs(event, keyword)

    @filter.command('今日烤猪', alias={'今日烤豬', '烤猪', '烤豬'}, priority=1000)
    async def roast_today_pig(self, event: AstrMessageEvent):
        """把自己的当天小猪做成趣味料理卡，不改变抽取结果。"""
        return await super().roast_today_pig(event)

    @filter.command('烤群友', alias={'烤群友'}, priority=1000)
    async def roast_group_member(self, event: AstrMessageEvent, args: str=''):
        """在群聊中烧烤 @ 目标或引用消息的发送者。"""
        return await super().roast_group_member(event, args)

    @filter.command('随机烤群友', alias={'隨機烤群友'}, priority=1000)
    async def roast_random_group_member(self, event: AstrMessageEvent):
        """从今天在当前群聊抽过小猪的成员中随机挑选一位。"""
        return await super().roast_random_group_member(event)

    @filter.command('吃群友', alias={'吃群友'}, priority=1000)
    async def eat_group_member(self, event: AstrMessageEvent, args: str=''):
        """低概率吃掉 @ 目标；失败者会把自己吃掉。"""
        return await super().eat_group_member(event, args)

    @filter.command('随机吃群友', alias={'隨機吃群友'}, priority=1000)
    async def eat_random_group_member(self, event: AstrMessageEvent):
        """从当天当前群可被吃的成员中随机选择一位。"""
        return await super().eat_random_group_member(event)

    @filter.command('打点后厨', alias={'打點後廚', '偷换烤架', '偷換烤架', '贿赂主厨', '賄賂主廚', '加急生火', '强行点火', '強行點火'}, priority=1000)
    async def force_roast_group_member(self, event: AstrMessageEvent, args: str=''):
        """后门口令：绕过烤群友冷却与概率，但不绕过资格限制。"""
        return await super().force_roast_group_member(event, args)

    @filter.command('猪圈日报', alias={'豬圈日報', '今日猪圈日报', '今日豬圈日報'}, priority=1000)
    async def pigsty_daily_report(self, event: AstrMessageEvent, args: str=''):
        """查看日报，或由群管理开启/关闭本群自动推送。"""
        return await super().pigsty_daily_report(event, args)
    # END MAIN COMMAND REGISTRATION

    # Keep the management UI cache contract visible at the plugin entry point.
    UI_ASSET_VERSION = "3.1.2"

    def _init_regular_font(self):
        """Load the packaged full CJK font before platform fallbacks.

        Marketplace archives have a strict 16 MB ceiling. Release builds keep
        荆南麦圆体.otf as the single bundled full CJK face so both body text and
        titles remain readable without silently falling through to DejaVu.
        """
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "常规")

    def _init_bold_font(self):
        """Load the packaged full CJK title font before platform fallbacks."""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "SourceHanSansCN-Bold.otf",
            "C:/Windows/Fonts/msyhbd.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        return self._load_font(font_paths, self.NAME_FONT_SIZE, "加粗")

    def _init_traditional_font(self):
        """Use the packaged full CJK face for traditional/AI copy before system fallbacks."""
        font_paths = [
            self.font_dir / "荆南麦圆体.otf",
            self.font_dir / "HanyiYongZiXiaoXiongMaoFan.ttf",
            self.font_dir / "SourceHanSansCN-Regular.otf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        return self._load_font(font_paths, self.DESC_FONT_SIZE, "繁体兜底")
