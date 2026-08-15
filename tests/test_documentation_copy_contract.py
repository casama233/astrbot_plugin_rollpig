from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_player_wiki_promotes_canonical_firewood_not_legacy_coal():
    player_pages = (
        "docs/index.md",
        "docs/getting-started/index.md",
        "docs/gameplay/index.md",
        "docs/gameplay/roast-charge.md",
        "docs/gameplay/daily-report.md",
    )
    for relative in player_pages:
        text = _read(relative)
        assert "/添柴" in text, relative
        assert "/添煤" not in text, relative

    # The legacy spelling remains searchable so old users can still discover
    # the new canonical docs without promoting it as the primary UI surface.
    terms = _read("docs/search-terms.txt")
    assert "添柴 100 nz" in terms
    assert "添煤 80 nz" in terms


def test_command_reference_tracks_charge_and_contextual_firewood_semantics():
    text = _read("docs/COMMANDS.md")
    assert "v3.6.3" not in text
    assert "group_roast_max_charges" in text
    assert "每缺一格 Charge" in text
    assert "/添柴 @目標" in text
    assert "只作補貨相容入口" in text


def test_configuration_reference_matches_public_schema_for_roast_energy():
    text = _read("docs/CONFIGURATION.md")
    assert "`group_roast_max_charges`" in text
    assert "每缺一格 Charge 的自然恢復時間" in text
    assert "/添柴 @目標" in text
    assert "它不是群體補貨的 `/添柴` 指令" not in text

    schema = json.loads(_read("_conf_schema.json"))
    assert schema["group_roast_max_charges"]["default"] == 2
    assert "每格能量的恢复周期" in schema["group_roast_cooldown_hours"]["hint"]
    reservation_hint = schema["enable_roast_reservation"]["hint"]
    assert "/添柴 @目标" in reservation_hint
    assert "再次 /烤群友 @同一目标 仍兼容" in reservation_hint


def test_pigsty_renderer_uses_player_facing_pig_registry_voice():
    source = _read("renderers/catalog.py")
    for signature in (
        "我的猪圈 · 猪籍档案",
        "现役入圈",
        "老猪留档",
        "最常返场",
        "老猪籍",
        "还没拱进你家",
        "熟猪优先",
    ):
        assert signature in source

    # Keep the exact data dimensions visible even after the copy remaster.
    assert "unlocked_count" in source
    assert "retired_count" in source
    assert "highest_ex" in source
    assert "total_draws" in source


def test_docs_index_covers_current_player_and_maintainer_surfaces():
    index = _read("docs/README.md")
    for required in (
        "gameplay/roast-charge.md",
        "ROAST-CHARGES.md",
        "ROAST-RESERVATIONS.md",
        "EX-ACCEPTANCE.md",
        "COPY-STYLE.md",
        "COLLECTION-IDENTITY.md",
    ):
        assert required in index

    style = _read("docs/COPY-STYLE.md")
    assert "Wiki / README" in style
    assert "永久豬籍／圖鑑 renderer" in style
    assert "compatibility alias" in style
