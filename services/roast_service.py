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
        return str(value.get("name") or value.get("id") or '变异形态').strip()

    def roast_block_reason(
        self, pig: Mapping[str, Any] | None, *, subject: str = "target"
    ) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        actor = subject == "actor"
        if state == "missing":
            return (
                '🐷 你今日还未领猪，手里攥着空火钳对着炉膛干瞪眼。'
                if actor
                else '🐷 翻遍名册他那栏仍是空白，对方今日尚未抽猪，根本无从下火。'
            )
        name = self._name(pig)
        if state == "human":
            if actor:
                return (
                    '🧍 你今日抽中了「人类」。猪圈铁律明文规定：人类仅限围观，严禁亲自下场操作。'
                )
            return (
                '🧍 对方今日身为人类，烤夹刚凑近便被一巴掌拍了回来。'
            )
        if state == "eaten":
            if actor:
                return (
                    '🍽️ 你今日状态已是「吃掉了」。餐盘都舔得锃亮，就别再幻想还有猪能折腾了。'
                )
            return (
                '🍽️ 对方今日已是「吃掉了」。碗底朝天连渣都不剩，实在没法回炉重造。'
            )
        if actor:
            return (
                f'🍖 你今日已是「{name}」：早已端上餐桌。熟猪就请体面躺平，莫要妄想爬起来掌勺。'
            )
        return (
            f'🍖 对方今日已是「{name}」：属于标准熟食。同一道菜可不兴架火烤上第二遭。'
        )

    def eat_actor_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state == "normal":
            return None
        if state == "missing":
            return (
                '🐷 你今日尚未抽猪。连猪圈户口本都还没领，先别急着张嘴啃群友。'
            )
        name = self._name(pig)
        if state == "human":
            return (
                '🧍 你今日抽到了「人类」。猪圈严禁人类发动吃群友，今日只管当个看客，莫要轻易下嘴。'
            )
        if state == "eaten":
            return (
                '🍽️ 你今日已是「吃掉了」。餐盘早就空空如也，别指望从回忆里爬出来继续干饭。'
            )
        return (
            f'🍖 你今日已是「{name}」：已经端盘上桌。熟猪请保持安详，别再爬起来追着旁人啃。'
        )

    def eat_target_block_reason(self, pig: Mapping[str, Any] | None) -> str | None:
        state = special_pig_state(dict(pig) if isinstance(pig, Mapping) else None)
        if state in {"normal", "cooked"}:
            return None
        if state == "missing":
            return '🐷 对方今日还没抽猪，你举着筷子在半空夹了个寂寞。'
        if state == "human":
            return (
                '🧍 对方今日是「人类」。吃人不在猪圈业务范畴内——再怎么野也不敢触碰刑法红线。'
            )
        return (
            '🍽️ 对方今日状态显示已被吃掉，无法重复进食，结账小票早就打印出来了。'
        )

    def eat_success_message(self, pig: Mapping[str, Any]) -> str:
        name = self._name(pig)
        action = (
            '开袋即食大成功'
            if special_pig_state(dict(pig)) == "cooked"
            else '吃群友大成功'
        )
        return (
            f' 🍴 {action}，「{name}」今日已被标为进食完毕并写入餐后回忆录（永久图鉴不受影响），明日抽猪照常发车，说不定还会重逢老熟猪。'
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
        return f'{hours} 小时 {minutes} 分钟' if hours else f"{minutes} 分钟"

    @staticmethod
    def roast_protection_message(count: int) -> str:
        return (
            f'🛡️ 对方昨日在本群被成功烤了 {count} 次，今日同群喜提『猪身安全险』。普通烤／吃会被猪圈保安直接架走，但后门强制模式依旧不讲武德。'
        )
