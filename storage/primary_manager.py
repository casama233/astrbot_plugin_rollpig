from __future__ import annotations

import hashlib
import json
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from . import manager as legacy_manager
from .json_storage import JSONStorage
from .manager import StorageManager as LegacyStorageManager
from .manager import StorageMigrationError
from .sqlite_primary import SQLitePrimaryStorage


class PrimaryStorageManager(LegacyStorageManager):
    """v3 storage selector with automatic verified SQLite bootstrap."""

    # Preserve the public v2 path set for integrations that instantiate the
    # legacy SQLiteStorage directly. v3 itself stores only runtime authority
    # documents; the cloud catalog remains an ordinary replaceable JSON cache.
    MANAGED_PATHS = {
        "rollpig_today.json",
        "pig_history.json",
        "roast_state.json",
        "ai_roast_copies.json",
        "pig_catalog.json",
        "local_overrides.json",
        "deleted_pigs.json",
    }
    RUNTIME_MANAGED_PATHS = MANAGED_PATHS - {"pig_catalog.json"}
    LEGACY_IMPORT_PATHS = MANAGED_PATHS

    def _new_sqlite(self, path: Path | None = None) -> SQLitePrimaryStorage:
        return SQLitePrimaryStorage(
            path or self.database_path,
            self.data_root,
            self.RUNTIME_MANAGED_PATHS,
            fallback=self.json_storage,
            lock=self._lock,
            busy_timeout_ms=self.busy_timeout_ms,
        )

    def _read_existing_json(self) -> dict[str, Any]:
        documents: dict[str, Any] = {}
        for relative in sorted(self.LEGACY_IMPORT_PATHS):
            path = self.data_root / relative
            if not path.exists():
                continue
            try:
                documents[relative] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise StorageMigrationError(f"迁移前无法读取 {relative}：{exc}") from exc
        return documents

    @staticmethod
    def _document_facts(documents: dict[str, Any]) -> dict[str, Any]:
        history = documents.get("pig_history.json")
        history = history if isinstance(history, dict) else {}
        users = history.get("users") if isinstance(history.get("users"), dict) else {}
        daily = history.get("daily") if isinstance(history.get("daily"), dict) else {}
        claims_root = (
            history.get("identity_claims")
            if isinstance(history.get("identity_claims"), dict)
            else {}
        )
        aliases_root = (
            history.get("identity_aliases")
            if isinstance(history.get("identity_aliases"), dict)
            else {}
        )
        roast = documents.get("roast_state.json")
        roast = roast if isinstance(roast, dict) else {}
        ai = documents.get("ai_roast_copies.json")
        ai = ai if isinstance(ai, dict) else {}
        copies = ai.get("copies") if isinstance(ai.get("copies"), dict) else {}
        attempts = ai.get("attempts") if isinstance(ai.get("attempts"), dict) else {}
        overrides = documents.get("local_overrides.json")
        tombstones = documents.get("deleted_pigs.json")
        return {
            "users": sum(1 for value in users.values() if isinstance(value, dict)),
            "user_pigs": sum(
                sum(
                    1
                    for record in value.get("pigs", {}).values()
                    if isinstance(record, dict)
                )
                for value in users.values()
                if isinstance(value, dict) and isinstance(value.get("pigs"), dict)
            ),
            "total_draws": sum(
                int(value.get("total_draws", 0) or 0)
                for value in users.values()
                if isinstance(value, dict)
            ),
            "daily_draws": sum(
                len(value.get("records", {}))
                for value in daily.values()
                if isinstance(value, dict) and isinstance(value.get("records"), dict)
            ),
            "identity_claims": sum(
                len(value) for value in claims_root.values() if isinstance(value, dict)
            ),
            "identity_aliases": sum(
                len(value.get("by_alias", {}))
                for value in aliases_root.values()
                if isinstance(value, dict) and isinstance(value.get("by_alias"), dict)
            ),
            "cooldowns": len(roast.get("cooldowns", {}))
            if isinstance(roast.get("cooldowns"), dict)
            else 0,
            "backdoors": len(roast.get("daily_backdoors", {}))
            if isinstance(roast.get("daily_backdoors"), dict)
            else 0,
            "roast_counts": len(roast.get("daily_roast_counts", {}))
            if isinstance(roast.get("daily_roast_counts"), dict)
            else 0,
            "penalties": len(roast.get("eaten_penalties", {}))
            if isinstance(roast.get("eaten_penalties"), dict)
            else 0,
            "eaten_events": len(roast.get("eaten_events", {}))
            if isinstance(roast.get("eaten_events"), dict)
            else 0,
            "ai_copies": sum(
                sum(1 for content in value.values() if str(content or "").strip())
                for value in copies.values()
                if isinstance(value, dict)
            ),
            "ai_attempts": sum(
                sum(1 for status in value.values() if str(status))
                for value in attempts.values()
                if isinstance(value, dict)
            ),
            "override_ids": sorted(
                str(value.get("id"))
                for value in overrides if isinstance(value, dict) and str(value.get("id") or "")
            )
            if isinstance(overrides, list)
            else [],
            "tombstones": sorted(str(value) for value in tombstones if str(value))
            if isinstance(tombstones, list)
            else [],
        }

    def _replace_database(self, temporary: Path) -> None:
        self._remove_sqlite_sidecars(temporary)
        legacy_manager.os.replace(temporary, self.database_path)
        self._remove_sqlite_sidecars(self.database_path)

    def _activate_sqlite(self) -> SQLitePrimaryStorage:
        backend = self._new_sqlite()
        verification = backend.verify()
        if not verification.get("ok"):
            raise StorageMigrationError("正式 SQLite 数据库未通过完整性检查")
        self.backend = backend
        self._last_error = ""
        return backend

    def _create_empty_sqlite(self) -> dict[str, Any]:
        temporary = self.data_root / f".rollpig.db.bootstrap-{uuid.uuid4().hex}.tmp"
        temporary.unlink(missing_ok=True)
        self._remove_sqlite_sidecars(temporary)
        try:
            target = self._new_sqlite(temporary)
            verification = target.verify()
            if not verification.get("ok"):
                raise StorageMigrationError("新建 SQLite 数据库未通过完整性检查")
            target.checkpoint()
            self._replace_database(temporary)
            backend = self._activate_sqlite()
            state = {
                "active_backend": "sqlite",
                "created_at": int(time.time()),
                "schema_version": backend.verify().get("schema_version", 0),
                "source": "empty-v3-bootstrap",
            }
            self.json_storage.save_json(self.state_path, state)
            result = {
                "status": "created-sqlite",
                "backend": "sqlite",
                "documents": 0,
                "verification": backend.verify(),
            }
            self._last_action = result
            return result
        except Exception:
            temporary.unlink(missing_ok=True)
            self._remove_sqlite_sidecars(temporary)
            raise

    def _migrate_documents_to_sqlite(
        self, documents: dict[str, Any], *, automatic: bool
    ) -> dict[str, Any]:
        backup = self._create_backup(documents)
        temporary = self.data_root / f".rollpig.db.migrating-{uuid.uuid4().hex}.tmp"
        temporary.unlink(missing_ok=True)
        self._remove_sqlite_sidecars(temporary)
        try:
            target = self._new_sqlite(temporary)
            target.import_legacy_documents(documents)
            verification = target.verify()
            if not verification.get("ok"):
                raise StorageMigrationError("SQLite 规范化导入未通过完整性检查")
            exported = target.export_documents()
            expected_facts = self._document_facts(documents)
            actual_facts = self._document_facts(exported)
            mismatched = {
                key: {"expected": expected_facts[key], "actual": actual_facts.get(key)}
                for key in expected_facts
                if expected_facts[key] != actual_facts.get(key)
            }
            if mismatched:
                names = ", ".join(sorted(mismatched)[:8])
                raise StorageMigrationError("迁移事实对账失败：" + names)
            target.checkpoint()
            self._replace_database(temporary)
            backend = self._activate_sqlite()
            final_verification = backend.verify()
            state = {
                "active_backend": "sqlite",
                "migrated_at": int(time.time()),
                "backup_name": backup.name,
                "documents": len(documents),
                "schema_version": final_verification.get("schema_version", 0),
                "source": "automatic-json-migration" if automatic else "manual-json-migration",
            }
            self.json_storage.save_json(self.state_path, state)
            result = {
                "status": "auto-migrated" if automatic else "migrated",
                "backend": "sqlite",
                "backup_name": backup.name,
                "documents": len(documents),
                "verification": final_verification,
            }
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

    def _select_initial_backend(self) -> None:
        if self.mode == "json":
            self.backend = self.json_storage
            return
        if self.database_path.exists():
            try:
                candidate = self._new_sqlite()
                verification = candidate.verify()
                if (
                    verification.get("integrity") == "ok"
                    and int(verification.get("foreign_key_errors", 0) or 0) == 0
                    and verification.get("projection_ok") is False
                ):
                    candidate.rebuild_projections(reason="startup-auto")
                    verification = candidate.verify()
                    self._last_action = {"status": "auto-repaired-normalized-state"}
                if not verification.get("ok"):
                    raise StorageMigrationError(
                        f"SQLite 完整性或规范化状态检查失败：{verification.get('integrity')}"
                    )
                self.backend = candidate
                self._last_error = ""
                return
            except Exception as exc:
                self.backend = self.json_storage
                self._last_error = f"SQLite 不可用，已回退 JSON：{exc}"
                return
        try:
            documents = self._read_existing_json()
            if documents:
                self._migrate_documents_to_sqlite(documents, automatic=True)
            else:
                self._create_empty_sqlite()
        except Exception as exc:
            self.backend = self.json_storage
            self._last_error = f"SQLite 自动建立失败，已安全回退 JSON：{exc}"

    def migrate_to_sqlite(self) -> dict[str, Any]:
        with self._lock:
            if self.mode == "json":
                raise StorageMigrationError(
                    "配置已强制使用 JSON；请先将 storage_backend 改为 auto"
                )
            if isinstance(self.backend, SQLitePrimaryStorage):
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
            if documents:
                return self._migrate_documents_to_sqlite(documents, automatic=False)
            return self._create_empty_sqlite()

    def export_json_backup(self) -> dict[str, Any]:
        with self._lock:
            if isinstance(self.backend, SQLitePrimaryStorage):
                documents = self.backend.export_documents()
                catalog_path = self.data_root / "pig_catalog.json"
                if catalog_path.exists():
                    documents["pig_catalog.json"] = self.json_storage.load_json(
                        catalog_path, []
                    )
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
                "compatibility_mode": "on-demand"
                if isinstance(self.backend, SQLitePrimaryStorage)
                else "native-json",
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
                "generated_on_demand": isinstance(self.backend, SQLitePrimaryStorage),
            }
            self._last_action = result
            return result

    def status(self) -> dict[str, Any]:
        status = super().status()
        status["sqlite_default"] = self.mode != "json"
        status["compatibility_exports_on_demand"] = isinstance(
            self.backend, SQLitePrimaryStorage
        )
        status["managed_documents"] = sorted(self.RUNTIME_MANAGED_PATHS)
        status["json_cache_documents"] = ["pig_catalog.json"]
        return status


StorageManager = PrimaryStorageManager
JSONStorageBackend = JSONStorage
