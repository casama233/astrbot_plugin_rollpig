# 今日小豬 · 增強版 v3.11.1

這是一個 README／市場展示相容性 patch，不改插件玩法或資料。

## 修復

- Logo 改用 GitHub Raw 絕對 URL，修復 AstrBot Cloud 等第三方 Markdown 渲染器的相對圖片破圖。
- 首屏文檔導航改用 GitHub 絕對 URL，避免第三方站點錯誤解析相對路徑。
- 新增 Minecraft 主題動態訪問量組件。
- 明確維護規範：沒有重大變更時一律只增加 patch 版本 `+0.0.1`。

## 相容性

可由 v3.11.0 直接升級；運行時、SQLite schema、Resource Protocol、指令、配置與玩法規則均不變。
