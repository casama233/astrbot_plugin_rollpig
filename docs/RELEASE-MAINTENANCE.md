# PR 與發版維護門禁

本頁記錄 `astrbot_plugin_rollpig` 的維護契約。目標是避免功能已經進入 `main`，但 Changelog、Wiki 或 Release Notes 仍停留在上一版的情況。

## PR 必須維護 Changelog

所有合併到 `main` 的 PR 都必須修改 `CHANGELOG.md`。

一般功能／修復 PR：

- 在 `## 未發佈` 下新增至少一條非占位記錄；
- 不能只保留「暫無」；
- CI 會比較 PR base/head，確認本 PR 確實新增了記錄，而不是只依賴之前 PR 留下的內容。

Release PR：

- `metadata.yaml` 版本變更時，`CHANGELOG.md` 必須存在對應 `## vX.Y.Z`；
- 必須在同一個 PR 新增或維護 `.github/release-vX.Y.Z.md`；
- 缺任何一項都不能通過發版門禁。

## 每個 PR 都必須聲明 Wiki 影響

PR 描述必須包含其中一種：

```text
Wiki-Impact: updated
```

或：

```text
Wiki-Impact: none — 這裡寫至少一句具體原因
```

`updated` 代表本 PR 已同步修改 `docs/**/*.md`。

`none` 只適用於確實不改變使用者／管理員可見語義的內部工作，例如純測試、CI 或不改行為的重構。不能只寫 `none`，必須說明理由。

## 指令與配置是硬性 Wiki 契約

以下兩類改動不能使用 `Wiki-Impact: none`：

### canonical 指令增刪

`main.py` 中 `@filter.command(...)` 的 canonical 指令集合若有變化：

- PR 必須同步修改 `docs/COMMANDS.md`；
- 新增 canonical 指令必須真的出現在 `docs/COMMANDS.md`；
- CI 還會掃描整個 Wiki，確認目前所有 canonical 指令至少有一處 Wiki 覆蓋。

### `_conf_schema.json` 配置鍵增刪

配置 schema 若有變化：

- PR 必須同步修改 `docs/CONFIGURATION.md`；
- 新增配置鍵必須真的出現在配置文檔；
- CI 與 Release gate 會再次確認目前所有 schema 鍵都有配置文檔覆蓋。

## 使用者可見修改的 Wiki 判定

CI 會把聊天指令、玩法 feature、renderer、管理頁、服務層、資源內容等視為可能影響使用者的修改。

這類 PR 必須明確完成一次 Wiki 判定：

- 行為、限制、指令、配置、管理方式或排障方式有變 → 更新對應 Wiki，使用 `Wiki-Impact: updated`；
- 純內部實作且對外語義不變 → 可以使用 `Wiki-Impact: none — <原因>`。

這個設計刻意不靠檔名猜測「一定需要改哪一頁」；除指令與配置兩個可機械驗證的硬契約外，其他行為修改由 PR 明確聲明，讓判定本身留下可審查記錄。

## CI 如何阻止漏維護 PR

`.github/workflows/ci.yml` 的 Python 3.12 job 會執行：

```bash
python scripts/maintenance_contract.py pr \
  --base <pull-request-base-sha> \
  --head <pull-request-head-sha> \
  --event "$GITHUB_EVENT_PATH"
```

同一個 job 還會執行：

```bash
python scripts/maintenance_contract.py coverage
```

因此現有 `test (3.12)` 檢查會直接因 Changelog／Wiki 契約失敗而變紅，不需要再依賴維護者人工記憶。

## Release 還有第二道保險

`.github/workflows/release.yml` 在建立 ZIP、Tag 與 GitHub Release **之前**會執行：

```bash
python scripts/maintenance_contract.py release
```

它會再次確認：

1. `metadata.yaml` 是穩定 `x.y.z`；
2. `CHANGELOG.md` 有目前版本段落；
3. `.github/release-vX.Y.Z.md` 存在且非空；
4. `CHANGELOG.md` 仍保留 `## 未發佈`；
5. canonical 指令在 Wiki 有覆蓋；
6. `_conf_schema.json` 所有配置鍵在 `docs/CONFIGURATION.md` 有覆蓋。

所以即使有人繞過正常 PR 流程直接修改 `main`，缺少發版文檔也不會產生新的穩定 Release。

## PR 模板

新 PR 會自動帶出 `.github/pull_request_template.md`，其中包含：

- Changelog 維護勾選項；
- Wiki 檢查勾選項；
- `Wiki-Impact` 聲明位置；
- Validation 區域。

模板是提醒，真正的強制來源仍是 CI 與 Release gate。
