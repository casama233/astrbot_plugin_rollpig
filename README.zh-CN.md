# 今日小猪 · 增强版 — AstrBot RollPig Plus

**简体中文** · [繁體中文](README.md) · [English](README.en.md)

`astrbot_plugin_rollpig_plus`：AstrBot 每日抽猪、永久猪籍、EX 成长和群聊后厨游戏。

当前源码版本 **v3.12.4**。**只有 GitHub 稳定版 Release、对应 tag、ZIP 和 SHA256SUMS 都建立后才算正式发布；合并 main 不等于已经可以更新。** [稳定下载](https://github.com/casama233/astrbot_plugin_rollpig/releases/latest) · [完整 Wiki](docs/index.md)

> [!CAUTION]
> 本插件代码由 AI 生成并经过人工审阅，仍可能存在缺陷与安全／兼容性风险。在重要账号、生产及敏感场景中部署前，请自行审查代码并测试。

> [!IMPORTANT]
> **来源与许可：** 直接上游是 [MegSopern/astrbot_plugin_rollpig](https://github.com/MegSopern/astrbot_plugin_rollpig)，更早来自 [Bearlele/nonebot-plugin-rollpig](https://github.com/Bearlele/nonebot-plugin-rollpig)。后续功能曾参考或移植 [Felis2026/nonebot-plugin-rollpig-plus](https://github.com/Felis2026/nonebot-plugin-rollpig-plus)。原始 MIT 署名、代码与第三方图片／文案的权利范围参见 [ATTRIBUTION.md](ATTRIBUTION.md)。不能将未核实来源的第三方图片或文字视为可自由再发布。

## 玩法

| 系统 | 内容 |
| --- | --- |
| 每日小猪 | 每人每日固定一只，重复查看不重新随机；昨天／明天／本周独立视图 |
| 永久猪籍 | `/我的豬圈` 保存解锁类型、再次获得次数、本命、EX 等级及退役记录 |
| EX 成长 | 第二次遇到同一只开始 EX；正式猪可在 Lv.1–5 使用不同文案和图片 |
| 新猪保底 | 连续重复加跨日疲劳提升条件性重抽机会，上限 **80%** |
| 群聊后厨 | 烤自己／群友、随机烤、吃群友、次日保护与反噬 |
| Roast Charge | 每人每群单独存储，默认 **2 格**，逐格恢复 |
| 预约和添柴 | 目标尚未抽猪时可预约；`/添柴 @目标` 明确参与 |
| 烤箱补货 | `/烤箱補貨` 发起，全群活跃玩家参与，达标最多恢复缺少的 1 格 |
| 猪圈日报 | 记录烧烤、逃脱、反噬、被吃和称号；手动只读，自动推送需群独立选择加入 |
| 创作者后厨 | 本地猪、EX 差分、私人猪源及公共源人工审核 |

## 安装

| 项目 | 要求 |
| --- | --- |
| AstrBot | **4.26.0+** |
| Python | **3.10+** |
| 依赖 | `Pillow >=10.0.0`、`httpx >=0.27.0,<1.0.0` |
| 插件身份 | **`astrbot_plugin_rollpig_plus`** |

可以在 AstrBot 插件市场搜索「今日小猪 · 增强版」或手动安装：

```bash
cd /AstrBot/data/plugins
git clone https://github.com/casama233/astrbot_plugin_rollpig astrbot_plugin_rollpig_plus
```

重启 AstrBot，确认载入身份是 `astrbot_plugin_rollpig_plus`。**v3.2.0 起使用独立配置／数据命名空间，不能把新版覆盖到旧 `astrbot_plugin_rollpig` 文件夹。** 升级／迁移参见 [OPERATIONS.md](docs/OPERATIONS.md)。

## 常用指令

| 原始指令 | 意义 |
| --- | --- |
| `/今日小豬` | 今天抽猪 |
| `/豬豬幫助` | 查看当前实例真正启用的玩法 |
| `/我的豬圈 [頁碼]` | 查看永久猪籍 |
| `/找豬 關鍵詞` | 搜索 ID、名称、描述或故事文案 |
| `/烤群友 @某人` | 尝试烤群友 |
| `/烤箱補貨` | 发起群体补货 |
| `/添柴` | 根据正在进行的补货或预约自动分流 |
| `/添柴 @某人` | 加入指定目标的预约 |
| `/豬圈日報` | 手动查看日报 |

部分命令提供繁简别名；**请以 [命令百科](docs/COMMANDS.md) 和运行时 `/豬豬幫助` 为准**。本翻译不新增命令别名。

## 永久猪籍、EX 和抽取

`/我的豬圈` 反映历史真正拥有过的猪，而不只是当前资源池。已退役但曾拥有的猪可以保留记录，管理员明确屏蔽的内容仍会隐藏。图鉴显示当前进度、退役保存、最多返场、最高 EX 和未知猪。规则见[永久图鉴与保底](docs/gameplay/collection-pity.md)及[EX 成长](docs/gameplay/ex-growth.md)。

## 后厨与 Roast Charge

1. **Charge 决定能否尝试烧烤。** 每人每群默认 2 格，`group_roast_cooldown_hours` 是**每格缺失能量的恢复时间**，默认 **8 小时**，不是整个人的单个冷却。
2. **70/20/10 的实际结果概率：** 成功 **70%**，逃脱 **20%**，反噬 **10%**。由 `services/roast_service.py` 的共享权重确定；预约／添柴不会增加成功率。
3. **`/添柴` 按上下文路由。** 补货进行时参与补货；`/添柴 @目标` 加入该预约；只有一张预约且无补货时可使用不带目标的形式，多张则要求指定目标。

旧 `/添煤`、`/加煤`、`/烤箱添煤`、`/烤箱添柴` 仅为兼容入口，不再建议作为主要指令。规则见 [Charge](docs/gameplay/roast-charge.md)、[结果权重](docs/gameplay/roast-outcomes.md)及[预约](docs/ROAST-RESERVATIONS.md)。

## 日报

手动 `/豬圈日報` 只读。自动日报有总开关，**每个群仍须明确 opt-in**；不会仅因曾使用插件就自动推送。可选「今日祭品」默认关闭，并且只在自动日报流程可能触发。详见[日报玩家页](docs/gameplay/daily-report.md)。

## 管理面板、资源与安全

AstrBot Plugin Page 工作台包含数据总览、猪图鉴编辑、EX 1–5 文案与图片、本地素材、公共投稿审核、资源源同步、SQLite／JSON 数据维护及经验证的稳定版更新。

资源合成顺序：**内置／AstrBot v1／私人 manifest 基础层 → 本地新增和覆盖 → 删除屏蔽 → 最终图鉴**。同步基础层不得覆盖管理员的本地创作。默认 manifest 为 `https://curryudon.top/astrbot-rollpig/v1/manifest.json`；403 可能只是客户端协议检查，**不代表强安全认证**，真正私有源需自己的 Token／mTLS。

公开投稿只在管理员确认后提交猪 ID、名称、文案、图片及 EX 变体；**不上传群聊原文、群号、数据库、备份或插件配置**。图片及文案仍受各自版权约束。

主数据使用 SQLite，JSON 为导出／灾难回滚。下载通过 manifest、大小、SHA-256 和图片检查后才原子切换，失败保留可用旧数据。身份迁移采用 **Copy → Verify → Atomic Commit**，不把未经证实同一人的群聊身份强行合并。参见 [OPERATIONS.md](docs/OPERATIONS.md) 和 [COLLECTION-IDENTITY.md](docs/COLLECTION-IDENTITY.md)。

## 常用配置

`enable_new_pig_pity`、`pity_step_percent`、`enable_daily_duplicate_pity`、`group_roast_max_charges`（默认 2）、`group_roast_cooldown_hours`（每格恢复，默认 8 小时）、`enable_roast_reservation`、`roast_reservation_max_participants`、`enable_oven_refill`、`oven_refill_*`、`enable_daily_report`、`daily_report_*`、`resource_sync_enabled`、`resource_manifest_url`、`storage_backend`。完整配置：[CONFIGURATION.md](docs/CONFIGURATION.md)。

## 文档、开发与授权

[30 秒开始](docs/getting-started/index.md) · [玩家玩法](docs/gameplay/index.md) · [命令百科](docs/COMMANDS.md) · [创作者](docs/creators/index.md) · [资源管理](docs/RESOURCE-MANAGEMENT.md) · [运维](docs/OPERATIONS.md) · [架构](docs/ARCHITECTURE.md)。

```bash
python -m pip install -r requirements.txt pytest pre-commit
python -m compileall -q main.py legacy_main.py storage services renderers
pytest -q
pre-commit run --all-files --show-diff-on-failure
```

发布流程另检查真实 AstrBot 加载、Marketplace 包、Wiki strict build 及资源源规则。代码为 [MIT](LICENSE)；**第三方图片、文案和数据并不自动拥有相同再分发权**，详见 [ATTRIBUTION.md](ATTRIBUTION.md)。
