# EX 成長產品閉環驗收表

這份文件是 EX 成長能否宣稱「100% 完成」的 release gate。單一功能 PR 合併、單元測試通過或 UI 看起來可用，都不足以單獨滿足這個標準。

## 1. 核心語義

- [ ] `EX Lv. = max(0, count - 1)`，第一次解鎖為 EX0。
- [ ] EX 等級可高於 5；展示差分只配置 Lv.1–5，高於 5 使用最後有效差分。
- [ ] 圖片、`description`、`analysis` 逐欄位稀疏繼承。
- [ ] EX 不能修改 ID、名稱、抽取／保底或任何玩法身份。
- [ ] `/明日小豬` 不套用玩家既有 EX 收藏狀態。

自動化證據：`tests/test_ex_variants.py`、`tests/test_ex_growth_e2e.py`。

## 2. 真實玩家路徑

- [ ] 今日小豬套用當前 ownership EX。
- [ ] 歷史／昨日小豬套用當前 ownership EX。
- [ ] 本週小豬套用 EX。
- [ ] 永久豬圈顯示正確 EX Lv.、抽取次數與差分圖片。
- [ ] 料理卡／烤豬顯示玩家目前 EX 差分。
- [ ] 同一天重看今日小豬不重複寫入 `ex_level_up`。
- [ ] active EX 壞掉時安全回退 bundled EX，而不是污染 active 資源。

自動化證據：`tests/test_ex_growth_e2e.py`、既有 renderer／collection tests。

## 3. 官方內容

- [ ] bundled `resource/pig_ex_variants.json` 非空。
- [ ] 內建 EX pig ID 全都存在於 canonical `pig.json`。
- [ ] 每隻配置豬至少有一個真正可見的文字或圖片差分。
- [ ] 內建內容仍遵守 Lv.1–5、欄位白名單與稀疏繼承規則。

自動化證據：`tests/test_bundled_ex_content.py`。

## 4. 本地作者工作流

- [ ] 管理員可在 **EX 成長管理** Plugin Page 搜尋／選擇小豬。
- [ ] 可分級新增／修改／刪除 description、analysis、image。
- [ ] 實際生效預覽正確顯示各欄位最後繼承來源。
- [ ] 本地 EX 可持久化並在插件重載後恢復。
- [ ] 本地 EX 優先於 cloud／bundled EX。
- [ ] 只有 base local override 而沒有 local EX 時，公共 EX 仍被阻擋。
- [ ] local EX 圖片找不到／資料無效時不繞過 EX schema。

自動化證據：`tests/test_ex_admin_feature.py`。

手動 smoke：在測試 AstrBot 建立一個 EX1 文字差分與 EX2 圖片差分，重啟插件後確認頁面預覽與 `/今日小豬` 一致。

## 5. 公共源投稿／審核／發布

- [ ] base-only 舊投稿仍能以 envelope v1 建立、審核、發布。
- [ ] EX 投稿使用 envelope v2，但 Resource Protocol 保持 v1。
- [ ] 投稿只能帶目前小豬的 Lv.1–5 EX 差分。
- [ ] EX 圖片固定 `<pig-id>-ex<level>.png`；引用與實際提交集合必須完全一致。
- [ ] 審核員可在批准前查看 base 圖、base 文案、每級 EX 文案差分與 EX 圖片。
- [ ] reject 不改動 production catalog 或 `v1` symlink。
- [ ] approve 把 base + EX 放入同一 candidate catalog，`build_source()` 成功後才原子發布。
- [ ] `submission_ex` sidecar 不修改舊 `submissions` schema。

自動化證據：`tests/test_public_source_ex_review.py`、既有 `tests/test_public_source_review.py`。

部署 smoke：

1. 服務器同版部署 `app.py`、`app_v2.py`、`build_resource_source.py`。
2. `systemctl restart rollpig-source-review.service` 後 `/healthz` 成功。
3. 建立一筆 v1 base-only 投稿並拒絕。
4. 建立一筆 v2 EX 投稿，審核頁可看 EX 圖／文案。
5. 批准 v2 投稿後確認新 `v1/manifest.json` 同時包含新 pig 與 EX metadata。
6. 另一台插件同步正式源後能直接顯示該 EX 差分。

## 6. 玩家文案共享層

- [ ] 動態幫助的 section title、功能名稱與描述不再散落硬編碼。
- [ ] `zh-TW` / `zh-CN` 使用相同 semantic key 集合。
- [ ] 同 key 的 placeholder 集合完全一致。
- [ ] 缺 key 或缺 placeholder 明確失敗，不靜默拼錯文案。
- [ ] 保底、Charge、群體補貨、預約、日報、AI 烤豬、EX／公共源入口都在共享 help copy 中可被發現。

自動化證據：`tests/test_player_copy.py`、`tests/test_dynamic_help_system.py`。

> 這一 gate 代表「新系統的動態發現文案已建立可強制執行的共享層」，不是宣稱歷史 `legacy_main.py` 裡每一句舊提示都已完成全量 i18n 遷移。歷史文案可繼續逐步搬遷，但不能把已遷移的 help surface 再寫回 inline literal。

## 7. Release / CI gate

宣稱 EX 100% 完成前，必須同時滿足：

- [ ] EX PR 系列按依賴順序全部合併到 `main`，沒有只存在於 stacked branch 的功能。
- [ ] 合併後 `main` 的 pre-commit／pytest／AstrBot smoke／Marketplace smoke 都通過；若某個 workflow 在倉庫沒有啟用，release note 必須明確說明實際跑了哪些驗證，不能用「CI 全綠」代替。
- [ ] 公共源 production 主機已部署 EX-aware review service，而不只是倉庫裡存在 `app_v2.py`。
- [ ] production `v1/manifest.json` 可由新版插件正常同步。
- [ ] 從乾淨安裝到「抽中重複豬 → 看到 EX → 本地編輯 → 投稿 → 審核 → 批准 → 第二台同步」完成一次人工 smoke。
- [ ] `docs/EX-VARIANTS.md`、玩家 Wiki 與 CHANGELOG 和 production 行為一致。

## 8. Release 判定

只有第 1–7 節全部打勾後，release note / README 才可以使用：

> **EX 成長產品閉環 100% 完成**

在那之前應使用更精確的描述，例如：

> EX runtime / authoring / public-source workflow 已實作，正在完成合併與 production smoke。
