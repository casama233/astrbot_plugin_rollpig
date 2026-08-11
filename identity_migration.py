from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from .storage import StorageManager
except ImportError:  # pragma: no cover - direct module loading compatibility
    from storage import StorageManager


LEGACY_PLUGIN_NAME = "astrbot_plugin_rollpig"
PLUGIN_NAME = "astrbot_plugin_rollpig_plus"
BRIDGE_MARKER = ".rollpig-enhanced-origin.json"
MIGRATION_STATE = "identity_migration_state.json"
SOURCE_REPOSITORY = "casama233/astrbot_plugin_rollpig"
TARGET_PLUGIN_ID = "casama233/astrbot_plugin_rollpig_plus"

USER_JSON_FILES = (
    "rollpig_today.json",
    "pig_history.json",
    "roast_state.json",
    "ai_roast_copies.json",
    "pig_catalog.json",
    "local_overrides.json",
    "deleted_pigs.json",
)
DISTINCTIVE_JSON_FILES = {
    "pig_history.json",
    "roast_state.json",
    "ai_roast_copies.json",
    "local_overrides.json",
    "deleted_pigs.json",
}
SQL_FINGERPRINT_TABLES = {
    "schema_migrations",
    "projection_meta",
    "identities",
    "daily_draws",
    "user_pigs",
}


class IdentityMigrationError(RuntimeError):
    """Raised when a qualified legacy migration cannot be completed safely."""


def _log(logger: Any, level: str, message: str) -> None:
    if logger is None:
        return
    callback = getattr(logger, level, None)
    if callable(callback):
        callback(message)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_bridge_marker(source: Path) -> dict[str, Any] | None:
    marker_path = source / BRIDGE_MARKER
    if not marker_path.exists():
        return None
    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IdentityMigrationError("旧数据身份标记损坏，拒绝自动迁移") from exc
    if not isinstance(payload, dict):
        raise IdentityMigrationError("旧数据身份标记格式无效，拒绝自动迁移")
    expected = {
        "source_repository": SOURCE_REPOSITORY,
        "source_plugin_name": LEGACY_PLUGIN_NAME,
        "migration_target": TARGET_PLUGIN_ID,
    }
    mismatched = [key for key, value in expected.items() if payload.get(key) != value]
    if mismatched:
        raise IdentityMigrationError(
            "旧数据身份标记与增强版来源不匹配：" + ", ".join(mismatched)
        )
    return payload


def _inspect_sqlite(path: Path) -> dict[str, Any]:
    try:
        connection = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True, timeout=10)
    except sqlite3.Error as exc:
        raise IdentityMigrationError("无法只读打开旧 SQLite 数据库") from exc
    try:
        integrity_row = connection.execute("PRAGMA integrity_check").fetchone()
        integrity = str(integrity_row[0]) if integrity_row else "missing"
        foreign_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_errors:
            raise IdentityMigrationError("旧 SQLite 数据库未通过完整性或外键检查")
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        versions: list[int] = []
        if "schema_migrations" in tables:
            versions = [
                int(row[0])
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ).fetchall()
            ]
        return {
            "integrity": integrity,
            "foreign_key_errors": len(foreign_errors),
            "tables": sorted(tables),
            "schema_versions": versions,
            "enhanced_fingerprint": SQL_FINGERPRINT_TABLES.issubset(tables)
            and bool(versions),
        }
    except sqlite3.Error as exc:
        raise IdentityMigrationError("检查旧 SQLite 数据库失败") from exc
    finally:
        connection.close()


def _qualify_source(source: Path) -> tuple[str, dict[str, Any]] | None:
    marker = _validate_bridge_marker(source)
    if marker is not None:
        return "bridge-marker", marker

    database = source / "rollpig.db"
    if database.exists():
        inspection = _inspect_sqlite(database)
        if inspection["enhanced_fingerprint"]:
            return "enhanced-sqlite-fingerprint", inspection
        raise IdentityMigrationError(
            "发现旧 SQLite，但无法确认它来自本增强分支；拒绝自动迁移"
        )

    distinctive = sorted(
        name for name in DISTINCTIVE_JSON_FILES if (source / name).is_file()
    )
    if len(distinctive) >= 2:
        return "enhanced-json-fingerprint", {"distinctive_files": distinctive}
    return None


def _copy_verified(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if _hash_file(source) != _hash_file(target):
        raise IdentityMigrationError(f"复制校验失败：{source.name}")


def _copy_tree_verified(source: Path, target: Path) -> int:
    count = 0
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise IdentityMigrationError(f"旧图片目录包含符号链接：{path.name}")
        relative = path.relative_to(source)
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if not path.is_file():
            continue
        _copy_verified(path, destination)
        count += 1
    return count


def _backup_sqlite(source: Path, target: Path) -> dict[str, Any]:
    inspection = _inspect_sqlite(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        source_connection = sqlite3.connect(
            f"file:{source}?mode=ro", uri=True, timeout=15
        )
        destination_connection = sqlite3.connect(target, timeout=15)
        try:
            source_connection.backup(destination_connection)
            destination_connection.commit()
        finally:
            destination_connection.close()
            source_connection.close()
    except sqlite3.Error as exc:
        raise IdentityMigrationError("创建旧 SQLite 一致性快照失败") from exc
    copied = _inspect_sqlite(target)
    if copied["integrity"] != "ok" or copied["foreign_key_errors"]:
        raise IdentityMigrationError("SQLite 快照未通过复制后检查")
    return inspection


def _manifest(root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == MIGRATION_STATE:
            continue
        if path.name.endswith(("-wal", "-shm")):
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(("storage_backups/", "storage_exports/")):
            continue
        manifest[relative] = _hash_file(path)
    return manifest


def _remove_generated_validation_artifacts(stage: Path) -> None:
    for name in ("storage_backups", "storage_exports"):
        path = stage / name
        if path.exists():
            shutil.rmtree(path)
    for suffix in ("-wal", "-shm"):
        Path(f"{stage / 'rollpig.db'}{suffix}").unlink(missing_ok=True)


def migrate_legacy_data(
    new_data_dir: Path,
    *,
    busy_timeout_ms: int = 5000,
    logger: Any = None,
) -> dict[str, Any]:
    """Copy verified enhanced-fork data into the isolated plus namespace."""
    destination = Path(new_data_dir).resolve()
    if destination.name != PLUGIN_NAME:
        raise IdentityMigrationError(
            f"新数据目录必须为 {PLUGIN_NAME}，实际为 {destination.name}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        return {"status": "destination-not-empty", "migrated": False}

    source = destination.parent / LEGACY_PLUGIN_NAME
    if not source.is_dir():
        return {"status": "no-legacy-data", "migrated": False}

    qualification = _qualify_source(source)
    if qualification is None:
        _log(
            logger,
            "warning",
            "发现 astrbot_plugin_rollpig 旧数据，但无法确认来自增强分支；已拒绝自动迁移。",
        )
        return {"status": "legacy-source-ambiguous", "migrated": False}

    method, _evidence = qualification
    stage = destination.parent / f".{PLUGIN_NAME}.migrating-{uuid.uuid4().hex}"
    stage.mkdir(parents=False, exist_ok=False)
    copied_items = 0
    try:
        database = source / "rollpig.db"
        source_db_inspection: dict[str, Any] | None = None
        if database.is_file():
            source_db_inspection = _backup_sqlite(database, stage / "rollpig.db")
            copied_items += 1

        for name in USER_JSON_FILES:
            path = source / name
            if path.is_file():
                _copy_verified(path, stage / name)
                try:
                    json.loads((stage / name).read_text(encoding="utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise IdentityMigrationError(f"旧 JSON 数据损坏：{name}") from exc
                copied_items += 1

        images = source / "images"
        copied_images = 0
        if images.is_dir():
            copied_images = _copy_tree_verified(images, stage / "images")
            copied_items += copied_images

        if copied_items == 0:
            shutil.rmtree(stage)
            return {"status": "qualified-but-empty", "migrated": False}

        validator = StorageManager(
            stage,
            mode="auto",
            busy_timeout_ms=busy_timeout_ms,
        )
        verification = validator.verify()
        if (stage / "rollpig.db").exists() and not verification.get("ok"):
            raise IdentityMigrationError("迁移暂存区未通过完整 SQLite 运行态验证")
        backend = getattr(validator, "backend", None)
        checkpoint = getattr(backend, "checkpoint", None)
        if callable(checkpoint):
            checkpoint()
        _remove_generated_validation_artifacts(stage)

        state = {
            "schema_version": 1,
            "status": "verified-copy",
            "source_plugin": LEGACY_PLUGIN_NAME,
            "source_repository": SOURCE_REPOSITORY,
            "target_plugin": PLUGIN_NAME,
            "target_plugin_id": TARGET_PLUGIN_ID,
            "qualification": method,
            "source_retained": True,
            "migrated_at": int(time.time()),
            "copied_images": copied_images,
            "source_db": source_db_inspection,
            "verification": {
                "ok": bool(verification.get("ok")),
                "integrity": verification.get("integrity"),
                "foreign_key_errors": verification.get("foreign_key_errors", 0),
                "schema_version": verification.get("schema_version", 0),
            },
            "files": _manifest(stage),
        }
        (stage / MIGRATION_STATE).write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if any(destination.iterdir()):
            raise IdentityMigrationError("迁移提交前新数据目录出现内容，拒绝覆盖")
        destination.rmdir()
        try:
            os.replace(stage, destination)
        except Exception:
            destination.mkdir(parents=True, exist_ok=True)
            raise

        _log(
            logger,
            "info",
            "今日小猪增强版旧数据已验证复制到 astrbot_plugin_rollpig_plus；旧数据仍完整保留。",
        )
        return {
            "status": "migrated",
            "migrated": True,
            "qualification": method,
            "source_retained": True,
            "copied_images": copied_images,
        }
    except Exception as exc:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        destination.mkdir(parents=True, exist_ok=True)
        if isinstance(exc, IdentityMigrationError):
            raise
        raise IdentityMigrationError(f"增强版身份数据迁移失败：{exc}") from exc


def migrate_legacy_config(config: Any, *, logger: Any = None) -> dict[str, Any]:
    """Copy only still-supported keys from the legacy config on first deploy."""
    if not getattr(config, "first_deploy", False):
        return {"status": "not-first-deploy", "migrated": False}
    raw_path = getattr(config, "config_path", None)
    if not raw_path:
        return {"status": "config-path-unavailable", "migrated": False}
    new_path = Path(str(raw_path))
    expected_name = f"{PLUGIN_NAME}_config.json"
    if new_path.name != expected_name:
        _log(
            logger,
            "warning",
            f"新插件配置文件名不是 {expected_name}；为避免命名空间冲突，拒绝自动迁移配置。",
        )
        return {"status": "unsafe-config-namespace", "migrated": False}
    old_path = new_path.with_name(f"{LEGACY_PLUGIN_NAME}_config.json")
    if not old_path.is_file():
        return {"status": "no-legacy-config", "migrated": False}
    try:
        payload = json.loads(old_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _log(logger, "warning", f"旧增强版配置无法读取，保留新插件默认配置：{exc}")
        return {"status": "legacy-config-invalid", "migrated": False}
    if not isinstance(payload, dict):
        return {"status": "legacy-config-invalid", "migrated": False}
    allowed = set(config.keys()) if hasattr(config, "keys") else set()
    migrated = {key: value for key, value in payload.items() if key in allowed}
    if not migrated:
        return {"status": "no-compatible-config-keys", "migrated": False}
    config.update(migrated)
    save = getattr(config, "save_config", None)
    if callable(save):
        save()
    _log(logger, "info", f"已迁移 {len(migrated)} 个旧增强版配置项到新插件命名空间。")
    return {"status": "migrated", "migrated": True, "keys": sorted(migrated)}


def validate_runtime_namespace(plugin_dir: Path, config: Any) -> None:
    """Reject installs that would reuse the legacy code/config namespace."""
    directory = Path(plugin_dir).resolve()
    if directory.name != PLUGIN_NAME:
        raise IdentityMigrationError(
            "今日小猪增强版 3.2.0 必须安装在 astrbot_plugin_rollpig_plus 目录。"
            "请通过 AstrBot 插件市场安装，或手动 clone 时显式指定该目录名。"
        )
    config_path = getattr(config, "config_path", None)
    if config_path and Path(str(config_path)).name != f"{PLUGIN_NAME}_config.json":
        raise IdentityMigrationError(
            "AstrBot 为本插件分配了旧配置命名空间，已拒绝启动以避免覆盖原版配置。"
        )


def warn_if_legacy_loaded(context: Any, *, logger: Any = None) -> bool:
    """Warn when the legacy package is simultaneously active."""
    getter = getattr(context, "get_all_stars", None)
    if not callable(getter):
        return False
    for star in getter() or []:
        if getattr(star, "name", None) != LEGACY_PLUGIN_NAME:
            continue
        if getattr(star, "activated", True) is False:
            continue
        _log(
            logger,
            "warning",
            "检测到 astrbot_plugin_rollpig 与 rollpig_plus 同时启用；两者指令重叠。"
            "确认新插件数据无误后请停用旧插件。",
        )
        return True
    return False
