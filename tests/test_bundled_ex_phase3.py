from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE3_SENTINELS = {
    "goblin-pig": ("外卖放门口，谢谢", "文明社会已退出"),
    "leek-pig": ("刚割完，又冒头了", "韭菜永动机"),
    "spider-pig": ("我不是猪，我是 Bug", "Issue 区生态保护"),
    "watermelon-pig": ("前排吃瓜", "瓜吃群众"),
}


def test_phase3_shard_reaches_effective_bundled_loader_text_only():
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

    for pig_id, (ex1, ex5) in PHASE3_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())
