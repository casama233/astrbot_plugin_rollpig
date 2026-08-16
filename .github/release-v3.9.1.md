# 今日小豬 · 增強版 v3.9.1

v3.9.1 是 v3.9.0 的維護版本，集中修正 **管理面板迷你趨勢圖失真** 與 **動態幫助卡繁簡混排／字型問題**，不改遊戲規則、資料格式或資源協議。

## 管理面板

- 修正頂部 KPI mini sparkline 仍以 0 作固定 Y 軸基線，令全部為正值的時間序列被壓扁；現在按實際局部 min/max 自適應縮放，並為平坦／非平坦資料加入安全留白。
- sparkline 幾何統一由實際 `width / height / padding` 計算，移除硬編碼 area baseline；SVG stroke 使用 `non-scaling-stroke`，卡片尺寸變化時不再把線寬一起拉伸。
- 這些變更只影響管理頁視覺呈現，不修改任何統計值或分析口徑。

## 動態幫助卡

- `/豬豬幫助` 生成的快速指令卡固定使用 **簡體中文 `zh-CN`**：標題、分類、說明、頁尾與顯示命令全部統一為簡體。
- 顯示命令改用已註冊的簡體 canonical 命令，例如 `/今日小猪`、`/我的猪圈`、`/猪圈日报`、`/烤箱补货`。
- renderer 不再優先使用 `font_traditional`，幫助卡統一使用標準中文 `font_bold`，避免繁體專用字型造成缺字、錯字形或繁簡混排。
- 幫助圖片 cache version 升級，舊的繁體 bitmap 不會繼續命中。
- 繁體指令 alias 仍完整保留；玩家仍可輸入 `/今日小豬`、`/豬豬幫助` 等舊指令，只是不再顯示於生成圖片。

## Changelog 維護

- 修復 `CHANGELOG.md` 在 v3.6.5 之後的歷史斷檔：重新以已發佈的 `.github/release-v*.md` 為來源回填 v3.7.0～v3.9.0 正式版本紀錄。
- 「未發佈」區重新清空，避免已經上線的功能長期留在未發佈章節造成版本語義錯亂。

## 本版合入 PR

- #131 — 修正管理面板 KPI mini sparkline 的局部縮放與 SVG 幾何。
- #132 — 快速指令幫助卡固定簡體中文並移除繁體字型依賴。

## 相容性

可由 v3.9.0 直接升級。本版不改變：

- SQLite schema 與永久豬籍 authority
- Resource Protocol v1
- 抽豬概率、新豬保底與跨日疲勞保底
- EX 等級計算
- Roast Charge、60/30/10、`/添柴` 與預約結算規則

## 驗證

- Python 3.10 / 3.12 全量 CI
- Marketplace Package
- AstrBot Market Smoke
- 管理趨勢 UI contract
- 動態幫助、字體、cache 與 Wiki bridge contract
