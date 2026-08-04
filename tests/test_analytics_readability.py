from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "pages/pig-manager/analytics-theme.css").read_text(encoding="utf-8")
OVERRIDE = CSS.split("/* v3.1.2 readable typography override */", 1)[1]


def test_readability_override_covers_all_dense_analytics_regions():
    required = {
        ".analytics-suite": "font-size: 14px",
        ".analytics-card__head h3": "font-size: 16px",
        ".analytics-card__head small": "font-size: 12px",
        ".activity-cell span": "font-size: 10.5px",
        ".platform-row > div": "font-size: 12.5px",
        ".rising-table__row": "min-height: 48px",
        ".rising-table__row small": "font-size: 11px",
        ".operations-grid span": "font-size: 12px",
    }
    for selector, declaration in required.items():
        assert selector in OVERRIDE
        assert declaration in OVERRIDE


def test_mobile_date_labels_do_not_return_to_micro_type():
    assert "@media (max-width: 430px)" in OVERRIDE
    assert ".activity-cell span { font-size: 10px; }" in OVERRIDE
