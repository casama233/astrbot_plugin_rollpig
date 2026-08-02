"""Small dependency-free helpers used by tests and future refactors."""
from __future__ import annotations

import ipaddress
import re


def legacy_identity(value: str) -> str:
    match = re.fullmatch(r"v2\|[^|]+\|(?:user|group)\|(.*)", str(value or ""))
    return match.group(1) if match else str(value or "")

def namespace_identity(platform: str, kind: str, value: str) -> str:
    raw = str(value or "").strip()
    if not raw or raw.startswith("v2|"):
        return raw
    safe_platform = re.sub(r"[^a-z0-9_.-]+", "-", str(platform or "unknown").lower()).strip("-") or "unknown"
    if kind not in {"user", "group"}:
        raise ValueError("kind must be user or group")
    return f"v2|{safe_platform}|{kind}|{raw}"

def is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified)
