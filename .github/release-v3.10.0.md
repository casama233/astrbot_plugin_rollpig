# 今日小豬 · 增強版 v3.10.0

這是一個整合型功能版本，將目前仍有獨立價值的待合工作集中收斂並完成組合回歸。

## 主要更新

- **動畫 GIF 小豬端到端支援**：PigHub／手動上傳、EX 差分、公共豬源、審核與完整小豬卡均可保留動畫。
- **AI 小豬工坊**：復用 AstrBot AI Provider 批量策劃，支援圖鑑參考生圖、短期草稿、反饋重畫及確認後入庫。
- **EX 預覽升級**：實際生效圖片來源、未儲存模擬、Base ↔ EX 圖文對比與圖片放大。
- **群聊回覆識別**：RollPig 指令第一條群聊回覆會單獨標示發起者，原玩法目標提及不受影響。
- **烤豬與管理品質**：2,528 組內置烤豬文案、AI 候選池、KPI 趨勢語義修正、幫助 At 提示與更精簡的 CI。

## GIF 公共豬源配套

公共豬源服務端已同步升級到 **2.2.0**，保留基礎 GIF 與 EX GIF 的投稿、審核、catalog 與 Resource Protocol v1 發布鏈路。

## 安全與相容性

- 動畫 GIF 受檔案大小、尺寸、幀數及總時長限制。
- AI 小豬工坊不會把已保存的生圖 API Key 回傳瀏覽器，遠端生成圖限制為同源 HTTPS。
- SQLite schema、Resource Protocol v1、抽豬概率、保底、EX 等級與 Roast Charge 規則均不變。
- 可由 v3.9.1 直接升級。

## 驗證

整合分支在發版前完成 **453 項 pytest 全通過**及 **pre-commit 全通過**；正式 Release PR 另跑 Marketplace Package、AstrBot Market Smoke 與發布維護門禁。
