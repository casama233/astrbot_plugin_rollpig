from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence

try:
    from ..rollpig_core import special_pig_state
except ImportError:  # pragma: no cover - direct module loading compatibility
    from rollpig_core import special_pig_state


class RoastService:
    """Pure eligibility, outcome and copy policy for roast/eat actions."""

    GROUP_ROAST_OUTCOMES = ("success", "escape", "backlash")
    GROUP_ROAST_WEIGHTS = (70, 20, 10)

    def __init__(self, rng=None):
        # Keep roast randomness isolated from Python's process-global ``random``
        # state. AstrBot hosts multiple plugins in one interpreter and another
        # plugin calling ``random.seed(...)`` must not make roast outcomes or
        # random roast targeting predictable/repeating.
        self._rng = rng or random.SystemRandom()

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
                '🐷 你自己今天还没抽猪，拎着空夹子对着炉火干瞪眼。'
                if actor
                else '🐷 翻遍菜单他那栏还是空的，人今天还没抽猪，点不着火。'
            )
        name = self._name(pig)
        if state == "human":
            if actor:
                return (
                    '🧍 你今天抽到的是「人类」。猪圈规矩写得很死：人类只准围观，不准上手操作。'
                )
            return (
                '🧍 对方今天是人类，烤夹刚凑过去就被一把拍开。'
            )
        if state == "eaten":
            if actor:
                return (
                    '🍽️ 你今天已经是「吃掉了」。盘子都舔反光了，别再假装还有猪能折腾。'
                )
            return (
                '🍽️ 对方今天已经是「吃掉了」。碗底都朝天了，没法再回炉折腾一遍。'
            )
        if actor:
            return (
                f'🍖 你今天是「{name}」：已经上桌了。熟猪就安详躺平，别想着爬起来掌勺。'
            )
        return (
            f'🍖 对方今天是「{name}」：已经是熟食了。同一盘菜可不兴再架火烤第二遍。'
        )

    def eat_actor_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        if state == "missing":
            return (
                '🐷 你今天还没抽猪。自己连猪圈户口都没领，先别急着张嘴啃群友。'
            )
        name = self._name(pig)
        if state == "human":
            return (
                '🧍 你今天是「人类」。猪圈禁止人类发动吃群友，今天你只负责围观，不负责下嘴。'
            )
        if state == "eaten":
            return (
                '🍽️ 你今天已经是「吃掉了」。盘子早空了，别指望从回忆里爬出来继续干饭。'
            )
        return (
            f'🍖 你今天是「{name}」：已经上桌了。熟猪请体面躺平，别再爬起来追着别人啃。'
        )

    def eat_target_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state in {"normal", "cooked"}:
            return None
        if state == "missing":
            return '🐷 对方今天还没抽猪，你举着筷子在空气里夹了个响。'
        if state == "human":
            return (
                '🧍 对方今天是「人类」。吃人不在猪圈业务范围内——再野也不敢翻开刑法那一页。'
            )
        return (
            '🍽️ 对方今日状态已被吃掉，无法再吃，收据早就打完啦。'
        )

    def eat_success_message(self, pig: Mapping[str, Any]) -> str:
        name = self._name(pig)
        action = (
            "开袋即食成功"
            if special_pig_state(dict(pig)) == "cooked"
            else "吃群友成功"
        )
        return (
            f' 🍴 {action}，「{name}」当场从猪圈名册掉进餐后回忆录，明天抽猪保不齐要翻车。'
        )

    def choose_group_roast_target(
        self, candidates: Sequence[str], *, rng=None
    ) -> str:
        """Choose one eligible target without using process-global RNG state."""
        pool = tuple(str(item) for item in candidates if str(item))
        if not pool:
            raise ValueError("roast target candidates must not be empty")
        chooser = rng or self._rng
        return str(chooser.choice(pool))

    def choose_group_roast_outcome(self, *, bypass: bool = False, rng=None) -> str:
        """Return the shared 70/20/10 roast outcome from one policy source."""
        if bypass:
            return "success"
        chooser = rng or self._rng
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
            f'🛡️ 对方昨天被成功烤了 {count} 次，今天喜提『猪身安全险』。普通烤／吃会被猪圈保安直接架走，但后门强制模式依旧不讲武德。'
        )
