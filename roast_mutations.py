from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RoastMode = Literal["direct", "random", "reservation"]
NO_ODDS_DELTA = (0, 0, 0)


@dataclass(frozen=True)
class Mutation:
    food: str
    odds_delta: tuple[int, int, int] = NO_ODDS_DELTA
    odds_mode: RoastMode | None = None
    draw_ex: int = 0
    roast_ex: int = 0
    roast_mode: RoastMode | None = None
    roast_copy: str = ""


# Food and effect IDs are saved separately so a meal can choose its effect once.
MUTATIONS: dict[str, Mutation] = {
    "spicy": Mutation("spicy", odds_delta=(-10, 0, 10)),
    "rich": Mutation("rich", roast_ex=1, roast_copy="feed_roast_bonus"),
    "dream_glow": Mutation("dream", draw_ex=2),
    "dream_thin": Mutation("dream", odds_delta=(-15, 15, 0), draw_ex=-2),
    "calm": Mutation(
        "calm", odds_delta=(30, -20, -10), roast_ex=-1,
        roast_copy="feed_calm_roast_bonus",
    ),
    "chewy": Mutation(
        "chewy", odds_delta=(-30, 30, 0), odds_mode="reservation",
        roast_ex=1, roast_mode="random", roast_copy="feed_chewy_roast_bonus",
    ),
    "butter": Mutation(
        "butter", odds_delta=(-20, 30, -10), roast_ex=2,
        roast_copy="feed_butter_roast_bonus",
    ),
    "redhot": Mutation(
        "redhot", odds_delta=(-5, -20, 25), draw_ex=1, roast_ex=1,
        roast_copy="feed_redhot_roast_bonus",
    ),
}

FEEDING_MENU: dict[str, tuple[str, ...]] = {}
for effect_id, mutation in MUTATIONS.items():
    FEEDING_MENU[mutation.food] = (*FEEDING_MENU.get(mutation.food, ()), effect_id)
