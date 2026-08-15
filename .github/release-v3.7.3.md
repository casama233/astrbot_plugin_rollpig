# 今日小豬 · 增強版 v3.7.3

> **這次不加新玩法，專心把兩個明顯的介面回歸收乾淨。**
>
> v3.7.3 是 v3.7.2 的穩定性 hotfix：修回 AstrBot 主管理入口，並修正 Wiki v3 首頁在手機上的裁切問題。

## 🐷 豬圈管理重新成為預設入口

新增 EX 獨立 Plugin Pages 後，AstrBot 會按 Page 目錄名排序，側欄又直接打開第一個 Page；原本的 `ex-manager` 因此排在 `pig-manager` 前面，造成點擊「今日小豬」時先進 EX 成長管理，看起來像原本的數據總覽、豬豬圖鑑與本地資源整頁消失。

本版已把入口順序重新固定為：

1. `pig-manager` — 豬圈管理（預設）
2. `pig-manager-ex` — EX 成長管理
3. `pig-manager-ex-public-source` — EX 公共源

原主管理頁的數據統計、豬豬管理、本地／雲端資源與既有管理功能都沒有被刪除；這次只是修正 AstrBot 的預設 Page 選擇結果。

同時加入回歸測試，之後再新增 Plugin Page 時，如果 `pig-manager` 被擠出第一位，CI 會直接失敗。

> 如果你曾經手動收藏舊的 `ex-manager` / `ex-public-source` Plugin Page 深鏈，升級後請改用新的 Page 名稱；從 AstrBot 正常 UI 進入不需要額外操作。

## 📱 Wiki v3 手機版不再被切掉右半邊

修正首頁 Hero 被 intrinsic / min-content 寬度反向撐開、再被 `overflow: hidden` 裁掉的問題。

本版新增最後載入的 mobile containment layer，並針對 900 / 600 / 430px 斷點收斂：

- Hero grid 改用 `minmax(0, 1fr)`；
- Hero 內容、console、CTA、徽章與 live strip 補上安全的 `min-width: 0` / `max-width: 100%`；
- kicker、CTA、badge 可以正常換行；
- 小螢幕 Hero padding、標題字級與 CTA 重新收斂；
- 430px 以下 HUD stats 收成單欄。

桌面版 Wiki v3 的原視覺與動畫保留不變。

## 🧪 發版驗證

合併前的完整整合 revision 已通過：

- Python 3.10 / 3.12 CI
- Piggy Wiki strict build / rendered checks
- Marketplace Package
- AstrBot Market Smoke
- 當前官方 AstrBot plugin load worker

發版 PR 會再對最新 `main` 執行完整門檻；合併後由既有 Release workflow 自動建立 `v3.7.3` tag、ZIP 與 `SHA256SUMS`。

## ⬆️ 升級

可由 **v3.7.2 直接升級**。

本版不修改：

- SQLite schema
- 永久收藏 / EX 成長算法
- 新豬保底概率
- 60 / 30 / 10 烤豬概率
- Roast Charge 核心規則
- Resource Protocol 公開契約

正常透過 AstrBot 插件更新或 GitHub Release ZIP 升級即可。
