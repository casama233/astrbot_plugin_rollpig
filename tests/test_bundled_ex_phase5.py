from __future__ import annotations

import json
from pathlib import Path

from bundled_ex_copy import load_bundled_ex_copy


ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = ROOT / "resource"
PHASE5_SENTINELS = {
    "bacon": ("猪已切换条状", "煎熬到最后成早餐"),
    "bandage-pig": ("绷不住了（物理）", "木乃猪热修版"),
    "clean-pig": ("泥坑已被拉黑", "洗到猪圈开始反光"),
    "coder-pig": ("本地明明是好的", "服务崩了，我也崩了"),
    "delivery-pig": ("此面朝上，猪也朝上", "拆箱发现是活猪"),
    "dirty-pig": ("这是泥膜，不是脏", "泥坑原厂漆"),
    "homebody-pig": ("今天也不出门", "世界很大，Wi-Fi 满格"),
    "roasted-pig": ("火有点大", "生活下手，直接出餐"),
}


def test_phase5_shard_reaches_effective_bundled_loader_text_only():
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

    for pig_id, (ex1, ex5) in PHASE5_SENTINELS.items():
        levels = variants[pig_id]
        assert levels[1]["description"] == ex1
        assert levels[5]["description"] == ex5
        assert set(levels) == {1, 2, 3, 4, 5}
        assert all(set(item) == {"description", "analysis"} for item in levels.values())
