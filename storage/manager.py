from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from .base import StorageBackend
from .json_storage import JSONStorage
from .sqlite_storage import SQLiteStorage


class StorageMigrationError(RuntimeError):
    """A dashboard-safe storage migration failure."""


class StorageManager:
    """Select, migrate, verify, export and roll back the storage backend."""

    MANAGED_PATHS = {
        "rollpig_today.json",
        "pig_history.json",
        "roast_state.json",
        "ai_roast_copies.json",
        "pig_catalog.json",
        "local_overrides.json",
        "deleted_pigs.json",
    }

    def __init__(
        self,
        data_root: Path,
        *,
        mode: str = "auto",
        lock: threading.RLock | None = None,
        busy_timeout_ms: int = 5000,
    ):
        self.data_root = Path(data_root).resolve()
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.mode = str(mode or "auto").strip().lower()
        if self.mode not in {"auto", "json", "sqlite"}:
            self.mode = "auto"
        self._lock = lock or threading.RLock()
        self.busy_timeout_ms = min(30000, max(1000, int(busy_timeout_ms)))
        self.json_storage = JSONStorage(lock=self._lock)
        self.database_path = self.data_root / "rollpig.db"
        self.state_path = self.data_root / "storage_state.json"
        self.backup_root = self.data_root / "storage_backups"
        self.export_root = self.data_root / "storage_exports"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.export_root.mkdir(parents=True, exist_ok=True)
        self._last_error = ""
        self._last_action: dict[str, Any] | None = None
        self.backend: StorageBackend = self.json_storage
        self._select_initial_backend()

    def _new_sqlite(self, path: Path | None = None) -> SQLiteStorage:
        return SQLiteStorage(
            path or self.database_path,
            self.data_root,
            self.MANAGED_PATHS,
            fallback=self.json_storage,
            lock=self._lock,
            busy_timeout_ms=self.busy_timeout_ms,
        )

    def _select_initial_backend(self) -> None:
        if self.mode == "json":
            self.backend = self.json_storage
            return
        if not self.database_path.exists():
            if self.mode == "sqlite":
                self._last_error = "配置要求 SQLite，但数据库尚未迁移；已安全回退 JSON"
            self.backend = self.json_storage
            return
        try:
            candidate = self._new_sqlite()
            verification = candidate.verify()
            if (
                verification.get("integrity") == "ok"
                and int(verification.get("foreign_key_errors", 0) or 0) == 0
                and verification.get("projection_ok") is False
            ):
                candidate.rebuild_projections()
                verification = candidate.verify()
                self._last_action = {"status": "auto-rebuilt-projections"}
            if not verification.get("ok"):
                raise StorageMigrationError(
                    f"SQLite 完整性或投影检查失败：{verification.get('integrity')}"
                )
            self.backend = candidate
            self._last_error = ""
        except Exception as exc:
            self.backend = self.json_storage
            self._last_error = f"SQLite 不可用，已回退 JSON：{exc}"

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _digest(cls, value: Any) -> str:
        return hashlib.sha256(cls._canonical(value).encode("utf-8")).hexdigest()

    def _read_existing_json(self) -> dict[str, Any]:
        documents: dict[str, Any] = {}
        for relative in sorted(self.MANAGED_PATHS):
            path = self.data_root / relative
            if not path.exists():
                continue
            try:
                documents[relative] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise StorageMigrationError(f"迁移前无法读取 {relative}：{exc}") from exc
        return documents

    def _create_backup(self, documents: dict[str, Any]) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = self.backup_root / f"{stamp}-json"
        suffix = 0
        while backup.exists():
            suffix += 1
            backup = self.backup_root / f"{stamp}-json-{suffix}"
        backup.mkdir(parents=True)
        manifest: dict[str, Any] = {
            "created_at": int(time.time()),
            "files": {},
        }
        for relative, value in documents.items():
            source = self.data_root / relative
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest["files"][relative] = {
                "sha256": self._digest(value),
                "size": target.stat().st_size,
            }
        (backup / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return backup

    @staticmethod
    def _remove_sqlite_sidecars(path: Path) -> None:
        for suffix in ("-wal", "-shm"):
            Path(f"{path}{suffix}").unlink(missing_ok=True)

    def migrate_to_sqlite(self) -> dict[str, Any]:
        with self._lock:
            if self.mode == "json":
                raise StorageMigrationError(
                    "配置已强制使用 JSON；请先将 storage_backend 改为 auto"
                )
            if isinstance(self.backend, SQLiteStorage):
                verification = self.backend.verify()
                if verification.get("ok"):
                    result = {
                        "status": "already-sqlite",
                        "backend": "sqlite",
                        "verification": verification,
                    }
                    self._last_action = result
                    return result

            documents = self._read_existing_json()
            if not documents:
                raise StorageMigrationError("没有找到可迁移的现有 JSON 数据")
            backup = self._create_backup(documents)
            temporary = self.data_root / f".rollpig.db.migrating-{uuid.uuid4().hex}.tmp"
            self._remove_sqlite_sidecars(temporary)
            temporary.unlink(missing_ok=True)
            try:
                target = self._new_sqlite(temporary)
                updates = {
                    self.data_root / relative: value
                    for relative, value in documents.items()
                }
                target.save_json_batch(updates)
                verification = target.verify()
                if not verification.get("ok"):
                    raise StorageMigrationError(
                        f"SQLite 完整性检查失败：{verification.get('integrity')}"
                    )
                expected = {
                    relative: self._digest(value)
                    for relative, value in documents.items()
                }
                actual = target.document_hashes()
                mismatched = sorted(
                    key for key, digest in expected.items() if actual.get(key) != digest
                )
                if mismatched:
                    raise StorageMigrationError(
                        "迁移对账失败：" + ", ".join(mismatched[:8])
                    )
                target.checkpoint()
                self._remove_sqlite_sidecars(temporary)
                os.replace(temporary, self.database_path)
                self._remove_sqlite_sidecars(self.database_path)
                self.backend = self._new_sqlite()
                final_verification = self.backend.verify()
                if not final_verification.get("ok"):
                    raise StorageMigrationError("迁移后的正式数据库完整性检查失败")
                state = {
                    "active_backend": "sqlite",
                    "migrated_at": int(time.time()),
                    "backup_name": backup.name,
                    "documents": len(documents),
                    "schema_version": final_verification.get("schema_version", 0),
                }
                self.json_storage.save_json(self.state_path, state)
                result = {
                    "status": "migrated",
                    "backend": "sqlite",
                    "backup_name": backup.name,
                    "documents": len(documents),
                    "verification": final_verification,
                }
                self._last_error = ""
                self._last_action = result
                return result
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                self._remove_sqlite_sidecars(temporary)
                self.backend = self.json_storage
                self._last_error = str(exc)
                if isinstance(exc, StorageMigrationError):
                    raise
                raise StorageMigrationError(f"SQLite 迁移失败：{exc}") from exc

    def verify(self) -> dict[str, Any]:
        with self._lock:
            if not self.database_path.exists():
                return {
                    "ok": False,
                    "backend": self.backend.backend_name,
                    "database_exists": False,
                    "message": "尚未建立 SQLite 数据库",
                }
            try:
                verification = self._new_sqlite().verify()
                self._last_error = ""
                return {
                    "backend": self.backend.backend_name,
                    "database_exists": True,
                    **verification,
                }
            except Exception as exc:
                self._last_error = str(exc)
                return {
                    "ok": False,
                    "backend": self.backend.backend_name,
                    "database_exists": True,
                    "message": str(exc),
                }

    def export_json_backup(self) -> dict[str, Any]:
        with self._lock:
            if isinstance(self.backend, SQLiteStorage):
                documents = self.backend.export_documents()
            else:
                documents = self._read_existing_json()
            if not documents:
                raise StorageMigrationError("没有可导出的存储数据")
            stamp = time.strftime("%Y%m%d-%H%M%S")
            archive = self.export_root / f"rollpig-json-{stamp}.zip"
            suffix = 0
            while archive.exists():
                suffix += 1
                archive = self.export_root / f"rollpig-json-{stamp}-{suffix}.zip"
            manifest = {
                "created_at": int(time.time()),
                "source_backend": self.backend.backend_name,
                "documents": {
                    key: self._digest(value) for key, value in documents.items()
                },
            }
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
                for relative, value in sorted(documents.items()):
                    output.writestr(
                        relative,
                        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    )
                output.writestr(
                    "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                )
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            result = {
                "status": "exported",
                "filename": archive.name,
                "size": archive.stat().st_size,
                "sha256": digest,
                "documents": len(documents),
            }
            self._last_action = result
            return result

    def rollback_to_json(self) -> dict[str, Any]:
        with self._lock:
            if not self.database_path.exists():
                self.backend = self.json_storage
                return {"status": "already-json", "backend": "json"}
            source = self._new_sqlite()
            verification = source.verify()
            if not verification.get("ok"):
                raise StorageMigrationError("SQLite 数据库未通过完整性检查，拒绝回滚覆盖 JSON")
            documents = source.export_documents()
            if not documents:
                raise StorageMigrationError("SQLite 数据库没有可回滚的文档")
            updates = {
                self.data_root / relative: value
                for relative, value in documents.items()
            }
            self.json_storage.save_json_batch(updates)
            reloaded = self._read_existing_json()
            mismatched = sorted(
                key
                for key, value in documents.items()
                if self._digest(reloaded.get(key)) != self._digest(value)
            )
            if mismatched:
                raise StorageMigrationError(
                    "JSON 回滚对账失败：" + ", ".join(mismatched[:8])
                )
            stamp = time.strftime("%Y%m%d-%H%M%S")
            disabled = self.data_root / f"rollpig.db.disabled-{stamp}"
            os.replace(self.database_path, disabled)
            self._remove_sqlite_sidecars(self.database_path)
            self.backend = self.json_storage
            state = {
                "active_backend": "json",
                "rolled_back_at": int(time.time()),
                "disabled_database": disabled.name,
                "documents": len(documents),
            }
            self.json_storage.save_json(self.state_path, state)
            result = {
                "status": "rolled-back",
                "backend": "json",
                "disabled_database": disabled.name,
                "documents": len(documents),
            }
            self._last_error = ""
            self._last_action = result
            return result

    def rebuild_projections(self) -> dict[str, Any]:
        with self._lock:
            if not self.database_path.exists():
                raise StorageMigrationError("尚未建立 SQLite 数据库")
            target = self._new_sqlite()
            result = target.rebuild_projections()
            verification = target.verify()
            if not verification.get("ok"):
                raise StorageMigrationError("投影重建后仍未通过一致性验证")
            if isinstance(self.backend, SQLiteStorage):
                self.backend = target
            action = {
                "status": "projections-rebuilt",
                "backend": self.backend.backend_name,
                "verification": verification,
            }
            self._last_error = ""
            self._last_action = action
            return action

    def status(self) -> dict[str, Any]:
        backups = sorted(
            (path.name for path in self.backup_root.iterdir() if path.is_dir()),
            reverse=True,
        )
        exports = sorted(
            (path.name for path in self.export_root.glob("*.zip")), reverse=True
        )
        return {
            "configured_mode": self.mode,
            "active_backend": self.backend.backend_name,
            "database_exists": self.database_path.exists(),
            "database_filename": self.database_path.name,
            "managed_documents": sorted(self.MANAGED_PATHS),
            "latest_backup": backups[0] if backups else "",
            "latest_export": exports[0] if exports else "",
            "last_error": self._last_error,
            "last_action": self._last_action,
            "health": self.backend.health(),
        }
