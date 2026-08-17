from pathlib import Path

updater = Path("updater.py")
text = updater.read_text(encoding="utf-8")

old_constants = '''    RELEASES_API = (
        "https://api.github.com/repos/casama233/astrbot_plugin_rollpig/releases?per_page=30"
    )
'''
new_constants = '''    LATEST_RELEASE_API = (
        "https://api.github.com/repos/casama233/astrbot_plugin_rollpig/releases/latest"
    )
    RELEASES_API = (
        "https://api.github.com/repos/casama233/astrbot_plugin_rollpig/releases?per_page=30"
    )
'''
if old_constants not in text:
    raise SystemExit("updater release constant block not found")
text = text.replace(old_constants, new_constants, 1)

old_check = '''    async def _check_unlocked(self) -> dict[str, Any]:
        releases = await self._request_json_list(self.RELEASES_API)
        payload = self._select_release_payload(releases)

        tag = str(payload.get("tag_name") or "")
'''
new_check = '''    async def _fetch_stable_release_payload(self) -> dict[str, Any]:
        # Prefer GitHub's dedicated latest-release endpoint so a stale or empty
        # collection response cannot hide a valid stable Release.
        latest_error = ""
        try:
            latest_payload = await self._request_json(self.LATEST_RELEASE_API)
            return self._select_release_payload([latest_payload])
        except UpdateError as exc:
            latest_error = str(exc)
            if self.logger is not None:
                try:
                    self.logger.warning(
                        "RollPig updater latest-release lookup failed; falling back to release list: %s",
                        exc,
                    )
                except Exception:
                    pass

        try:
            releases = await self._request_json_list(self.RELEASES_API)
            return self._select_release_payload(releases)
        except UpdateError as exc:
            detail = f"latest={latest_error or 'unknown'}; list={exc}"
            raise UpdateError(
                f"未找到可验证的 RollPig Plus 稳定 Release（{detail}）"
            ) from exc

    async def _check_unlocked(self) -> dict[str, Any]:
        payload = await self._fetch_stable_release_payload()

        tag = str(payload.get("tag_name") or "")
'''
if old_check not in text:
    raise SystemExit("updater _check_unlocked block not found")
text = text.replace(old_check, new_check, 1)

old_headers = '''        headers = {
            "Accept": accept,
            "User-Agent": "AstrBot-RollPig-Safe-Updater/3.6.5",
            "X-GitHub-Api-Version": "2022-11-28",
        }
'''
new_headers = '''        headers = {
            "Accept": accept,
            "User-Agent": "AstrBot-RollPig-Safe-Updater/3.11.3",
            "X-GitHub-Api-Version": "2022-11-28",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
'''
if old_headers not in text:
    raise SystemExit("updater request header block not found")
text = text.replace(old_headers, new_headers, 1)
updater.write_text(text, encoding="utf-8")

test_text = '''import asyncio
from pathlib import Path

import pytest

from updater import PluginUpdateManager, UpdateError


def _manager(tmp_path: Path) -> PluginUpdateManager:
    plugin = tmp_path / "plugin"
    data = tmp_path / "data"
    plugin.mkdir()
    data.mkdir()
    (plugin / "metadata.yaml").write_text(
        'name: "astrbot_plugin_rollpig_plus"\\nversion: "3.11.2"\\n',
        encoding="utf-8",
    )
    return PluginUpdateManager(plugin, data)


def _release(version: str = "3.11.3") -> dict:
    archive = f"astrbot_plugin_rollpig_plus-v{version}.zip"
    base = "https://github.com/casama233/astrbot_plugin_rollpig"
    return {
        "draft": False,
        "prerelease": False,
        "tag_name": f"v{version}",
        "html_url": f"{base}/releases/tag/v{version}",
        "assets": [
            {
                "name": archive,
                "browser_download_url": f"{base}/releases/download/v{version}/{archive}",
            }
        ],
    }


def test_updater_uses_latest_endpoint_when_release_list_would_be_empty(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    calls = []

    async def fake_json(url):
        calls.append(("json", url))
        return _release()

    async def fake_list(url):
        calls.append(("list", url))
        return []

    monkeypatch.setattr(manager, "_request_json", fake_json)
    monkeypatch.setattr(manager, "_request_json_list", fake_list)

    payload = asyncio.run(manager._fetch_stable_release_payload())
    assert payload["tag_name"] == "v3.11.3"
    assert calls == [("json", manager.LATEST_RELEASE_API)]


def test_updater_falls_back_to_release_list_when_latest_is_not_verifiable(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    calls = []

    async def fake_json(url):
        calls.append(("json", url))
        return {"tag_name": "v3.11.3", "draft": False, "prerelease": False, "assets": []}

    async def fake_list(url):
        calls.append(("list", url))
        return [_release("3.11.2")]

    monkeypatch.setattr(manager, "_request_json", fake_json)
    monkeypatch.setattr(manager, "_request_json_list", fake_list)

    payload = asyncio.run(manager._fetch_stable_release_payload())
    assert payload["tag_name"] == "v3.11.2"
    assert calls == [
        ("json", manager.LATEST_RELEASE_API),
        ("list", manager.RELEASES_API),
    ]


def test_updater_reports_both_release_channels_when_neither_is_usable(tmp_path, monkeypatch):
    manager = _manager(tmp_path)

    async def fake_json(_url):
        return {"tag_name": "v3.11.3", "draft": False, "prerelease": False, "assets": []}

    async def fake_list(_url):
        return []

    monkeypatch.setattr(manager, "_request_json", fake_json)
    monkeypatch.setattr(manager, "_request_json_list", fake_list)

    with pytest.raises(UpdateError, match="latest=.*list="):
        asyncio.run(manager._fetch_stable_release_payload())


def test_latest_release_endpoint_is_the_primary_channel():
    assert PluginUpdateManager.LATEST_RELEASE_API.endswith("/releases/latest")
    assert PluginUpdateManager.RELEASES_API.endswith("/releases?per_page=30")
'''
Path("tests/test_updater_latest_release_endpoint.py").write_text(test_text, encoding="utf-8")

metadata = Path("metadata.yaml")
metadata_text = metadata.read_text(encoding="utf-8")
if 'version: "3.11.2"' not in metadata_text:
    raise SystemExit("expected metadata version 3.11.2 not found")
metadata.write_text(
    metadata_text.replace('version: "3.11.2"', 'version: "3.11.3"', 1),
    encoding="utf-8",
)

changelog = Path("CHANGELOG.md")
changelog_text = changelog.read_text(encoding="utf-8")
marker = "## v3.11.2"
if marker not in changelog_text:
    raise SystemExit("v3.11.2 changelog marker missing")
_, tail = changelog_text.split(marker, 1)
release_section = '''# 更新

## 未發佈

- 暫無。

## v3.11.3

發佈日期：2026-08-17

v3.11.3 是管理面板安全更新器修復版。它修正「GitHub 已有有效穩定 Release，但更新面板誤報未找到可驗證 Release」的發布發現故障，不修改玩法或資料契約。

### 安全更新器

- 更新檢查改以 GitHub 官方 `releases/latest` 作為主通道，仍保留 Release collection 作相容 fallback；不再因 collection 回傳空列表或陳舊結果而把有效 Latest Release 判定為不存在。
- `latest` 回應仍必須通過既有嚴格驗證：stable SemVer、非 draft／prerelease、官方倉庫 Release URL、精確的 `astrbot_plugin_rollpig_plus-vX.Y.Z.zip` 名稱與官方下載 URL；安全邊界沒有放寬。
- GitHub 請求加入 `Cache-Control: no-cache`／`Pragma: no-cache`，降低中間快取讓更新檢查讀到過期 Release metadata 的風險。
- 當 latest 與列表兩個通道都不可用時，錯誤訊息會同時保留兩邊的失敗原因，方便定位網路／Release 資料問題。
- 新增回歸測試，直接覆蓋「latest 有效但 releases list 為空」這次實際故障型態，以及 latest 無效時的 fallback 行為。

### 升級提示

- v3.11.0–v3.11.2 的舊更新器本身依賴出問題的 Release collection；如果面板已出現「未找到可驗證的 RollPig Plus 穩定 Release」，需要先透過 AstrBot 插件市場／重新安裝或手動覆蓋 v3.11.3 完成一次引導升級。升到 v3.11.3 後，面板安全更新通道即可恢復正常。

### 相容性

- 可由 v3.11.0、v3.11.1、v3.11.2 直接升級。
- 不修改 SQLite schema、Resource Protocol、指令、配置、抽取／保底／EX／烤豬規則或管理 API。

'''
changelog.write_text(release_section + marker + tail, encoding="utf-8")

release_notes = '''# 今日小豬 · 增強版 v3.11.3

這是一個管理面板安全更新器修復版，不修改插件玩法或資料契約。

## 修復

- 更新檢查改以 GitHub `releases/latest` 為主通道，Release collection 僅作 fallback，修復 GitHub 已存在有效 Release 時仍誤報「未找到可驗證的 RollPig Plus 穩定 Release」。
- 保留完整 Release 身份／SemVer／資產名稱／官方下載地址／SHA-256 驗證，不降低安全更新邊界。
- GitHub metadata 請求加入 no-cache headers，降低中間快取造成的陳舊 Release 判定。
- 新增 latest 有效但列表為空、latest 無效回退列表、雙通道診斷等回歸測試。

## 重要升級提示

如果 v3.11.0–v3.11.2 已經出現「未找到可驗證的 RollPig Plus 穩定 Release」，舊更新器無法靠自己取得這個修復；請先透過 AstrBot 插件市場／重新安裝或手動覆蓋 v3.11.3 完成一次引導升級。之後面板安全更新會恢復正常。

## 相容性

可由 v3.11.0–v3.11.2 直接升級；SQLite schema、Resource Protocol、指令、配置、玩法與管理 API 均不變。
'''
Path(".github/release-v3.11.3.md").write_text(release_notes, encoding="utf-8")
