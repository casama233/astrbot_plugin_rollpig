# 今日小豬 · 增強版 v3.6.4

這是一個穩定性 patch，集中修復公共豬源切換造成的歷史內容縮水，以及 QQ/NapCat/NTQQ 圖片已送達後 ACK timeout 被誤判失敗的問題。

## 修復

- 恢復 v3.4 切源前完整兼容下限：固定 Felis `17ac1586a91c33995883803a55e2f755047f6e1f` 快照的 199 個 ID 作為官方源最低兼容集合；目前 AstrBot canonical 同 ID 內容優先。
- 官方 Resource Source CI 現在會拒絕任何低於固定 compatibility floor 的發布，並驗證 `miku-pig`、`wechat-pig`、`duke-pig` 等回歸哨兵。
- `/我的豬圈` 對 NTQQ `retcode=1200`、`NodeIKernelMsgService/sendMsg` ACK timeout 不再重試或誤報「生成失敗」；圖片可能已經投遞時只記錄 warning。
- 真正的圖鑑渲染失敗與真正的圖片發送失敗分開處理；永久圖鑑頁碼按完整 display catalog 校驗。

## 升級

可由 v3.6.3 直接更新。無 SQLite migration，無玩家收藏重建，無 EX / 保底 / 烤豬概率變更。

本版仍不包含 PR #68 identity-fragment merge，也不包含烤箱 charge/refill 新玩法。
