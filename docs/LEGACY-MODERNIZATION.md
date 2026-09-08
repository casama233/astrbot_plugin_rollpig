# RollPig legacy 收斂契約

`legacy_main.py` 是歷史相容層，不再是新功能的落點。P2 的目標不是一次重寫，而是在保持現有玩法、SQLite／JSON 資料與 AstrBot handler 邊界不變的前提下，讓它只能逐步縮小。

## Shrink-only budget

最初以 2026-08-31 的 `main` 為基線（286,646 bytes）；2026-09-09 抽離資源同步設定正規化後降低上限：

- `legacy_main.py` 上限：**279,565 bytes**；
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

## 已抽離的資源同步設定

`services/resource_settings.py` 是同步間隔、下載逾時、系統代理布林值及單檔大小限制的唯一正規化位置；它只接收設定映射並回傳不可變的設定值，不持有插件物件、不讀寫檔案。`legacy_main.py` 保留既有屬性名稱，負責接上執行期；來源地址遷移與公共鏡像封鎖仍由原有邊界處理。

本次沒有改設定鍵、預設值、容錯或上下限。後續可以逐塊抽離其他責任，每一塊仍須保留行為回歸，不把整個插件物件轉交新服務。

## 已抽離的資源暫存交易

`services/resource_staging.py` 接收下載／圖片驗證函式、目錄及大小限制，負責受限並發、實際包大小、檔名與引用完整性及目錄切換失敗恢復；不持有插件物件。同步被取消時，先終止並等待下載任務及已開始的檔案寫入，再讓入口清理暫存目錄。

本輪第四批以設定正規化與資源暫存交易兩個獨立邊界收口。入口保留來源選擇、manifest 協議、同步鎖、狀態保存與目錄快取重載。管理 API 已委派既有 storage／updater manager，這次保留授權及 HTTP 包裝；更大範圍的繼承／前端重寫不屬於本輪修復。
