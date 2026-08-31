# RollPig legacy 收斂契約

`legacy_main.py` 是歷史相容層，不再是新功能的落點。P2 的目標不是一次重寫，而是在保持現有玩法、SQLite／JSON 資料與 AstrBot handler 邊界不變的前提下，讓它只能逐步縮小。

## Shrink-only budget

以 2026-08-31 的 `main` 為基線：

- `legacy_main.py` 上限：**286,646 bytes**；
- `tests/test_legacy_shrink_budget.py` 會在完整 pytest 中強制檢查；
- 任何讓檔案超過上限的 PR 都應直接失敗，而不是提高上限；
- 每次把一段 legacy 實作移到正式模組後，應把測試中的上限同步降低到新的實際大小。

## 新代碼應放哪裡

- AstrBot command decorator／薄入口：`main.py`；
- 單一玩法或生命週期 orchestration：獨立 `*_feature.py`／mixin；
- 純 domain 規則：`services/`；
- 圖片輸出：`renderers/`；
- SQLite／JSON 權威資料與 migration：`storage/`；
- 跨功能但不屬於 Star 入口的純工具：獨立模組。

若某次修改確實必須碰 `legacy_main.py`，優先採「搬出多於新增」：完成後檔案總大小仍需低於當前 budget，並保留／新增對應 boundary regression。

## 不做的事

這個契約不要求：

- 一次性重寫 `RollPigPlugin`；
- 為了降 bytes 而壓縮可讀性、刪註解或合併行；
- 把 legacy 依賴整個 plugin instance 的問題直接搬進新的 service；
- 改變既有玩家指令、玩法、資料 schema 或 release contract。

它只建立一條不可逆邊界：**技術債可以被消化，但不能重新長回去。**
