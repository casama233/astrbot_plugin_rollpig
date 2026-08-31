from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_MAIN = ROOT / "legacy_main.py"

# P2 architecture debt baseline captured from main on 2026-08-31.
# This is intentionally a shrink-only ceiling: extracting legacy code should
# lower the number; new features belong in main.py, feature modules, services,
# renderers, or storage modules rather than growing legacy_main.py again.
LEGACY_MAIN_MAX_BYTES = 286_646


def test_legacy_main_is_shrink_only() -> None:
    size = LEGACY_MAIN.stat().st_size
    assert size <= LEGACY_MAIN_MAX_BYTES, (
        "legacy_main.py exceeded the shrink-only architecture budget: "
        f"{size:,} > {LEGACY_MAIN_MAX_BYTES:,} bytes. "
        "Do not add new functionality to legacy_main.py; place it behind the "
        "canonical main.py/feature/service/renderer/storage boundaries instead. "
        "When a refactor makes legacy_main.py smaller, lower the budget in this test."
    )
