from __future__ import annotations

import ast
import asyncio
import hashlib
import hmac
import ipaddress
import json
import os
import re
import shutil
import socket
import stat
import tempfile
import time
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx


class UpdateError(RuntimeError):
    """A user-safe update failure."""


class PluginUpdateManager:
    """Install stable releases from the one hard-coded official repository.

    The updater deliberately has no arbitrary URL, branch or prerelease input.
    User data lives under AstrBot's plugin data directory and is never included
    in the replacement set.  Code is staged, validated and backed up before an
    overlay replacement; a failed replacement restores the previous files.
    """

    OFFICIAL_REPOSITORY = "casama233/astrbot_plugin_rollpig"
    PACKAGE_NAME = "astrbot_plugin_rollpig_plus"
    RELEASES_API = (
        "https://api.github.com/repos/casama233/astrbot_plugin_rollpig/releases?per_page=30"
    )
    ALLOWED_HOSTS = {
        "api.github.com",
        "github.com",
        "codeload.github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "github-releases.githubusercontent.com",
    }
    MAX_JSON_BYTES = 2 * 1024 * 1024
    MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
    MAX_CHECKSUM_BYTES = 256 * 1024
    MAX_FILES = 3000
    MAX_SINGLE_FILE_BYTES = 32 * 1024 * 1024
    MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
    MAX_REDIRECTS = 5
    BACKUP_KEEP = 3
    PROTECTED_TOP_LEVEL = {
        ".git",
        ".github",
        ".venv",
        "__pycache__",
        "data",
        "plugin_data",
    }

    def __init__(
        self,
        plugin_dir: Path,
        data_dir: Path,
        *,
        timeout: float = 30.0,
        trust_env: bool = False,
        logger: Any = None,
    ):
        self.plugin_dir = Path(plugin_dir).resolve()
        self.data_dir = Path(data_dir).resolve()
        self.timeout = min(120.0, max(5.0, float(timeout)))
        self.trust_env = bool(trust_env)
        self.logger = logger
        self._lock = asyncio.Lock()
        self._pending: dict[str, Any] | None = None
        self._last_check_at = 0
        self._last_error = ""
        self._last_result: dict[str, Any] | None = None
        self.backup_root = self.data_dir / "update_backups"
        self.state_path = self.data_dir / "update_state.json"
        self.backup_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalise_version(value: str) -> str:
        text = str(value or "").strip()
        if text.lower().startswith("v"):
            text = text[1:]
        if not re.fullmatch(r"\d+\.\d+\.\d+", text):
            raise UpdateError(f"版本号不是稳定语义版本：{value}")
        return text

    @classmethod
    def _version_tuple(cls, value: str) -> tuple[int, int, int]:
        return tuple(int(item) for item in cls._normalise_version(value).split("."))  # type: ignore[return-value]

    def current_version(self) -> str:
        metadata = self.plugin_dir / "metadata.yaml"
        try:
            content = metadata.read_text(encoding="utf-8")
        except OSError as exc:
            raise UpdateError("无法读取当前插件 metadata.yaml") from exc
        match = re.search(r'^version:\s*["\']?([^"\'\s]+)', content, re.MULTILINE)
        if not match:
            raise UpdateError("当前插件 metadata.yaml 缺少 version")
        return self._normalise_version(match.group(1))

    def status(self) -> dict[str, Any]:
        current = self.current_version()
        pending = dict(self._pending or {})
        pending.pop("checksum_url", None)
        pending.pop("download_url", None)
        last_result = dict(self._last_result or {})
        last_result.pop("backup_dir", None)
        return {
            "current_version": current,
            "backend": "official-github-plus-release-channel",
            "official_repository": self.OFFICIAL_REPOSITORY,
            "busy": self._lock.locked(),
            "last_check_at": self._last_check_at,
            "last_error": self._last_error,
            "pending": pending or None,
            "last_result": last_result or None,
        }

    async def check_for_update(self) -> dict[str, Any]:
        if self._lock.locked():
            raise UpdateError("已有版本检查或更新任务正在运行")
        async with self._lock:
            try:
                result = await self._check_unlocked()
                self._last_error = ""
                return result
            except Exception as exc:
                self._last_error = str(exc)
                if isinstance(exc, UpdateError):
                    raise
                raise UpdateError(f"检查更新失败：{exc}") from exc

    async def _check_unlocked(self) -> dict[str, Any]:
        releases = await self._request_json_list(self.RELEASES_API)
        payload = self._select_release_payload(releases)

        tag = str(payload.get("tag_name") or "")
        latest = self._normalise_version(tag)
        current = self.current_version()
        html_url = str(payload.get("html_url") or "")
        expected_release_prefix = (
            f"https://github.com/{self.OFFICIAL_REPOSITORY}/releases/tag/"
        )
        if not html_url.startswith(expected_release_prefix):
            raise UpdateError("Release 仓库身份校验失败")

        assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
        archive_asset = self._select_archive_asset(assets)
        if not archive_asset:
            raise UpdateError("RollPig Plus Release 缺少正式插件 ZIP 资源")
        archive_name = str(archive_asset.get("name") or "")
        expected_archive_name = f"{self.PACKAGE_NAME}-v{latest}.zip"
        if archive_name != expected_archive_name:
            raise UpdateError("RollPig Plus Release 插件 ZIP 名称与版本不匹配")
        download_url = str(archive_asset.get("browser_download_url") or "")
        expected_prefix = (
            f"https://github.com/{self.OFFICIAL_REPOSITORY}/releases/download/"
        )
        if not download_url.startswith(expected_prefix):
            raise UpdateError("Release 资源地址不属于官方仓库")

        checksum_url = self._select_checksum_url(assets, archive_name)
        expected_sha256 = ""
        if checksum_url:
            expected_checksum_prefix = (
                f"https://github.com/{self.OFFICIAL_REPOSITORY}/releases/download/"
            )
            if not checksum_url.startswith(expected_checksum_prefix):
                raise UpdateError("Release 校验文件地址不属于官方仓库")
            checksum_text = (
                await self._request_bytes(
                    checksum_url,
                    max_bytes=self.MAX_CHECKSUM_BYTES,
                    accept="text/plain, application/octet-stream",
                )
            ).decode("utf-8", errors="replace")
            expected_sha256 = self._parse_checksum(checksum_text, archive_name)
            if not expected_sha256:
                raise UpdateError("Release 提供了校验文件，但未找到对应压缩包的 SHA-256")

        result = {
            "current_version": current,
            "latest_version": latest,
            "tag": tag,
            "update_available": self._version_tuple(latest) > self._version_tuple(current),
            "archive_name": archive_name,
            "checksum_available": bool(expected_sha256),
            "expected_sha256": expected_sha256,
            "release_url": html_url,
            "published_at": str(payload.get("published_at") or ""),
            "notes": str(payload.get("body") or "").strip()[:1600],
        }
        self._pending = {
            **result,
            "download_url": download_url,
            "checksum_url": checksum_url,
        }
        self._last_check_at = int(time.time())
        return result

    async def apply_update(self, *, confirm_unsigned: bool = False) -> dict[str, Any]:
        if self._lock.locked():
            raise UpdateError("已有版本检查或更新任务正在运行")
        async with self._lock:
            try:
                release = await self._check_unlocked()
                if not release["update_available"]:
                    raise UpdateError("当前已经是最新稳定版本")
                if not release["checksum_available"] and not confirm_unsigned:
                    raise UpdateError("此 Release 未提供 SHA-256；需要在面板二次确认后再更新")

                assert self._pending is not None
                raw = await self._request_bytes(
                    str(self._pending["download_url"]),
                    max_bytes=self.MAX_ARCHIVE_BYTES,
                    accept="application/zip, application/octet-stream",
                )
                actual_sha256 = hashlib.sha256(raw).hexdigest()
                expected_sha256 = str(release.get("expected_sha256") or "")
                if expected_sha256 and not hmac.compare_digest(
                    actual_sha256, expected_sha256.lower()
                ):
                    raise UpdateError("下载包 SHA-256 与 Release 校验文件不一致")

                result = await asyncio.to_thread(
                    self._stage_validate_and_apply,
                    raw,
                    release,
                    actual_sha256,
                )
                self._last_result = result
                self._last_error = ""
                return result
            except Exception as exc:
                self._last_error = str(exc)
                if isinstance(exc, UpdateError):
                    raise
                raise UpdateError(f"安全更新失败：{exc}") from exc

    @classmethod
    def _select_archive_asset(cls, assets: list[Any]) -> dict[str, Any] | None:
        prefix = f"{cls.PACKAGE_NAME}-v".lower()
        candidates = [
            item
            for item in assets
            if isinstance(item, dict)
            and str(item.get("name") or "").lower().startswith(prefix)
            and str(item.get("name") or "").lower().endswith(".zip")
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: str(item.get("name") or ""))
        return candidates[0]

    @classmethod
    def _select_release_payload(cls, releases: list[Any]) -> dict[str, Any]:
        candidates: list[tuple[tuple[int, int, int], dict[str, Any]]] = []
        for item in releases:
            if not isinstance(item, dict) or item.get("draft") or item.get("prerelease"):
                continue
            tag = str(item.get("tag_name") or "")
            try:
                version = cls._normalise_version(tag)
            except UpdateError:
                continue
            assets = item.get("assets") if isinstance(item.get("assets"), list) else []
            archive = cls._select_archive_asset(assets)
            if not archive:
                continue
            if str(archive.get("name") or "") != f"{cls.PACKAGE_NAME}-v{version}.zip":
                continue
            candidates.append((cls._version_tuple(version), item))
        if not candidates:
            raise UpdateError("未找到可验证的 RollPig Plus 稳定 Release")
        candidates.sort(key=lambda entry: entry[0], reverse=True)
        return candidates[0][1]

    @staticmethod
    def _select_checksum_url(assets: list[Any], archive_name: str) -> str:
        exact = {f"{archive_name}.sha256", f"{archive_name}.sha256sum"}
        generic = {"sha256sums", "sha256sums.txt", "checksums.txt", "checksum.txt"}
        ranked: list[tuple[int, str]] = []
        for item in assets:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            url = str(item.get("browser_download_url") or "")
            lower = name.lower()
            if name in exact:
                ranked.append((0, url))
            elif lower in generic:
                ranked.append((1, url))
        ranked.sort()
        return ranked[0][1] if ranked else ""

    @staticmethod
    def _parse_checksum(text: str, archive_name: str) -> str:
        standalone = re.fullmatch(r"\s*([0-9a-fA-F]{64})\s*", text)
        if standalone:
            return standalone.group(1).lower()
        for line in text.splitlines():
            match = re.match(r"\s*([0-9a-fA-F]{64})\s+[* ]?(.+?)\s*$", line)
            if match and Path(match.group(2)).name == Path(archive_name).name:
                return match.group(1).lower()
        return ""

    async def _request_json(self, url: str) -> dict[str, Any]:
        raw = await self._request_bytes(
            url,
            max_bytes=self.MAX_JSON_BYTES,
            accept="application/vnd.github+json, application/json",
        )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise UpdateError("GitHub 返回了无效 JSON") from exc
        if not isinstance(payload, dict):
            raise UpdateError("GitHub Release 响应格式无效")
        return payload

    async def _request_json_list(self, url: str) -> list[Any]:
        raw = await self._request_bytes(
            url,
            max_bytes=self.MAX_JSON_BYTES,
            accept="application/vnd.github+json, application/json",
        )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise UpdateError("GitHub 返回了无效 JSON") from exc
        if not isinstance(payload, list):
            raise UpdateError("GitHub Releases 响应格式无效")
        return payload

    async def _request_bytes(self, url: str, *, max_bytes: int, accept: str) -> bytes:
        current = url
        timeout = httpx.Timeout(self.timeout, connect=min(15.0, self.timeout))
        headers = {
            "Accept": accept,
            "User-Agent": "AstrBot-RollPig-Safe-Updater/3.4.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            trust_env=self.trust_env,
            headers=headers,
        ) as client:
            for _ in range(self.MAX_REDIRECTS + 1):
                await self._validate_url(current)
                try:
                    async with client.stream("GET", current) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise UpdateError("GitHub 重定向缺少 Location")
                            current = urljoin(current, location)
                            continue
                        response.raise_for_status()
                        length = response.headers.get("content-length")
                        if length and int(length) > max_bytes:
                            raise UpdateError("远程文件超过安全大小上限")
                        chunks: list[bytes] = []
                        total = 0
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            if total > max_bytes:
                                raise UpdateError("远程文件超过安全大小上限")
                            chunks.append(chunk)
                        return b"".join(chunks)
                except httpx.HTTPError as exc:
                    raise UpdateError(f"GitHub 请求失败：{exc}") from exc
            raise UpdateError("GitHub 重定向次数过多")

    async def _validate_url(self, url: str) -> None:
        parsed = urlsplit(str(url or ""))
        host = str(parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or host not in self.ALLOWED_HOSTS
        ):
            raise UpdateError("更新地址未通过 HTTPS / 官方主机白名单校验")
        try:
            records = await asyncio.to_thread(
                socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM
            )
        except OSError as exc:
            raise UpdateError(f"无法解析更新主机：{host}") from exc
        addresses = {str(item[4][0]).split("%", 1)[0] for item in records}
        if not addresses:
            raise UpdateError(f"更新主机没有可用地址：{host}")
        for address in addresses:
            try:
                ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise UpdateError("更新主机返回了无效 IP") from exc
            if not ip.is_global:
                raise UpdateError(f"更新主机解析到非公网地址：{host}")

    def _stage_validate_and_apply(
        self, raw: bytes, release: dict[str, Any], actual_sha256: str
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="rollpig-update-") as temporary_root:
            root = Path(temporary_root)
            archive_path = root / "release.zip"
            archive_path.write_bytes(raw)
            staging = root / "staging"
            staging.mkdir()
            self._safe_extract(archive_path, staging)
            self._validate_staging(staging, str(release["latest_version"]))
            backup_dir = self._create_backup(str(release["current_version"]))
            try:
                written_count = self._overlay_install(staging, backup_dir)
            except Exception as exc:
                self._restore_backup(backup_dir)
                raise UpdateError(f"文件替换失败，已回滚：{exc}") from exc

        state = {
            "status": "installed-restart-required",
            "from_version": str(release["current_version"]),
            "to_version": str(release["latest_version"]),
            "installed_at": int(time.time()),
            "sha256": actual_sha256,
            "checksum_verified": bool(release.get("checksum_available")),
            "backup_dir": str(backup_dir),
            "written_files": written_count,
            "restart_required": True,
        }
        warnings: list[str] = []
        try:
            self._write_state(state)
        except OSError as exc:
            warning = f"代码已更新，但状态记录写入失败：{type(exc).__name__}"
            warnings.append(warning)
            self._log("warning", warning)
        try:
            self._prune_backups()
        except OSError as exc:
            warning = f"代码已更新，但旧备份清理失败：{type(exc).__name__}"
            warnings.append(warning)
            self._log("warning", warning)
        self._log(
            "info",
            f"今日小猪已安全更新到 {release['latest_version']}，等待 AstrBot 重启加载",
        )
        public_state = dict(state)
        public_state.pop("backup_dir", None)
        if warnings:
            public_state["warnings"] = warnings
        return public_state

    def _safe_extract(self, archive_path: Path, staging: Path) -> None:
        try:
            archive = zipfile.ZipFile(archive_path)
        except zipfile.BadZipFile as exc:
            raise UpdateError("下载内容不是有效 ZIP") from exc
        with archive:
            files = [item for item in archive.infolist() if not item.is_dir()]
            if not files or len(files) > self.MAX_FILES:
                raise UpdateError("ZIP 文件数量无效或超过上限")
            total = sum(max(0, item.file_size) for item in files)
            if total > self.MAX_UNCOMPRESSED_BYTES:
                raise UpdateError("ZIP 解压后体积超过安全上限")

            parsed: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
            for item in files:
                if "\\" in item.filename or "\x00" in item.filename:
                    raise UpdateError("ZIP 包含非法路径")
                path = PurePosixPath(item.filename)
                if path.is_absolute() or not path.parts or ".." in path.parts:
                    raise UpdateError("ZIP 包含路径穿越项")
                mode = (item.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise UpdateError("ZIP 包含符号链接，已拒绝")
                if item.file_size > self.MAX_SINGLE_FILE_BYTES:
                    raise UpdateError(f"ZIP 单文件过大：{item.filename}")
                if item.compress_size and item.file_size > item.compress_size * 250 + 1024 * 1024:
                    raise UpdateError(f"ZIP 文件压缩比异常：{item.filename}")
                parsed.append((item, tuple(path.parts)))

            first_parts = {parts[0] for _, parts in parsed}
            strip_root = len(first_parts) == 1 and all(len(parts) > 1 for _, parts in parsed)
            for item, parts in parsed:
                relative_parts = parts[1:] if strip_root else parts
                if not relative_parts:
                    continue
                if relative_parts[0] in self.PROTECTED_TOP_LEVEL:
                    continue
                if relative_parts[-1] in {".env", "update_state.json"}:
                    continue
                relative = Path(*relative_parts)
                destination = (staging / relative).resolve()
                if staging.resolve() not in destination.parents:
                    raise UpdateError("ZIP 解压目标越界")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)

    def _validate_staging(self, staging: Path, expected_version: str) -> None:
        required = [staging / "main.py", staging / "metadata.yaml", staging / "resource" / "pig.json"]
        if any(not path.is_file() for path in required):
            raise UpdateError("Release 缺少 main.py、metadata.yaml 或 resource/pig.json")
        metadata = (staging / "metadata.yaml").read_text(encoding="utf-8")
        name = re.search(r'^name:\s*["\']?([^"\'\s]+)', metadata, re.MULTILINE)
        author = re.search(r'^author:\s*["\']?([^"\'\n]+?)["\']?\s*$', metadata, re.MULTILINE)
        repo = re.search(r'^repo:\s*["\']?([^"\'\s]+)', metadata, re.MULTILINE)
        version = re.search(r'^version:\s*["\']?([^"\'\s]+)', metadata, re.MULTILINE)
        if not name or name.group(1) != "astrbot_plugin_rollpig_plus":
            raise UpdateError("Release metadata 插件名不匹配")
        if not author or author.group(1).strip() != "casama233":
            raise UpdateError("Release metadata 作者身份不匹配")
        if not repo or repo.group(1).rstrip("/") != f"https://github.com/{self.OFFICIAL_REPOSITORY}":
            raise UpdateError("Release metadata 官方仓库不匹配")
        if not version or self._normalise_version(version.group(1)) != expected_version:
            raise UpdateError("Release metadata 版本与 GitHub tag 不匹配")
        for path in staging.rglob("*.py"):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, UnicodeError, SyntaxError) as exc:
                raise UpdateError(f"Release Python 完整性检查失败：{path.name}") from exc

    def _create_backup(self, current_version: str) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = self.backup_root / f"{stamp}-v{current_version}"
        plugin_backup = backup_dir / "plugin"
        backup_dir.mkdir(parents=True, exist_ok=False)

        data_relative: Path | None = None
        try:
            data_relative = self.data_dir.relative_to(self.plugin_dir)
        except ValueError:
            pass

        def ignore(directory: str, names: list[str]) -> set[str]:
            ignored = {".git", "__pycache__", ".venv"}.intersection(names)
            current = Path(directory).resolve()
            if data_relative is not None and current == self.plugin_dir:
                ignored.add(data_relative.parts[0])
            return ignored

        shutil.copytree(self.plugin_dir, plugin_backup, ignore=ignore)
        return backup_dir

    def _overlay_install(self, staging: Path, backup_dir: Path) -> int:
        created: list[Path] = []
        written = 0
        try:
            for source in sorted(path for path in staging.rglob("*") if path.is_file()):
                relative = source.relative_to(staging)
                target = self.plugin_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    created.append(target)
                temporary = target.with_name(f".{target.name}.update-{uuid.uuid4().hex}")
                shutil.copy2(source, temporary)
                os.replace(temporary, target)
                written += 1
            (backup_dir / "created_files.json").write_text(
                json.dumps(
                    [str(path.relative_to(self.plugin_dir)) for path in created],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return written
        except Exception:
            for target in created:
                try:
                    target.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def _restore_backup(self, backup_dir: Path) -> None:
        plugin_backup = backup_dir / "plugin"
        created_file = backup_dir / "created_files.json"
        if created_file.exists():
            try:
                for relative in json.loads(created_file.read_text(encoding="utf-8")):
                    target = self.plugin_dir / str(relative)
                    target.unlink(missing_ok=True)
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        if not plugin_backup.exists():
            return
        for source in sorted(path for path in plugin_backup.rglob("*") if path.is_file()):
            relative = source.relative_to(plugin_backup)
            target = self.plugin_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.rollback-{uuid.uuid4().hex}")
            shutil.copy2(source, temporary)
            os.replace(temporary, target)

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(f".{self.state_path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, self.state_path)

    def _prune_backups(self) -> None:
        backups = sorted(
            (path for path in self.backup_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in backups[self.BACKUP_KEEP :]:
            shutil.rmtree(path, ignore_errors=True)

    def _log(self, level: str, message: str) -> None:
        target = getattr(self.logger, level, None)
        if callable(target):
            target(message)
