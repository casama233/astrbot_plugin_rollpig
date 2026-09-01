from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE4_SENTINELS = {
    "abstract-pig": ("面数不足，猪味够", "再减就是猪方块"),
    "big-lazy-pig": ("先躺五分钟", "猪生已永久横屏"),
    "computer-pig": ("开机请等半小时", "答案出了：明天再看"),
    "fishing-pig": ("今天真摸到鱼了", "带薪摸鱼，功德圆满"),
    "landmine-pig": ("没事，先开一罐", "天亮了，箱也空了"),
    "pig-turtle": ("有事先缩一下", "问题还在，猪没了"),
    "stuck-pig": ("门：禁止本猪通过", "门框先辞职了"),
    "study-pig": ("书名有点针对猪", "知识改变命运：先跑路"),
}


def test_phase4_shard_reaches_effective_bundled_loader_text_only():
    pigs = json.loads((RESOURCE_DIR / "pig.json").read_text(encoding="utf-8-sig"))
    pig_ids = {
        str(item.get("id") or "")
        for item in pigs
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    variants = load_bundled_ex_copy(
        RESOURCE_DIR,
        pig_ids,
        pig_ids,
        image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
    )

    for pig_id, (ex1, ex5) in PHASE4_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())
