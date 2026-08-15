from __future__ import annotations

import json
from pathlib import Path

from ex_variants import validate_ex_variants


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "resource"
RESTORED_COMPAT_IDS = {
    "ai-pig",
    "arknights-pig",
    "astro-pig",
    "awakened-pig",
    "balloon-pig",
    "big-stomach-pig",
    "bone-soup-pig",
    "bull-pig",
    "cage-pig",
    "canned-pig",
    "carrot-ghost-pig",
    "cart-pig",
    "chainsaw-pig",
    "charge-pig",
    "chat-spam-pig",
    "christmas-pig",
    "civil-eng-pig",
    "class-pig",
    "cloud-pig",
    "cocktail-pig",
    "coding-pig",
    "doctor-pig",
    "doomsday-pig",
    "doro-pig",
    "drunk-pig",
    "duel-pig",
    "duke-pig",
    "dumb-pig",
    "dumpling-pig",
    "earthy-pig",
    "eaten",
    "emoji-king-pig",
    "fat-pig",
    "fine-chaff-boar",
    "flu-pig",
    "ground-impact-pig",
    "gym-pig",
    "halloween-pig",
    "hannibal-pig",
    "hotdog-pig",
    "jelly-pig",
    "jiahao-pig",
    "jurassic-pig",
    "katsu-rice-pig",
    "kiss-pig",
    "laborer-pig",
    "lion-pig",
    "lone-pig",
    "lucky-mud-pig",
    "magic-pig-cat",
    "maid-pig",
    "mc-pig",
    "mcdonalds-pig",
    "melting-pig",
    "miku-pig",
    "ninja-pig",
    "niuma-pig",
    "noob-pig",
    "nurse-pig",
    "oil-painting-pig",
    "oriental-pearl-pig",
    "palico-pig",
    "parking-pig",
    "party-pig",
    "pig-coin",
    "pig-king",
    "pig-rabbit-cage",
    "pig-rice",
    "piggsium",
    "pigtok",
    "police-pig",
    "rail-pig",
    "rolling-pig",
    "room-check-pig",
    "samurai-pig",
    "screenshot-pig",
    "shit-pig",
    "shocking-delicious",
    "shop-pig",
    "shopping-pig",
    "shrimp-sushi-pig",
    "sleepy-pig",
    "slippery-pig",
    "smug-pig",
    "sold-out",
    "soup-pig",
    "spring-festival-pig",
    "squint-pig",
    "stacking-pig",
    "stem-pig",
    "strawberry-cake-pig",
    "stressed-pig",
    "sushi-platter-pig",
    "tamagoyaki-pig",
    "thief-pig",
    "trap-pig",
    "tv-pig",
    "twitch-pig",
    "ufo-pig",
    "unchained-pig-king",
    "wechat-pig",
    "yiwei-pig",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _curated_authoring() -> tuple[dict, dict[str, str]]:
    merged: dict = {}
    source_by_id: dict[str, str] = {}
    documents = [RESOURCE / "pig_ex_variants.json", *sorted((RESOURCE / "ex_curated").glob("*.json"))]
    assert len(documents) == 11  # one original 10-pig pack + ten curated packs
    for path in documents:
        variants = validate_ex_variants(
            _load(path),
            image_extensions={"png", "jpg", "jpeg", "webp", "gif"},
        )
        duplicates = set(merged).intersection(variants)
        assert not duplicates, f"duplicate curated pig IDs in {path.name}: {sorted(duplicates)}"
        for pig_id in variants:
            source_by_id[pig_id] = path.name
        merged.update(variants)
    return merged, source_by_id


def test_handcrafted_authoring_exactly_covers_all_201_official_pigs():
    primary = _load(RESOURCE / "pig.json")
    primary_ids = {str(item["id"]) for item in primary}
    assert len(primary_ids) == 99
    assert len(RESTORED_COMPAT_IDS) == 102
    assert not primary_ids.intersection(RESTORED_COMPAT_IDS)

    curated, _ = _curated_authoring()
    expected = primary_ids | RESTORED_COMPAT_IDS
    assert len(expected) == 201
    assert set(curated) == expected


def test_every_official_pig_has_five_complete_distinct_handcrafted_levels():
    curated, source_by_id = _curated_authoring()
    for pig_id, levels in curated.items():
        assert set(levels) == {1, 2, 3, 4, 5}, (pig_id, source_by_id[pig_id])
        descriptions = [str(levels[level].get("description") or "").strip() for level in range(1, 6)]
        analyses = [str(levels[level].get("analysis") or "").strip() for level in range(1, 6)]
        assert all(descriptions), (pig_id, "description", source_by_id[pig_id])
        assert all(analyses), (pig_id, "analysis", source_by_id[pig_id])
        assert len(set(descriptions)) == 5, (pig_id, "description", source_by_id[pig_id])
        assert len(set(analyses)) == 5, (pig_id, "analysis", source_by_id[pig_id])
        assert all(len(value) <= 120 for value in descriptions), pig_id
        assert all(len(value) <= 800 for value in analyses), pig_id


def test_curated_pack_counts_lock_the_191_new_handwritten_pigs():
    base = validate_ex_variants(_load(RESOURCE / "pig_ex_variants.json"))
    curated, source_by_id = _curated_authoring()
    pack_ids = set(curated).difference(base)

    assert len(base) == 10
    assert len(pack_ids) == 191
    assert len(curated) == 201
    assert all(source_by_id[pig_id].startswith(tuple(f"{index:02d}-" for index in range(1, 11))) for pig_id in pack_ids)
