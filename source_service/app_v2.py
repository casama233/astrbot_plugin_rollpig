#!/usr/bin/env python3
"""EX-aware wrapper for the RollPig public-source review service.

Resource Protocol v1 and every legacy HTTP route remain compatible. Base-only
clients keep the implicit submission envelope v1. EX-aware clients use envelope
v2, while EX metadata is stored in a sidecar table so the original submissions
schema and insert path remain untouched.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:  # package import under tests
    from . import app as legacy
except ImportError:  # direct systemd execution beside app.py
    import app as legacy


SUBMISSION_ENVELOPE_VERSION = 2
MAX_VARIANT_IMAGES = 5
MAX_VARIANT_IMAGE_BYTES = 10 * 1024 * 1024
SAFE_VARIANT_FILENAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}-ex[1-5]\.png")
_ALLOWED_FIELDS = {"image", "description", "analysis"}


def _canonical_ex_payload(payload: object, pig_id: str) -> dict:
    if payload in (None, {}, ""):
        return {"schema_version": 1, "pigs": {}}
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 差分 schema_version 必須為 1")
    pigs = payload.get("pigs")
    if not isinstance(pigs, dict):
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 差分 pigs 必須是物件")
    if {str(key) for key in pigs}.difference({pig_id}):
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 投稿只能包含目前這隻小豬")
    levels_raw = pigs.get(pig_id, {})
    if not isinstance(levels_raw, dict):
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 等級資料必須是物件")
    levels: dict[str, dict[str, str]] = {}
    for raw_level, raw_item in levels_raw.items():
        try:
            level = int(raw_level)
        except (TypeError, ValueError) as exc:
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 等級必須為 1-5") from exc
        if level < 1 or level > 5 or str(level) != str(raw_level):
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 等級必須為 1-5")
        if not isinstance(raw_item, dict) or not raw_item:
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 差分內容不能為空")
        if set(raw_item).difference(_ALLOWED_FIELDS):
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 差分包含不允許欄位")
        item: dict[str, str] = {}
        description = str(raw_item.get("description") or "").strip()
        analysis = str(raw_item.get("analysis") or "").strip()
        image = str(raw_item.get("image") or "").strip()
        if description:
            if len(description) > 120:
                raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 短描述不能超過 120 字")
            item["description"] = description
        if analysis:
            if len(analysis) > 800:
                raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 完整文案不能超過 800 字")
            item["analysis"] = analysis
        if image:
            expected = f"{pig_id}-ex{level}.png"
            if image != expected or not SAFE_VARIANT_FILENAME.fullmatch(image):
                raise legacy.APIError(
                    HTTPStatus.BAD_REQUEST,
                    f"EX Lv.{level} 圖片必須命名為 {expected}",
                )
            item["image"] = image
        if not item:
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 差分內容不能為空")
        levels[str(level)] = item
    return {"schema_version": 1, "pigs": {pig_id: levels} if levels else {}}


def _normalize_variant_images(
    payload: object, ex_payload: dict, pig_id: str
) -> dict[str, bytes]:
    rows = payload if isinstance(payload, list) else []
    if len(rows) > MAX_VARIANT_IMAGES:
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "每次投稿最多包含 5 張 EX 圖片")
    declared = {
        str(item.get("image") or "")
        for item in ex_payload.get("pigs", {}).get(pig_id, {}).values()
        if str(item.get("image") or "")
    }
    images: dict[str, bytes] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 圖片資料格式無效")
        filename = str(row.get("filename") or "").strip()
        if not SAFE_VARIANT_FILENAME.fullmatch(filename) or not filename.startswith(
            f"{pig_id}-ex"
        ):
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 圖片檔名無效")
        if filename in images:
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 圖片檔名重複")
        normalized, _ = legacy._normalize_image(str(row.get("content") or ""))
        if len(normalized) > MAX_VARIANT_IMAGE_BYTES:
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 圖片超過 10 MiB")
        images[filename] = normalized
    provided = set(images)
    if provided != declared:
        missing = sorted(declared.difference(provided))
        extra = sorted(provided.difference(declared))
        detail = []
        if missing:
            detail.append("缺少：" + ", ".join(missing))
        if extra:
            detail.append("未引用：" + ", ".join(extra))
        raise legacy.APIError(
            HTTPStatus.BAD_REQUEST,
            "EX 圖片與差分引用不一致"
            + ("（" + "；".join(detail) + "）" if detail else ""),
        )
    return images


def _decode_submission_ex(payload: object, pig_id: str) -> tuple[dict, dict[str, bytes]]:
    if not isinstance(payload, dict):
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "投稿資料必須是物件")
    try:
        version = int(payload.get("submission_version") or 1)
    except (TypeError, ValueError) as exc:
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "submission_version 無效") from exc
    if version == 1:
        return {"schema_version": 1, "pigs": {}}, {}
    if version != SUBMISSION_ENVELOPE_VERSION:
        raise legacy.APIError(HTTPStatus.BAD_REQUEST, "不支援的投稿 envelope 版本")
    ex_payload = _canonical_ex_payload(payload.get("ex_variants"), pig_id)
    images = _normalize_variant_images(payload.get("variant_images"), ex_payload, pig_id)
    return ex_payload, images


class ReviewApplicationV2(legacy.ReviewApplication):
    def __init__(self, config: legacy.ServiceConfig):
        self.variant_image_root = config.state_root / "variant-images"
        self.variant_image_root.mkdir(parents=True, exist_ok=True)
        super().__init__(config)

    def _init_database(self) -> None:
        super()._init_database()
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS submission_ex (
                    submission_id TEXT PRIMARY KEY,
                    submission_version INTEGER NOT NULL DEFAULT 2,
                    ex_variants_json TEXT NOT NULL,
                    variant_image_dir TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(submission_id) REFERENCES submissions(submission_id)
                );
                """
            )

    def submit(self, payload: object, *, source_address: str, client_version: str) -> dict:
        record = legacy._validate_record(payload)
        ex_payload, variant_images = _decode_submission_ex(payload, record["id"])
        if not ex_payload.get("pigs"):
            return super().submit(
                payload, source_address=source_address, client_version=client_version
            )

        result = super().submit(
            payload, source_address=source_address, client_version=client_version
        )
        submission_id = str(result["submission_id"])
        target_dir = self.variant_image_root / submission_id
        temporary_dir: Path | None = None
        try:
            if variant_images:
                temporary_dir = Path(
                    tempfile.mkdtemp(
                        prefix=f".{submission_id}.", dir=self.variant_image_root
                    )
                )
                for filename, raw in variant_images.items():
                    (temporary_dir / filename).write_bytes(raw)
                temporary_dir.rename(target_dir)
                temporary_dir = None
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO submission_ex "
                    "(submission_id,submission_version,ex_variants_json,variant_image_dir) "
                    "VALUES (?,?,?,?)",
                    (
                        submission_id,
                        SUBMISSION_ENVELOPE_VERSION,
                        json.dumps(ex_payload, ensure_ascii=False, sort_keys=True),
                        str(target_dir) if variant_images else "",
                    ),
                )
        except Exception:
            if temporary_dir and temporary_dir.exists():
                shutil.rmtree(temporary_dir, ignore_errors=True)
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT image_path FROM submissions WHERE submission_id=?",
                    (submission_id,),
                ).fetchone()
                connection.execute(
                    "DELETE FROM submissions WHERE submission_id=? AND status='pending'",
                    (submission_id,),
                )
            if row:
                Path(str(row["image_path"])).unlink(missing_ok=True)
            raise
        result["submission_version"] = SUBMISSION_ENVELOPE_VERSION
        result["ex_variant_levels"] = len(
            ex_payload.get("pigs", {}).get(record["id"], {})
        )
        return result

    def list_submissions(self, status: str = "pending") -> list[dict]:
        items = super().list_submissions(status)
        if not items:
            return items
        ids = [str(item.get("submission_id") or "") for item in items]
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT submission_id,submission_version,ex_variants_json,variant_image_dir "
                f"FROM submission_ex WHERE submission_id IN ({placeholders})",
                ids,
            ).fetchall()
        extra = {str(row["submission_id"]): row for row in rows}
        for item in items:
            row = extra.get(str(item.get("submission_id") or ""))
            if not row:
                item["submission_version"] = 1
                item["ex_variants"] = {"schema_version": 1, "pigs": {}}
                item["ex_variant_levels"] = 0
                item["variant_images"] = []
                continue
            try:
                ex_payload = json.loads(str(row["ex_variants_json"] or ""))
            except Exception:
                ex_payload = {"schema_version": 1, "pigs": {}}
            pig_id = str(item.get("pig_id") or "")
            levels = ex_payload.get("pigs", {}).get(pig_id, {})
            item["submission_version"] = int(row["submission_version"] or 2)
            item["ex_variants"] = ex_payload
            item["ex_variant_levels"] = len(levels) if isinstance(levels, dict) else 0
            item["variant_images"] = sorted(
                {
                    str(value.get("image") or "")
                    for value in levels.values()
                    if isinstance(value, dict) and str(value.get("image") or "")
                }
            )
        return items

    def variant_image_path(self, submission_id: str, filename: str) -> Path:
        if not legacy.SUBMISSION_PATTERN.fullmatch(submission_id):
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "投稿 ID 無效")
        filename = unquote(str(filename or ""))
        if not SAFE_VARIANT_FILENAME.fullmatch(filename):
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 圖片檔名無效")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT s.pig_id,e.variant_image_dir FROM submissions s "
                "JOIN submission_ex e ON e.submission_id=s.submission_id "
                "WHERE s.submission_id=?",
                (submission_id,),
            ).fetchone()
        if not row:
            raise legacy.APIError(HTTPStatus.NOT_FOUND, "EX 投稿不存在")
        if not filename.startswith(f"{row['pig_id']}-ex"):
            raise legacy.APIError(HTTPStatus.BAD_REQUEST, "EX 圖片與投稿小豬不匹配")
        root = Path(str(row["variant_image_dir"] or "")).resolve()
        expected_parent = (self.variant_image_root / submission_id).resolve()
        path = (root / filename).resolve()
        if root != expected_parent or path.parent != expected_parent or not path.is_file():
            raise legacy.APIError(HTTPStatus.NOT_FOUND, "EX 投稿圖片不存在")
        return path

    def _submission_ex(self, submission_id: str) -> tuple[dict, Path | None]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT ex_variants_json,variant_image_dir FROM submission_ex "
                "WHERE submission_id=?",
                (submission_id,),
            ).fetchone()
        if not row:
            return {"schema_version": 1, "pigs": {}}, None
        try:
            payload = json.loads(str(row["ex_variants_json"] or ""))
        except Exception as exc:
            raise legacy.APIError(
                HTTPStatus.CONFLICT, "投稿 EX 差分資料已損壞"
            ) from exc
        raw_dir = str(row["variant_image_dir"] or "")
        return payload, Path(raw_dir) if raw_dir else None

    def _publish(self, row) -> str:
        if str(row["pig_id"]) in self._catalog_ids():
            raise legacy.APIError(HTTPStatus.CONFLICT, "公共豬源已存在同 ID 小豬")
        parent = self.config.catalog_root.parent
        candidate = Path(tempfile.mkdtemp(prefix=".catalog-candidate-", dir=parent))
        shutil.rmtree(candidate)
        backup: Path | None = None
        try:
            shutil.copytree(self.config.catalog_root, candidate)
            records = json.loads(
                (candidate / "pig.json").read_text(encoding="utf-8-sig")
            )
            records.append(
                {
                    "id": str(row["pig_id"]),
                    "name": str(row["name"]),
                    "description": str(row["description"]),
                    "analysis": str(row["analysis"]),
                }
            )
            (candidate / "pig.json").write_text(
                json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            shutil.copyfile(
                Path(str(row["image_path"])),
                candidate / "image" / f"{row['pig_id']}.png",
            )

            incoming, variant_dir = self._submission_ex(str(row["submission_id"]))
            incoming_levels = incoming.get("pigs", {}).get(str(row["pig_id"]), {})
            if incoming_levels:
                ex_path = candidate / "pig_ex_variants.json"
                if ex_path.is_file():
                    ex_catalog = json.loads(ex_path.read_text(encoding="utf-8-sig"))
                else:
                    ex_catalog = {"schema_version": 1, "pigs": {}}
                if ex_catalog.get("schema_version") != 1 or not isinstance(
                    ex_catalog.get("pigs"), dict
                ):
                    raise legacy.APIError(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        "正式公共源 EX 差分檔案格式無效",
                    )
                ex_catalog["pigs"][str(row["pig_id"])] = incoming_levels
                ex_path.write_text(
                    json.dumps(ex_catalog, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                destination = candidate / "ex_variants"
                destination.mkdir(exist_ok=True)
                for level_data in incoming_levels.values():
                    filename = str(level_data.get("image") or "")
                    if not filename:
                        continue
                    source = (variant_dir / filename) if variant_dir else Path()
                    if not variant_dir or not source.is_file():
                        raise legacy.APIError(
                            HTTPStatus.CONFLICT,
                            f"投稿缺少 EX 圖片：{filename}",
                        )
                    shutil.copyfile(source, destination / filename)

            version = self._next_resource_version()
            release = self.config.publish_root / "releases" / version
            legacy.build_source(candidate, release, version)
            backup_root = self.config.publish_root / "catalog-backups"
            backup_root.mkdir(exist_ok=True)
            backup = backup_root / f"{version}-{uuid.uuid4().hex[:8]}"
            self.config.catalog_root.rename(backup)
            try:
                candidate.rename(self.config.catalog_root)
                link = self.config.publish_root / f".v1.{uuid.uuid4().hex}.tmp"
                os.symlink(f"releases/{version}", link)
                os.replace(link, self.config.publish_root / "v1")
            except Exception:
                failed = backup_root / f"failed-{version}-{uuid.uuid4().hex[:8]}"
                if self.config.catalog_root.exists():
                    self.config.catalog_root.rename(failed)
                backup.rename(self.config.catalog_root)
                raise
            return version
        finally:
            if candidate.exists():
                shutil.rmtree(candidate, ignore_errors=True)


class ReviewHandlerV2(legacy.ReviewHandler):
    def do_GET(self) -> None:
        try:
            parsed = urlsplit(self.path)
            match = re.fullmatch(
                r"/v1/admin/submissions/([0-9a-f]{32})/variant-image/([^/]+)",
                parsed.path,
            )
            if not match:
                return super().do_GET()
            if not self._client_allowed():
                raise legacy.APIError(HTTPStatus.FORBIDDEN, "AstrBot v1 client required")
            if not self._admin_allowed():
                raise legacy.APIError(HTTPStatus.UNAUTHORIZED, "管理憑證無效")
            image = self.app.variant_image_path(match.group(1), match.group(2)).read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(image)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(image)
        except legacy.APIError as exc:
            self._error(exc)
        except Exception:
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"status": "error", "message": "服務內部錯誤"},
            )


def main() -> int:
    legacy.ReviewApplication = ReviewApplicationV2
    legacy.ReviewHandler = ReviewHandlerV2
    return legacy.main()


if __name__ == "__main__":
    raise SystemExit(main())
