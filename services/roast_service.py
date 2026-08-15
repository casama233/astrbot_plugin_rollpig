from __future__ import annotations

import math
import random
from typing import Any, Mapping

try:
    from ..rollpig_core import special_pig_state
except ImportError:  # pragma: no cover - direct module loading compatibility
    from rollpig_core import special_pig_state


class RoastService:
    """Pure eligibility, outcome and copy policy for roast/eat actions."""

    GROUP_ROAST_OUTCOMES = ("success", "escape", "backlash")
    GROUP_ROAST_WEIGHTS = (60, 30, 10)

    @staticmethod
    def _name(pig: Mapping[str, Any] | None) -> str:
        value = pig or {}
        return str(value.get("name") or value.get("id") or "特殊形态").strip()

    def roast_block_reason(
        self, pig: Mapping[str, Any] | None, *, subject: str = "target"
    ) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        actor = subject == "actor"
        if state == "missing":
            return (
                "🐷 你今天还没抽猪。没有食材证，后厨不让你碰火。"
                if actor
                else "🐷 对方今天还没抽猪。现在烤架上只有空气。"
            )
        name = self._name(pig)
        if state == "human":
            if actor:
                return (
                    "🧍 你今天抽到的是「人类」。"
                    "猪圈菜单写得很清楚：人只能围观，不能掌勺。"
                )
            return (
                "🧍 对方今天是「人类」。"
                "猪圈劳动合同再离谱，也没写可以把员工送上烤架。"
            )
        if state == "eaten":
            if actor:
                return (
                    "🍽️ 你今天已经是「吃掉了」。盘子都舔干净了，"
                    "别再假装还有一只猪能行动。"
                )
            return (
                "🍽️ 对方今天已经是「吃掉了」。"
                "盘子里只剩反光，后厨没法二次加工。"
            )
        if actor:
            return (
                f"🍖 你今天是「{name}」：已经上桌了。"
                "后厨不接受熟食重新报名当主厨。"
            )
        return (
            f"🍖 对方今天是「{name}」：已经是熟食。"
            "同一盘菜不能再过一次烤架。"
        )

    def eat_actor_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        if state == "missing":
            return (
                "🐷 你今天还没抽猪。自己连猪证都没有，"
                "先别急着张嘴吃群友。"
            )
        name = self._name(pig)
        if state == "human":
            return (
                "🧍 你今天是「人类」。猪圈菜单拒绝人类发动吃群友。"
                "今天你负责拿筷子，不负责吃人。"
            )
        if state == "eaten":
            return (
                "🍽️ 你今天已经是「吃掉了」。盘子都空了，"
                "就别从餐后回忆里爬回来找饭。"
            )
        return (
            f"🍖 你今天是「{name}」：已经上桌了。"
            "熟食先躺好，暂时别去追着别人吃。"
        )

    def eat_target_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state in {"normal", "cooked"}:
            return None
        if state == "missing":
            return "🐷 对方今天还没抽猪。菜单上目前只有一个空盘子。"
        if state == "human":
            return (
                "🧍 对方今天是「人类」。吃人不在猪圈菜单里——"
                "后厨再野，也还没野到刑法那一页。"
            )
        return (
            "🍽️ 对方今天已经是「吃掉了」。"
            "盘子里连渣都没剩，不能再吃一次。"
        )

    def eat_success_message(self, pig: Mapping[str, Any]) -> str:
        name = self._name(pig)
        action = (
            "开袋即食成功"
            if special_pig_state(dict(pig)) == "cooked"
            else "吃群友成功"
        )
        return (
            f" 🍴 {action}，「{name}」当场从猪圈名册变成餐后回忆；"
            "明天抽猪可能会翻车。"
        )

    def choose_group_roast_outcome(self, *, bypass: bool = False, rng=None) -> str:
        """Return the existing 60/30/10 roast outcome from one policy source."""
        if bypass:
            return "success"
        chooser = rng or random
        return str(
            chooser.choices(
                self.GROUP_ROAST_OUTCOMES,
                weights=self.GROUP_ROAST_WEIGHTS,
                k=1,
            )[0]
        )

    @staticmethod
    def format_cooldown(seconds: int) -> str:
        seconds = max(1, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes = max(1, math.ceil(remainder / 60)) if remainder else 0
        return f"{hours} 小时 {minutes} 分" if hours else f"{minutes} 分钟"

    @staticmethod
    def roast_protection_message(count: int) -> str:
        return (
            f"🛡️ 对方昨天被成功烤了 {count} 次，今天领到『猪身安全险』。"
            "普通烤／吃会被猪圈保安拦下；后门强制模式仍然不讲武德。"
        )
