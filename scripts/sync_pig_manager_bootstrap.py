from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "pig-manager" / "index.html"
BOOTSTRAP = ROOT / "pages" / "pig-manager" / "ui-bootstrap.js"

_BOOTSTRAP_BLOCK = re.compile(
    r'<script data-rollpig-bootstrap="3\.2\.0">.*?</script>',
    re.S,
)
_OLD_SYNC_FEEDBACK = (
    "const setSyncFeedback=message=>$('syncFeedback').textContent=message;"
)
_EVENT_SYNC_FEEDBACK = (
    "const setSyncFeedback=message=>{const host=$('syncFeedback');"
    "host.textContent=message;"
    "window.__rollpigUiBootstrapState?.setResourceSyncFeedback?.(host,message)};"
)


def render_page(page: str, bootstrap: str) -> str:
    block = (
        '<script data-rollpig-bootstrap="3.2.0">\n'
        f"{bootstrap.rstrip()}\n"
        "</script>"
    )
    # Use a replacement function instead of a replacement string. ``re.sub``
    # interprets backslash escapes in replacement strings, which would turn
    # JavaScript ``\\n`` literals inside the bootstrap into real newlines and
    # break the byte-for-byte inline/source contract.
    updated, count = _BOOTSTRAP_BLOCK.subn(lambda _match: block, page, count=1)
    if count != 1:
        raise RuntimeError("pig-manager bootstrap block not found exactly once")

    if _OLD_SYNC_FEEDBACK in updated:
        updated = updated.replace(
            _OLD_SYNC_FEEDBACK,
            _EVENT_SYNC_FEEDBACK,
            1,
        )
    elif _EVENT_SYNC_FEEDBACK not in updated:
        raise RuntimeError("pig-manager setSyncFeedback hook not found")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize pig-manager inline bootstrap and Wiki feedback hook."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if index.html is not already synchronized.",
    )
    args = parser.parse_args()

    original = PAGE.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    expected = render_page(original, bootstrap)

    if args.check:
        if expected != original:
            print("pig-manager bootstrap is out of sync; run this script without --check")
            return 1
        print("pig-manager bootstrap and Wiki feedback hook are synchronized")
        return 0

    if expected == original:
        print("pig-manager bootstrap already synchronized")
        return 0

    PAGE.write_text(expected, encoding="utf-8")
    print("updated pages/pig-manager/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
