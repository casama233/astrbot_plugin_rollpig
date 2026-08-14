from __future__ import annotations

from collections.abc import Mapping


def is_uncertain_send_timeout(exc: BaseException) -> bool:
    """Return True when the adapter timed out waiting for a send acknowledgement.

    NapCat/NTQQ may raise aiocqhttp ActionFailed(retcode=1200) after the message has
    already reached the chat. Retrying or emitting a failure fallback in that case
    can duplicate a successfully delivered image and mislead users.
    """

    result = getattr(exc, "result", None)
    retcode = None
    text_parts: list[str] = []
    if isinstance(result, Mapping):
        retcode = result.get("retcode")
        for key in ("message", "wording"):
            value = result.get(key)
            if value:
                text_parts.append(str(value))
    else:
        retcode = getattr(exc, "retcode", None)

    text_parts.append(str(exc))
    try:
        code = int(retcode)
    except (TypeError, ValueError):
        code = None

    text = " ".join(text_parts).lower()
    return (
        code == 1200
        and "timeout" in text
        and (
            "sendmsg" in text
            or "nodeikernelmsgservice" in text
            or "onmsginfolistupdate" in text
        )
    )
