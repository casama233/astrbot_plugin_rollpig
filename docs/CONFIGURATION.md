# ⚙️ 配置參考：管理員調參，豬圈照規矩運轉

本文件對應當前分支的 `_conf_schema.json` 與運行時的數值夾取邏輯。建議直接透過 AstrBot 的插件配置介面進行調整；除非你非常熟悉配置的載入機制，否則請勿直接手動修改運行時檔案。

> 本頁的 SQLite 停止載入／JSON 預檢保護屬於未發佈維護變更，不代表 v3.12.1 已有此行為。正式可安裝版本以 GitHub 穩定 Release 為準。

> 文案雖然可以充滿豬言豬語，但**數值、權限、機率與儲存邏輯絕不開玩笑**。填入超出範圍的數值通常會被程式自動限制在安全區間內，但仍請盡量依照本文列出的有效範圍設定。

## 🐣 每日抽取、豬籍與保底

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `at_view_pig` | bool | `false` | bool | 允許使用 `/今日小豬 @某人` 進行純讀取查看，不會替對方代抽小豬 |
| `enable_new_pig_pity` | bool | `true` | bool | 當連續抽到已解鎖的小豬時，逐步提高觸發條件式新豬重抽的機率 |
| `pity_step_percent` | int | `15` | `0-50` | 每累積一層 `duplicate_streak` 所增加的機率百分點 |
| `enable_daily_duplicate_pity` | bool | `true` | bool | 額外開啟跨自然日連抽重複保底補償（重複疲勞機制） |
| `daily_duplicate_pity_start_day` | int | `2` | `2-7` | 連續幾天抽到重複豬後，從第幾天開始疊加跨日補償 |
| `daily_duplicate_pity_step_percent` | int | `5` | `0-25` | 跨日重複疲勞每一層額外增加的機率百分點 |
| `daily_duplicate_pity_max_percent` | int | `15` | `0-50` | 跨日補償自身的機率上限；與基礎保底加總後，最終仍共同封頂於 80% |
| `timezone` | string | `local` | IANA / `local` | 用來判定跨日邊界的基準時區，例如 `Asia/Hong_Kong` |

跨日重複疲勞只會沿著**相鄰的自然日**往回推算；只要中間漏抽一天、成功開出新豬，或是找不到有效紀錄，跨日連擊鏈就會當場中斷。同一天內重複查詢 `/今日小豬` 並不會疊加層數。原本的 `duplicate_streak` 與跨日疲勞屬於兩套獨立計算的狀態，最後才會合併結算，但最終觸發條件式新豬重抽的總機率絕不會超過 80%。

## 🔥 群聊後廚開火、Roast Charge 能量與烤豬預約

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `enable_roast` | bool | `true` | bool | 烤豬玩法總開關 |
| `enable_group_roast` | bool | `true` | bool | 統管群聊開烤、預約蹲點、隨機開吃、後門與烤箱補貨的總控開關 |
| `group_roast_max_charges` | int | `2` | `1-5` | **每位玩家在每個群組中**各自獨立計算的 Roast Charge 最大能量上限；發起普通群烤或建立預約各自消耗 1 格 |
| `group_roast_cooldown_hours` | float | `8` | `1-72` | **每消耗一格 Charge 後的自然回充時間**；失去的能量會按排隊順序逐格慢慢回滿，而非一次性統一冷卻 |
| `enable_roast_reservation` | bool | `true` | bool | 針對當天還沒抽豬的指定群友，在該群組建立當日烤豬預約 |
| `roast_reservation_max_participants` | int | `12` | `2-20` | 每張烤豬預約單的參與人數上限（包含發起預約的固定主廚在內） |
| `enable_roast_protection` | bool | `true` | bool | 當某位群友昨日在同群被烤過頭後，今日在普通後廚玩法中獲得冷靜保護 |
| `roast_protection_threshold` | int | `3` | `1-20` | 昨日在同群被成功烤到累積達幾次後，今日就會自動觸發保護機制 |
| `enable_group_eat` | bool | `true` | bool | 直接開吃指定群友，或交由系統隨機挑一位群友開吃 |
| `eat_success_percent` | int | `15` | `1-80` | 開吃群友的基礎成功率；一旦失手，發起者自己反而會淪為被「吃掉」的一方 |
| `eaten_next_day_failure_percent` | int | `20` | `1-80` | **相容舊版設定鍵名**：今天不幸被吃掉後，隔天抽豬若命中此機率，會強制從已解鎖圖鑑中抽出一隻重複豬；新版不再直接判定抽豬失敗或鎖定整天 |
| `enable_ai_roast_copy` | bool | `false` | bool | 嘗試呼叫當前對話的 AI 模型來即時撰寫料理風味文案 |
| `ai_generation_timeout_seconds` | float | `45` | `5-120` | AI 生成料理文案的等待逾時秒數；若發生錯誤或逾時則自動切換回本地預設文案 |

### Charge 語義

`group_roast_cooldown_hours` 為了相容舊版設定檔名稱而保留了 `cooldown` 的字樣，但目前實際代表的意義是「**每缺一格 Charge 的獨立回充週期**」。以預設的 2 格上限與 8 小時為例：

```text
剛連用兩格   0 / 2
+ 8 小時     1 / 2
+16 小時     2 / 2
```

只有把 `group_roast_max_charges` 調整為 1 時，整體體感才會接近舊版「一次耗光後整段時間統一冷卻」的節奏。

### 預約烤豬流程

第一位發起預約的主廚輸入 `/烤群友 @未抽目標` 建立預約單並先支付 1 格 Charge；建立完成當下，主廚本人即計為第 1 位參與者。

後續跟車圍觀的玩家：

- **優先推薦**使用 `/添柴 @目標` 指令跟單；
- 若直接再次輸入 `/烤群友 @同一目標` 系統也依然相容支援；
- 跟車加入並不會額外消耗自己的 Charge；
- 等到目標群友稍後抽豬觸發預約開烤時，系統也不會再扣除主廚的第二格能量；
- 後續添柴加碼的參與人數多寡，並不會影響原本共用的成功 70%、逃脫 20% 或反噬 10% 結算規則。

單獨輸入不帶參數的 `/添柴` 還會依據當下群聊情境自動分流：若正在進行烤箱補貨則優先響應補貨；若無補貨且場上僅有一張預約單則直接加入該單；若同時存在多張預約單，系統會要求明確指定 `@目標`。

## ⛽ 群體烤箱能量補貨

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `enable_oven_refill` | bool | `true` | bool | 開啟 `/烤箱補貨` 指令與補貨情境自動判讀 `/添柴` |
| `oven_refill_daily_limit` | int | `2` | `1-5` | 每個群組每天最多可成功結算並封帳的補貨輪數上限 |
| `oven_refill_support_ratio_percent` | int | `30` | `1-100` | 發起補貨當下，依據該群今日活躍玩家人數計算所需應援人數的基礎比例 |
| `oven_refill_min_supporters` | int | `3` | `2-20` | 一般情況下的最低應援人數門檻；若是 2 人以下的迷你小群，則固定只需 2 人響應 |
| `oven_refill_max_base_supporters` | int | `8` | `3-50` | 單輪補貨所需基礎應援人數的最高上限 |
| `oven_refill_extra_supporters_per_success` | int | `2` | `0-10` | 同一個群組同一天每成功完成一輪補貨，下一輪所需應援人數就會額外增加的人數 |
| `oven_refill_round_timeout_minutes` | int | `120` | `5-720` | 單輪補貨的有效倒數時間（TTL）；時間一到仍未湊齊人數便自動失效關閉，需要重新發起 |

應援人數門檻在 `/烤箱補貨` 發起那一刻就會直接鎖定，本輪倒數期間才新加入的活躍玩家並不會重新拉高已公告的門檻。順利達標結算時，系統仍會從當下的活躍玩家中篩選符合條件且尚缺 Charge 的成員，每人最多回補 +1 格。

萬一在啟動結算發放的過程中遭遇資料庫寫入異常或程式中斷，系統會採取「直接封帳、絕不重播」的 fail-closed 保護機制，防止少數已經成功入帳的玩家在重試過程中重複領取 Charge。

## 📰 豬圈每日頭條日報

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `enable_daily_report` | bool | `true` | bool | 豬圈日報總開關；一旦關閉，無論手動查閱或排程自動推播都會全面停用 |
| `daily_report_auto_send` | bool | `true` | bool | 自動定時推播的總控制開關；**開啟此項並不代表所有群組都會自動訂閱** |
| `daily_report_send_time` | string | `23:50` | `HH:MM` | 依照 `timezone` 所設定的時區進行時間基準換算 |
| `daily_report_random_delay_minutes` | int | `10` | `0-60` | 抵達預定推播時間點後，額外加入的隨機延遲錯峰上限 |
| `daily_report_skip_empty_groups` | bool | `true` | bool | 若某群組當天完全沒有任何 RollPig 抽豬紀錄，則自動略過當日日報推播 |
| `daily_report_random_eat_enabled` | bool | `false` | bool | 選配的「今日祭品」環節；僅會在排程自動發送日報時觸發，玩家手動查詢日報永遠只做純讀取、不觸發結算 |
| `daily_report_avatar_enabled` | bool | `true` | bool | 生成稱號卡片時，嘗試抓取並顯示玩家的聊天平台頭像 |
| `daily_report_avatar_cache_hours` | int | `24` | `1-168` | 玩家頭像在本地端的快取有效時間 |

所有群組的自動日報預設皆為未訂閱狀態；就算全局開啟了 `daily_report_auto_send=true`，依然需要到各群內手動下指令開啟。目前群組層級的管理操作權限統一由 AstrBot 管理員身分判定。

## 🖼️ 視覺卡片日夜主題

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `image_theme` | string | `auto` | `auto` / `light` / `dark` | `auto` 模式下於 19:00–06:59 時段自動切換為夜間深色主題；時間判定以插件設定的每日時區為準 |

## ☁️ 雲端圖鑑與資源同步

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `resource_sync_enabled` | bool | `true` | bool | 自動從雲端同步 AstrBot 官方或私人小豬資源包；關閉此功能並不會刪除本地已快取的檔案 |
| `felis_direct_enabled` | bool | `true` | bool | 非商業 Bot 直接讀取 Felis 官方 34 項 overlay 並本機快取；關閉不刪既有快取 |
| `felis_direct_manifest_url` | string | Felis 官方 raw manifest | 固定官方 HTTPS URL | 只允許 `Felis2026/rollpig-resources` 官方 manifest，不作本站 CDN／公共 Manifest 鏡像 |
| `resource_manifest_url` | string | 官方 AstrBot v1 | HTTPS URL | 可替換為擁有存取權限的相容私人 manifest 網址；一旦自訂來源，系統將不再啟用官方備援線路 |
| `resource_vercel_mirror_url` | string | 官方 Vercel 鏡像節點位址 | HTTPS URL / 空字串 | 僅接受預設的官方鏡像網址，留空則關閉此節點；切換節點前會強制核對獨立批准清單與完整資源快照 |
| `resource_github_fallback_enabled` | bool | `true` | bool | 當主來源與 Vercel 節點皆無法連線時嘗試切換至 GitHub 節點，同樣須通過完整安全核驗 |
| `resource_github_mirror_url` | string | 官方 GitHub 鏡像節點位址 | HTTPS URL | 僅接受預設的官方鏡像網址；任何未經批准、已遭撤回或版本較舊的快照都會被拒絕載入 |
| `resource_sync_interval_hours` | float | `6` | `1-168` | 全新安裝時的預設自動檢查更新間隔；若原先已有明確設定則保留原有數值 |
| `resource_sync_timeout` | float | `30` | `2-120` | 網路請求連線逾時限制；下載圖片資源時另有較寬鬆的逾時下限與自動重試機制 |
| `resource_use_system_proxy` | bool | `false` | bool | 是否信任並套用系統環境變數中的代理伺服器設定；預設為直接連線 |
| `resource_max_file_size_mb` | int | `10` | `1-50` | 單一資源檔案的容量上限（單位 MiB），此限制同時套用於 PigHub 圖片匯入功能 |

預設 manifest：

```text
https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

v3.12.3 起，官方遠端鏈為主源 → 預設 Vercel → 預設 GitHub。鏡像只接受固定 GitHub 倉庫當前批准的 exact snapshot，包含來源、授權、EX 發布記錄及逐檔大小／SHA-256。批准表讀取失敗不啟用新鏡像；較舊版本不覆蓋本地新版。撤回被讀取後停用對應鏡像快取。自訂私人源仍不進入公共鏈，詳見 [公共災備邊界](PUBLIC-MIRROR-FAIL-CLOSED.md)。

舊 `pig.felislab.cc` 精確地址會遷移到 AstrBot 專用源；其他自訂 HTTPS 私人 manifest 不改寫，失敗時不偷偷切回官方公共鏈。同步成功只代表資源已驗證，不代表第三方素材取得新的再分發許可。

## 🔄 後台管理面板安全更新

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `panel_update_enabled` | bool | `true` | bool | 是否准許面板檢查並安裝本倉庫的穩定版 Release |
| `panel_update_timeout` | float | `30` | `5-120` | 檢查更新與下載時的網路超時上限 |

更新器不支援任意網址、自訂分支或預發布版本，且安裝完畢後不會自動重啟 AstrBot。

## 🗄️ 存儲

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `storage_backend` | string | `auto` | `auto` / `sqlite` / `json` | 推薦使用 `auto`（現有 SQL 異常時將中止載入）；`json` 僅限原生安裝或已完成對帳回滾的 JSON 環境 |
| `storage_busy_timeout_ms` | int | `5000` | `1000-30000` | 等待 SQLite 寫入鎖定的毫秒數 |

### `auto`

全新安裝會直接建立 SQLite 資料庫；若偵測到可讀取的舊版 JSON，系統會先備份再匯入臨時資料庫，確認完整性、外鍵與資料對帳無誤後才正式切換。首次遷移若在提交前出錯，原有的 JSON 檔案仍會完整保留；若來源 JSON 無法讀取則直接中止，絕不覆寫為空白預設值。

一旦現有的 SQLite 資料庫開啟或驗證失敗，插件會立刻停止載入，不會自動退回 JSON 模式。若資料庫檔案遺失，但仍留有 SQL 權威紀錄、紀錄無法核驗，或僅殘留 WAL／SHM 檔案，系統同樣不會將其視為全新安裝。中止載入期間插件工作台將無法使用，請參閱 [SQLite 恢復保護](SQLITE-RECOVERY.md) 並從 AstrBot 載入日誌排查原因。

### `sqlite`

延續與 `auto` 相同的資料保護機制，絕不強行掛載無法通過驗證的資料庫，也不會貿然用舊版或空白的 JSON 接管資料。

### `json`

此模式僅適用於純原生 JSON 安裝，或是已完成「SQL 匯出至 JSON、資料對帳並停用資料庫」的回滾環境。載入前會以唯讀方式解析現有的受管 JSON；若解析或讀取失敗便直接停擺，防止修復載入器寫入空白預設值。單純把設定改成 json 並無法繞過現存的 SQL 資料庫、權威紀錄或未清理的 WAL／SHM 檔案。

## 推薦設定範例

```json
{
  "at_view_pig": false,
  "enable_new_pig_pity": true,
  "enable_daily_duplicate_pity": true,
  "enable_roast": true,
  "enable_group_roast": true,
  "group_roast_max_charges": 2,
  "group_roast_cooldown_hours": 8,
  "enable_roast_reservation": true,
  "enable_oven_refill": true,
  "oven_refill_round_timeout_minutes": 120,
  "enable_group_eat": true,
  "enable_daily_report": true,
  "daily_report_random_eat_enabled": false,
  "image_theme": "auto",
  "timezone": "local",
  "storage_backend": "auto"
}
```

### 指定採用香港時區日界線

```json
{
  "timezone": "Asia/Hong_Kong"
}
```

## 修改設定後沒反應？

部分參數僅在插件初始化時讀取。請先到 AstrBot 管理後台重新載入插件；若依然無效，再嘗試重啟整個 AstrBot。鏡像網址僅接受官方預設值，重新載入並不會讓未獲批准或已撤回的快照通過驗證。詳細排查步驟請見 [OPERATIONS.md](OPERATIONS.md)。
