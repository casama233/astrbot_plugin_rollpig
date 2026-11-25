# AstrBot 插件市場上架指南

本文件詳細記錄了 `astrbot_plugin_rollpig_plus` 遵循的 AstrBot 官方插件市場發佈規範、專案側安全防線以及上架所需的提交資料。

> 本說明彙整自 AstrBot 官方文件與 2026-06-27 Plugin Market JSON Specification。若官方規範有所調整，請一律以官方最新文件為準。

## 插件市場專屬身份

AstrBot 插件市場係透過 `metadata.yaml` 內的 `author/name` 欄位來辨識全局唯一身份，而非直接採用 GitHub 倉庫名稱。

本插件於市場註冊的固定識別名稱為：

```text
casama233/astrbot_plugin_rollpig_plus
```

對應的 GitHub 原始碼倉庫位置仍為：

```text
https://github.com/casama233/astrbot_plugin_rollpig
```

切勿僅為了追求倉庫與插件同名，而擅自更動 `author` 或 `name`；這兩項屬於既定的套件識別碼，一旦修改將被系統判定為全新插件。

## 上架與發佈必備條件

- 公開的 GitHub 倉庫必須能順利執行 clone 取得完整內容。
- 倉庫根目錄下需備妥格式無誤的 `metadata.yaml` 檔案。
- 根目錄必須具備 `main.py`，或是與插件 `name` 同名的 Python 主程式入口。
- `metadata.yaml` 內至少要完整填寫 `name`、`display_name`、`desc`、`version`、`author` 與 `repo`，且各項數值須與實際發佈的版本相符。
- `repo` 需填寫 `https://github.com/{owner}/{repo}`，且末尾不可加上 `.git`。
- 所有外部第三方 Python 相依套件均須明確列於 `requirements.txt` 中。
- 上架分發的 ZIP 壓縮包總容量不得超過官方規定的 **16 MB** 上限。
- 插件必須能在當前官方版本的 AstrBot 環境下，由 PluginManager 順利載入並運行。
- 程式碼皆已通過完整測試驗證，且絕無夾帶任何惡意程式。

## 專案打包與體積控制策略

早期 v3.2.0 版本的 Release ZIP 曾超出 16 MB 限制。目前插件市場與 Release 工作流程已統一整合 `scripts/prepare_install_bundle.py --source`，並實施以下分發瘦身策略：

- 打包時會自動剔除測試腳本、開發環境設定、Node 測試套件以及 runtime `plugin_data`；僅保留 README 導覽列所需之 `docs/`。
- 透過 `scripts/prepare_install_bundle.py` 將完整的圖鑑編撰清單精簡為固定 **22 項**、圖文精準對應的離線基礎包（bootstrap）；待玩家首次啟動插件後，再從經過驗證的公共資源庫下載擴充內容。
- 市場與 Release 壓縮包僅收錄目前渲染器（renderer）優先調用的 `resource/font/荆南麦圆体.otf` 及其 OFL 授權聲明，並移除其餘閒置的 `HanyiYongZiXiaoXiongMaoFan.ttf`。
- Release 工作流程在執行上傳前會自動檢核 ZIP 檔案大小，凡超過 **16,000,000 bytes** 即刻中止並判定失敗；PR 自動化檢查亦套用相同的容量門檻。
- 現行正式流程產出的安裝包大小約為 **6 MB**，完整囊括了 `metadata.yaml`、`main.py`、`requirements.txt`、唯一的 `pig-manager` Plugin Page、22 項離線基礎資源以及中文渲染專用字體。

AI 烤豬文案產生器預設處於關閉狀態；核心的每日抽豬、小豬圖鑑、群友互動玩法、資源同步及管理後台皆可在離線基礎包（bootstrap）狀態下直接載入，即便外部公共源暫時無法連線，也完全不會影響插件正常啟動。

## 市場提交資料對照建議

前往 AstrBot 官方插件發佈頁面提交審核時，請填入與 `metadata.yaml` 完全一致的欄位資訊：

```json
{
  "name": "astrbot_plugin_rollpig_plus",
  "display_name": "今日小豬 · 增強版",
  "desc": "獨立維護的今日小豬增強版；提供永久圖鑑、群聊玩法、自建公共豬源投稿審核、本地資源分層、SQLite 安全存儲與管理面板",
  "author": "casama233",
  "repo": "https://github.com/casama233/astrbot_plugin_rollpig",
  "tags": ["娛樂", "群聊互動", "每日抽取", "圖鑑", "WebUI"],
  "social_link": "https://github.com/casama233"
}
```

插件市場卡片上顯示的簡短介紹，直接取自 `metadata.yaml` 內的 `short_desc` 欄位：

```text
每日抽小豬、圖鑑收集、群友互動與可視化資源管理
```

## 正式發佈前檢核清單

1. 所有持續整合（CI）自動化測試項目皆已綠燈通過。
2. `metadata.yaml` 內的版號已同步更新，並符合穩定的語意化版本（SemVer）規範。
3. Release 自動化流程已順利建置出對應相同版號的 ZIP 壓縮檔。
4. 產出的 Release ZIP 檔案大小確實小於或等於 16,000,000 bytes。
5. 解開 Release ZIP 後，根目錄下包含插件主資料夾，且資料夾內至少備齊 `metadata.yaml`、`main.py` 與 `requirements.txt`。
6. 壓縮包解壓後，插件內部的 `author/name/version` 設定內容與市場頁面提交的資料完全吻合。
7. 已在官方支援的 AstrBot 環境中，完整跑過一遍安裝、啟動、抽豬、瀏覽圖鑑及開啟管理後台的基礎冒煙測試（smoke test）。
8. 確認 README / LICENSE / 原作者署名未被移除。

## 官方上架與提交通道

建議優先透過 AstrBot 官方插件發佈頁面進行提交。依據官方說明，發佈流程需登入 AstrBot Cloud 帳號。請留意，GitHub 成功建立 tag 或發佈 Release 僅代表產出了可下載的檔案，並不會自動同步更新市場索引；開發者仍須親自前往官方發佈頁，為相同的 `author/name/version` 送出新版本資訊。

官方 Plugins Collection 倉庫目前仍保留 `Plugin Publish` Issue Form 提交通道；填寫表單時需檢附插件 JSON 資料、聲明已完成充分測試且無惡意程式碼，並勾選同意遵守 GitHub Code of Conduct。
