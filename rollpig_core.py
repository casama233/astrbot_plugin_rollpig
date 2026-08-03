"""Small dependency-free helpers used by tests and future refactors."""
from __future__ import annotations

import ipaddress
import re


def legacy_identity(value: str) -> str:
    match = re.fullmatch(r"v2\|[^|]+\|(?:user|group)\|(.*)", str(value or ""))
    return match.group(1) if match else str(value or "")


def pre_instance_identity(value: str) -> str:
    """Return the old adapter-type-only key for an instance-aware v2 key."""
    match = re.fullmatch(
        r"v2\|([^|]+)\|(user|group)\|(.*)", str(value or "")
    )
    if not match or "@" not in match.group(1):
        return ""
    platform_type = match.group(1).split("@", 1)[0]
    return f"v2|{platform_type}|{match.group(2)}|{match.group(3)}"


def identity_candidates(value: str) -> tuple[str, ...]:
    """Return instance-aware, pre-instance and raw keys in preference order."""
    text = str(value or "").strip()
    raw = legacy_identity(text)
    if raw == text:
        return (text,)
    candidates = [text]
    previous = pre_instance_identity(text)
    if previous:
        candidates.append(previous)
    if raw not in candidates:
        candidates.append(raw)
    return tuple(candidates)


def namespace_identity(platform: str, kind: str, value: str) -> str:
    raw = str(value or "").strip()
    if not raw or raw.startswith("v2|"):
        return raw
    safe_platform = re.sub(
        r"[^a-z0-9_.@-]+", "-", str(platform or "unknown").lower()
    ).strip("-") or "unknown"
    if kind not in {"user", "group"}:
        raise ValueError("kind must be user or group")
    return f"v2|{safe_platform}|{kind}|{raw}"


def is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)
