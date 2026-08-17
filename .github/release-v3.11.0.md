# 今日小豬 · 增強版 v3.11.0

v3.11.0 集中完成三條管理端收斂：總覽 Analytics 語義與視覺、主管理 EX 預覽一致性，以及公共豬源審核權限邊界。

## 主要更新

- **管理面板大翻修**：累計值與短期趨勢分離、14 日活躍範圍明確、熱門小豬改為緊湊排行榜；AI 文案健康改為未啟用／無樣本／生成中／完成樣本四態，成功率只統計完成樣本。
- **EX 主管理入口對齊**：主管理 modal 補齊實際生效圖片、待保存圖片模擬、移除後回退、Base ↔ EX 對比與頁內 lightbox，並加入雙入口 parity 回歸契約。
- **公共豬源審核收緊**：只有具有效 maintainer token 的安裝才註冊 review proxy routes 並掛載審核 UI；普通安裝不再暴露審核 DOM 或管理路由，token 本身不回傳前端。

## 相容性

- 可由 v3.10.0 直接升級。
- SQLite schema、Resource Protocol、抽豬概率、保底、EX 等級與稀疏繼承規則均不變。
- 若運行中新增公共豬源 maintainer token，需要重新啟動插件以註冊審核路由；移除 token 時前端 capability 會立即撤銷。

## 驗證

#147、#148、#149 的來源分支門禁已通過；v3.11.0 Release PR 會再次在最終整合樹上執行 CI、pytest、pre-commit、Marketplace Package 與 AstrBot Market Smoke。
