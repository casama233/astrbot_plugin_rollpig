from __future__ import annotations


def mention_body_on_new_line(text: object) -> str:
    """Place mention-following body text on exactly one fresh line.

    Existing callers historically prefix their copy with a single space so the
    text does not stick to an @ mention.  The shared mention sender now gives the
    mention its own line instead, so remove only leading layout whitespace while
    preserving the body and any internal paragraph breaks.
    """
    body = str(text or "").lstrip(" \t\r\n")
    return f"\n{body}" if body else ""
