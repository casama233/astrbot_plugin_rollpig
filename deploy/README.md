# RollPig 公共源審核服務部署

`rollpig-source-review.service` 使用 `source_service/app_v2.py` 作為入口。`app_v2.py` 是 EX-aware 相容層，仍以既有 `source_service/app.py` 為公共源 v1 協議與基礎投稿實作，因此部署時兩個檔案必須一起存在。

## 必要檔案

建議部署目錄：

```text
/opt/rollpig-source-review/
├── app.py
├── app_v2.py
└── build_resource_source.py
```

對應倉庫來源：

```text
source_service/app.py                 -> /opt/rollpig-source-review/app.py
source_service/app_v2.py              -> /opt/rollpig-source-review/app_v2.py
scripts/build_resource_source.py      -> /opt/rollpig-source-review/build_resource_source.py
```

`app.py` 在倉庫內運行時會優先 import `scripts.build_resource_source`；部署到獨立目錄時會安全回退到同目錄的 `build_resource_source.py`。

## 更新服務

把上述三個檔案更新到同一版本後，再安裝／更新 unit：

```bash
install -m 0644 deploy/rollpig-source-review.service \
  /etc/systemd/system/rollpig-source-review.service
systemctl daemon-reload
systemctl restart rollpig-source-review.service
systemctl status --no-pager rollpig-source-review.service
```

不要只更新 `app_v2.py` 而保留舊版 `app.py` 或 builder；EX envelope v2 的審核與發布仍會調用既有 v1 基礎服務及資源 builder。

## 相容與資料

- Resource Protocol 仍為 v1。
- 舊的 base-only 投稿仍使用既有 `submissions` 表，不需要資料庫遷移。
- EX 投稿使用 sidecar `submission_ex` 表與 `state-root/variant-images/`；首次啟動 `app_v2.py` 會自動建立，不修改舊 `submissions` schema。
- 正式發布仍採 candidate catalog -> `build_source()` 驗證 -> catalog 原子切換 -> `v1` symlink 原子替換。
- `public_source_admin.token` 仍由 systemd unit 指定的 `--admin-token-file` 讀取，不應複製到倉庫或前端。

## 最小健康檢查

服務重啟後至少確認：

```bash
curl -fsS http://127.0.0.1:17841/healthz
```

然後從 AstrBot 管理頁檢查：

1. 舊版／無 EX 的基礎投稿仍能進入待審核隊列。
2. EX 投稿顯示 `Envelope v2`、EX 差分與 EX 圖片。
3. 拒絕不改動正式 `v1` 資源。
4. 批准後基礎豬與 EX 差分在同一新 resource version 中出現。
