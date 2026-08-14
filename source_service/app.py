#!/usr/bin/env python3
"""Review API and atomic publisher for the AstrBot RollPig public source."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
from difflib import SequenceMatcher
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image, ImageOps

try:
    from scripts.build_resource_source import build_source
except ImportError:  # pragma: no cover - deployed beside the builder
    from build_resource_source import build_source


CLIENT_ID = "astrbot_plugin_rollpig_plus"
PROTOCOL_VERSION = "1"
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{32,256}")
SUBMISSION_PATTERN = re.compile(r"[0-9a-f]{32}")
MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
MAX_PENDING_PER_DAY = 5
MAX_PENDING_TOTAL = 200
DUPLICATE_NAME_THRESHOLD = 0.82
DUPLICATE_IMAGE_DISTANCE = 8


class APIError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class ServiceConfig:
    state_root: Path
    catalog_root: Path
    publish_root: Path
    admin_token_file: Path


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")


def _read_admin_token(path: Path) -> str:
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"admin token unavailable: {exc}") from exc
    if not TOKEN_PATTERN.fullmatch(token):
        raise RuntimeError("admin token format is invalid")
    return token


def _normalize_image(encoded: str) -> tuple[bytes, str]:
    if not encoded or len(encoded) > MAX_REQUEST_BYTES:
        raise APIError(HTTPStatus.BAD_REQUEST, "圖片資料缺失或過大")
    if "," in encoded:
        encoded = encoded.split(",", 1)[1]
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise APIError(HTTPStatus.BAD_REQUEST, "圖片不是有效 Base64") from exc
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise APIError(HTTPStatus.BAD_REQUEST, "圖片必須小於 10 MiB")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image)
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise APIError(HTTPStatus.BAD_REQUEST, "圖片像素超過安全上限")
            method = getattr(Image, "Resampling", Image).LANCZOS
            normalized = ImageOps.fit(image.convert("RGBA"), (512, 512), method)
            output = io.BytesIO()
            normalized.save(output, "PNG", optimize=True)
            result = output.getvalue()
    except APIError:
        raise
    except Exception as exc:
        raise APIError(HTTPStatus.BAD_REQUEST, "圖片無法解碼") from exc
    return result, hashlib.sha256(result).hexdigest()


def _validate_record(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise APIError(HTTPStatus.BAD_REQUEST, "投稿資料必須是物件")
    record = payload.get("record")
    if not isinstance(record, dict):
        raise APIError(HTTPStatus.BAD_REQUEST, "投稿缺少小豬資料")
    pig_id = str(record.get("id") or "").strip().lower()
    name = str(record.get("name") or "").strip()
    description = str(record.get("description") or "").strip()
    analysis = str(record.get("analysis") or "").strip()
    if not ID_PATTERN.fullmatch(pig_id):
        raise APIError(HTTPStatus.BAD_REQUEST, "小豬 ID 無效")
    if not name or len(name) > 30:
        raise APIError(HTTPStatus.BAD_REQUEST, "名稱必填且不能超過 30 字")
    if not description or len(description) > 80:
        raise APIError(HTTPStatus.BAD_REQUEST, "描述必填且不能超過 80 字")
    if not analysis or len(analysis) > 500:
        raise APIError(HTTPStatus.BAD_REQUEST, "文案必填且不能超過 500 字")
    return {
        "id": pig_id,
        "name": name,
        "description": description,
        "analysis": analysis,
    }


def _name_key(value: object) -> str:
    text = str(value or "").strip().lower().replace("豬", "猪")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def _image_dhash(raw: bytes) -> int:
    with Image.open(io.BytesIO(raw)) as image:
        method = getattr(Image, "Resampling", Image).LANCZOS
        resized = image.convert("L").resize((9, 8), method)
        getter = getattr(resized, "get_flattened_data", None)
        pixels = list(getter() if callable(getter) else resized.getdata())
    value = 0
    for y in range(8):
        row = y * 9
        for x in range(8):
            value = (value << 1) | int(pixels[row + x] > pixels[row + x + 1])
    return value


def _duplicate_hints(
    record: dict[str, str], image: bytes, catalog_index: list[dict[str, object]]
) -> list[dict[str, object]]:
    name_key = _name_key(record.get("name"))
    image_hash = _image_dhash(image)
    hints: list[dict[str, object]] = []
    for item in catalog_index:
        reasons: list[str] = []
        candidate_name = str(item.get("name") or "")
        candidate_key = str(item.get("name_key") or "")
        ratio = SequenceMatcher(None, name_key, candidate_key).ratio() if name_key and candidate_key else 0.0
        if name_key and name_key == candidate_key:
            reasons.append("名称相同")
        elif ratio >= DUPLICATE_NAME_THRESHOLD:
            reasons.append(f"名称相似 {round(ratio * 100)}%")
        distance = 64
        candidate_hash = item.get("image_dhash")
        if isinstance(candidate_hash, int):
            distance = (image_hash ^ candidate_hash).bit_count()
            if distance <= DUPLICATE_IMAGE_DISTANCE:
                reasons.append(f"图片相似 dHash={distance}")
        if reasons:
            hints.append(
                {
                    "id": str(item.get("id") or ""),
                    "name": candidate_name,
                    "reasons": reasons,
                    "name_similarity": round(ratio, 3),
                    "image_distance": distance if distance < 64 else None,
                }
            )
    hints.sort(
        key=lambda item: (
            int(item.get("image_distance") if item.get("image_distance") is not None else 99),
            -float(item.get("name_similarity") or 0),
            str(item.get("id") or ""),
        )
    )
    return hints[:5]


class ReviewApplication:
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.config.state_root.mkdir(parents=True, exist_ok=True)
        self.image_root = self.config.state_root / "images"
        self.image_root.mkdir(exist_ok=True)
        self.database = self.config.state_root / "reviews.db"
        self.admin_token = _read_admin_token(self.config.admin_token_file)
        self._review_lock = threading.Lock()
        self._duplicate_index_cache_key: tuple[int, int] | None = None
        self._duplicate_index_cache: list[dict[str, object]] = []
        self._init_database()
        self._reconcile_published_submissions()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _init_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS submissions (
                    submission_id TEXT PRIMARY KEY,
                    pig_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    analysis TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    image_sha256 TEXT NOT NULL,
                    client_version TEXT NOT NULL,
                    source_fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
                    reviewer_note TEXT NOT NULL DEFAULT '',
                    resource_version TEXT NOT NULL DEFAULT '',
                    submitted_at INTEGER NOT NULL,
                    reviewed_at INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_submissions_status_time
                    ON submissions(status, submitted_at DESC);
                CREATE INDEX IF NOT EXISTS idx_submissions_source_time
                    ON submissions(source_fingerprint, submitted_at DESC);
                """
            )

    def _reconcile_published_submissions(self) -> None:
        """Close the publish/database crash window without approving mismatched files."""
        current = self.config.publish_root / "v1"
        try:
            manifest = json.loads((current / "manifest.json").read_text(encoding="utf-8"))
            version = str(manifest.get("resource_version") or "")
        except Exception:
            return
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT submission_id,pig_id,image_sha256 FROM submissions "
                "WHERE status='pending'"
            ).fetchall()
            for row in rows:
                image = self.config.catalog_root / "image" / f"{row['pig_id']}.png"
                if not image.is_file():
                    continue
                digest = hashlib.sha256(image.read_bytes()).hexdigest()
                if hmac.compare_digest(digest, str(row["image_sha256"])):
                    connection.execute(
                        "UPDATE submissions SET status='approved',resource_version=?,"
                        "reviewer_note='啟動時確認已發佈',reviewed_at=? "
                        "WHERE submission_id=? AND status='pending'",
                        (version, int(time.time()), row["submission_id"]),
                    )

    def _source_fingerprint(self, address: str) -> str:
        return hmac.new(
            self.admin_token.encode("utf-8"),
            address.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()


    def _catalog_records(self) -> list[dict]:
        path = self.config.catalog_root / "pig.json"
        try:
            records = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise APIError(HTTPStatus.SERVICE_UNAVAILABLE, "公共豬源目錄暫不可用") from exc
        return [dict(item) for item in records if isinstance(item, dict)]

    def _catalog_duplicate_index(self) -> list[dict[str, object]]:
        catalog_path = self.config.catalog_root / "pig.json"
        try:
            stat = catalog_path.stat()
            cache_key = (int(stat.st_mtime_ns), int(stat.st_size))
        except OSError:
            cache_key = (-1, -1)
        if cache_key == self._duplicate_index_cache_key and self._duplicate_index_cache:
            return [dict(item) for item in self._duplicate_index_cache]
        image_root = self.config.catalog_root / "image"
        index: list[dict[str, object]] = []
        for record in self._catalog_records():
            pig_id = str(record.get("id") or "")
            item: dict[str, object] = {
                "id": pig_id,
                "name": str(record.get("name") or pig_id),
                "name_key": _name_key(record.get("name")),
                "image_dhash": None,
            }
            for path in sorted(image_root.glob(f"{pig_id}.*")):
                if not path.is_file():
                    continue
                try:
                    item["image_dhash"] = _image_dhash(path.read_bytes())
                    break
                except Exception:
                    continue
            index.append(item)
        self._duplicate_index_cache_key = cache_key
        self._duplicate_index_cache = [dict(item) for item in index]
        return index

    def _catalog_ids(self) -> set[str]:
        path = self.config.catalog_root / "pig.json"
        try:
            records = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise APIError(HTTPStatus.SERVICE_UNAVAILABLE, "公共豬源目錄暫不可用") from exc
        return {
            str(item.get("id") or "")
            for item in records
            if isinstance(item, dict)
        }

    def submit(self, payload: object, *, source_address: str, client_version: str) -> dict:
        record = _validate_record(payload)
        image, image_hash = _normalize_image(str(payload.get("image") or ""))
        if record["id"] in self._catalog_ids():
            raise APIError(HTTPStatus.CONFLICT, "公共豬源已存在同 ID 小豬")
        fingerprint = self._source_fingerprint(source_address)
        cutoff = int(time.time()) - 24 * 3600
        with self._connect() as connection:
            pending_total = int(
                connection.execute("SELECT COUNT(*) FROM submissions WHERE status = 'pending'").fetchone()[0]
            )
            if pending_total >= MAX_PENDING_TOTAL:
                raise APIError(HTTPStatus.TOO_MANY_REQUESTS, "公共豬源待审核队列已满，请稍后再试")
            recent = connection.execute(
                "SELECT COUNT(*) FROM submissions WHERE source_fingerprint = ? "
                "AND submitted_at >= ?",
                (fingerprint, cutoff),
            ).fetchone()[0]
            if int(recent) >= MAX_PENDING_PER_DAY:
                raise APIError(HTTPStatus.TOO_MANY_REQUESTS, "今天的投稿數量已達上限")
            duplicate = connection.execute(
                "SELECT submission_id FROM submissions WHERE status = 'pending' "
                "AND (pig_id = ? OR image_sha256 = ?) LIMIT 1",
                (record["id"], image_hash),
            ).fetchone()
            if duplicate:
                raise APIError(HTTPStatus.CONFLICT, "相同 ID 或圖片已在待審核隊列")
            submission_id = uuid.uuid4().hex
            image_path = self.image_root / f"{submission_id}.png"
            with tempfile.NamedTemporaryFile(
                "wb", dir=self.image_root, prefix=f".{submission_id}.", delete=False
            ) as temporary:
                temporary.write(image)
                temporary_path = Path(temporary.name)
            temporary_path.replace(image_path)
            try:
                connection.execute(
                    "INSERT INTO submissions VALUES (?,?,?,?,?,?,?,?,?,'pending','','',?,0)",
                    (
                        submission_id,
                        record["id"],
                        record["name"],
                        record["description"],
                        record["analysis"],
                        str(image_path),
                        image_hash,
                        client_version[:40],
                        fingerprint,
                        int(time.time()),
                    ),
                )
            except Exception:
                image_path.unlink(missing_ok=True)
                raise
        return {
            "submission_id": submission_id,
            "status": "pending",
            "message": "已提交到 AstrBot 公共豬源審核隊列",
        }

    def list_submissions(self, status: str = "pending") -> list[dict]:
        if status not in {"pending", "approved", "rejected"}:
            raise APIError(HTTPStatus.BAD_REQUEST, "審核狀態無效")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT submission_id,pig_id,name,description,analysis,image_path,image_sha256,"
                "client_version,status,reviewer_note,resource_version,submitted_at,reviewed_at "
                "FROM submissions WHERE status = ? ORDER BY submitted_at DESC LIMIT 50",
                (status,),
            ).fetchall()
        catalog_index = self._catalog_duplicate_index()
        items: list[dict] = []
        for row in rows:
            item = dict(row)
            image_path = Path(str(item.pop("image_path", "")))
            try:
                item["duplicate_hints"] = _duplicate_hints(
                    {"name": str(item.get("name") or "")},
                    image_path.read_bytes(),
                    catalog_index,
                )
            except Exception:
                item["duplicate_hints"] = []
            items.append(item)
        return items

    def image_path(self, submission_id: str) -> Path:
        if not SUBMISSION_PATTERN.fullmatch(submission_id):
            raise APIError(HTTPStatus.BAD_REQUEST, "投稿 ID 無效")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT image_path FROM submissions WHERE submission_id = ?",
                (submission_id,),
            ).fetchone()
        if not row:
            raise APIError(HTTPStatus.NOT_FOUND, "投稿不存在")
        path = Path(str(row["image_path"])).resolve()
        if path.parent != self.image_root.resolve() or not path.is_file():
            raise APIError(HTTPStatus.NOT_FOUND, "投稿圖片不存在")
        return path

    def _next_resource_version(self) -> str:
        # Use the server's configured local day so release numbers remain
        # monotonic for the Hong Kong deployment around UTC midnight.
        today = dt.datetime.now().astimezone().strftime("%Y.%m.%d")
        releases = self.config.publish_root / "releases"
        numbers = []
        for path in releases.iterdir() if releases.is_dir() else ():
            match = re.fullmatch(re.escape(today) + r"\.(\d+)", path.name)
            if match:
                numbers.append(int(match.group(1)))
        return f"{today}.{max(numbers, default=0) + 1}"

    def _publish(self, row: sqlite3.Row) -> str:
        if str(row["pig_id"]) in self._catalog_ids():
            raise APIError(HTTPStatus.CONFLICT, "公共豬源已存在同 ID 小豬")
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
            version = self._next_resource_version()
            release = self.config.publish_root / "releases" / version
            build_source(candidate, release, version)
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

    def review(self, submission_id: str, decision: str, note: str = "") -> dict:
        if not SUBMISSION_PATTERN.fullmatch(submission_id):
            raise APIError(HTTPStatus.BAD_REQUEST, "投稿 ID 無效")
        if decision not in {"approve", "reject"}:
            raise APIError(HTTPStatus.BAD_REQUEST, "審核決定無效")
        note = str(note or "").strip()[:300]
        with self._review_lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM submissions WHERE submission_id = ?",
                    (submission_id,),
                ).fetchone()
                if not row:
                    raise APIError(HTTPStatus.NOT_FOUND, "投稿不存在")
                if row["status"] != "pending":
                    raise APIError(HTTPStatus.CONFLICT, "投稿已完成審核")
            version = self._publish(row) if decision == "approve" else ""
            status = "approved" if decision == "approve" else "rejected"
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE submissions SET status=?,reviewer_note=?,resource_version=?,"
                    "reviewed_at=? WHERE submission_id=? AND status='pending'",
                    (status, note, version, int(time.time()), submission_id),
                ).rowcount
                if changed != 1:
                    raise APIError(HTTPStatus.CONFLICT, "投稿審核狀態已改變")
        return {
            "submission_id": submission_id,
            "status": status,
            "resource_version": version,
            "message": "已批准並發佈到公共豬源" if version else "已拒絕投稿",
        }


class ReviewHandler(BaseHTTPRequestHandler):
    server_version = "AstrBotRollPigSource/1"

    @property
    def app(self) -> ReviewApplication:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {self.client_address[0]} {format % args}")

    def _json(self, status: int, payload: object) -> None:
        data = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, error: APIError) -> None:
        self._json(error.status, {"status": "error", "message": error.message})

    def _client_allowed(self) -> bool:
        user_agent = str(self.headers.get("User-Agent") or "")
        return (
            re.match(r"^AstrBot-RollPig/\d+\.\d+\.\d+", user_agent) is not None
            and self.headers.get("X-RollPig-Client") == CLIENT_ID
            and self.headers.get("X-RollPig-Protocol") == PROTOCOL_VERSION
        )

    def _admin_allowed(self) -> bool:
        authorization = str(self.headers.get("Authorization") or "")
        expected = f"Bearer {self.app.admin_token}"
        return hmac.compare_digest(authorization, expected)

    def _read_json(self) -> object:
        length = str(self.headers.get("Content-Length") or "")
        if not length.isdigit():
            raise APIError(HTTPStatus.LENGTH_REQUIRED, "缺少 Content-Length")
        size = int(length)
        if size <= 0 or size > MAX_REQUEST_BYTES:
            raise APIError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "請求內容過大")
        try:
            return json.loads(self.rfile.read(size).decode("utf-8"))
        except Exception as exc:
            raise APIError(HTTPStatus.BAD_REQUEST, "請求不是有效 JSON") from exc

    def _source_address(self) -> str:
        return str(
            self.headers.get("X-Real-IP")
            or self.headers.get("X-Forwarded-For")
            or self.client_address[0]
        ).split(",", 1)[0].strip()

    def do_GET(self) -> None:
        try:
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                self._json(HTTPStatus.OK, {"status": "ok", "protocol_version": 1})
                return
            if not self._client_allowed():
                raise APIError(HTTPStatus.FORBIDDEN, "AstrBot v1 client required")
            if parsed.path == "/v1/admin/submissions":
                if not self._admin_allowed():
                    raise APIError(HTTPStatus.UNAUTHORIZED, "管理憑證無效")
                status = parse_qs(parsed.query).get("status", ["pending"])[0]
                self._json(
                    HTTPStatus.OK,
                    {"status": "ok", "data": {"items": self.app.list_submissions(status)}},
                )
                return
            match = re.fullmatch(r"/v1/admin/submissions/([0-9a-f]{32})/image", parsed.path)
            if match:
                if not self._admin_allowed():
                    raise APIError(HTTPStatus.UNAUTHORIZED, "管理憑證無效")
                image = self.app.image_path(match.group(1)).read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(image)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(image)
                return
            raise APIError(HTTPStatus.NOT_FOUND, "端點不存在")
        except APIError as exc:
            self._error(exc)
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error", "message": "服務內部錯誤"})

    def do_POST(self) -> None:
        try:
            parsed = urlsplit(self.path)
            if not self._client_allowed():
                raise APIError(HTTPStatus.FORBIDDEN, "AstrBot v1 client required")
            if parsed.path == "/v1/submissions":
                result = self.app.submit(
                    self._read_json(),
                    source_address=self._source_address(),
                    client_version=str(self.headers.get("X-RollPig-Version") or ""),
                )
                self._json(HTTPStatus.CREATED, {"status": "ok", "data": result})
                return
            match = re.fullmatch(r"/v1/admin/submissions/([0-9a-f]{32})/review", parsed.path)
            if match:
                if not self._admin_allowed():
                    raise APIError(HTTPStatus.UNAUTHORIZED, "管理憑證無效")
                payload = self._read_json()
                if not isinstance(payload, dict):
                    raise APIError(HTTPStatus.BAD_REQUEST, "審核資料無效")
                result = self.app.review(
                    match.group(1),
                    str(payload.get("decision") or ""),
                    str(payload.get("note") or ""),
                )
                self._json(HTTPStatus.OK, {"status": "ok", "data": result})
                return
            raise APIError(HTTPStatus.NOT_FOUND, "端點不存在")
        except APIError as exc:
            self._error(exc)
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error", "message": "服務內部錯誤"})


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: ReviewApplication):
        self.app = app
        super().__init__(address, ReviewHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=17841)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--catalog-root", type=Path, required=True)
    parser.add_argument("--publish-root", type=Path, required=True)
    parser.add_argument("--admin-token-file", type=Path, required=True)
    args = parser.parse_args()
    app = ReviewApplication(
        ServiceConfig(
            state_root=args.state_root.resolve(),
            catalog_root=args.catalog_root.resolve(),
            publish_root=args.publish_root.resolve(),
            admin_token_file=args.admin_token_file.resolve(),
        )
    )
    server = ReviewServer((args.host, args.port), app)
    print(f"review service listening on {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
