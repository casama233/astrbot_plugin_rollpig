# ⚙️ 配置參考：管理員調參，豬圈照規矩運轉

本文對應目前 `_conf_schema.json` 與運行時夾取邏輯。推薦透過 AstrBot 插件配置介面修改；除非你清楚配置載入方式，否則不要直接手改運行時文件。

> 文案可以豬言豬語，**數值、權限、概率和存儲語義不跟著開玩笑**。超出範圍的值通常會被程式夾到安全區間，但仍請使用本文列出的有效值。

## 🐣 每日抽取、豬籍與保底

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `at_view_pig` | bool | `false` | bool | 允許 `/今日小豬 @某人` 只讀查看；不替對方抽豬 |
| `enable_new_pig_pity` | bool | `true` | bool | 連續抽到已解鎖小豬後逐步提高條件式新豬重抽機會 |
| `pity_step_percent` | int | `15` | `0-50` | 每層 `duplicate_streak` 增加的百分點 |
| `enable_daily_duplicate_pity` | bool | `true` | bool | 額外啟用跨自然日重複疲勞 |
| `daily_duplicate_pity_start_day` | int | `2` | `2-7` | 從第幾個連續重複日開始追加跨日加成 |
| `daily_duplicate_pity_step_percent` | int | `5` | `0-25` | 跨日每層追加百分點 |
| `daily_duplicate_pity_max_percent` | int | `15` | `0-50` | 跨日部分自己的上限；與原保底合計仍共同封頂 80% |
| `timezone` | string | `local` | IANA / `local` | 每日邊界時區，如 `Asia/Hong_Kong` |

跨日疲勞只沿**相鄰自然日**回溯；中間漏抽、抽到新豬或沒有有效記錄都會截斷跨日鏈。同一天重查 `/今日小豬` 不增加層數。原 `duplicate_streak` 與跨日疲勞是兩套狀態，最後一起算，但條件式新豬重抽率不超過 80%。

## 🔥 群聊後廚、Roast Charge 與預約

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `enable_roast` | bool | `true` | bool | 烤豬總開關 |
| `enable_group_roast` | bool | `true` | bool | 群烤、預約、隨機、後門與補貨的上層開關 |
| `group_roast_max_charges` | int | `2` | `1-5` | **每位玩家 × 每個群**獨立持有的最大 Roast Charge；普通群烤／建立預約各消耗 1 格 |
| `group_roast_cooldown_hours` | float | `8` | `1-72` | **每缺一格 Charge 的自然恢復時間**；缺失能量按隊列逐格恢復，不是整段單一冷卻 |
| `enable_roast_reservation` | bool | `true` | bool | 對尚未抽豬的明確目標建立本群當日預約 |
| `roast_reservation_max_participants` | int | `12` | `2-20` | 每張預約最大參與人數，包含固定主廚 |
| `enable_roast_protection` | bool | `true` | bool | 昨日同群實際被烤過多後，今日普通後廚受保護 |
| `roast_protection_threshold` | int | `3` | `1-20` | 昨日同群被成功烤到多少次後觸發今日保護 |
| `enable_group_eat` | bool | `true` | bool | 吃群友／隨機吃群友 |
| `eat_success_percent` | int | `15` | `1-80` | 吃群友成功率；失敗時發起者自己變「吃掉了」 |
| `eaten_next_day_failure_percent` | int | `20` | `1-80` | **兼容舊鍵名**：今天被吃後，次日抽豬命中此概率時強制從已解鎖池抽一隻重複豬；不再抽取失敗或鎖天 |
| `enable_ai_roast_copy` | bool | `false` | bool | 嘗試請當前會話模型生成料理文案 |
| `ai_generation_timeout_seconds` | float | `45` | `5-120` | AI 文案超時；失敗／超時回退本地模板 |

### Charge 語義

`group_roast_cooldown_hours` 為了兼容舊配置名保留了 `cooldown` 字樣，但現在實際意思是「**每一格缺失 Charge 的恢復週期**」。例如預設 2 格、8 小時：

```text
剛連用兩格   0 / 2
+ 8 小時     1 / 2
+16 小時     2 / 2
```

把 `group_roast_max_charges` 設為 1，才會近似舊版一次用完等整段時間的節奏。

### 預約烤豬

第一位主廚 `/烤群友 @未抽目標` 建立預約並支付 1 格 Charge。建立時主廚已經算第 1 位參與者。

後續玩家：

- **推薦** `/添柴 @目標`；
- 再次 `/烤群友 @同一目標` 仍保留相容；
- 加入不消耗自己的額外 Charge；
- 目標之後觸發預約時不再扣主廚第二格；
- 添柴人數目前不增加 60/30/10 成功率。

裸 `/添柴` 還會依上下文路由：補貨進行中優先補貨；沒有補貨且只有一張預約時加入該預約；多張預約則要求 `@目標`。

## ⛽ 群體烤箱補貨

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `enable_oven_refill` | bool | `true` | bool | 啟用 `/烤箱補貨` 與補貨上下文 `/添柴` |
| `oven_refill_daily_limit` | int | `2` | `1-5` | 每群每天可封帳的成功補貨次數 |
| `oven_refill_support_ratio_percent` | int | `30` | `1-100` | 發起當刻按今日活躍人數計算的基礎比例 |
| `oven_refill_min_supporters` | int | `3` | `2-20` | 一般最低支持人數；2 人小群固定需要 2 人 |
| `oven_refill_max_base_supporters` | int | `8` | `3-50` | 基礎支持門檻上限 |
| `oven_refill_extra_supporters_per_success` | int | `2` | `0-10` | 同群同日每成功一輪後，下一輪增加的人數 |
| `oven_refill_round_timeout_minutes` | int | `120` | `5-720` | 單輪 TTL；超時未達標就關閉，需重新發起 |

門檻在 `/烤箱補貨` 發起當刻固定，本輪進行中新加入的活躍玩家不會重算已公示門檻。達標時仍按當刻活躍玩家挑選符合條件且缺 Charge 的對象，最多各補 +1 格。

若結算已啟動後遇到存儲錯誤或進程中斷，採「封帳而不重播」的 fail-closed 策略，避免少數已成功寫入的人在重試時再次領到 Charge。

## 📰 豬圈日報

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `enable_daily_report` | bool | `true` | bool | 日報總開關；關閉後手動／自動都停止 |
| `daily_report_auto_send` | bool | `true` | bool | 自動推送 master switch；**不等於所有群自動訂閱** |
| `daily_report_send_time` | string | `23:50` | `HH:MM` | 以 `timezone` 對應時區計算 |
| `daily_report_random_delay_minutes` | int | `10` | `0-60` | 定時點之後的隨機延遲上限 |
| `daily_report_skip_empty_groups` | bool | `true` | bool | 當天沒有 RollPig 抽取活動的群跳過自動日報 |
| `daily_report_random_eat_enabled` | bool | `false` | bool | 可選「今日祭品」；只可能在自動日報流程觸發，手動查看永遠只讀 |
| `daily_report_avatar_enabled` | bool | `true` | bool | 稱號卡嘗試顯示平台頭像 |
| `daily_report_avatar_cache_hours` | int | `24` | `1-168` | 頭像本地快取時間 |

每個群的自動日報預設未訂閱；即使 `daily_report_auto_send=true`，仍需群內明確開啟。當前群級管理權限由 AstrBot 管理員判定。

## 🖼️ 卡片主題

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `image_theme` | string | `auto` | `auto` / `light` / `dark` | `auto` 在 19:00–06:59 走夜間主題；依插件每日時區判定 |

## ☁️ 資源同步

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `resource_sync_enabled` | bool | `true` | bool | 自動同步 AstrBot／私人小豬資源；關閉不刪既有快取 |
| `resource_manifest_url` | string | 官方 AstrBot v1 | HTTPS URL | 可改成有權使用的相容私人 manifest；自訂後不啟用官方備援鏈 |
| `resource_vercel_mirror_url` | string | 官方 Vercel 鏡像 | HTTPS URL / 空字串 | 僅預設官方源失敗時使用；留空停用 Vercel 層 |
| `resource_github_fallback_enabled` | bool | `true` | bool | Vercel 也失敗時是否再嘗試公開 GitHub 快照 |
| `resource_github_mirror_url` | string | 官方 GitHub 鏡像 | HTTPS URL | GitHub 最終災備 manifest，通常不需修改 |
| `resource_sync_interval_hours` | float | `6` | `1-168` | 新安裝自動檢查間隔；既有明確配置保持原值 |
| `resource_sync_timeout` | float | `30` | `2-120` | 連線超時；圖片讀取另有較寬下限與重試 |
| `resource_use_system_proxy` | bool | `false` | bool | 是否信任系統代理環境；預設直連 |
| `resource_max_file_size_mb` | int | `10` | `1-50` | 單資源文件上限（MiB），亦用於 PigHub 圖片導入 |

預設 manifest：

```text
https://curryudon.top/astrbot-rollpig/v1/manifest.json
```

使用預設官方源時，故障轉移固定為 **curryudon 主源 → Vercel 驗證快照 → GitHub 公開快照 → 最近一次已驗證本地快取／內置資源**。備用源的 `schema_version`、`client`、大小與 SHA-256 仍走同一套校驗；數字版 `resource_version` 低於本地版本時拒絕降級。舊 `pig.felislab.cc` 精確地址會遷移到 AstrBot 專用源；其他自訂 URL 不擅自改寫，也不會被偷偷串到官方備援鏈。詳見 [RESOURCE-MANAGEMENT.md](RESOURCE-MANAGEMENT.md)。

## 🔄 管理面板安全更新

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `panel_update_enabled` | bool | `true` | bool | 是否允許面板檢查／安裝本倉庫穩定 Release |
| `panel_update_timeout` | float | `30` | `5-120` | 更新檢查與下載相關網路超時 |

更新器不接受任意 URL、任意分支或預發布版本；安裝後不自動重啟 AstrBot。

## 🗄️ 存儲

| 配置鍵 | 類型 | 預設 | 範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `storage_backend` | string | `auto` | `auto` / `sqlite` / `json` | `auto` 推薦；新安裝直接 SQLite，舊 JSON 先備份、遷移、對帳；`json` 只建議災難回退 |
| `storage_busy_timeout_ms` | int | `5000` | `1000-30000` | SQLite 寫鎖等待毫秒數 |

### `auto`

新安裝直接建 SQLite；舊 JSON 先備份後匯入臨時 DB，通過完整性／外鍵／事實對帳才切換。失敗保留恢復證據，不拿壞資料硬頂上去。

### `sqlite`

明確偏好 SQLite，但「資料安全優先」仍高於強制打開損壞 DB。

### `json`

僅作緊急災難回退，不建議當正常長期模式。

## 推薦配置範例

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

### 明確使用香港日界線

```json
{
  "timezone": "Asia/Hong_Kong"
}
```

## 改完沒生效？

部分設定在插件初始化時讀入。先在 AstrBot 管理介面重新載入插件；仍沒變再重啟 AstrBot。更深排查見 [OPERATIONS.md](OPERATIONS.md)。
