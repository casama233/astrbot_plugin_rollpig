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
            return "你今天还没有抽取小猪。" if actor else "对方今天还没有抽取小猪。"
        name = self._name(pig)
        if state == "human":
            if actor:
                return "你今天是「人类」：只能围观，不能参与猪圈料理。"
            return "对方今天是「人类」：猪圈劳动合同不支持把人送上烤架。"
        if state == "eaten":
            if actor:
                return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
            return "对方今天是「吃掉了」：盘子都空了，不能继续参与烧烤流程。"
        if actor:
            return f"你今天是「{name}」：已经上桌了，不能再次参与烧烤。"
        return f"对方今天是「{name}」：已经是熟食，不能再上一次烤架。"

    def eat_actor_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        if state == "missing":
            return "你今天还没有抽取小猪，不能发动吃群友。"
        name = self._name(pig)
        if state == "human":
            return "你今天是「人类」：猪圈菜单不允许人类发动吃群友。"
        if state == "eaten":
            return "你今天是「吃掉了」：盘子都空了，已经无法行动。"
        return f"你今天是「{name}」：已经上桌了，暂时不能去吃群友。"

    def eat_target_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state in {"normal", "cooked"}:
            return None
        if state == "missing":
            return "对方今天还没有抽取小猪。"
        if state == "human":
            return "对方今天是「人类」：吃人不在猪圈菜单里。"
        return "对方今天已经是「吃掉了」：盘子空了，不能再吃一次。"

    def eat_success_message(self, pig: Mapping[str, Any]) -> str:
        name = self._name(pig)
        action = (
            "开袋即食成功"
            if special_pig_state(dict(pig)) == "cooked"
            else "吃群友成功"
        )
        return f" 🍴 {action}，「{name}」被吃掉了；明天抽猪可能失败。"

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
            f"🛡️ 对方昨天被烤了 {count} 次，今天已获得猪圈保护。"
            "普通烧烤会被拦截；后门强制模式仍可突破保护。"
        )
