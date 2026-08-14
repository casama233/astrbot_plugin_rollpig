# v3.4 公共豬源兼容下限與恢復流程

## 背景

v3.4.0 將預設資源源由舊 Felis 公共源切換到 AstrBot 專用的
`https://curryudon.top/astrbot-rollpig/v1/manifest.json`。新源最初卻只由插件內置的
99 隻小豬建立，沒有把切源前舊預設源的完整 catalog 一併帶入，因此部分已被玩家
抽到的小豬仍保留在 ownership / snapshot，卻從 active catalog 與圖片源消失。

這不是玩家收藏資料遺失，而是 **v3.4.0 source cut-over 的內容縮水回歸**。

## 固定兼容基線

不得跟隨 Felis 倉庫最新 `main`。兼容基線固定為 v3.4.0 發佈前最後一個公開 RollPig
快照：

- repository: `Felis2026/rollpig-resources`
- commit: `17ac1586a91c33995883803a55e2f755047f6e1f`
- resource version: `2026-08-10.1`
- `rollpig/pig.json` SHA-256:
  `687a491e541869cf1ef4f495e9189cf358a0d68655d1f780395a482113bc8be8`

`miku-pig`、`wechat-pig`、`duke-pig` 是 CI 的兼容哨兵；真正的契約不是只有這三隻，
而是 **上述固定快照中的所有 ID 都不得被官方源靜默刪除**。

## 合併語義

官方源的 canonical catalog 使用：

```text
frozen pre-v3.4 compatibility floor
              ∪
current AstrBot canonical catalog
```

同 ID 衝突時，以目前 AstrBot canonical catalog 的資料與圖片為準。固定舊快照只填補
缺失 ID，不會把舊文案／舊圖片覆蓋到目前版本，也不會把 Felis 在切源之後新增的內容
自動帶進官方抽池。

`scripts/prepare_resource_catalog.py` 會驗證固定快照的 resource version 與 `pig.json`
SHA-256，任何錯誤、變造或誤用最新分支都直接失敗；合併後寫出
`compatibility_floor.json`，記錄完整 compatibility ID 集。

## CI 建構

`AstrBot Resource Source` workflow 會：

1. checkout 本倉庫；
2. 以完整 commit SHA checkout 固定 Felis 快照；
3. 合併 compatibility floor 與 `resource/`；
4. 用既有 `build_resource_source.py` 做全量資料／圖片／SHA 驗證；
5. 驗證輸出 ID 是 compatibility floor 的超集；
6. 額外檢查 `miku-pig`、`wechat-pig`、`duke-pig`；
7. 同時輸出可部署 public release 與已合併的 canonical catalog Artifact。

因此 GitHub 上的 Felis `main` 後續新增／刪除內容不會改變本專案兼容基線。

## 正式環境一次性恢復

正式來源服務的 canonical catalog 位於：

```text
/opt/1panel/www/sites/curryudon.top/index/astrbot-rollpig/catalog
```

public root 位於：

```text
/opt/1panel/www/sites/curryudon.top/index/astrbot-rollpig
```

先在伺服器取得固定快照，**必須 checkout 指定 SHA**：

```bash
rm -rf /tmp/rollpig-resources-compat
git clone https://github.com/Felis2026/rollpig-resources.git /tmp/rollpig-resources-compat
git -C /tmp/rollpig-resources-compat checkout --detach 17ac1586a91c33995883803a55e2f755047f6e1f
```

先 dry-run：

```bash
cd /opt/rollpig-source-review
python3 migrate_public_source_compat.py \
  --catalog-root /opt/1panel/www/sites/curryudon.top/index/astrbot-rollpig/catalog \
  --compat-root /tmp/rollpig-resources-compat/rollpig \
  --publish-root /opt/1panel/www/sites/curryudon.top/index/astrbot-rollpig \
  --version 2026.08.14.compat1 \
  --dry-run
```

確認輸出的 `restored_count` / `restored_ids` 合理後，再移除 `--dry-run` 執行正式遷移。
工具會：

- 保留現有 canonical 同 ID 內容；
- 補回固定基線中缺失的小豬與原圖；
- 全量調用正式 builder 驗證；
- 建立新的不可變 `releases/<version>`；
- 把舊 canonical 移到 `catalog-backups/`；
- 原子切換 `v1` symlink；
- 任一步驟失敗時恢復原 canonical，並刪除未完成 release。

遷移後不需要修改玩家 ownership，也不需要重建 EX count。相同 ID 重新進入 active catalog
後，既有 `count`、首次解鎖時間與歷史 snapshot 會自然繼續使用。

## 驗證

正式切換後至少驗證：

```bash
curl -fsS \
  -H 'User-Agent: AstrBot-RollPig/3.6.3' \
  -H 'X-RollPig-Client: astrbot_plugin_rollpig_plus' \
  -H 'X-RollPig-Protocol: 1' \
  https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

再以同樣標頭取得 `pig.json`，確認 compatibility floor 全部存在，並在一個實際 AstrBot
實例執行資源同步。原先被顯示為「歷史收藏」的 `miku-pig`、`wechat-pig`、`duke-pig`
等 ID 應重新成為 active catalog 成員並恢復圖片。

## 以後的發布契約

- 不得用目前 `resource/` 的數量作為「可以縮水」的依據。
- 不得把 Felis 最新 `main` 當 compatibility baseline。
- 官方公共源的新 release 必須是固定 compatibility floor 的超集。
- 若未來確實要退役某個歷史 ID，必須設計明確的管理員 tombstone / retirement 流程，
  不能靠漏檔或重建 catalog 達成。
- v3.5+ 正式投稿服務以 live canonical catalog 為持續來源；不要用未合併 compatibility
  floor 的舊 99-pig seed 覆寫正式 canonical catalog。
