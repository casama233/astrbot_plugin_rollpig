"""Check source-service bytes against a separately reviewed publication policy.

The policy is maintained outside the candidate. No matching approval means no
publication. Structural validity is not proof of copyright or permission.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

try:
    from .snapshot_protocol import (CLIENT, ID, MAX_MANIFEST, MAX_PROVENANCE, PROFILE,
                                    COMPLETE_PROFILE, PROFILES, BINDING_FIELDS,
                                    SHA256, digest, parse_json, safe_path, validate_manifest)
except ImportError:
    from snapshot_protocol import (CLIENT, ID, MAX_MANIFEST, MAX_PROVENANCE, PROFILE,
                                   COMPLETE_PROFILE, PROFILES, BINDING_FIELDS,
                                   SHA256, digest, parse_json, safe_path, validate_manifest)

PRIMARY = "https://curryudon.top/astrbot-rollpig/v1/manifest.json"
DEFAULT_APPROVALS = Path(__file__).resolve().parents[1] / "publication-approvals.json"
RIGHTS_BASES = {"original-work", "explicit-permission", "public-domain", "permissive-asset-license"}


def _read(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular publication file: {path.name}")
    with path.open("rb") as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"publication file exceeds limit: {path.name}")
    return data


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _https(value) -> bool:
    if not _text(value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def validate_publication(root: Path, approvals_path: Path = DEFAULT_APPROVALS) -> dict:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("snapshot root must be a real directory")
    policy = parse_json(_read(Path(approvals_path), MAX_PROVENANCE))
    if (not isinstance(policy, dict) or type(policy.get("schema_version")) is not int
            or policy["schema_version"] != 2 or not isinstance(policy.get("approved_snapshots"), dict)):
        raise ValueError("invalid publication approval policy")
    raw = _read(root / "manifest.json", MAX_MANIFEST)
    manifest_hash = digest(raw)
    review = policy["approved_snapshots"].get(manifest_hash)
    if not isinstance(review, dict) or review.get("status") != "approved":
        raise ValueError("snapshot has no separately reviewed publication approval")
    if review.get("profile") not in PROFILES or review.get("primary_manifest_url") != PRIMARY:
        raise ValueError("approval does not identify the audited primary base-only publication")
    if not _https(review.get("review_url")):
        raise ValueError("approval is missing a review reference")
    manifest, members = validate_manifest(raw)
    if review["profile"] != manifest["profile"]:
        raise ValueError("review profile differs from manifest")
    complete = manifest["profile"] == COMPLETE_PROFILE
    files = review.get("files")
    if not isinstance(files, dict) or not 1 <= len(files) <= 521:
        raise ValueError("approval requires a bounded exact file inventory")
    expected = {safe_path(name) for name in files}
    if len({name.casefold() for name in expected}) != len(expected):
        raise ValueError("case-colliding approved paths")
    required = {"manifest.json", *(member["path"] for member in members)}
    if not required <= expected or expected - required - {"health.json"}:
        raise ValueError("missing or forbidden/unexpected publication files")
    actual = set()
    allowed_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents if str(parent) != "."}
    if complete:
        allowed_dirs.add("ex_variants")
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError("publication symlinks are forbidden")
        if path.is_dir() and name in allowed_dirs:
            continue
        if not path.is_file() or name not in expected:
            raise ValueError("undeclared publication path")
        actual.add(name)
    if actual != expected:
        raise ValueError("publication inventory is incomplete")
    by_path = {member["path"]: member for member in members}
    for name, sha in files.items():
        if not isinstance(sha, str) or not SHA256.fullmatch(sha):
            raise ValueError("invalid approved file digest")
        member = by_path.get(name)
        data = _read(root / name, member["size"] if member else MAX_MANIFEST)
        if digest(data) != sha:
            raise ValueError(f"reviewed bytes changed: {name}")
        if member and (len(data) != member["size"] or digest(data) != member["sha256"]):
            raise ValueError(f"protocol size/sha256 mismatch: {name}")
        if name == "NOTICE.md" or name.startswith("LICENSES/"):
            if not data.decode("utf-8").strip():
                raise ValueError("empty attribution or license document")
    # Keep the actual service provenance shape; do not rewrite it into a new
    # per-file document just to satisfy the mirror. Bind original bytes above.
    catalog = parse_json(_read(root / "pig.json", by_path["pig.json"]["size"]))
    if not isinstance(catalog, list) or len(catalog) != manifest["pig_count"]:
        raise ValueError("catalog count differs from manifest")
    ids = set()
    for item in catalog:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or not ID.fullmatch(item["id"]) or item["id"] in ids
                or not all(_text(item.get(key)) for key in ("name", "description", "analysis"))):
            raise ValueError("invalid or duplicate catalog item")
        ids.add(item["id"])
    image_ids = [PurePosixPath(item["path"]).stem for item in manifest["images"]]
    if len(set(image_ids)) != len(image_ids) or set(image_ids) != ids:
        raise ValueError("image IDs differ from catalog")
    provenance = parse_json(_read(root / "PROVENANCE.json", MAX_PROVENANCE))
    if (not isinstance(provenance, dict) or type(provenance.get("resource_count")) is not int
            or provenance["resource_count"] != len(ids) or not isinstance(provenance.get("items"), list)):
        raise ValueError("provenance must contain resource_count and items")
    seen = set()
    for item in provenance["items"]:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or item["id"] not in ids or item["id"] in seen
                or not _text(item.get("source")) or not _text(item.get("classification"))):
            raise ValueError("invalid or duplicate provenance item")
        seen.add(item["id"])
    if seen != ids:
        raise ValueError("provenance IDs differ from catalog")
    # Rights are an independent review, not inferred from provenance labels.
    rights = review.get("rights")
    asset_paths = {"pig.json", *(item["path"] for item in manifest["images"])}
    if complete:
        asset_paths |= {"pig_ex_variants.json", "roast_copy.json"}
    licenses = {item["path"] for item in manifest["licenses"]}
    if not isinstance(rights, dict) or set(rights) != asset_paths:
        raise ValueError("independent rights review must cover catalog text and every image")
    for name, record in rights.items():
        if not isinstance(record, dict) or record.get("redistribution_verified") is not True:
            raise ValueError(f"redistribution is unverified: {name}")
        if (record.get("rights_basis") not in RIGHTS_BASES
                or (record["rights_basis"] == "permissive-asset-license" and record.get("license_file") not in licenses)
                or (record.get("license_file") and record["license_file"] not in licenses)):
            raise ValueError(f"missing asset-specific rights basis: {name}")
        if not _https(record.get("source_url")) or not _https(record.get("evidence_url")):
            raise ValueError(f"missing source or permission evidence: {name}")
        if not all(_text(record.get(key)) for key in ("author", "review_note")):
            raise ValueError(f"missing attribution or review note: {name}")
    if complete:
        _validate_complete_content(root, manifest, ids, by_path)
    if "health.json" in expected:
        health = parse_json(_read(root / "health.json", MAX_MANIFEST))
        matching = {"status": "ok", "client": CLIENT, "protocol_version": 1,
                    "resource_version": manifest["resource_version"], "profile": manifest["profile"],
                    "pig_count": len(ids), "package_size": manifest["package_size"],
                    "generated_at": manifest["generated_at"],
                    "attribution_bundle": True, "extended_resources": complete}
        if complete:
            matching.update({key: manifest[key] for key in BINDING_FIELDS | {
                "handwritten_ex_pig_count", "handwritten_ex_level_count", "ex_variant_pig_count",
                "roast_copy_dish_count", "roast_copy_line_count"}})
            matching["ex_variant_image_count"] = 0
        if not isinstance(health, dict) or health != matching or any(type(health[key]) is not type(value) for key, value in matching.items()):
            raise ValueError("health metadata disagrees with the base-only publication")
    return {"publication_profile": manifest["profile"], "manifest_sha256": manifest_hash,
            "review_url": review["review_url"], "approved_files": len(files),
            "resource_version": manifest["resource_version"], "pig_count": len(ids),
            "members": len(members), "package_size": manifest["package_size"]}


def _validate_complete_content(root, manifest, ids, by_path):
    def read(name):
        return parse_json(_read(root / name, by_path[name]["size"]))
    authoring = read("EX-AUTHORING.json")
    if (not isinstance(authoring, dict) or authoring.get("publication_state") != "published"
            or authoring.get("profile") != COMPLETE_PROFILE
            or not _text(authoring.get("publication_reviewer"))):
        raise ValueError("complete EX publication has not been published")
    for key in BINDING_FIELDS | {"pig_count", "handwritten_ex_pig_count", "handwritten_ex_level_count"}:
        if authoring.get(key) != manifest[key] or type(authoring.get(key)) is not type(manifest[key]):
            raise ValueError("published EX review binding/count mismatch")
    ex = read("pig_ex_variants.json")
    if not isinstance(ex, dict) or ex.get("schema_version") != 1 or not isinstance(ex.get("pigs"), dict) or set(ex["pigs"]) != ids:
        raise ValueError("EX IDs differ from catalog")
    descriptions, analyses = set(), set()
    for levels in ex["pigs"].values():
        if not isinstance(levels, dict) or set(levels) != {"1", "2", "3", "4", "5"}:
            raise ValueError("EX levels must be complete 1-5")
        for item in levels.values():
            if not isinstance(item, dict) or set(item) != {"description", "analysis"} or not all(_text(v) for v in item.values()):
                raise ValueError("EX entries must contain reviewed text only")
            if item["description"] in descriptions or item["analysis"] in analyses:
                raise ValueError("duplicate handwritten EX text")
            descriptions.add(item["description"])
            analyses.add(item["analysis"])
    roast = read("roast_copy.json")
    if not isinstance(roast, dict) or roast.get("schema_version") != 1:
        raise ValueError("invalid roast copy schema")
    for field, count_key in (("dish_names", "roast_copy_dish_count"), ("lines", "roast_copy_line_count")):
        values = roast.get(field)
        if not isinstance(values, list) or len(values) != manifest[count_key] or not all(_text(v) for v in values):
            raise ValueError("roast copy count/content differs from manifest")
