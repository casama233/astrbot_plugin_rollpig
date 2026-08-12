# 配置參考

本文對應 v3.2.0 的 `_conf_schema.json`。推薦透過 AstrBot 插件配置介面修改；除非你清楚 AstrBot 的配置載入方式，否則不要直接改寫運行時配置檔。

> [!NOTE]
> 程式會對數值配置再次做範圍夾取與類型容錯，因此超出範圍的值通常會被限制到安全區間；仍建議只填本文列出的有效值。

## 每日抽取與圖鑑

| 配置鍵 | 類型 | 預設 | 有效值／範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `at_view_pig` | bool | `false` | `true` / `false` | 允許 `/今日小豬 @某人` 只讀查看對方今日結果。對方未抽取時不會替對方抽。 |
| `enable_new_pig_pity` | bool | `true` | `true` / `false` | 啟用連續抽到已解鎖小豬後的「新豬保底」。 |
| `pity_step_percent` | int | `15` | `0-50` | 每連續重複一次，下一次重抽未解鎖小豬的概率增量百分點。設為 `0` 等同保留機制但不增加概率。 |
| `timezone` | string | `local` | IANA 時區或 `local` | 每日邊界時區，例如 `Asia/Hong_Kong`、`Asia/Shanghai`、`America/Los_Angeles`。`local` 使用伺服器系統時區。 |

### 時區建議

如果 AstrBot 主機時區與群友所在地不同，建議明確填 IANA 時區，而不是依賴 `local`。錯誤或未知時區會回退到系統時區並寫入警告日誌。

## 烤豬與群聊玩法

| 配置鍵 | 類型 | 預設 | 有效值／範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `enable_roast` | bool | `true` | `true` / `false` | 烤豬總開關；關閉後今日烤豬與烤群友相關流程不可用。 |
| `enable_group_roast` | bool | `true` | `true` / `false` | 群聊烤群友玩法開關，包括普通、隨機與後門口令。 |
| `enable_group_eat` | bool | `true` | `true` / `false` | 吃群友與隨機吃群友開關。 |
| `eat_success_percent` | int | `15` | `1-80` | 吃群友成功率。失敗時發起者會變成當天的「吃掉了」。 |
| `eaten_next_day_failure_percent` | int | `20` | `1-80` | 今天被成功吃掉後，次日第一次抽豬失敗的概率。若判定失敗，當天維持無法抽取直到下一日。 |
| `group_roast_cooldown_hours` | float | `8` | `1-72` | 普通烤群友按「發起者 + 群組」計算的冷卻時間。後門口令可繞過。 |
| `enable_roast_protection` | bool | `true` | `true` / `false` | 啟用「昨日被烤過多 → 今日保護」機制。 |
| `roast_protection_threshold` | int | `3` | `1-20` | 同一群中，昨日實際被烤次數達到此值後，今日普通烤群友會被阻擋；吃群友選目標時也尊重保護。 |
| `enable_ai_roast_copy` | bool | `false` | `true` / `false` | 嘗試用當前會話模型生成料理文案；不可用、超時或失敗時回退本地模板。 |
| `ai_generation_timeout_seconds` | float | `45` | `5-120` | AI 文案調用超時。超時不會阻塞整個烤豬流程，而是回退本地文案。 |

### AI 文案成本與節流

AI 烤豬文案預設關閉。啟用後，同一隻小豬同一天最多實際進行一次模型生成嘗試；成功文案會保留並在近七個自然日窗口內供後續復用。這可以避免熱門小豬被多人重複烤時反覆消耗模型 Token。

## 圖片卡片

| 配置鍵 | 類型 | 預設 | 有效值 | 說明 |
| --- | --- | --- | --- | --- |
| `image_theme` | string | `auto` | `auto` / `light` / `dark` | `auto` 在 19:00–06:59 使用深色夜間主題；其他值固定亮／暗主題。 |

主題時間使用插件的每日時區設定。

## 公共資源同步

| 配置鍵 | 類型 | 預設 | 有效值／範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `resource_sync_enabled` | bool | `true` | `true` / `false` | 是否自動同步公共小豬資源。關閉不會刪除已存在的本地快取。 |
| `resource_manifest_url` | string | `https://pig.felislab.cc/resources/rollpig/manifest.json` | HTTPS URL | 公共資源 manifest。程式會限制協議與網路目的地，避免不安全下載。 |
| `resource_sync_interval_hours` | float | `24` | `1-168` | 自動檢查公共資源的時間間隔。 |
| `resource_sync_timeout` | float | `30` | `2-120` | 資源網路連線超時秒數；圖片讀取會保留更寬裕的下限並帶重試。 |
| `resource_use_system_proxy` | bool | `false` | `true` / `false` | 是否讓 HTTP 客戶端信任系統代理環境。預設直連，避免失效代理造成 TLS 卡住。 |
| `resource_max_file_size_mb` | int | `10` | `1-50` | 單個資源檔大小上限（MiB）；也用於 PigHub 圖片導入限制。 |

### 自訂 manifest 的注意事項

雖然 `resource_manifest_url` 可配置，但它不是任意檔案下載器。插件仍會：

- 要求 HTTPS。
- 限制重定向與解析結果，拒絕不安全／私網目的地。
- 限制 manifest、資源包、單檔與圖片像素。
- 校驗 manifest 宣告的檔案大小與 SHA-256。
- 整包通過後才原子替換 active 資源。

如果同步失敗，插件會繼續使用既有快取或內置資源，不會先刪掉可用資料。

## 管理面板安全更新

| 配置鍵 | 類型 | 預設 | 有效值／範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `panel_update_enabled` | bool | `true` | `true` / `false` | 是否允許管理面板檢查／安裝官方穩定 Release。 |
| `panel_update_timeout` | float | `30` | `5-120` | 安全更新檢查與下載相關網路超時。 |

管理面板更新器只接受 `casama233/astrbot_plugin_rollpig` 的最新穩定 Release，不接受自訂 URL、任意分支或預發布版本。安裝完成後不會自動重啟 AstrBot。

## 資料存儲

| 配置鍵 | 類型 | 預設 | 有效值／範圍 | 說明 |
| --- | --- | --- | --- | --- |
| `storage_backend` | string | `auto` | `auto` / `sqlite` / `json` | `auto` 為推薦模式；新安裝直接使用 SQLite，舊 JSON 先備份、遷移與對帳。`json` 只建議災難回退。 |
| `storage_busy_timeout_ms` | int | `5000` | `1000-30000` | SQLite 遇到寫鎖時的等待時間，單位毫秒。 |

### `storage_backend` 模式

#### `auto`（推薦）

- 新安裝直接建立 SQLite。
- 舊 JSON 安裝會先備份，再匯入臨時 SQLite。
- 通過完整性、外鍵與事實級對帳後才原子切換。
- 若既有 SQLite 無效，會保留恢復證據並採取安全回退，而不是靜默覆蓋。

#### `sqlite`

明確要求 SQLite。若資料庫無效，程式仍以「資料安全優先」處理並避免把錯誤資料當成有效權威；不要把它理解成「無論如何都強制打開損壞 DB」。

#### `json`

保留給緊急災難回退。v3.0+ 的正常運行、統計與熱路徑都以規範化 SQLite 為主要設計目標，不建議長期把 `json` 當成預設模式。

## 推薦配置範例

### 一般群聊

```json
{
  "at_view_pig": false,
  "enable_new_pig_pity": true,
  "pity_step_percent": 15,
  "enable_roast": true,
  "enable_group_roast": true,
  "enable_group_eat": true,
  "eat_success_percent": 15,
  "eaten_next_day_failure_percent": 20,
  "group_roast_cooldown_hours": 8,
  "enable_roast_protection": true,
  "roast_protection_threshold": 3,
  "enable_ai_roast_copy": false,
  "image_theme": "auto",
  "timezone": "local",
  "storage_backend": "auto"
}
```

### 偏保守／低打擾群聊

```json
{
  "at_view_pig": false,
  "enable_roast": true,
  "enable_group_roast": false,
  "enable_group_eat": false,
  "enable_ai_roast_copy": false,
  "resource_sync_enabled": true,
  "storage_backend": "auto"
}
```

### 明確使用香港日界線

```json
{
  "timezone": "Asia/Hong_Kong"
}
```

## 配置變更後沒有生效？

依 AstrBot 當前插件配置機制，部分配置會在插件初始化時讀入。若修改後行為沒有變化，先在管理介面重新載入插件；若仍無效，再重啟 AstrBot。

進一步排查請看 [`OPERATIONS.md`](OPERATIONS.md)。
