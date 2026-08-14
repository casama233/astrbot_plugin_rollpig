# AstrBot 專用小豬源維護手冊

本文說明本專案如何產生、驗證、部署與回退 AstrBot RollPig Resource Protocol v1。

## 1. 對外端點

預設 manifest：

```text
https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

服務只接受同時具備以下條件的 `GET`／`HEAD` 請求：

- `User-Agent` 以 `AstrBot-RollPig/x.y.z` 開頭。
- `X-RollPig-Client: astrbot_plugin_rollpig_plus`。
- `X-RollPig-Protocol: 1`。

普通瀏覽器、其他插件和舊 nonebot 客戶端會收到 HTTP 403。

> 這是協議相容性閘門，不是密碼學身份認證。因插件原始碼公開，標頭可以被模仿；若來源必須只供少數私人實例使用，應在反向代理再加入各實例獨立、可撤銷的 Token 或 mTLS。

## 2. 來源結構

```text
manifest.json
health.json
pig.json
images/
  pig.png
  ...
# 可選 EX 成長差分
pig_ex_variants.json
ex_variants/
  pig-ex2.png
  ...
```

v1 manifest 除原有大小與 SHA-256 欄位外，新增：

```json
{
  "schema_version": 1,
  "client": "astrbot_plugin_rollpig_plus",
  "resource_version": "2026.08.14.1",
  "generated_at": "2026-08-14T05:00:00+08:00",
  "pig_count": 99,
  "package_size": 12969833
}
```

插件仍向下兼容未聲明 `schema_version`／`client` 的私人 manifest；本專案預設源則強制要求兩者正確。EX 成長使用 v1 的可選 `ex_variants`／`variant_images` 欄位，不需要提升協議版本；舊來源不提供時維持基礎圖與文案。

## 3. 建構與驗證

從倉庫根目錄執行：

```bash
python scripts/build_resource_source.py \
  --source resource \
  --output /tmp/rollpig-source-2026.08.14.1 \
  --version 2026.08.14.1
```

建構器會拒絕：

- 重複或不合法的小豬 ID。
- 缺少名稱、描述或完整文案的記錄。
- 缺圖、一個 ID 多圖或沒有對應資料的多餘圖片。
- 符號連結、無法解碼、超過 10 MiB 或超過像素上限的圖片。
- 超過 500 張基礎圖片，或超過 1000 張 EX 差分圖片的來源。
- EX 差分引用未知小豬、超出 Lv.1–5、使用非法欄位、缺圖或存在未引用差分圖片。

全部通過後才會原子建立輸出目錄，並為 `pig.json`、可選 `pig_ex_variants.json` 與每張基礎／差分圖片生成大小和 SHA-256。

GitHub 的 `AstrBot Resource Source` workflow 會在資源或建構器變更時重建並保存 14 天的可部署 Artifact。

## 4. 正式部署

建議保留不可變版本目錄，只原子切換 `v1` 符號連結：

```text
/www/sites/curryudon.top/index/astrbot-rollpig/
  releases/
    2026.08.14.1/
  v1 -> releases/2026.08.14.1
```

OpenResty 規則範本位於 `deploy/rollpig-source.nginx.conf`。部署順序：

1. 產生新的版本目錄。
2. 逐一核對 manifest 內的大小與 SHA-256。
3. 將版本目錄複製到 `releases/`，不要覆寫既有版本。
4. 建立新的臨時符號連結，再原子替換 `v1`。
5. 執行 OpenResty 配置檢查，通過後才 reload。
6. 驗證無標頭為 403、錯誤客戶端為 403、AstrBot v1 標頭為 200。
7. 用插件手動同步一次，確認完整 99 張圖片通過校驗並切換成功。

## 5. 更新與回退

每次內容改變都必須使用新的 `resource_version`，不可原地修改舊版本目錄。

若新來源出現問題：

1. 把 `v1` 連結切回上一個 `releases/<version>`。
2. reload OpenResty 並重新驗證端點。
3. 插件同步失敗時會保留原有 active 快取，不會清空圖鑑。
4. 修正資源後使用另一個新版本號重新發佈。

## 6. 公共投稿審核服務

v3.5.0 起公共源不是只讀靜態目錄。插件管理員可向固定端點提交本地小豬，維護者在自己的 AstrBot 管理面板完成審核：

```text
POST /astrbot-rollpig/api/v1/submissions
GET  /astrbot-rollpig/api/v1/admin/submissions?status=pending
GET  /astrbot-rollpig/api/v1/admin/submissions/<id>/image
POST /astrbot-rollpig/api/v1/admin/submissions/<id>/review
```

服務實作位於 `source_service/app.py`，OpenResty 與 systemd 範本分別位於：

- `deploy/rollpig-source-api.nginx.conf`
- `deploy/rollpig-source-review.service`

### 權限邊界

- 投稿只要求正確 AstrBot Client／Protocol／版本標頭，每個來源 24 小時最多 5 次。
- 審核端點另要求高熵 Bearer Token；Token 只保存在來源服務與維護者插件資料目錄的 `public_source_admin.token`。
- Token 不可寫進 Git、`_conf_schema.json`、瀏覽器儲存、前端響應或日誌。
- 普通插件實例沒有 Token，面板自動隱藏審核區，但仍可投稿。

### 批准發佈流程

1. 服務校驗 ID、名稱、描述、完整文案、Base64 與圖片像素，統一轉為 `512×512 PNG`。
2. SQLite 保存待審核資料、圖片 SHA-256、客戶端版本與經 HMAC 處理的來源指紋；不保存原始來源地址。
3. 維護者批准後，在同一把審核鎖內複製 canonical catalog、加入記錄與圖片，再調用正式建構器做全量驗證。
4. 建立新的不可變 `releases/<resource_version>`，備份 canonical catalog，最後以臨時符號連結原子替換 `v1`。
5. 發佈或目錄切換失敗會恢復原 catalog；服務啟動時還會對齊「已發佈但資料庫未及時更新」的極短崩潰窗口。

拒絕操作只更新審核狀態與備註，不改動公共目錄。日常備份應同時涵蓋 canonical catalog、`releases/`、`catalog-backups/`、審核 SQLite 與投稿圖片。

## 7. 私人實例加固

若不希望所有 AstrBot 增強版使用者共用來源，可在此協議閘門之外加入：

- 每個實例獨立 Token，支援撤銷與輪換。
- 限速、請求日誌與異常流量告警。
- IP allowlist（僅適合固定出口地址）。
- mTLS（適合少量、完全受控的伺服器）。

不要把全體客戶端共用的秘密直接寫進公開插件倉庫。
