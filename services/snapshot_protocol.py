"""Offline contract for the source service's provenance-safe base-only output.

No HTTP, publication or approval operations live here. Attribution descriptors
are part of package_size; manifest.json and optional health.json are not.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

CLIENT = "astrbot_plugin_rollpig_plus"
PROFILE = "provenance-safe-base-only"
COMPLETE_PROFILE = "complete-handwritten-ex"
PROFILES = {PROFILE, COMPLETE_PROFILE}
BINDING_FIELDS = {"freeze_fingerprint", "source_fingerprint", "public_only_copy_digest",
                  "bundled_copy_digest", "overlap_plan_sha256"}
MAX_MANIFEST = 1024 * 1024
MAX_PROVENANCE = 2 * 1024 * 1024
MAX_PACKAGE = 128 * 1024 * 1024
MAX_IMAGE = 10 * 1024 * 1024
MAX_TEXT = 128 * 1024
ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
SHA256 = re.compile(r"[0-9a-f]{64}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_json(raw: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique,
                      parse_constant=reject_constant)


def safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or any(c in value for c in "\\:%?#\x00"):
        raise ValueError("invalid publication path")
    if any(part in {"", ".", ".."} or part != part.strip() for part in value.split("/")):
        raise ValueError("non-canonical publication path")
    if any(ord(char) < 32 for char in value):
        raise ValueError("control character in publication path")
    return value


def validate_manifest(raw: bytes) -> tuple[dict, list[dict]]:
    if len(raw) > MAX_MANIFEST:
        raise ValueError("manifest exceeds size limit")
    manifest = parse_json(raw)
    allowed = {"schema_version", "client", "resource_version", "generated_at", "profile",
               "pig_count", "package_size", "pig_json", "images", "notice", "provenance", "licenses"}
    complete = isinstance(manifest, dict) and manifest.get("profile") == COMPLETE_PROFILE
    if complete:
        allowed |= {"ex_variants", "variant_images", "ex_variant_pig_count", "ex_authoring",
                    "roast_copy", "roast_copy_dish_count", "roast_copy_line_count",
                    "extended_resources", "handwritten_ex_pig_count", "handwritten_ex_level_count"} | BINDING_FIELDS
    if not isinstance(manifest, dict) or set(manifest) != allowed:
        raise ValueError("base-only manifest has missing or unexpected fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    if manifest["client"] != CLIENT or manifest["profile"] not in PROFILES:
        raise ValueError("unexpected client or publication profile")
    version = manifest["resource_version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}", version):
        raise ValueError("invalid resource_version")
    if not isinstance(manifest["generated_at"], str) or not manifest["generated_at"].strip():
        raise ValueError("missing generation timestamp")
    count = manifest["pig_count"]
    if type(count) is not int or not 1 <= count <= 500:
        raise ValueError("invalid pig_count")
    images, licenses = manifest["images"], manifest["licenses"]
    if not isinstance(images, list) or len(images) != count:
        raise ValueError("image count differs from pig_count")
    if not isinstance(licenses, list) or not 1 <= len(licenses) <= 16:
        raise ValueError("invalid license count")
    declarations = [(manifest["pig_json"], "pig.json", MAX_IMAGE),
                    (manifest["notice"], "NOTICE.md", MAX_TEXT),
                    (manifest["provenance"], "PROVENANCE.json", MAX_PROVENANCE)]
    if complete:
        if manifest["variant_images"] != [] or manifest["extended_resources"] is not True:
            raise ValueError("complete handwritten profile permits text EX only")
        for key, expected in (("ex_variant_pig_count", count), ("handwritten_ex_pig_count", count),
                              ("handwritten_ex_level_count", count * 5)):
            if type(manifest[key]) is not int or manifest[key] != expected:
                raise ValueError("incomplete handwritten EX counts")
        for key in BINDING_FIELDS:
            if not isinstance(manifest[key], str) or not SHA256.fullmatch(manifest[key]):
                raise ValueError("invalid authoring review binding")
        for key in ("roast_copy_dish_count", "roast_copy_line_count"):
            if type(manifest[key]) is not int or manifest[key] < 1:
                raise ValueError("invalid roast copy counts")
        declarations += [(manifest["ex_variants"], "pig_ex_variants.json", MAX_PROVENANCE),
                         (manifest["ex_authoring"], "EX-AUTHORING.json", MAX_TEXT),
                         (manifest["roast_copy"], "roast_copy.json", 256 * 1024)]
    declarations += [(item, "image", MAX_IMAGE) for item in images]
    declarations += [(item, "license", MAX_TEXT) for item in licenses]
    members, seen = [], set()
    for item, role, limit in declarations:
        if not isinstance(item, dict) or set(item) - {"path", "size", "sha256", "filename"}:
            raise ValueError("invalid member descriptor")
        path = safe_path(item.get("path"))
        parts = PurePosixPath(path)
        if role == "image":
            if (len(parts.parts) != 2 or parts.parts[0] != "images" or not ID.fullmatch(parts.stem)
                    or parts.suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}):
                raise ValueError("invalid base image path")
        elif role == "license":
            if len(parts.parts) != 2 or parts.parts[0] != "LICENSES" or parts.suffix.lower() not in {".md", ".txt"}:
                raise ValueError("invalid license path")
        elif path != role:
            raise ValueError("unexpected attribution/catalog path")
        if "filename" in item and item["filename"] != parts.name:
            raise ValueError("filename disagrees with member path")
        size, sha = item.get("size"), item.get("sha256")
        if type(size) is not int or not 0 < size <= limit:
            raise ValueError("member size is outside its limit")
        if not isinstance(sha, str) or not SHA256.fullmatch(sha):
            raise ValueError("invalid member sha256")
        if path.casefold() in seen:
            raise ValueError("duplicate or case-colliding member path")
        seen.add(path.casefold())
        members.append({"path": path, "size": size, "sha256": sha})
    if sum(item["size"] for item in licenses) > 512 * 1024:
        raise ValueError("licenses exceed total size limit")
    total = sum(member["size"] for member in members)
    if type(manifest["package_size"]) is not int or manifest["package_size"] != total or total > MAX_PACKAGE:
        raise ValueError("package_size must include catalog, images and all attribution members")
    return manifest, members
