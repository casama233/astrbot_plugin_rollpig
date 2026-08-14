# 今日小豬 · 增強版 v3.6.5

這是一個穩定性與安全性 patch，重點收口群組日報的 opt-in 行為、收藏身份 fragment 的安全讀取，以及公共源人工審核的圖片／重複提示／服務端防護。

## 修復與加固

- 群組自動日報預設關閉；僅群主、群管理員或 AstrBot 管理員在群內 `/豬圈日報 開啟` 後才會自動推送，並提供 `關閉` / `狀態`。
- 自動日報不再跨自然日；今天才 opt-in 的群不補發更早日期。
- 修正 16 種豬各出現 1 次時硬選「最熱門」的誤導；歷史只有總量、缺人物事件明細的烤豬統計會明確披露。
- 修復公共源審核圖片只顯示 🐽 fallback；review list/image 增加 same-origin + CSRF。
- 審核頁新增名稱近似與 dHash 圖片疑似重複提示；模糊相似只供人審，不自動拒絕。
- 公共投稿增加全局 pending 200 上限，review service 增加更嚴格 systemd sandbox。
- 新增 claim-aware `CollectionService`：只合併已證明屬於同一 logical user 的 ownership；同豬 count 取 max，舊 fragment 不回灌 duplicate streak／總抽取／活躍天數，避免虛增 EX 或保底。

## 升級

可由 v3.6.4 直接更新。無 SQLite migration，無 EX／保底／烤豬概率／Resource Protocol 變更。

> 維護公共源審核服務的主機還需同步新版 `source_service/app.py` 與 `deploy/rollpig-source-review.service` 才能啟用服務端 duplicate/security hardening；一般插件安裝不需要做此步驟。
