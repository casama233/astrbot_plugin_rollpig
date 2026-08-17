from __future__ import annotations

import json
import random
from pathlib import Path

from roast_copy import (
    ai_candidate_key,
    decode_ai_candidates,
    encode_ai_candidates,
    load_roast_copy_catalog,
    select_ai_candidate,
    select_local_roast_copy,
)


def test_bundled_roast_copy_has_thousands_of_combinations():
    path = Path(__file__).resolve().parents[1] / "resource" / "roast_copy.json"
    catalog = load_roast_copy_catalog(path)
    assert len(catalog["dish_names"]) >= 24
    assert len(catalog["lines"]) >= 64
    assert len(catalog["dish_names"]) * len(catalog["lines"]) >= 1500


def test_local_selector_avoids_recent_combination_keys():
    path = Path(__file__).resolve().parents[1] / "resource" / "roast_copy.json"
    catalog = load_roast_copy_catalog(path)
    first = select_local_roast_copy(catalog, pig_name="測試豬", rng=random.Random(3))
    second = select_local_roast_copy(
        catalog,
        pig_name="測試豬",
        recent_keys=[first["key"]],
        rng=random.Random(3),
    )
    assert second["key"] != first["key"]
    assert "{pig}" not in second["copy"]


def test_ai_bundle_supports_four_candidates_and_old_plain_text():
    candidates = [
        "豬鼻一拱，今天不是翻身而是翻面。",
        "豬籍還在，菜單先替它辦完了入住。",
        "EX 升滿也沒躲過後廚的升溫通知。",
        "Charge 掉了一格，群友的壞心眼滿格。",
    ]
    encoded = encode_ai_candidates(candidates)
    assert decode_ai_candidates(encoded) == candidates
    assert decode_ai_candidates("舊版單條文案") == ["舊版單條文案"]


def test_ai_selector_avoids_recent_candidate_when_possible():
    candidates = ["豬圈甲", "豬圈乙", "豬圈丙", "豬圈丁"]
    blocked = [ai_candidate_key(candidates[0]), ai_candidate_key(candidates[1]), ai_candidate_key(candidates[2])]
    picked = select_ai_candidate(candidates, recent_keys=blocked, rng=random.Random(1))
    assert picked == candidates[3]
