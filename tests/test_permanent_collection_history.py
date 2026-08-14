from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

from renderers.catalog import render_pigsty
from services.catalog_service import CatalogService


def _pig(pig_id: str, name: str | None = None) -> dict:
    return {
        "id": pig_id,
        "name": name or pig_id,
        "description": f"desc-{pig_id}",
        "analysis": f"analysis-{pig_id}",
    }


def test_collection_display_keeps_unlocked_retired_snapshot_outside_active_catalog():
    service = CatalogService(page_size=12)
    active = [_pig("a"), _pig("b"), _pig("c")]
    unlocked = {
        "b": {"count": 2, "first_unlocked": "2026-08-10"},
        "old-cloud": {"count": 4, "first_unlocked": "2026-08-01"},
    }
    snapshots = {"old-cloud": _pig("old-cloud", "旧云端猪")}

    display = service.collection_display_catalog(active, unlocked, snapshots)

    assert [pig["id"] for pig in display] == ["b", "old-cloud", "a", "c"]
    retired = display[1]
    assert retired["name"] == "旧云端猪"
    assert retired["_collection_retired"] is True
    # The read model must never mutate the active draw/search catalog.
    assert [pig["id"] for pig in active] == ["a", "b", "c"]
    assert "old-cloud" not in {pig["id"] for pig in service.sample(active, 3)}


def test_collection_display_respects_explicit_tombstone_for_historical_pig():
    display = CatalogService.collection_display_catalog(
        [_pig("active")],
        {
            "active": {"count": 1},
            "removed-by-admin": {"count": 3},
        },
        {"removed-by-admin": _pig("removed-by-admin")},
        hidden_ids={"removed-by-admin"},
    )

    assert [pig["id"] for pig in display] == ["active"]


def test_collection_display_has_safe_fallback_when_snapshot_is_missing():
    display = CatalogService.collection_display_catalog(
        [_pig("active")],
        {"missing-history": {"count": 1, "first_unlocked": "2026-07-01"}},
        {},
    )

    assert [pig["id"] for pig in display] == ["missing-history", "active"]
    assert display[0]["_collection_retired"] is True
    assert display[0]["name"] == "missing-history"
    assert "永久收藏" in display[0]["analysis"]


def test_retired_collection_entries_are_sorted_by_first_unlock_then_id():
    display = CatalogService.collection_display_catalog(
        [_pig("active")],
        {
            "old-b": {"count": 1, "first_unlocked": "2026-08-02"},
            "old-a": {"count": 1, "first_unlocked": "2026-08-02"},
            "old-first": {"count": 1, "first_unlocked": "2026-08-01"},
        },
        {},
    )

    assert [pig["id"] for pig in display[:3]] == ["old-first", "old-a", "old-b"]


def test_renderer_paginates_over_retired_entries_without_expanding_active_rate_denominator():
    active = [_pig(f"active-{index}") for index in range(12)]
    retired = {
        **_pig("retired", "历史猪"),
        "_collection_retired": True,
    }
    ordered = [*active, retired]
    user = {
        "total_draws": 1,
        "pigs": {
            "retired": {
                "count": 3,
                "first_unlocked": "2026-07-01",
                "last_drawn": "2026-07-03",
            }
        },
    }
    font_path = Path("resource/font/荆南麦圆体.otf")
    font = ImageFont.truetype(str(font_path), 24)
    palette = {
        "canvas": "#111111",
        "surface": "#222222",
        "title": "#ffffff",
        "secondary": "#dddddd",
        "muted": "#aaaaaa",
        "accent": "#eeeeee",
        "locked": "#333333",
        "locked_text": "#777777",
    }

    output, resolved_page = render_pigsty(
        catalog=active,
        user=user,
        ordered_pigs=ordered,
        favorite_name="历史猪",
        page=2,
        # Deliberately pass the active-only old value. The renderer must derive
        # pagination from the permanent display model and still reach page 2.
        total_pages=1,
        page_size=12,
        palette=palette,
        font_bold=font,
        font_regular=font,
        image_resolver=lambda _pig_id, _ex_level: None,
    )
    try:
        assert resolved_page == 2
        assert output.is_file()
        assert output.stat().st_size > 0
    finally:
        output.unlink(missing_ok=True)
