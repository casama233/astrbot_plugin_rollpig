# 今日小豬 · 增強版 v3.11.3

這是一個管理面板安全更新器修復版，不修改插件玩法或資料契約。

## 修復

- 更新檢查改以 GitHub `releases/latest` 為主通道，Release collection 僅作 fallback，修復 GitHub 已存在有效 Release 時仍誤報「未找到可驗證的 RollPig Plus 穩定 Release」。
- 保留完整 Release 身份／SemVer／資產名稱／官方下載地址／SHA-256 驗證，不降低安全更新邊界。
- GitHub metadata 請求加入 no-cache headers，降低中間快取造成的陳舊 Release 判定。
- 新增 latest 有效但列表為空、latest 無效回退列表、雙通道診斷等回歸測試。

## 重要升級提示

如果 v3.11.0–v3.11.2 已經出現「未找到可驗證的 RollPig Plus 穩定 Release」，舊更新器無法靠自己取得這個修復；請先透過 AstrBot 插件市場／重新安裝或手動覆蓋 v3.11.3 完成一次引導升級。之後面板安全更新會恢復正常。

## 相容性

可由 v3.11.0–v3.11.2 直接升級；SQLite schema、Resource Protocol、指令、配置、玩法與管理 API 均不變。
