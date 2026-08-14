# AstrBot 插件市場上架指南

本文記錄 `astrbot_plugin_rollpig_plus` 的 AstrBot 官方插件市場發佈要求、專案側防線與提交資料。

> 依據 AstrBot 官方文件與 2026-06-27 Plugin Market JSON Specification 整理。若官方規範更新，以官方文件為準。

## 市場身份

AstrBot 市場以 `metadata.yaml` 中的 `author/name` 作為全局插件身份，而不是 GitHub 倉庫名稱。

本插件的固定身份為：

```text
casama233/astrbot_plugin_rollpig_plus
```

GitHub 倉庫仍為：

```text
https://github.com/casama233/astrbot_plugin_rollpig
```

請勿只為了讓倉庫名與插件名一致而再次修改 `author` 或 `name`；兩者屬於穩定包身份，變更會被視為不同插件。

## 必須滿足的發佈條件

- GitHub 公開倉庫可正常 clone。
- 根目錄包含有效的 `metadata.yaml`。
- 根目錄包含 `main.py` 或與插件 `name` 同名的 Python 入口。
- `metadata.yaml` 至少保持 `name`、`display_name`、`desc`、`version`、`author`、`repo` 完整且與實際發行版本一致。
- `repo` 使用 `https://github.com/{owner}/{repo}`，不以 `.git` 結尾。
- 第三方 Python 依賴寫入 `requirements.txt`。
- 市場分發 ZIP 不超過官方標示的 **16 MB**。
- 插件能在官方當前 AstrBot 環境中被 PluginManager 正常載入。
- 已充分測試，且不存在惡意程式碼。

## 本專案的體積策略

v3.2.0 的 Release ZIP 為 19,933,444 bytes，超過官方 16 MB 上限。v3.2.1 起採用以下市場分發策略：

- 不打包測試、開發配置與 Node 測試依賴資訊；README 導航所需的 `docs/` 隨包保留。
- 市場與 Release 精簡包不打包 `resource/font/HanyiYongZiXiaoXiongMaoFan.ttf` 與 `resource/font/荆南麦圆体.otf` 兩個大型、非核心字體。
- 兩個字體仍保留在 Git 倉庫，原始碼 clone / 開發環境不受影響。
- 精簡包保留 `可爱字体.ttf`、小豬圖片、資料、Plugin Pages 與全部運行程式碼；缺少裝飾/兜底字體時使用現有系統字體降級鏈。
- Release workflow 在上傳前檢查 ZIP 大小，超過 **16,000,000 bytes** 直接失敗。
- PR workflow 同樣建立市場尺寸的 ZIP 並使用相同保守上限，避免後續回歸。
- `.gitattributes` 使用 `export-ignore` 標記非市場運行所需內容，配合官方建議縮減來源封裝。

AI 烤豬文案功能預設為關閉；主要抽豬、圖鑑、群友互動、資源同步與管理面板功能不依賴繁體兜底字體。卡片名稱在精簡包缺少裝飾粗體時會回退到系統粗體候選。

## 建議提交資料

提交到 AstrBot 官方插件發佈頁時使用與 `metadata.yaml` 一致的資料：

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

市場卡片的短描述由 `metadata.yaml` 的 `short_desc` 提供：

```text
每日抽小豬、圖鑑收集、群友互動與可視化資源管理
```

## 發佈前檢查

1. CI 全部通過。
2. `metadata.yaml` 版本已更新，且為穩定 SemVer。
3. Release workflow 成功生成同版本 ZIP。
4. Release ZIP 小於等於 16,000,000 bytes。
5. Release ZIP 根目錄包含插件目錄，且其內至少有 `metadata.yaml`、`main.py`、`requirements.txt`。
6. 解壓後插件 `author/name/version` 與市場提交資料一致。
7. 在支持的 AstrBot 版本上完成一次安裝、啟動、抽取、圖鑑與管理頁基本 smoke test。
8. 確認 README / LICENSE / 原作者署名未被移除。

## 官方提交入口

優先使用 AstrBot 官方插件發佈頁提交。官方文件指出發佈需要 AstrBot Cloud 帳號。

官方 Plugins Collection 仍保留 `Plugin Publish` Issue Form；表單要求插件 JSON、已充分測試、無惡意程式碼及同意 GitHub Code of Conduct。
