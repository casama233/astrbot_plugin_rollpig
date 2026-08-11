from pathlib import Path

path = Path("updater.py")
text = path.read_text(encoding="utf-8")

if "RELEASES_API =" in text and "_select_release_payload" in text:
    raise SystemExit(0)

old = '''    OFFICIAL_REPOSITORY = "casama233/astrbot_plugin_rollpig"\n    RELEASE_API = (\n        "https://api.github.com/repos/casama233/astrbot_plugin_rollpig/releases/latest"\n    )\n'''
new = '''    OFFICIAL_REPOSITORY = "casama233/astrbot_plugin_rollpig"\n    PACKAGE_NAME = "astrbot_plugin_rollpig_plus"\n    RELEASES_API = (\n        "https://api.github.com/repos/casama233/astrbot_plugin_rollpig/releases?per_page=30"\n    )\n'''
if old not in text:
    raise SystemExit("release API block not found")
text = text.replace(old, new, 1)

old = '''            "backend": "official-github-release",\n'''
new = '''            "backend": "official-github-plus-release-channel",\n'''
if old not in text:
    raise SystemExit("status backend block not found")
text = text.replace(old, new, 1)

old = '''    async def _check_unlocked(self) -> dict[str, Any]:\n        payload = await self._request_json(self.RELEASE_API)\n        if payload.get("draft") or payload.get("prerelease"):\n            raise UpdateError("GitHub latest 返回了草稿或预发布版本，已拒绝")\n\n        tag = str(payload.get("tag_name") or "")\n'''
new = '''    async def _check_unlocked(self) -> dict[str, Any]:\n        releases = await self._request_json_list(self.RELEASES_API)\n        payload = self._select_release_payload(releases)\n\n        tag = str(payload.get("tag_name") or "")\n'''
if old not in text:
    raise SystemExit("check_unlocked prefix not found")
text = text.replace(old, new, 1)

old = '''        archive_asset = self._select_archive_asset(assets)\n        if archive_asset:\n            archive_name = str(archive_asset.get("name") or "rollpig-release.zip")\n            download_url = str(archive_asset.get("browser_download_url") or "")\n            expected_prefix = (\n                f"https://github.com/{self.OFFICIAL_REPOSITORY}/releases/download/"\n            )\n            if not download_url.startswith(expected_prefix):\n                raise UpdateError("Release 资源地址不属于官方仓库")\n        else:\n            archive_name = f"astrbot_plugin_rollpig_plus-v{latest}.zip"\n            download_url = str(payload.get("zipball_url") or "")\n            expected_api_prefix = (\n                f"https://api.github.com/repos/{self.OFFICIAL_REPOSITORY}/zipball/"\n            )\n            if not download_url.startswith(expected_api_prefix):\n                raise UpdateError("Release 源码包地址不属于官方仓库")\n'''
new = '''        archive_asset = self._select_archive_asset(assets)\n        if not archive_asset:\n            raise UpdateError("RollPig Plus Release 缺少正式插件 ZIP 资源")\n        archive_name = str(archive_asset.get("name") or "")\n        expected_archive_name = f"{self.PACKAGE_NAME}-v{latest}.zip"\n        if archive_name != expected_archive_name:\n            raise UpdateError("RollPig Plus Release 插件 ZIP 名称与版本不匹配")\n        download_url = str(archive_asset.get("browser_download_url") or "")\n        expected_prefix = (\n            f"https://github.com/{self.OFFICIAL_REPOSITORY}/releases/download/"\n        )\n        if not download_url.startswith(expected_prefix):\n            raise UpdateError("Release 资源地址不属于官方仓库")\n'''
if old not in text:
    raise SystemExit("archive selection block not found")
text = text.replace(old, new, 1)

old = '''    @staticmethod\n    def _select_archive_asset(assets: list[Any]) -> dict[str, Any] | None:\n        candidates = [\n            item\n            for item in assets\n            if isinstance(item, dict)\n            and str(item.get("name") or "").lower().endswith(".zip")\n            and "rollpig" in str(item.get("name") or "").lower()\n        ]\n        if not candidates:\n            return None\n        candidates.sort(\n            key=lambda item: (\n                "astrbot_plugin_rollpig" not in str(item.get("name") or "").lower(),\n                "rollpig" not in str(item.get("name") or "").lower(),\n                str(item.get("name") or ""),\n            )\n        )\n        return candidates[0]\n'''
new = '''    @classmethod\n    def _select_archive_asset(cls, assets: list[Any]) -> dict[str, Any] | None:\n        prefix = f"{cls.PACKAGE_NAME}-v".lower()\n        candidates = [\n            item\n            for item in assets\n            if isinstance(item, dict)\n            and str(item.get("name") or "").lower().startswith(prefix)\n            and str(item.get("name") or "").lower().endswith(".zip")\n        ]\n        if not candidates:\n            return None\n        candidates.sort(key=lambda item: str(item.get("name") or ""))\n        return candidates[0]\n\n    @classmethod\n    def _select_release_payload(cls, releases: list[Any]) -> dict[str, Any]:\n        candidates: list[tuple[tuple[int, int, int], dict[str, Any]]] = []\n        for item in releases:\n            if not isinstance(item, dict) or item.get("draft") or item.get("prerelease"):\n                continue\n            tag = str(item.get("tag_name") or "")\n            try:\n                version = cls._normalise_version(tag)\n            except UpdateError:\n                continue\n            assets = item.get("assets") if isinstance(item.get("assets"), list) else []\n            archive = cls._select_archive_asset(assets)\n            if not archive:\n                continue\n            if str(archive.get("name") or "") != f"{cls.PACKAGE_NAME}-v{version}.zip":\n                continue\n            candidates.append((cls._version_tuple(version), item))\n        if not candidates:\n            raise UpdateError("未找到可验证的 RollPig Plus 稳定 Release")\n        candidates.sort(key=lambda entry: entry[0], reverse=True)\n        return candidates[0][1]\n'''
if old not in text:
    raise SystemExit("archive helper block not found")
text = text.replace(old, new, 1)

old = '''    async def _request_json(self, url: str) -> dict[str, Any]:\n        raw = await self._request_bytes(\n            url,\n            max_bytes=self.MAX_JSON_BYTES,\n            accept="application/vnd.github+json, application/json",\n        )\n        try:\n            payload = json.loads(raw.decode("utf-8"))\n        except (UnicodeError, json.JSONDecodeError) as exc:\n            raise UpdateError("GitHub 返回了无效 JSON") from exc\n        if not isinstance(payload, dict):\n            raise UpdateError("GitHub Release 响应格式无效")\n        return payload\n\n'''
new = '''    async def _request_json(self, url: str) -> dict[str, Any]:\n        raw = await self._request_bytes(\n            url,\n            max_bytes=self.MAX_JSON_BYTES,\n            accept="application/vnd.github+json, application/json",\n        )\n        try:\n            payload = json.loads(raw.decode("utf-8"))\n        except (UnicodeError, json.JSONDecodeError) as exc:\n            raise UpdateError("GitHub 返回了无效 JSON") from exc\n        if not isinstance(payload, dict):\n            raise UpdateError("GitHub Release 响应格式无效")\n        return payload\n\n    async def _request_json_list(self, url: str) -> list[Any]:\n        raw = await self._request_bytes(\n            url,\n            max_bytes=self.MAX_JSON_BYTES,\n            accept="application/vnd.github+json, application/json",\n        )\n        try:\n            payload = json.loads(raw.decode("utf-8"))\n        except (UnicodeError, json.JSONDecodeError) as exc:\n            raise UpdateError("GitHub 返回了无效 JSON") from exc\n        if not isinstance(payload, list):\n            raise UpdateError("GitHub Releases 响应格式无效")\n        return payload\n\n'''
if old not in text:
    raise SystemExit("request json block not found")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
